import re

def _clean_field(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r'^[\s\-_–—•·▪►|:,;~"\'*\ufffd]+', '', text)
    cleaned = re.sub(r'[\s\-_–—•·▪►|:,;~"\'*\ufffd]+$', '', cleaned)
    return cleaned.strip()

print("Cleaned degree 1:", repr(_clean_field("**10th STD / SSLC**")))
print("Cleaned degree 2:", repr(_clean_field("**Diploma**")))
