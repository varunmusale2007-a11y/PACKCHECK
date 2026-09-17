# Packaged Commodity Legal Metrology Compliance Checker

AI-powered Legal Metrology (Packaged Commodities) Rules compliance verification system with strictly isolated OCR extraction and audit logging.

## Fixed Stale Data / OCR Reuse Bug

### Backend Fixes Applied:
1. **`POST /upload`**: Inserts a new row with a distinct `scan_id` and saves the file isolated per scan.
2. **`POST /ocr/{scan_id}`**: Executes OCR on that scan's image only and updates strictly `WHERE id = scan_id`.
3. **`POST /check/{scan_id}`**: Reads OCR text exclusively from `scan_id` and evaluates mandatory Legal Metrology declarations (MRP, Net Quantity, Manufacturer details, Date of Manufacture, Consumer Care details, Country of Origin, Unit Sale Price).
4. **Zero Global Cache / Unscoped Queries**: Removed any `LIMIT 1` or `first()` or global variables. Every operation requires `scan_id`.
5. **Real-Time Request Logging**: Detailed audit logs emitted for each request containing `scan_id`, filename, OCR text preview, and compliance score.
6. **Anti-Caching Response Headers**: Every response enforces `Cache-Control: no-cache, no-store, must-revalidate, max-age=0`, `Pragma: no-cache`, and `Expires: 0`.

### Frontend Fixes Applied:
1. **Scan ID State Management**: Stores the returned `scan_id` from `/upload` in application state.
2. **Dynamic Endpoint Invocation**: Calls `/ocr/${scan_id}` and `/check/${scan_id}` with the active `scan_id`.
3. **Dynamic Report Routing**: Opens `/report/${scan_id}` (or routes to `/report/{scan_id}`) rather than a static page.
4. **Anti-Caching Fetch**: Attaches timestamp query parameter `?_t=${Date.now()}` and HTTP headers on all API requests.


## Running the Application
Open https://ketannemade5-ui.github.io/Project/ in your browser.
