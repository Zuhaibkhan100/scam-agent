import re

# ==================================================
# Regex patterns for concrete scam intelligence
# ==================================================
URL_PATTERN = r"https?://[^\s]+"
UPI_PATTERN = r"\b[\w.\-]{2,}@[a-zA-Z]{2,}\b"
EMAIL_PATTERN = r"[\w\.-]+@[\w\.-]+\.\w+"
PHONE_PATTERN = r"\b(?:\+?\d{1,3}[-.\s]?)?\d{10}\b"
BANK_ACCOUNT_PATTERN = r"\b\d{9,18}\b"

# ==================================================
# Scam tactic keywords (deterministic signals)
# ==================================================
TACTIC_KEYWORDS = {
    "urgency": [
        "urgent", "immediately", "now", "right away", "asap"
    ],
    "authority": [
        "bank", "support", "official", "team", "department"
    ],
    "threat": [
        "blocked", "suspended", "closed", "limited"
    ],
    "reward": [
        "prize", "refund", "cashback", "won"
    ]
}

# ==================================================
# Core Intelligence Extraction Engine
# ==================================================
def extract_intelligence(text: str) -> dict:
    """
    Extracts structured scam intelligence from raw text.

    Returns:
    {
        "urls": [...],
        "upi_ids": [...],
        "emails": [...],
        "phone_numbers": [...],
        "tactics": [...],
        "impersonation": str | None
    }
    """

    text_lower = text.lower()

    urls = re.findall(URL_PATTERN, text)
    upi_ids = re.findall(UPI_PATTERN, text)
    emails = re.findall(EMAIL_PATTERN, text)
    phone_numbers = re.findall(PHONE_PATTERN, text)
    bank_accounts = re.findall(BANK_ACCOUNT_PATTERN, text)

    # Detect scam tactics
    tactics = []
    for tactic, keywords in TACTIC_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            tactics.append(tactic)

    # Detect impersonation type
    impersonation = None
    if "bank" in text_lower:
        impersonation = "bank"
    elif "upi" in text_lower or "payment" in text_lower:
        impersonation = "payment"
    elif "gov" in text_lower or "income tax" in text_lower:
        impersonation = "government"

    return {
        "urls": urls,
        "upi_ids": upi_ids,
        "emails": emails,
        "phone_numbers": phone_numbers,
        "bank_accounts": bank_accounts,
        "tactics": tactics,
        "impersonation": impersonation
    }
