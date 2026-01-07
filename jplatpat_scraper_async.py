import re
import asyncio
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

JPLATPAT_URL = "https://www.j-platpat.inpit.go.jp/s0100"

# Cache for abstracts to avoid re-fetching
_abstract_cache: Dict[str, str] = {}


async def _clean_text(element) -> str:
    if not element:
        return ""
    text = (await element.inner_text()).strip()
    return " ".join(text.split())


async def _extract_abstract(detail_page, timeout_ms: int = 1000) -> str:
    """
    Extract abstract (要約) from patent detail page.
    Ultra-fast extraction - fail at 500ms.
    """
    try:
        # Just try to read body immediately without waiting
        body_text = await asyncio.wait_for(
            detail_page.inner_text('body'),
            timeout=0.5
        )
    except (asyncio.TimeoutError, Exception):
        return ""
    
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


async def _fetch_abstract_for_row(context, doc_num_el, doc_num: str, idx: int, page, semaphore: asyncio.Semaphore) -> Optional[str]:
    """
    Fetch abstract - ultra aggressive timeout.
    Total time: max 1 second from click to extract.
    """
    if not doc_num_el:
        return ""
    
    # Check cache first
    if doc_num in _abstract_cache:
        return _abstract_cache[doc_num]
    
    async with semaphore:  # Limit concurrent page opens (max 4 simultaneous)
        try:
            async with context.expect_page() as new_page_info:
                await doc_num_el.click()
            
            # Wait for page with 0.8s timeout
            detail_page = await asyncio.wait_for(
                new_page_info.value,
                timeout=0.8
            )
            
            # Don't wait for page load - extract immediately
            abstract = await _extract_abstract(detail_page, timeout_ms=500)
            await detail_page.close()
            
            # Cache the result
            if abstract:
                _abstract_cache[doc_num] = abstract
            return abstract
        except Exception:
            return ""


async def _extract_rows(page, context, limit: int = 50, fetch_abstract: bool = True) -> List[Dict[str, str]]:
    """
    Extract rows from 簡易書誌 (Simple Bibliography) view table.
    Table ID: patentUtltyIntnlSimpleBibLst
    Columns: No., 文献番号, 出願番号, 出願日, 公知日, 発明の名称, 出願人/権利者, ステータス, FI, 各種機能
    """
    rows = await page.query_selector_all("table#patentUtltyIntnlSimpleBibLst tbody tr")
    results: List[Dict[str, str]] = []
    abstract_tasks = []  # Store tasks for parallel abstract fetching
    
    # Create semaphore to limit concurrent page opens (max 4 simultaneous)
    semaphore = asyncio.Semaphore(4)
    
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
        
        # FI (Classification) - skip for speed (rarely used)
        fi_codes = []
        # Uncomment below if FI codes are needed, but it adds ~50ms per row
        # fi_links = await cells[7].query_selector_all("a") if len(cells) > 7 else []
        # fi_codes = []
        # for link in fi_links:
        #     clean = await _clean_text(link)
        #     if clean:
        #         fi_codes.append(clean)
        
        # 各種機能 (Various Functions) - skip for speed
        actions = []
        # Uncomment below if action buttons are needed
        # action_links = await cells[8].query_selector_all("a") if len(cells) > 8 else []
        # actions = []
        # for link in action_links:
        #     clean = await _clean_text(link)
        #     if clean:
        #         actions.append(clean)
        
        # Get document URL by clicking URL button (with reduced timeout)
        doc_url = ""
        # SKIP URL fetching - too slow (dialog wait + click)
        # If needed in future, uncomment below, but it adds 300-500ms per row
        # url_btn = await row.query_selector(f"a[id='patentUtltyIntnlSimpleBibLst_tableView_url{idx}']")
        # if url_btn:
        #     try:
        #         await url_btn.click()
        #         await page.wait_for_timeout(300)
        #         dialog = await page.query_selector(".mat-dialog-container, [role='dialog']")
        #         if dialog:
        #             dialog_text = await dialog.inner_text()
        #             url_match = re.search(r'(https://www\.j-platpat\.inpit\.go\.jp/[^\s]+)', dialog_text)
        #             if url_match:
        #                 doc_url = url_match.group(1)
        #             await page.keyboard.press("Escape")
        #             await page.wait_for_timeout(100)
        #     except Exception:
        #         pass
        
        # Get abstract by clicking document link and opening detail page
        abstract_task = None
        if fetch_abstract and doc_num_el:
            abstract_task = _fetch_abstract_for_row(context, doc_num_el, doc_num, idx, page, semaphore)
            abstract_tasks.append(abstract_task)
        else:
            abstract_tasks.append(asyncio.sleep(0))  # Placeholder for consistent indexing
        
        results.append({
            "no": number,
            "document_number": doc_num,
            "document_url": doc_url,
            "abstract": "",  # Placeholder, will be filled after parallel fetch
            "application_number": app_num,
            "application_date": app_date,
            "publication_date": pub_date,
            "invention_title": invention_title,
            "applicant": applicant,
            "status": status,
            "fi_codes": fi_codes,
            "actions": actions,
        })
    
    # Execute all abstract fetching tasks in parallel
    if abstract_tasks:
        abstracts = await asyncio.gather(*abstract_tasks, return_exceptions=True)
        for idx, abstract in enumerate(abstracts):
            if isinstance(abstract, str):
                results[idx]["abstract"] = abstract
    
    return results


async def search_jplatpat_async(query: str, headless: bool = True, row_limit: int = 50, timeout_ms: int = 20000, fetch_abstract: bool = True) -> Dict[str, object]:
    launch_args = ["--no-sandbox", "--disable-dev-shm-usage"]
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=launch_args)
        context = await browser.new_context(locale="ja-JP", user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()

        try:
            await page.goto(JPLATPAT_URL, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_selector("input#s01_srchCondtn_txtSimpleSearch", timeout=timeout_ms)
            await page.fill("input#s01_srchCondtn_txtSimpleSearch", query)

            # Click the search button instead of pressing Enter
            await page.click("a#s01_srchBtn_btnSearch")

            # Wait for results table with aggressive timeout
            try:
                await asyncio.wait_for(
                    page.wait_for_selector("table#patentUtltyIntnlSimpleBibLst tbody tr"),
                    timeout=8.0
                )
            except (asyncio.TimeoutError, PlaywrightTimeoutError, Exception):
                # If table doesn't appear, wait minimally and continue
                await page.wait_for_timeout(1000)

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
