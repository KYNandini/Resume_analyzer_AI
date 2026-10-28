import re

lines_list = [
    "Additional Information",
    "- Languages: Kannada (Native), English (Professional), Hindi (Fluent) Strengths: Analytical Thinking, Quick Learner",
    "Just a normal line"
]

extracted_langs = []
lines_to_keep = []

for line in lines_list:
    clean_line = line.lstrip(" \t\n\r-*•·▪►").strip()
    lower_line = clean_line.lower()
    if "languages:" in lower_line:
        parts = re.split(r'(?i)languages:\s*', clean_line)
        if len(parts) > 1:
            lang_part = parts[1]
            for stop_word in ["Strengths:", "Skills:", "Hobbies:"]:
                if stop_word.lower() in lang_part.lower():
                    lang_part = re.split(r'(?i)' + stop_word, lang_part)[0]
            extracted_langs.append(lang_part.strip())
            if parts[0].strip():
                lines_to_keep.append(parts[0].strip())
    else:
        lines_to_keep.append(line)

print("Keep:", lines_to_keep)
print("Langs:", extracted_langs)
