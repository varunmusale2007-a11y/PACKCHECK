import os
import sys
import logging
import uuid
from typing import Optional

# Setup high-visibility request logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [ScanID: %(scan_id)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

class ScanLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        scan_id = self.extra.get("scan_id", "-")
        return f"[scan_id={scan_id}] {msg}", kwargs

base_logger = logging.getLogger("compliance_checker")
logger = ScanLoggerAdapter(base_logger, {"scan_id": "-"})

from database import (
    init_db,
    insert_scan_record,
    update_ocr_text,
    update_compliance_result,
    get_scan_by_id,
    get_all_scans
)
from ocr_engine import extract_ocr_text
from compliance import evaluate_compliance

# Initialize Database schema
init_db()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Frontend")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def handle_upload(filename: str, file_bytes: bytes, commodity_type: str = "Packaged Commodity"):
    """
    Step 1: /upload must INSERT a new row and return scan_id.
    Strictly isolated: Generates a unique file path, inserts new DB row, returns scan_id.
    """
    unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    save_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    scan_id = insert_scan_record(filename=filename, image_path=save_path, commodity_type=commodity_type)
    
    # Requirement 5: Log scan_id and filename
    logger.info(
        f"UPLOAD COMPLETED | scan_id={scan_id} | filename='{filename}' | saved_to='{save_path}'",
        extra={"scan_id": scan_id}
    )
    
    return {
        "success": True,
        "scan_id": scan_id,
        "filename": filename,
        "status": "UPLOADED",
        "message": f"Commodity image uploaded successfully with scan_id {scan_id}"
    }

def handle_ocr(scan_id: int):
    """
    Step 2: /ocr/{scan_id} must run EasyOCR on that image and UPDATE only scan_records.id = scan_id.
    Step 4: NO LIMIT 1, NO first(), NO global variable, NO cached OCR result.
    """
    record = get_scan_by_id(scan_id)
    if not record:
        logger.error(f"OCR FAILED | scan_id={scan_id} NOT FOUND", extra={"scan_id": scan_id})
        return {"error": f"Scan ID {scan_id} not found", "status_code": 404}

    image_path = record["image_path"]
    filename = record["filename"]

    # Run OCR strictly for this record's image
    ocr_text = extract_ocr_text(image_path, filename)
    
    # Update strictly WHERE id = scan_id
    update_ocr_text(scan_id=scan_id, ocr_text=ocr_text)

    # Preview of extracted OCR text (first 100 characters cleaned)
    preview = ocr_text.replace("\n", " ")[:100] + "..." if len(ocr_text) > 100 else ocr_text.replace("\n", " ")

    # Requirement 5: Log scan_id, filename, OCR text preview
    logger.info(
        f"OCR COMPLETED | scan_id={scan_id} | filename='{filename}' | ocr_preview='{preview}'",
        extra={"scan_id": scan_id}
    )

    return {
        "success": True,
        "scan_id": scan_id,
        "filename": filename,
        "ocr_text": ocr_text,
        "ocr_preview": preview,
        "status": "OCR_COMPLETED"
    }

def handle_check(scan_id: int):
    """
    Step 3: /check/{scan_id} must read OCR text only from that scan_id.
    Step 4: Strict query WHERE id = scan_id, no LIMIT 1, no cached result.
    """
    record = get_scan_by_id(scan_id)
    if not record:
        logger.error(f"CHECK FAILED | scan_id={scan_id} NOT FOUND", extra={"scan_id": scan_id})
        return {"error": f"Scan ID {scan_id} not found", "status_code": 404}

    ocr_text = record.get("ocr_text")
    if not ocr_text:
        logger.warning(f"CHECK WARNING | scan_id={scan_id} has no OCR text yet", extra={"scan_id": scan_id})
        return {"error": f"No OCR text found for scan_id {scan_id}. Please run /ocr/{scan_id} first.", "status_code": 400}

    filename = record["filename"]
    
    # Run compliance evaluation strictly on this scan's OCR text
    result = evaluate_compliance(ocr_text)
    
    # Update strictly for scan_records.id = scan_id
    update_compliance_result(
        scan_id=scan_id,
        score=result["score"],
        status=result["status"],
        rule_results=result
    )

    preview = ocr_text.replace("\n", " ")[:80] + "..." if len(ocr_text) > 80 else ocr_text.replace("\n", " ")

    # Requirement 5: Log scan_id, filename, OCR text preview, and compliance score
    logger.info(
        f"COMPLIANCE EVALUATED | scan_id={scan_id} | filename='{filename}' | score={result['score']}% | status={result['status']} | ocr_preview='{preview}'",
        extra={"scan_id": scan_id}
    )

    return {
        "success": True,
        "scan_id": scan_id,
        "filename": filename,
        "compliance_score": result["score"],
        "compliance_status": result["status"],
        "rule_results": result,
        "ocr_text": ocr_text,
        "status": "CHECK_COMPLETED"
    }

def handle_report(scan_id: int):
    """
    Step 3: /report/{scan_id} returns the full compliance report scoped strictly to scan_id.
    """
    record = get_scan_by_id(scan_id)
    if not record:
        return {"error": f"Report for scan_id {scan_id} not found", "status_code": 404}

    return {
        "success": True,
        "scan_id": record["id"],
        "filename": record["filename"],
        "commodity_type": record["commodity_type"],
        "ocr_text": record["ocr_text"],
        "compliance_score": record["compliance_score"],
        "compliance_status": record["compliance_status"],
        "rule_results": record["rule_results"],
        "status": record["status"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"]
    }

# FastAPI implementation if FastAPI is available
try:
    from fastapi import FastAPI, UploadFile, File, Form, Response, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles

    fastapi_app = FastAPI(title="Packaged Commodity Legal Metrology Compliance Checker")

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def anti_cache_headers(response: Response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    @fastapi_app.post("/upload")
    async def upload_endpoint(request: Request, response: Response):
        anti_cache_headers(response)
        content_type = request.headers.get("content-type", "")
        
        if "multipart/form-data" in content_type:
            form = await request.form()
            file_obj = form.get("file")
            commodity_type = form.get("commodity_type", "Packaged Commodity")
            if file_obj and hasattr(file_obj, "read"):
                filename = getattr(file_obj, "filename", "uploaded_commodity.jpg")
                contents = await file_obj.read()
            else:
                filename = "uploaded_commodity.jpg"
                contents = b""
            return handle_upload(filename=filename, file_bytes=contents, commodity_type=str(commodity_type))
        elif "application/json" in content_type:
            try:
                data = await request.json()
            except Exception:
                data = {}
            filename = data.get("filename", "uploaded_commodity.jpg")
            commodity_type = data.get("commodity_type", "Packaged Commodity")
            return handle_upload(filename=filename, file_bytes=b"", commodity_type=str(commodity_type))
        else:
            return handle_upload(filename="uploaded_commodity.jpg", file_bytes=b"", commodity_type="Packaged Commodity")

    @fastapi_app.post("/ocr/{scan_id}")
    async def ocr_endpoint(scan_id: int, response: Response):
        anti_cache_headers(response)
        res = handle_ocr(scan_id)
        if "error" in res:
            return JSONResponse(status_code=res.get("status_code", 400), content=res)
        return res

    @fastapi_app.post("/check/{scan_id}")
    async def check_endpoint(scan_id: int, response: Response):
        anti_cache_headers(response)
        res = handle_check(scan_id)
        if "error" in res:
            return JSONResponse(status_code=res.get("status_code", 400), content=res)
        return res

    @fastapi_app.get("/report/{scan_id}")
    async def report_web_endpoint(scan_id: int, request: Request, response: Response):
        anti_cache_headers(response)
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            index_path = os.path.join(FRONTEND_DIR, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path, media_type="text/html")
        res = handle_report(scan_id)
        if "error" in res:
            return JSONResponse(status_code=res.get("status_code", 404), content=res)
        return res

    @fastapi_app.get("/api/report/{scan_id}")
    async def report_api_endpoint(scan_id: int, response: Response):
        anti_cache_headers(response)
        res = handle_report(scan_id)
        if "error" in res:
            return JSONResponse(status_code=res.get("status_code", 404), content=res)
        return res

    @fastapi_app.get("/api/scans")
    async def scans_list_endpoint(response: Response):
        anti_cache_headers(response)
        return {"scans": get_all_scans()}

    @fastapi_app.get("/styles.css")
    async def styles_alias():
        style_path = os.path.join(FRONTEND_DIR, "style.css")
        if os.path.exists(style_path):
            return FileResponse(style_path, media_type="text/css")
        return JSONResponse(status_code=404, content={"error": "Not Found"})

    # Mount static Frontend directory
    if os.path.exists(FRONTEND_DIR):
        fastapi_app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

except ImportError:
    pass

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print(" Packaged Commodity Legal Metrology Compliance Checker")
    print(" Direct Web App URL: http://127.0.0.1:8000")
    print("=" * 60)
    uvicorn.run("app:fastapi_app", host="127.0.0.1", port=8000, reload=False)