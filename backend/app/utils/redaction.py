import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}")
IBAN_LIKE_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")


def redact_pii(text: str) -> str:
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = IBAN_LIKE_RE.sub("[REDACTED_ACCOUNT]", text)
    return text


def contains_unredacted_pii(text: str) -> bool:
    return bool(EMAIL_RE.search(text) or PHONE_RE.search(text) or IBAN_LIKE_RE.search(text))
