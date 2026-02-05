import re

# ==================================================
# Regex patterns for concrete scam intelligence
# ==================================================
URL_PATTERN = r"https?://[^\s<>\"]+|www\.[^\s<>\"]+"
UPI_PATTERN = r"\b[\w.\-]{2,}@[a-zA-Z]{2,}\b"
EMAIL_PATTERN = r"[\w\.-]+@[\w\.-]+\.\w+"
# Looser phone capture; we normalize and validate later.
PHONE_PATTERN = r"(?:\+?\d[\d\s().-]{7,}\d)"
BANK_ACCOUNT_PATTERN = r"\b\d{9,18}\b"

# ==================================================
# Scam tactic keywords (deterministic signals)
# ==================================================
TACTIC_KEYWORDS = {
    "urgency": [
        "urgent",
        "immediately",
        "right away",
        "asap",
        "act now",
        "within",
        "today",
        "limited time",
    ],
    "authority": [
        "bank",
        "customer care",
        "support",
        "official",
        "team",
        "department",
        "rbi",
        "npci",
    ],
    "threat": [
        "blocked",
        "account blocked",
        "blocked today",
        "suspended",
        "account suspended",
        "closed",
        "limited",
        "freeze",
        "deactivated",
    ],
    "verification": [
        "verify",
        "verify now",
        "verify immediately",
        "verification",
        "confirm",
        "update",
        "update kyc",
        "kyc",
    ],
    "payment": [
        "upi",
        "upi id",
        "share your upi",
        "collect request",
        "pay",
        "payment",
        "transfer",
    ],
    "reward": [
        "prize", "refund", "cashback", "won"
    ]
}


def _clean_url(url: str) -> str:
    # Strip common trailing punctuation from URLs found in free-form text.
    return url.rstrip(").,;!?\"'")


def _normalize_phone(candidate: str) -> str | None:
    digits = re.sub(r"\D", "", candidate or "")
    if not digits:
        return None

    # India-focused normalization (hackathon examples are IN).
    if len(digits) == 10 and digits[0] in "6789":
        return "+91" + digits
    if len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
        return "+91" + digits[1:]
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return "+" + digits

    # Generic E.164-ish: accept 11-15 digits.
    if 11 <= len(digits) <= 15:
        return "+" + digits

    return None


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

    urls = [_clean_url(u) for u in re.findall(URL_PATTERN, text)]
    upi_ids = re.findall(UPI_PATTERN, text)
    emails = re.findall(EMAIL_PATTERN, text)

    # Phones: normalize and validate; dedupe later by caller if needed.
    phone_candidates = re.findall(PHONE_PATTERN, text)
    phone_numbers = []
    for c in phone_candidates:
        n = _normalize_phone(c)
        if n:
            phone_numbers.append(n)

    bank_accounts = re.findall(BANK_ACCOUNT_PATTERN, text)

    # Avoid double-counting phone numbers as bank accounts when digits overlap.
    phone_digits = {re.sub(r"\D", "", p) for p in phone_numbers}
    bank_accounts = [
        acc for acc in bank_accounts if acc not in phone_digits and not (len(acc) == 10 and acc[0] in "6789")
    ]

    # Detect scam tactics + the specific keywords/phrases that triggered them
    tactics = []
    suspicious_keywords = []
    for tactic, keywords in TACTIC_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in text_lower]
        if matched:
            tactics.append(tactic)
            suspicious_keywords.extend(matched)

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
        "suspicious_keywords": suspicious_keywords,
        "impersonation": impersonation
    }
