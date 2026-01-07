import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import List, Dict
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

JPLATPAT_URL = "https://www.j-platpat.inpit.go.jp/s0100"


def _clean_text(element) -> str:
    if not element:
        return ""
    text = element.inner_text().strip()
    return " ".join(text.split())


def _extract_abstract(detail_page, timeout_ms: int = 5000) -> str:
    """
    Extract abstract (要約) from patent detail page.
    """
    detail_page.wait_for_timeout(3000)
    body_text = detail_page.inner_text('body')
    
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


def _extract_rows(page, context, limit: int = 50, fetch_abstract: bool = True) -> List[Dict[str, str]]:
    """
    Extract rows from 簡易書誌 (Simple Bibliography) view table.
    Table ID: patentUtltyIntnlSimpleBibLst
    Columns: No., 文献番号, 出願番号, 出願日, 公知日, 発明の名称, 出願人/権利者, ステータス, FI, 各種機能
    """
    rows = page.query_selector_all("table#patentUtltyIntnlSimpleBibLst tbody tr")
    results: List[Dict[str, str]] = []
    
    for idx, row in enumerate(rows[:limit]):
        cells = row.query_selector_all("td")
        
        # No.
        number = _clean_text(row.query_selector("th[scope='row'] p"))
        
        # 文献番号 (Document Number) - usually has a link
        doc_num_el = cells[0].query_selector("a") if len(cells) > 0 else None
        doc_num = _clean_text(doc_num_el) if doc_num_el else _clean_text(cells[0]) if len(cells) > 0 else ""
        
        # 出願番号 (Application Number)
        app_num = _clean_text(cells[1]) if len(cells) > 1 else ""
        
        # 出願日 (Application Date)
        app_date = _clean_text(cells[2]) if len(cells) > 2 else ""
        
        # 公知日 (Publication Date)
        pub_date = _clean_text(cells[3]) if len(cells) > 3 else ""
        
        # 発明の名称 (Invention Title)
        invention_title = _clean_text(cells[4]) if len(cells) > 4 else ""
        
        # 出願人/権利者 (Applicant/Rights Holder)
        applicant = _clean_text(cells[5]) if len(cells) > 5 else ""
        
        # ステータス (Status) - may have multiple labels
        status_labels = cells[6].query_selector_all("label") if len(cells) > 6 else []
        status = " / ".join([_clean_text(label) for label in status_labels if _clean_text(label)])
        if not status and len(cells) > 6:
            status = _clean_text(cells[6])
        
        # FI (Classification) - may have multiple links
        fi_links = cells[7].query_selector_all("a") if len(cells) > 7 else []
        fi_codes = [_clean_text(link) for link in fi_links if _clean_text(link)]
        
        # 各種機能 (Various Functions) - action buttons
        action_links = cells[8].query_selector_all("a") if len(cells) > 8 else []
        actions = [_clean_text(link) for link in action_links if _clean_text(link)]
        
        # Get document URL by clicking URL button
        doc_url = ""
        url_btn = row.query_selector(f"a[id='patentUtltyIntnlSimpleBibLst_tableView_url{idx}']")
        if url_btn:
            url_btn.click()
            page.wait_for_timeout(800)
            # Find the dialog and extract URL
            dialog = page.query_selector(".mat-dialog-container, [role='dialog']")
            if dialog:
                dialog_text = dialog.inner_text()
                # Extract URL from dialog text (format: https://www.j-platpat.inpit.go.jp/...)
                url_match = re.search(r'(https://www\.j-platpat\.inpit\.go\.jp/[^\s]+)', dialog_text)
                if url_match:
                    doc_url = url_match.group(1)
                # Close the dialog by pressing Escape or clicking close button
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
        
        # Get abstract by clicking document link and opening detail page
        abstract = ""
        if fetch_abstract and doc_num_el:
            try:
                with context.expect_page() as new_page_info:
                    doc_num_el.click()
                detail_page = new_page_info.value
                detail_page.wait_for_load_state('domcontentloaded')
                abstract = _extract_abstract(detail_page)
                detail_page.close()
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


def search_jplatpat(query: str, headless: bool = True, row_limit: int = 50, timeout_ms: int = 20000, fetch_abstract: bool = True) -> Dict[str, object]:
    launch_args = ["--no-sandbox", "--disable-dev-shm-usage"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=launch_args)
        context = browser.new_context(locale="ja-JP", user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()

        try:
            page.goto(JPLATPAT_URL, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_selector("input#s01_srchCondtn_txtSimpleSearch", timeout=timeout_ms)
            page.fill("input#s01_srchCondtn_txtSimpleSearch", query)

            # Click the search button instead of pressing Enter
            page.click("a#s01_srchBtn_btnSearch")

            # Wait for results to render - use fixed timeout as the SPA can be unreliable with selectors
            page.wait_for_timeout(5000)

            message = ""
            msg_el = page.query_selector("#patentUtltyIntnlDocLst_searchResultMsg")
            if msg_el:
                message = _clean_text(msg_el)

            rows = _extract_rows(page, context, limit=row_limit, fetch_abstract=fetch_abstract)
            return {
                "query": query,
                "message": message,
                "count": len(rows),
                "rows": rows,
            }
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"Timed out waiting for page elements: {exc}") from exc
        finally:
            context.close()
            browser.close()


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Search j-platpat and return result table as JSON")
    parser.add_argument("query", help="Search string to input into the simple search box")
    parser.add_argument("--headful", action="store_true", help="Run browser in headful mode for debugging")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of rows to return")
    parser.add_argument("--timeout", type=int, default=20000, help="Timeout in milliseconds for page waits")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file path. If not specified, auto-generates filename with timestamp.")
    parser.add_argument("--no-abstract", action="store_false", dest="abstract", help="Disable fetching abstract (要約) for each patent. By default, abstract is fetched.")
    args = parser.parse_args(argv)

    try:
        data = search_jplatpat(args.query, headless=not args.headful, row_limit=args.limit, timeout_ms=args.timeout, fetch_abstract=args.abstract)
        
        # Determine output filename
        if args.output:
            output_path = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"jplatpat_result_{timestamp}.json"
        
        # Save to JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"结果已保存到: {output_path}")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
