import os
import glob
import fitz

for folder in ['backend/temp', '..']:
    for p in glob.glob(os.path.join(folder, '*.pdf')) + glob.glob(os.path.join(folder, '*.docx')):
        try:
            if p.endswith('.pdf'):
                doc = fitz.open(p)
                txt = "".join([page.get_text("text") for page in doc])
                if "Basamma" in txt or "basamma" in txt.lower() or "kalaburagi" in txt.lower() or "Gangadhar" in txt:
                    print("FOUND BASAMMA PDF:", p)
                    print(txt)
                    exit(0)
        except Exception as e:
            pass
print("Not found in PDFs.")
