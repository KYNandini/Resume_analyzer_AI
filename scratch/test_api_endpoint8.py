import requests

pdf_path = r'C:\Users\nandi\Desktop\Resumes\Resume 8(M).pdf'
with open(pdf_path, 'rb') as f:
    files = {'resume': ('Resume 8(M).pdf', f, 'application/pdf')}
    data = {
        'jobText': 'Full stack developer with Python, React, SQL.',
        'shortBio': '',
        'preferredTitle': 'Software Engineer',
        'preferredLocation': 'Hassan, Karnataka',
        'template': 'modern'
    }
    resp = requests.post('http://localhost:3000/build-resume', files=files, data=data)
    print("STATUS CODE:", resp.status_code)
    res_json = resp.json()
    md = res_json.get('tailoredResume', '')
    start_table = md.find('<table class="education-table"')
    end_table = md.find('</table>', start_table)
    if start_table != -1 and end_table != -1:
        print("\n--- GENERATED EDUCATION TABLE HTML FOR RESUME 8(M) ---")
        print(md[start_table:end_table + 8])
