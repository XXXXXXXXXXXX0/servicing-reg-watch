"""Static configuration: sources, window, tracked CFR parts (BUILD_SPEC Section 3)."""

FR_API = "https://www.federalregister.gov/api/v1/documents.json"
ECFR_API = "https://www.ecfr.gov/api/versioner/v1"

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

# CFR parts whose appearance in a document's cfr_references keeps it through
# the prefilter. Superset of ECFR_TRACKED: adds register parts that are not
# diffed (bank/CU security, incident notification, CFPB larger participants).
PREFILTER_CFR_PARTS = {(t["title"], t["part"]) for t in ECFR_TRACKED} | {
    (12, "30"), (12, "364"), (12, "208"), (12, "748"),
    (12, "53"), (12, "225"), (12, "304"), (12, "1090"),
}

FINANCE_AGENCIES = set(AGENCIES) - {"federal-communications-commission"}
