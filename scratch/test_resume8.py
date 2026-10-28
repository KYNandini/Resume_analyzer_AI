import fitz
import re
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.analyzer import _parse_resume_sections, _clean_inst_name, _format_degree_name, _extract_year_field, _extract_grade_field, _is_summary_or_non_edu, _parse_single_line_qual, _clean_field, _is_edu_header_line

def test():
    doc = fitz.open(r'C:\Users\nandi\Desktop\Resumes\Resume 8(M).pdf')
    text = '\n'.join(p.get_text() for p in doc)
    sec = _parse_resume_sections(text)
    lines = sec.get('Education', [])

    DEGREE_PATTERNS = [
        r'\b(?:ph\.?d|doctorate|doctor\s+of\s+(?:philosophy|science)|d\.phil)\b',
        r'\b(?:m\.?tech|m\.?e\.?|(?<![a-z]\.)m\.s\.|(?<![a-z]\.)ms\b|m\.?sc|mca|mba|m\.?com|m\.?a\.|m\.?des|pg\s+diploma|post\s+graduate\s+diploma)\b',
        r'\b(?:master(?:\'?s)?\s+of\s+(?:technology|engineering|science|arts|commerce|business\s+administration|computer\s+applications|philosophy|design|architecture|pharmacy|education))\b',
        r'\bmaster(?:\'?s)?\s+degree\b',
        r'\b(?:b\.?tech|b\.?e\.?|(?<![a-z]\.)b\.s\.|(?<![a-z]\.)bs\b|b\.?sc|bca|bba|b\.?com|b\.?a\.|b\.?des|b\.?arch|mbbs)\b',
        r'\b(?:bachelor(?:\'?s)?\s+of\s+(?:technology|engineering|science|arts|commerce|business\s+administration|computer\s+applications|philosophy|design|architecture|pharmacy|education|laws))\b',
        r'\bbachelor(?:\'?s)?\s+degree\b',
        r'\b(?:computer\s+science(?:\s+(?:and|&)\s+engineering)?|information\s+(?:science|technology)(?:\s+(?:and|&)\s+engineering)?|electrical(?:\s+(?:and|&)\s+electronics)?(?:\s+engineering)?|electronics(?:\s+(?:and|&)\s+communication)?(?:\s+engineering)?|(?:mechanical|civil|chemical|biotechnology|aeronautical|automobile|aerospace|industrial|robotics|data\s+science)\s+engineering)\b',
        r'\b(?:diploma(?:\s+in\s+[A-Za-z\s&]+)?|polytechnic(?:\s+diploma)?|advanced\s+diploma)\b',
        r'\b(?:pre[- ]university(?:\s+course)?|puc(?:\s*-\s*[a-z]+)?|higher\s+secondary(?:\s+education)?|senior\s+secondary(?:\s+education)?|intermediate(?:\s*\(?[a-z]+\)?)?|12th(?:\s+std|\s+standard|\s+grade)?|class\s+(?:xii|12|12th)|hsc|plus\s+two|\+2)\b',
        r'\b(?:secondary\s+school\s+leaving\s+certificate|secondary\s+education|secondary\s+school|sslc|10th(?:\s+std|\s+standard|\s+grade)?|class\s+(?:x|10|10th)|matriculation|high\s+school\s+(?:certificate|diploma))\b',
        r'\b(?:associate(?:\'?s)?\s+degree)\b'
    ]

    INST_PATTERNS = [
        r'\b(?:college|pu\s+college)\b',
        r'(?<!pre[- ])\buniversity\b',
        r'\b(?:institute|institution|academy|vidyalaya|polytechnic|campus|vtu|iit|nit|iisc|bits|mit)\b',
        r'(?<!secondary\s)(?<!senior\s)(?<!higher\s)\bschool\b',
        r'\b(?:board|council|examination\s+board)\b',
        r'\b(?:society|trust|samiti|sanstha|mandal|kendra|bhavan|vidyapeeth(?:a)?|shikshan(?:a)?|sangh(?:a)?)\b',
        r'(?<!secondary\s)(?<!higher\s)(?<!technical\s)\beducation\b'
    ]

    def _is_degree_kw(t):
        return any(re.search(pat, t.lower()) for pat in DEGREE_PATTERNS)

    def _is_inst_kw(t):
        low = t.lower()
        if re.search(r'\b(?:pre[- ]university\s+course|secondary\s+school\s+leaving\s+certificate|secondary\s+school|secondary\s+education|higher\s+secondary\s+education|sslc|puc)\b', low):
            if not re.search(r'\b(?:pu\s+college|high\s+school|public\s+school|grammar\s+school|secondary\s+school\s+examination\s+board)\b', low):
                return False
        return any(re.search(pat, low) for pat in INST_PATTERNS)

    combined = []
    for line in lines:
        l_str = _clean_field(line)
        if not l_str or _is_edu_header_line(l_str): continue
        combined.append(l_str)

    records = []
    current = {'degree': '', 'inst': '', 'year': '', 'grade': ''}

    def flush_current():
        nonlocal current
        deg = _format_degree_name(current['degree'])
        inst = _clean_inst_name(current['inst'])
        yr = current['year']
        gr = current['grade']
        if deg or inst:
            records.append([deg or '—', inst or '—', yr or '—', gr or '—'])
        current = {'degree': '', 'inst': '', 'year': '', 'grade': ''}

    for line in combined:
        y_val, y_rem = _extract_year_field(line)
        g_val, g_rem = _extract_grade_field(line)

        if _is_summary_or_non_edu(line):
            if g_val and not current['grade']: current['grade'] = g_val
            if y_val and not current['year']: current['year'] = y_val
            continue

        has_deg = _is_degree_kw(line)
        has_inst = _is_inst_kw(line)

        if has_deg and has_inst:
            if current['degree'] or current['inst']: flush_current()
            single = _parse_single_line_qual(line)
            if single and (single[0] != '—' and single[1] != '—'):
                current['degree'], current['inst'] = single[0], single[1]
                if single[2] != '—': current['year'] = single[2]
                if single[3] != '—': current['grade'] = single[3]
                continue

        if has_deg:
            if current['degree']: flush_current()
            deg_clean = line
            if g_val: deg_clean = deg_clean.replace(g_val, ' ')
            if y_val: deg_clean = deg_clean.replace(y_val, ' ')
            deg_clean = re.sub(r'^(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?[\s,;:-]*', '', deg_clean, flags=re.IGNORECASE)
            deg_clean = re.sub(r'[,;\s]*(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?.*$', '', deg_clean, flags=re.IGNORECASE)
            deg_clean = _clean_field(deg_clean)
            parts = [_clean_field(p) for p in re.split(r'[,|–—]', deg_clean) if _clean_field(p)]
            if len(parts) > 1 and _is_degree_kw(parts[0]):
                current['degree'] = parts[0]
                if not current['inst']: current['inst'] = ', '.join(parts[1:])
            else:
                current['degree'] = deg_clean or line
            if y_val and not current['year']: current['year'] = y_val
            if g_val and not current['grade']: current['grade'] = g_val
            continue

        if has_inst:
            if current['inst']:
                if current['degree'] or current['year'] or current['grade']:
                    flush_current()
                    current['inst'] = line
                else:
                    if line.lower() not in current['inst'].lower():
                        current['inst'] += " " + line
            else:
                current['inst'] = line
            if y_val and not current['year']: current['year'] = y_val
            if g_val and not current['grade']: current['grade'] = g_val
            continue

        if y_val:
            if current['year'] and (current['degree'] or current['inst']):
                flush_current()
            if not current['year']: current['year'] = y_val
        if g_val and not current['grade']: current['grade'] = g_val

        rem_str = _clean_field(y_rem.replace(g_val, '')) if y_val else _clean_field(g_rem)
        if rem_str and len(rem_str) < 90 and not _is_summary_or_non_edu(rem_str):
            if current['inst'] and rem_str.lower() not in current['inst'].lower():
                current['inst'] += ", " + rem_str
            elif not current['inst']:
                current['inst'] = rem_str

    flush_current()

    print("PARSED FOR RESUME 8(M):")
    for r in records:
        print(" ", r)

if __name__ == '__main__':
    test()
