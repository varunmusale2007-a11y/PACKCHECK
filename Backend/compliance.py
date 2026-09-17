import re
from typing import Dict, Any

def evaluate_compliance(ocr_text: str) -> Dict[str, Any]:
    """
    Evaluates Legal Metrology (Packaged Commodities) Rules compliance
    strictly against the provided OCR text for a specific scan.
    """
    if not ocr_text or not ocr_text.strip():
        return {
            "score": 0.0,
            "status": "NON_COMPLIANT",
            "summary": "No OCR text was detected or extracted.",
            "rules": {}
        }

    text = ocr_text.lower()
    
    rules = {
        "manufacturer_details": {
            "name": "Manufacturer / Packer Name & Address",
            "passed": bool(re.search(r"(manufactured|mfd by|packed by|marketed by|imported by|pvt\.? ltd|limited)", text)),
            "details": "Legal Metrology Rule 6(1)(a): Complete name and address of manufacturer or packer.",
            "extracted": extract_match(ocr_text, r"(?:Manufactured|Packed|Marketed|Imported)[^\n]+(?:\n[^\n]+)?")
        },
        "commodity_name": {
            "name": "Generic / Commodity Name",
            "passed": bool(re.search(r"(atta|flour|biscuit|conditioner|shampoo|commodity|product|pure|inverter)", text)),
            "details": "Legal Metrology Rule 6(1)(b): Generic name of the commodity contained in the package.",
            "extracted": extract_first_line(ocr_text)
        },
        "net_quantity": {
            "name": "Net Quantity in Standard Units",
            "passed": bool(re.search(r"(net (?:quantity|qty|volume|weight)|(?:[0-9]+(?:\.[0-9]+)?\s*(?:kg|g|gm|l|ml|unit|n\b)))", text)),
            "details": "Legal Metrology Rule 6(1)(c): Net quantity in terms of standard unit of weight/measure.",
            "extracted": extract_match(ocr_text, r"(?:Net (?:Quantity|Qty|Volume|Weight)[^\n]+|\d+\s*(?:kg|g|l|ml|Unit))")
        },
        "mrp_declaration": {
            "name": "Maximum Retail Price (MRP) incl. Taxes",
            "passed": bool(re.search(r"(mrp|maximum retail price|rs\.?|₹|inclusive of all taxes|incl\. of all taxes)", text)),
            "details": "Legal Metrology Rule 6(1)(e): Maximum retail price with inclusive of all taxes declaration.",
            "extracted": extract_match(ocr_text, r"(?:MRP|Maximum Retail Price)[^\n]+")
        },
        "unit_sale_price": {
            "name": "Unit Sale Price (USP)",
            "passed": bool(re.search(r"(unit sale price|usp|rs\.?\s*[0-9.]+\s*/\s*(?:kg|g|gm|l|ml|unit|n))", text)),
            "details": "Legal Metrology Rule 6(1)(e)(ii): Unit sale price declaration (Rs. per g/kg/ml/unit).",
            "extracted": extract_match(ocr_text, r"(?:Unit Sale Price|USP)[^\n]+")
        },
        "mfg_date": {
            "name": "Date / Month & Year of Manufacture",
            "passed": bool(re.search(r"(mfg|date of manufacture|manufacture|packed|packaging|mfd|month & year|\d{1,2}/\d{1,2}/\d{2,4}|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{4})", text)),
            "details": "Legal Metrology Rule 6(1)(d): Month and year in which commodity is manufactured/pre-packed.",
            "extracted": extract_match(ocr_text, r"(?:Date of (?:Manufacture|Packaging)|Mfg Date|Month & Year[^\n]+|\d{2}/\d{2}/\d{4})")
        },
        "consumer_care": {
            "name": "Consumer Care / Grievance Details",
            "passed": bool(re.search(r"(customer care|consumer care|toll free|1800|helpline|care cell|email|tel:|support@)", text)),
            "details": "Legal Metrology Rule 6(1)(g): Name, address, telephone number and email of person/office to contact for consumer complaints.",
            "extracted": extract_match(ocr_text, r"(?:Customer Care|Consumer Care|Toll Free|Helpline|Customer Support)[^\n]+(?:\n[^\n]+)?")
        },
        "country_of_origin": {
            "name": "Country of Origin",
            "passed": bool(re.search(r"(country of origin|made in|origin:\s*india|india)", text)),
            "details": "Legal Metrology Rule 6(10): Country of origin for imported or domestic packaged commodities.",
            "extracted": extract_match(ocr_text, r"(?:Country of Origin|Made in)[^\n]+")
        }
    }

    # Calculate compliance score
    total_rules = len(rules)
    passed_count = sum(1 for r in rules.values() if r["passed"])
    score = round((passed_count / total_rules) * 100, 1)

    if score >= 90:
        status = "COMPLIANT"
    elif score >= 60:
        status = "PARTIALLY_COMPLIANT"
    else:
        status = "NON_COMPLIANT"

    return {
        "score": score,
        "status": status,
        "total_rules": total_rules,
        "passed_rules": passed_count,
        "failed_rules": total_rules - passed_count,
        "rules": rules
    }

def extract_match(text: str, pattern: str) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(0).strip() if m else "Not explicitly detected"

def extract_first_line(text: str) -> str:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return lines[0] if lines else "Not detected"