import requests

pdf_path = r'C:\Users\nandi\Desktop\Resumes\Resume 5.pdf'
with open(pdf_path, 'rb') as f:
    files = {'resume': ('Resume 5.pdf', f, 'application/pdf')}
    data = {
        'jobText': 'Looking for an Electrical Engineer skilled in MATLAB, circuit simulation, and power systems.',
        'shortBio': '',
        'preferredTitle': 'Electrical Engineer',
        'preferredLocation': 'Hassan, Karnataka',
        'template': 'modern'
    }
    resp = requests.post('http://localhost:3000/build-resume-latex', files=files, data=data)
    print("STATUS CODE:", resp.status_code)
    res_json = resp.json()
    latex = res_json.get('latexResume', '')
    print("HAS tabularx:", 'tabularx' in latex)
    print("HAS Percentage / CGPA:", 'Percentage / CGPA' in latex)
    print("HAS B.E. in Electrical and Electronics Engineering:", 'Electrical and Electronics Engineering' in latex)
    print("HAS Sri Ranga high school:", 'Sri Ranga high school' in latex)
    print("HAS Presidency PU College:", 'Presidency PU College' in latex)
    
    start_table = latex.find(r'\begin{tabularx}')
    end_table = latex.find(r'\end{tabularx}')
    if start_table != -1 and end_table != -1:
        print("\n--- GENERATED LATEX EDUCATION TABLE ---")
        print(latex[start_table:end_table + 14])
