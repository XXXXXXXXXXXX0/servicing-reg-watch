"""Static configuration: sources, window, tracked CFR parts (BUILD_SPEC Section 3)."""

FR_API = "https://www.federalregister.gov/api/v1/documents.json"
ECFR_API = "https://www.ecfr.gov/api/versioner/v1"

# Full text of Federal Register documents comes from GovInfo, not
# federalregister.gov (whose text URLs redirect to a bot wall). Primary route:
# the API granule /htm endpoint, key sent in the X-Api-Key header. Fallback:
# the public www content link. Package = FR-<publication_date>, granule =
# document number.
GOVINFO_API = "https://api.govinfo.gov"
GOVINFO_WWW = "https://www.govinfo.gov"
GOVINFO_KEY_ENV = "GOVINFO_API_KEY"

WINDOW_MONTHS = 24

AGENCIES = [
    "consumer-financial-protection-bureau",
    "federal-communications-commission",
    "federal-trade-commission",
    "comptroller-of-the-currency",
    "federal-deposit-insurance-corporation",
    "federal-reserve-system",
    "national-credit-union-administration",
]

# Federal Register API condition values -> the `type` string returned in results.
DOC_TYPES = {"RULE": "Rule", "PRORULE": "Proposed Rule", "NOTICE": "Notice"}

# Fields requested from the Federal Register API and stored as raw JSON.
FR_FIELDS = [
    "document_number", "title", "type", "subtype", "action", "abstract", "dates",
    "agencies", "agency_names", "publication_date", "effective_on", "signing_date",
    "comments_close_on", "cfr_references", "citation", "docket_ids",
    "regulation_id_numbers", "significant", "topics", "html_url", "pdf_url",
    "raw_text_url", "full_text_xml_url", "json_url", "correction_of", "corrections",
]

# eCFR parts diffed at section level (BUILD_SPEC Section 3). A `section`
# restricts the diff to one section of a large part.
ECFR_TRACKED = [
    {"title": 12, "part": "1005", "label": "Reg E"},
    {"title": 12, "part": "1002", "label": "Reg B"},
    {"title": 12, "part": "1006", "label": "Reg F"},
    {"title": 12, "part": "1016", "label": "Reg P"},
    {"title": 12, "part": "1022", "label": "Reg V"},
    {"title": 12, "part": "1026", "label": "Reg Z"},
    {"title": 47, "part": "64", "section": "64.1200", "label": "TCPA rules"},
    {"title": 16, "part": "314", "label": "FTC Safeguards"},
]

# Prefilter rule A (PREFILTER.md): a document citing any of these CFR parts is
# kept. Superset of ECFR_TRACKED: adds bank/CU security, incident-notification
# and supervision parts that are not diffed. The list is a floor, biased toward
# keeping: add parts freely, remove only with a stated reason.
PREFILTER_CFR_PARTS = {(t["title"], t["part"]) for t in ECFR_TRACKED} | {
    (12, "30"), (12, "208"), (12, "225"), (12, "364"), (12, "748"),
    (12, "53"), (12, "304"), (12, "1090"),
}

