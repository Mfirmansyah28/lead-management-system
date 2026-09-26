import re
from dataclasses import dataclass

ALLOWED_CHANNELS = {
    "Website",
    "Event",
    "LinkedIn",
    "Organic Search",
    "Referral",
    "Manual/Sales",
    "Other",
}


@dataclass(frozen=True)
class SourceExtraction:
    channel: str
    detail: str


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def extract_source(raw_text: str | None) -> SourceExtraction:
    """Extract a normalized source channel and human-readable detail from CRM notes.

    The assignment explicitly allows a rules/regex or hybrid approach. This implementation
    uses deterministic rules because the synthetic notes use recognizable source phrases.
    """
    text = _clean(raw_text)
    lowered = text.casefold()

    # Event signals are checked before generic website/LinkedIn signals.
    event_patterns = [
        r"(?:at|during|from) (?:the )?(.+?) booth",
        r"at (?:our )?(.+?) booth",
        r"at the (.+?)(?:,|\.|$)",
        r"met (?:him|her|them) at (?:the )?(.+?)(?: booth|,|\.)",
    ]
    event_keywords = [
        "festival", "conference", "summit", "expo", "booth", "disrupt",
        "fintech week", "fintech festival", "mobile world congress",
        "saastr annual", "techcrunch",
    ]
    if any(k in lowered for k in event_keywords):
        detail = "Event"
        for pattern in event_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                name = _clean(match.group(1))
                name = re.sub(r"^(our|the)\s+", "", name, flags=re.IGNORECASE)
                if name:
                    detail = name
                    break
        if "qr" in lowered:
            detail += " — Booth QR Code" if detail != "Event" else "Booth QR Code"
        return SourceExtraction("Event", detail)

    if "linkedin" in lowered or ("our post" in lowered and "comment" in lowered):
        detail = "LinkedIn"
        if "dm" in lowered:
            detail = "LinkedIn DM"
        elif "comment" in lowered:
            detail = "LinkedIn post/comment"
        elif "connect" in lowered:
            detail = "LinkedIn connection"
        return SourceExtraction("LinkedIn", detail)

    if "referred by" in lowered or "warm intro" in lowered or "referral" in lowered:
        match = re.search(r"referred by\s+([^,.]+)", text, flags=re.IGNORECASE)
        detail = f"Referral — {match.group(1).strip()}" if match else "Referral"
        return SourceExtraction("Referral", detail)

    if any(phrase in lowered for phrase in [
        "googled us", "google search", "organic google", "organic search",
        "found us through organic",
    ]):
        match = re.search(r"(?:landed on|ended up on|before booking a demo|then landed on)\s+(?:the )?([^,.]+)", text, flags=re.IGNORECASE)
        detail = f"Organic Search — {match.group(1).strip()}" if match else "Organic Search"
        return SourceExtraction("Organic Search", detail)

    if any(phrase in lowered for phrase in [
        "manually added", "manual -", "manual—", "inbound phone call",
        "cold outreach list", "sales added",
    ]):
        return SourceExtraction("Manual/Sales", "Manual/Sales")

    if any(phrase in lowered for phrase in [
        "filled out the form", "contact page", "book-a-demo page",
        "newsletter signup", "website", "form on the blog", "pricing page",
    ]):
        match = re.search(r"form on the ([^.]+)", text, flags=re.IGNORECASE)
        detail = f"Website — {match.group(1).strip()}" if match else "Website"
        return SourceExtraction("Website", detail)

    return SourceExtraction("Other", "Other")
