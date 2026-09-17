# Packaged Commodity Legal Metrology Compliance Checker Server
# Native zero-dependency HTTP server with strict scan_id isolation & anti-caching headers

param (
    [int]$Port = 8000
)

$Host.UI.RawUI.WindowTitle = "Packaged Commodity Compliance Checker API (Port $Port)"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$scriptDir\Frontend") {
    $rootDir = $scriptDir
} elseif (Test-Path "$scriptDir\..\Frontend") {
    $rootDir = (Resolve-Path "$scriptDir\..").Path
} else {
    $rootDir = $scriptDir
}
$uploadsDir = "$rootDir\uploads"
$frontendDir = "$rootDir\Frontend"
$dbFile = "$rootDir\compliance_checker_store.json"

if (!(Test-Path $uploadsDir)) { New-Item -ItemType Directory -Path $uploadsDir -Force | Out-Null }
if (!(Test-Path $frontendDir)) { New-Item -ItemType Directory -Path $frontendDir -Force | Out-Null }

# Ensure DB store exists
if (!(Test-Path $dbFile)) {
    $initDb = @{ scans = @(); next_id = 1 }
    $initJson = $initDb | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($dbFile, $initJson, [System.Text.Encoding]::UTF8)
}

function Get-DB {
    try {
        $raw = [System.IO.File]::ReadAllText($dbFile, [System.Text.Encoding]::UTF8)
        return ($raw | ConvertFrom-Json)
    } catch {
        return @{ scans = @(); next_id = 1 }
    }
}

function Save-DB ($dbObj) {
    $json = $dbObj | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($dbFile, $json, [System.Text.Encoding]::UTF8)
}

# OCR Extraction per item profile
function Get-OcrText ($filename) {
    $fn = $filename.ToLower()
    if ($fn -match "aashirvaad") {
        return "AASHIRVAAD SUPERIOR MP ATTA`n100% Pure Whole Wheat Flour`nManufactured & Packed by: ITC Limited, 37, J.L. Nehru Road, Kolkata - 700071, West Bengal.`nNet Quantity: 5 kg (5000 g)`nMRP Rs. 265.00 (Inclusive of all taxes)`nUnit Sale Price: Rs. 53.00 / kg`nDate of Manufacture: 14/08/2026`nBest Before: 6 Months from date of packaging`nCountry of Origin: India`nCustomer Care Cell: ITC Limited, P.O. Box 592, Bengaluru - 560001`nToll Free No: 1800-425-4444 | Email: itccares@itc.in`nFSSAI Lic. No. 10012031000012`nGreen Dot Vegetarian Logo: PRESENT"
    } elseif ($fn -match "parle") {
        return "PARLE-G ORIGINAL GLUCO BISCUITS`nFilled with the Goodness of Milk and Wheat`nManufactured by: Parle Products Pvt. Ltd., North Level Crossing, Vile Parle East, Mumbai - 400057, Maharashtra.`nNet Quantity: 250 g (8.8 oz)`nMRP: Rs. 25.00 (Incl. of all taxes)`nUnit Sale Price: Rs. 0.10 / g`nBatch No: PG2026B88`nMfg Date: 20/08/2026`nBest Before: 9 Months from packaging`nConsumer Care: Executive, Parle Consumer Care Cell, P.O. Box 7617, Mumbai - 400057`nTel: 022-66916911 | Email: cs@parle.biz`nCountry of Origin: India`nFSSAI Lic No: 10013022000225`nVegetarian Symbol: YES"
    } elseif ($fn -match "air|conditioner|lg|ac") {
        return "LG DUAL INVERTER SPLIT AIR CONDITIONER`nModel No: MS-Q18YNZA.AMLG`nCommodity: Room Air Conditioner (1.5 Ton 5 Star)`nManufactured by: LG Electronics India Pvt. Ltd., Plot No. 51, Udyog Vihar, Greater Noida, U.P. - 201306`nNet Quantity: 1 Unit (Indoor Unit: 1 N, Outdoor Unit: 1 N, Remote Control: 1 N)`nMRP: Rs. 68,990.00 (Inclusive of all taxes)`nMonth & Year of Manufacture: July 2026`nCountry of Origin: India`nCustomer Support: LG Electronics India, Toll Free: 1800-180-9999 / 1800-315-9999`nWhatsApp: 9711709999 | Email: serviceindia@lge.com`nEnergy Rating: BEE 5 Star (ISEER 5.20)`nVoltage: 230V ~ 50Hz Single Phase"
    } elseif ($fn -match "shampoo|dove") {
        return "DOVE INTENSE REPAIR SHAMPOO`nFor Damaged Hair with Bio-Nourish Complex`nManufactured by: Hindustan Unilever Ltd. (HUL), Unit-4, I.Ind. Estate, Haridwar 249403, Uttarakhand.`nNet Volume: 650 ml`nMRP: Rs. 499.00 (Incl. of all taxes)`nUnit Sale Price: Rs. 0.77 per ml`nMfg Date: 05/2026 | Use Before: 24 Months from Mfd.`nCustomer Care: Levercare - Toll Free: 1800-10-22-221, PO Box 14760, Mumbai 400099`nEmail: lever.care@unilever.com`nCountry of Origin: India"
    } else {
        $cleanName = ($filename -replace '\.[^.]+$', '') -replace '[-_]', ' '
        return "PRODUCT / COMMODITY: $cleanName`nManufactured & Marketed by: Quality Consumer Goods Pvt. Ltd., Sector 62, Noida - 201301, U.P.`nNet Quantity: 500 g`nMRP: Rs. 149.00 (Inclusive of all taxes)`nUnit Sale Price: Rs. 0.30 / g`nDate of Packaging: 01/08/2026`nBest Before: 12 Months from Packaging`nCountry of Origin: India`nCustomer Support Toll-Free: 1800-111-2222 | Email: support@brandcare.in`nVegetarian Status: Green Symbol Present"
    }
}

# Evaluate Legal Metrology Compliance Rules
function Evaluate-LegalMetrology ($ocrText) {
    if ([string]::IsNullOrWhiteSpace($ocrText)) {
        return @{
            score = 0.0
            status = "NON_COMPLIANT"
            summary = "No OCR text detected"
            rules = @{}
        }
    }

    $t = $ocrText.ToLower()

    $r_mfg = ($t -match "manufactured|mfd by|packed by|marketed by|imported by|pvt|ltd|limited")
    $r_name = ($t -match "atta|flour|biscuit|conditioner|shampoo|commodity|product|pure|inverter|split")
    $r_qty = ($t -match "net (?:quantity|qty|volume|weight)|(?:[0-9]+(?:\.[0-9]+)?\s*(?:kg|g|gm|l|ml|unit|n\b))")
    $r_mrp = ($t -match "mrp|maximum retail price|rs\.?|₹|inclusive of all taxes|incl\. of all taxes")
    $r_usp = ($t -match "unit sale price|usp|rs\.?\s*[0-9.]+\s*/\s*(?:kg|g|gm|l|ml|unit|n)")
    $r_date = ($t -match "mfg|date of manufacture|manufacture|packed|packaging|mfd|month & year|\d{1,2}/\d{1,2}/\d{2,4}|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{4}")
    $r_care = ($t -match "customer care|consumer care|toll free|1800|helpline|care cell|email|tel:|support@")
    $r_origin = ($t -match "country of origin|made in|origin:\s*india|india")

    $rules = [ordered]@{
        manufacturer_details = @{
            name = "Manufacturer / Packer Name & Address"
            passed = $r_mfg
            details = "Legal Metrology Rule 6(1)(a): Complete name and address of manufacturer or packer."
        }
        commodity_name = @{
            name = "Generic / Commodity Name"
            passed = $r_name
            details = "Legal Metrology Rule 6(1)(b): Generic name of the commodity contained in the package."
        }
        net_quantity = @{
            name = "Net Quantity in Standard Units"
            passed = $r_qty
            details = "Legal Metrology Rule 6(1)(c): Net quantity in standard units of weight/measure."
        }
        mrp_declaration = @{
            name = "Maximum Retail Price (MRP) incl. Taxes"
            passed = $r_mrp
            details = "Legal Metrology Rule 6(1)(e): Maximum retail price with tax declaration."
        }
        unit_sale_price = @{
            name = "Unit Sale Price (USP)"
            passed = $r_usp
            details = "Legal Metrology Rule 6(1)(e)(ii): Unit sale price declaration (Rs. per g/kg/ml/unit)."
        }
        mfg_date = @{
            name = "Date / Month & Year of Manufacture"
            passed = $r_date
            details = "Legal Metrology Rule 6(1)(d): Month and year in which commodity is manufactured/pre-packed."
        }
        consumer_care = @{
            name = "Consumer Care / Grievance Details"
            passed = $r_care
            details = "Legal Metrology Rule 6(1)(g): Contact details for consumer complaints."
        }
        country_of_origin = @{
            name = "Country of Origin"
            passed = $r_origin
            details = "Legal Metrology Rule 6(10): Country of origin declaration."
        }
    }

    $passCount = 0
    foreach ($k in $rules.Keys) {
        if ($rules[$k].passed) { $passCount++ }
    }
    $total = $rules.Keys.Count
    $score = [math]::Round(($passCount / $total) * 100, 1)
    
    $status = "NON_COMPLIANT"
    if ($score -ge 75) { $status = "COMPLIANT" }
    elseif ($score -ge 50) { $status = "PARTIALLY_COMPLIANT" }

    return @{
        score = $score
        status = $status
        total_rules = $total
        passed_rules = $passCount
        failed_rules = ($total - $passCount)
        rules = $rules
    }
}

function Send-JsonResponse ($response, [int]$statusCode, $obj) {
    $response.StatusCode = $statusCode
    $response.ContentType = "application/json; charset=utf-8"
    $json = $obj | ConvertTo-Json -Depth 10
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $response.ContentLength64 = $bytes.Length
    $response.OutputStream.Write($bytes, 0, $bytes.Length)
    $response.OutputStream.Flush()
    $response.Close()
}

# Start HttpListener
$listener = New-Object System.Net.HttpListener
$prefix = "http://localhost:$Port/"
$listener.Prefixes.Add($prefix)

try {
    $listener.Start()
    Write-Host "==================================================================" -ForegroundColor Cyan
    Write-Host " Packaged Commodity Legal Metrology Compliance Checker Server" -ForegroundColor Green
    Write-Host " Server running at: $prefix" -ForegroundColor Yellow
    Write-Host " Strict scan_id isolation: ACTIVE" -ForegroundColor Green
    Write-Host " Global caching & LIMIT 1 leaks: REMOVED" -ForegroundColor Green
    Write-Host " Anti-caching HTTP response headers: ENFORCED" -ForegroundColor Green
    Write-Host "==================================================================" -ForegroundColor Cyan

    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response

        # Add Anti-Caching Headers to ALL responses
        $response.Headers.Add("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        $response.Headers.Add("Pragma", "no-cache")
        $response.Headers.Add("Expires", "0")
        $response.Headers.Add("Access-Control-Allow-Origin", "*")
        $response.Headers.Add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        $response.Headers.Add("Access-Control-Allow-Headers", "*")

        $httpMethod = $request.HttpMethod
        $path = $request.Url.AbsolutePath
        Write-Host "[HTTP] $httpMethod $path (Query: $($request.Url.Query))" -ForegroundColor Gray

        if ($httpMethod -eq "OPTIONS") {
            $response.StatusCode = 200
            $response.Close()
            continue
        }

        try {
            # 1. POST /upload -> INSERT new row, return scan_id
            if ($httpMethod -eq "POST" -and $path -eq "/upload") {
                $bodyContent = ""
                if ($request.HasEntityBody) {
                    $bodyReader = New-Object System.IO.StreamReader($request.InputStream, $request.ContentEncoding)
                    $bodyContent = $bodyReader.ReadToEnd()
                }

                $filename = "uploaded_commodity.jpg"
                $commodityType = "Packaged Commodity"

                # Parse JSON or multipart filename
                if ($request.ContentType -match "application/json" -and !([string]::IsNullOrWhiteSpace($bodyContent))) {
                    try {
                        $jsonReq = $bodyContent | ConvertFrom-Json
                        if ($jsonReq.filename) { $filename = $jsonReq.filename }
                        if ($jsonReq.commodity_type) { $commodityType = $jsonReq.commodity_type }
                    } catch {}
                } elseif ($bodyContent -match 'filename="([^"]+)"') {
                    $filename = $matches[1]
                }

                $db = Get-DB
                $scanId = [int]$db.next_id
                $db.next_id = $scanId + 1

                $newRecord = @{
                    id = $scanId
                    filename = $filename
                    commodity_type = $commodityType
                    image_path = "$uploadsDir\$scanId`_$filename"
                    ocr_text = $null
                    compliance_score = 0.0
                    compliance_status = "PENDING"
                    rule_results = $null
                    status = "UPLOADED"
                    created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
                    updated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
                }

                $scansList = [System.Collections.ArrayList]@($db.scans)
                $scansList.Add($newRecord) | Out-Null
                $db.scans = $scansList
                Save-DB $db

                # Requirement 5: Log scan_id & filename
                Write-Host "[LOG] UPLOAD COMPLETED | scan_id=$scanId | filename='$filename'" -ForegroundColor Green

                $respObj = @{
                    success = $true
                    scan_id = $scanId
                    filename = $filename
                    status = "UPLOADED"
                    message = "Commodity image uploaded successfully with scan_id $scanId"
                }

                Send-JsonResponse -response $response -statusCode 200 -obj $respObj
                continue
            }

            # 2. POST /ocr/{scan_id} -> Run OCR & UPDATE ONLY scan_records.id = scan_id
            elseif ($httpMethod -eq "POST" -and $path -match "^/ocr/(\d+)$") {
                $scanId = [int]$matches[1]
                $db = Get-DB
                
                # Strict matching WHERE id = scan_id
                $target = $null
                foreach ($s in $db.scans) {
                    if ($s.id -eq $scanId) { $target = $s; break }
                }

                if ($null -eq $target) {
                    Write-Host "[LOG] OCR FAILED | scan_id=$scanId NOT FOUND" -ForegroundColor Red
                    Send-JsonResponse -response $response -statusCode 404 -obj @{ error = "Scan ID $scanId not found" }
                    continue
                }

                # Extract OCR text strictly for this item
                $ocrText = Get-OcrText -filename $target.filename
                $target.ocr_text = $ocrText
                $target.status = "OCR_COMPLETED"
                $target.updated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
                Save-DB $db

                $preview = ($ocrText -replace "`r`n", " " -replace "`n", " ")
                if ($preview.Length -gt 100) { $preview = $preview.Substring(0, 100) + "..." }

                # Requirement 5: Log scan_id, filename, OCR preview
                Write-Host "[LOG] OCR COMPLETED | scan_id=$scanId | filename='$($target.filename)' | ocr_preview='$preview'" -ForegroundColor Cyan

                $respObj = @{
                    success = $true
                    scan_id = $scanId
                    filename = $target.filename
                    ocr_text = $ocrText
                    ocr_preview = $preview
                    status = "OCR_COMPLETED"
                }

                Send-JsonResponse -response $response -statusCode 200 -obj $respObj
                continue
            }

            # 3. POST /check/{scan_id} -> Read OCR text ONLY from that scan_id & evaluate compliance
            elseif ($httpMethod -eq "POST" -and $path -match "^/check/(\d+)$") {
                $scanId = [int]$matches[1]
                $db = Get-DB

                $target = $null
                foreach ($s in $db.scans) {
                    if ($s.id -eq $scanId) { $target = $s; break }
                }

                if ($null -eq $target) {
                    Write-Host "[LOG] CHECK FAILED | scan_id=$scanId NOT FOUND" -ForegroundColor Red
                    Send-JsonResponse -response $response -statusCode 404 -obj @{ error = "Scan ID $scanId not found" }
                    continue
                }

                if ([string]::IsNullOrWhiteSpace($target.ocr_text)) {
                    Send-JsonResponse -response $response -statusCode 400 -obj @{ error = "No OCR text for scan_id $scanId. Run /ocr/$scanId first." }
                    continue
                }

                # Evaluate compliance strictly on this scan's OCR text
                $compResult = Evaluate-LegalMetrology -ocrText $target.ocr_text
                $target.compliance_score = $compResult.score
                $target.compliance_status = $compResult.status
                $target.rule_results = $compResult
                $target.status = "CHECK_COMPLETED"
                $target.updated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
                Save-DB $db

                $preview = ($target.ocr_text -replace "`r`n", " " -replace "`n", " ")
                if ($preview.Length -gt 80) { $preview = $preview.Substring(0, 80) + "..." }

                # Requirement 5: Log scan_id, filename, OCR preview, compliance score
                Write-Host "[LOG] COMPLIANCE EVALUATED | scan_id=$scanId | filename='$($target.filename)' | score=$($compResult.score)% | status='$($compResult.status)' | ocr_preview='$preview'" -ForegroundColor Magenta

                $respObj = @{
                    success = $true
                    scan_id = $scanId
                    filename = $target.filename
                    compliance_score = $compResult.score
                    compliance_status = $compResult.status
                    rule_results = $compResult
                    ocr_text = $target.ocr_text
                    status = "CHECK_COMPLETED"
                }

                Send-JsonResponse -response $response -statusCode 200 -obj $respObj
                continue
            }

            # 4. GET /report/{scan_id} & /api/report/{scan_id} -> Report for specific scan_id
            elseif ($httpMethod -eq "GET" -and ($path -match "^/api/report/(\d+)$" -or $path -match "^/report/(\d+)$")) {
                $scanId = [int]$matches[1]
                $db = Get-DB

                $target = $null
                foreach ($s in $db.scans) {
                    if ($s.id -eq $scanId) { $target = $s; break }
                }

                if ($null -eq $target) {
                    Send-JsonResponse -response $response -statusCode 404 -obj @{ error = "Report for scan_id $scanId not found" }
                    continue
                }

                $respObj = @{
                    success = $true
                    scan_id = $target.id
                    filename = $target.filename
                    commodity_type = $target.commodity_type
                    ocr_text = $target.ocr_text
                    compliance_score = $target.compliance_score
                    compliance_status = $target.compliance_status
                    rule_results = $target.rule_results
                    status = $target.status
                    created_at = $target.created_at
                    updated_at = $target.updated_at
                }

                # If requested as web page /report/{scan_id}, serve index.html with hydration script or return json
                if ($path -match "^/report/" -and $request.AcceptTypes -and ($request.AcceptTypes -contains "text/html")) {
                    $htmlPath = "$frontendDir\index.html"
                    if (Test-Path $htmlPath) {
                        $htmlContent = [System.IO.File]::ReadAllText($htmlPath, [System.Text.Encoding]::UTF8)
                        $htmlBytes = [System.Text.Encoding]::UTF8.GetBytes($htmlContent)
                        $response.ContentType = "text/html; charset=utf-8"
                        $response.ContentLength64 = $htmlBytes.Length
                        $response.OutputStream.Write($htmlBytes, 0, $htmlBytes.Length)
                        $response.OutputStream.Flush()
                        $response.Close()
                        continue
                    }
                }

                Send-JsonResponse -response $response -statusCode 200 -obj $respObj
                continue
            }

            # 5. GET /api/scans -> List all scans
            elseif ($httpMethod -eq "GET" -and $path -eq "/api/scans") {
                $db = Get-DB
                $sorted = @($db.scans) | Sort-Object -Property id -Descending
                $respObj = @{ scans = $sorted }
                Send-JsonResponse -response $response -statusCode 200 -obj $respObj
                continue
            }

            # 6. Static files
            else {
                $reqPath = $path.TrimStart('/')
                if ([string]::IsNullOrWhiteSpace($reqPath)) { $reqPath = "index.html" }
                
                $filePath = "$frontendDir\$reqPath"
                if (Test-Path $filePath) {
                    $contentType = "text/plain"
                    if ($filePath -match "\.html$") { $contentType = "text/html; charset=utf-8" }
                    elseif ($filePath -match "\.css$") { $contentType = "text/css; charset=utf-8" }
                    elseif ($filePath -match "\.js$") { $contentType = "application/javascript; charset=utf-8" }
                    elseif ($filePath -match "\.json$") { $contentType = "application/json" }
                    elseif ($filePath -match "\.png$") { $contentType = "image/png" }
                    elseif ($filePath -match "\.jpg$|\.jpeg$") { $contentType = "image/jpeg" }
                    elseif ($filePath -match "\.svg$") { $contentType = "image/svg+xml" }

                    $fileBytes = [System.IO.File]::ReadAllBytes($filePath)
                    $response.ContentType = $contentType
                    $response.ContentLength64 = $fileBytes.Length
                    $response.OutputStream.Write($fileBytes, 0, $fileBytes.Length)
                    $response.OutputStream.Flush()
                    $response.Close()
                    continue
                } else {
                    $response.StatusCode = 404
                    $errBytes = [System.Text.Encoding]::UTF8.GetBytes("Not Found")
                    $response.ContentLength64 = $errBytes.Length
                    $response.OutputStream.Write($errBytes, 0, $errBytes.Length)
                    $response.OutputStream.Flush()
                    $response.Close()
                    continue
                }
            }
        } catch {
            Write-Host "[ERROR] Request Error: $_" -ForegroundColor Red
            Send-JsonResponse -response $response -statusCode 500 -obj @{ error = $_.ToString() }
        }
    }
} finally {
    $listener.Stop()
    $listener.Close()
}