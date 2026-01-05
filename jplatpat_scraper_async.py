import re
from typing import List, Dict
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

JPLATPAT_URL = "https://www.j-platpat.inpit.go.jp/s0100"


async def _clean_text(element) -> str:
    if not element:
        return ""
    text = (await element.inner_text()).strip()
    return " ".join(text.split())


async def _extract_abstract(detail_page, timeout_ms: int = 5000) -> str:
    """
    Extract abstract (要約) from patent detail page.
    """
    await detail_page.wait_for_timeout(3000)
    body_text = await detail_page.inner_text('body')
    
    # Extract 【要約】 section - usually after (57)
    abstract = ""
    if '(57)【要約】' in body_text:
        start = body_text.find('(57)【要約】')
        # Find the end of abstract section
        end_markers = ['【特許請求の範囲】', '【図面', '【図１', '【図 1', '【発明の詳細な説明】', '請求の範囲', '詳細な説明']
        end = len(body_text)
        for marker in end_markers:
            pos = body_text.find(marker, start + 10)
            if pos != -1 and pos < end:
                end = pos
        
        abstract = body_text[start:end].strip()
        # Clean up the abstract text
        abstract = abstract.replace('(57)【要約】', '').strip()
    elif '【要約】' in body_text:
        start = body_text.find('【要約】')
        end_markers = ['【特許請求の範囲】', '【図面', '【図１', '【発明の詳細な説明】', '請求の範囲']
        end = len(body_text)
        for marker in end_markers:
            pos = body_text.find(marker, start + 5)
            if pos != -1 and pos < end:
                end = pos
        abstract = body_text[start:end].strip()
        abstract = abstract.replace('【要約】', '').strip()
    
    return abstract


async def _extract_rows(page, context, limit: int = 50, fetch_abstract: bool = True) -> List[Dict[str, str]]:
    """
    Extract rows from 簡易書誌 (Simple Bibliography) view table.
    Table ID: patentUtltyIntnlSimpleBibLst
    Columns: No., 文献番号, 出願番号, 出願日, 公知日, 発明の名称, 出願人/権利者, ステータス, FI, 各種機能
    """
    rows = await page.query_selector_all("table#patentUtltyIntnlSimpleBibLst tbody tr")
    results: List[Dict[str, str]] = []
    
    for idx, row in enumerate(rows[:limit]):
        cells = await row.query_selector_all("td")
        
        # No.
        number = await _clean_text(await row.query_selector("th[scope='row'] p"))
        
        # 文献番号 (Document Number) - usually has a link
        doc_num_el = await cells[0].query_selector("a") if len(cells) > 0 else None
        doc_num = await _clean_text(doc_num_el) if doc_num_el else await _clean_text(cells[0]) if len(cells) > 0 else ""
        
        # 出願番号 (Application Number)
        app_num = await _clean_text(cells[1]) if len(cells) > 1 else ""
        
        # 出願日 (Application Date)
        app_date = await _clean_text(cells[2]) if len(cells) > 2 else ""
        
        # 公知日 (Publication Date)
        pub_date = await _clean_text(cells[3]) if len(cells) > 3 else ""
        
        # 発明の名称 (Invention Title)
        invention_title = await _clean_text(cells[4]) if len(cells) > 4 else ""
        
        # 出願人/権利者 (Applicant/Rights Holder)
        applicant = await _clean_text(cells[5]) if len(cells) > 5 else ""
        
        # ステータス (Status) - may have multiple labels
        status_labels = await cells[6].query_selector_all("label") if len(cells) > 6 else []
        status_parts = []
        for label in status_labels:
            clean = await _clean_text(label)
            if clean:
                status_parts.append(clean)
        status = " / ".join(status_parts)
        if not status and len(cells) > 6:
            status = await _clean_text(cells[6])
        
        # FI (Classification) - may have multiple links
        fi_links = await cells[7].query_selector_all("a") if len(cells) > 7 else []
        fi_codes = []
        for link in fi_links:
            clean = await _clean_text(link)
            if clean:
                fi_codes.append(clean)
        
        # 各種機能 (Various Functions) - action buttons
        action_links = await cells[8].query_selector_all("a") if len(cells) > 8 else []
        actions = []
        for link in action_links:
            clean = await _clean_text(link)
            if clean:
                actions.append(clean)
        
        # Get document URL by clicking URL button
        doc_url = ""
        url_btn = await row.query_selector(f"a[id='patentUtltyIntnlSimpleBibLst_tableView_url{idx}']")
        if url_btn:
            await url_btn.click()
            await page.wait_for_timeout(800)
            # Find the dialog and extract URL
            dialog = await page.query_selector(".mat-dialog-container, [role='dialog']")
            if dialog:
                dialog_text = await dialog.inner_text()
                # Extract URL from dialog text (format: https://www.j-platpat.inpit.go.jp/...)
                url_match = re.search(r'(https://www\.j-platpat\.inpit\.go\.jp/[^\s]+)', dialog_text)
                if url_match:
                    doc_url = url_match.group(1)
                # Close the dialog by pressing Escape or clicking close button
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
        
        # Get abstract by clicking document link and opening detail page
        abstract = ""
        if fetch_abstract and doc_num_el:
            try:
                async with context.expect_page() as new_page_info:
                    await doc_num_el.click()
                detail_page = await new_page_info.value
                await detail_page.wait_for_load_state('domcontentloaded')
                abstract = await _extract_abstract(detail_page)
                await detail_page.close()
            except Exception as e:
                abstract = f"Error: {str(e)}"
        
        results.append({
            "no": number,
            "document_number": doc_num,
            "document_url": doc_url,
            "abstract": abstract,
            "application_number": app_num,
            "application_date": app_date,
            "publication_date": pub_date,
            "invention_title": invention_title,
            "applicant": applicant,
            "status": status,
            "fi_codes": fi_codes,
            "actions": actions,
        })
    
    return results


async def search_jplatpat_async(query: str, headless: bool = True, row_limit: int = 50, timeout_ms: int = 20000, fetch_abstract: bool = True) -> Dict[str, object]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(locale="ja-JP", user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()

        try:
            await page.goto(JPLATPAT_URL, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_selector("input#s01_srchCondtn_txtSimpleSearch", timeout=timeout_ms)
            await page.fill("input#s01_srchCondtn_txtSimpleSearch", query)

            # Click the search button instead of pressing Enter
            await page.click("a#s01_srchBtn_btnSearch")

            # Wait for results to render - use fixed timeout as the SPA can be unreliable with selectors
            await page.wait_for_timeout(5000)

            message = ""
            msg_el = await page.query_selector("#patentUtltyIntnlDocLst_searchResultMsg")
            if msg_el:
                message = await _clean_text(msg_el)

            rows = await _extract_rows(page, context, limit=row_limit, fetch_abstract=fetch_abstract)
            return {
                "query": query,
                "message": message,
                "count": len(rows),
                "rows": rows,
            }
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"Timed out waiting for page elements: {exc}") from exc
        finally:
            await context.close()
            await browser.close()
