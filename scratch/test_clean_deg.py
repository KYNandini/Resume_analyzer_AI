import re

def _clean_field(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r'^[\s\-_–—•·▪►|:,;~"\ufffd]+', '', text)
    cleaned = re.sub(r'[\s\-_–—•·▪►|:,;~"\ufffd]+$', '', cleaned)
    return cleaned.strip()

def _format_degree_name(degree: str) -> str:
    d = _clean_field(degree)
    low = d.lower()
    if low in ['secondary education', 'secondary school', 'sslc', '10th', 'class 10', 'class x']:
        return "Secondary Education (SSLC)"
    if low in ['pre-university', 'pre university', 'puc', 'pre-university course']:
        return "Pre-University (PUC)"
    if low in ['higher secondary', '12th', 'class 12', 'class xii', 'hsc', 'plus two', '+2']:
        return "Higher Secondary (Class XII)"
    return d

def _infer_degree_from_inst(inst: str, year: str = "") -> str:
    low = inst.lower()
    if any(k in low for k in ['high school', 'public school', 'grammar school', 'secondary school', 'english medium school', 'school', 'vidyalaya']):
        return "Class X (SSLC)"
    if any(k in low for k in ['pu college', 'junior college', 'intermediate', 'puc', 'higher secondary']):
        return "Pre-University (PUC)"
    if any(k in low for k in ['engineering', 'technology', 'institute of technology', 'polytechnic']):
        return "Bachelor of Engineering (B.E.)"
    if any(k in low for k in ['college', 'university', 'institute']):
        return "Bachelor's Degree"
    return "Class X (SSLC)"

# Test raw lines from Rakesh's resume
raw_lines = [
    "Bachelor of Engineering in Computer Science",
    "Government Engineering College, Mosalehosahalli, Hassan",
    "CGPA: 7.75 / 10",
    "Pre-University \u2013",
    "2023",
    "M S PU College, Honnali, Davangere",
    "Percentage: 73.44%",
    "Secondary Education \u2013",
    "2021",
    "Jnana Ganga English Medium School, Kundur, Davangere",
    "Percentage: 90.72%"
]

print("Cleaned degree 1:", repr(_format_degree_name("Pre-University \u2013")))
print("Cleaned degree 2:", repr(_format_degree_name("Secondary Education \u2013")))
print("Inferred degree for school:", repr(_infer_degree_from_inst("Jnana Ganga English Medium School, Kundur, Davangere")))
