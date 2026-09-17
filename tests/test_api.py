import urllib.request
import json
import mimetypes

API_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=== Testing Packaged Commodity Compliance Checker API ===")

    # 1. Test Static files
    print("\n1. Testing Frontend Static Files...")
    html = urllib.request.urlopen(f"{API_URL}/").read().decode("utf-8")
    assert "<title>" in html, "HTML title tag not found"
    print("   [PASS] GET / -> index.html served correctly")

    css = urllib.request.urlopen(f"{API_URL}/style.css").read().decode("utf-8")
    assert ":root" in css, "CSS :root not found"
    print("   [PASS] GET /style.css -> style.css loaded")

    js = urllib.request.urlopen(f"{API_URL}/app.js").read().decode("utf-8")
    assert "startScanPipeline" in js, "JS startScanPipeline not found"
    print("   [PASS] GET /app.js -> app.js loaded")

    # 2. Test Preset Commodity JSON Upload
    print("\n2. Testing POST /upload with Preset Commodity...")
    payload = {
        "filename": "aashirvaad_superior_atta_5kg.jpg",
        "commodity_type": "Food Grain / Flour"
    }
    req = urllib.request.Request(
        f"{API_URL}/upload",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    upload_res = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
    assert upload_res.get("success") is True, f"Upload failed: {upload_res}"
    scan_id = upload_res["scan_id"]
    print(f"   [PASS] POST /upload -> scan_id: #{scan_id}, status: {upload_res['status']}")

    # 3. Test OCR Endpoint
    print(f"\n3. Testing POST /ocr/{scan_id}...")
    ocr_req = urllib.request.Request(
        f"{API_URL}/ocr/{scan_id}",
        data=b"",
        headers={"Content-Type": "application/json"}
    )
    ocr_res = json.loads(urllib.request.urlopen(ocr_req).read().decode("utf-8"))
    assert ocr_res.get("success") is True, f"OCR failed: {ocr_res}"
    print(f"   [PASS] POST /ocr/{scan_id} -> status: {ocr_res['status']}, chars: {len(ocr_res['ocr_text'])}")

    # 4. Test Compliance Check Endpoint
    print(f"\n4. Testing POST /check/{scan_id}...")
    check_req = urllib.request.Request(
        f"{API_URL}/check/{scan_id}",
        data=b"",
        headers={"Content-Type": "application/json"}
    )
    check_res = json.loads(urllib.request.urlopen(check_req).read().decode("utf-8"))
    assert check_res.get("success") is True, f"Check failed: {check_res}"
    print(f"   [PASS] POST /check/{scan_id} -> Score: {check_res['compliance_score']}%, Status: {check_res['compliance_status']}")

    # 5. Test API Report Endpoint
    print(f"\n5. Testing GET /api/report/{scan_id}...")
    rep_res = json.loads(urllib.request.urlopen(f"{API_URL}/api/report/{scan_id}").read().decode("utf-8"))
    assert rep_res.get("success") is True, f"Report failed: {rep_res}"
    assert rep_res["compliance_score"] == 100.0, f"Expected 100% score for sample, got {rep_res['compliance_score']}"
    print(f"   [PASS] GET /api/report/{scan_id} -> Verified compliance report data")

    # 6. Test Web Report Navigation Endpoint (Accept: text/html)
    print(f"\n6. Testing GET /report/{scan_id} (Browser request)...")
    web_rep_req = urllib.request.Request(
        f"{API_URL}/report/{scan_id}",
        headers={"Accept": "text/html,application/xhtml+xml"}
    )
    web_rep_res = urllib.request.urlopen(web_rep_req).read().decode("utf-8")
    assert "<!DOCTYPE html>" in web_rep_res, "Web report did not return HTML"
    print(f"   [PASS] GET /report/{scan_id} -> Rendered SPA HTML")

    # 7. Test Parle-G Preset
    print("\n7. Testing Parle-G Sample...")
    req2 = urllib.request.Request(
        f"{API_URL}/upload",
        data=json.dumps({"filename": "parle_g_gluco_biscuits_250g.jpg", "commodity_type": "Biscuits"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    upload_res2 = json.loads(urllib.request.urlopen(req2).read().decode("utf-8"))
    scan_id2 = upload_res2["scan_id"]
    
    urllib.request.urlopen(urllib.request.Request(f"{API_URL}/ocr/{scan_id2}", data=b"", headers={"Content-Type": "application/json"}))
    check_res2 = json.loads(urllib.request.urlopen(urllib.request.Request(f"{API_URL}/check/{scan_id2}", data=b"", headers={"Content-Type": "application/json"})).read().decode("utf-8"))
    assert check_res2["compliance_score"] == 100.0
    print(f"   [PASS] Parle-G scan #{scan_id2} -> Score: {check_res2['compliance_score']}%")

    # 8. Test Scans List
    print("\n8. Testing GET /api/scans...")
    scans_res = json.loads(urllib.request.urlopen(f"{API_URL}/api/scans").read().decode("utf-8"))
    assert len(scans_res.get("scans", [])) >= 2, "Expected at least 2 scans in history"
    print(f"   [PASS] GET /api/scans -> Total Scans recorded: {len(scans_res['scans'])}")

    print("\n============================================================")
    print(" ALL 8 INTEGRATION TESTS PASSED PERFECTLY! [100% SUCCESS]")
    print("============================================================")

if __name__ == "__main__":
    run_tests()
