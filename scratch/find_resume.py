import os
import glob
import fitz

for folder in ['backend/temp', '..']:
    for p in glob.glob(os.path.join(folder, '*.pdf')):
        try:
            doc = fitz.open(p)
            txt = ""
            for page in doc:
                txt += page.get_text("text") + "\n"
            if "Mosalehosahalli" in txt or "Honnali" in txt or "Jnana Ganga" in txt:
                print("FOUND RESUME:", p)
                print("--- TEXT ---")
                print(txt)
                exit(0)
        except Exception:
            pass
print("Not found in pdfs.")
