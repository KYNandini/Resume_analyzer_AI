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
    resp = requests.post('http://localhost:3000/build-resume', files=files, data=data)
    print("STATUS CODE:", resp.status_code)
    res_json = resp.json()
    md = res_json.get('tailoredResume', '')
    print("HAS education-table:", 'education-table' in md)
    print("HAS Percentage / CGPA:", 'Percentage / CGPA' in md)
    print("HAS B.E. in Electrical and Electronics Engineering:", 'Electrical and Electronics Engineering' in md)
    print("HAS Sri Ranga high school:", 'Sri Ranga high school' in md)
    print("HAS Presidency PU College:", 'Presidency PU College' in md)
    
    # Print the table from the returned markdown
    start_table = md.find('<table class="education-table"')
    end_table = md.find('</table>', start_table)
    if start_table != -1 and end_table != -1:
        print("\n--- GENERATED EDUCATION TABLE HTML ---")
        print(md[start_table:end_table + 8])

    # Check Summary
    start_summary = md.find('## PROFESSIONAL SUMMARY')
    end_summary = md.find('## EDUCATION')
    if start_summary != -1 and end_summary != -1:
        print("\n--- GENERATED SUMMARY ---")
        print(md[start_summary:end_summary].strip())
