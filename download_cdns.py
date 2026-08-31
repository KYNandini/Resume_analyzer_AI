import os
import requests
import json
import urllib.request

def download_file(url, dest_path):
    print(f"Downloading {url}...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(response.content)
        print(f"Saved to {dest_path}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def main():
    base_dir = r"c:\Users\nandi\Downloads\Resume_Analyzer_AI"
    vendor_dirs = [
        os.path.join(base_dir, "resume-analyzer-login", "vendor"),
        os.path.join(base_dir, "analysis-dashboard", "vendor")
    ]
    
    for v_dir in vendor_dirs:
        os.makedirs(os.path.join(v_dir, "webfonts"), exist_ok=True)
        
    assets = [
        # marked.js
        ("https://cdn.jsdelivr.net/npm/marked/marked.min.js", "marked.min.js"),
        # pdf.js
        ("https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js", "pdf.min.js"),
        ("https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js", "pdf.worker.min.js"),
        # fontawesome css
        ("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css", "all.min.css")
    ]
    
    # FontAwesome WebFonts
    webfonts = [
        "fa-solid-900.woff2",
        "fa-solid-900.ttf",
        "fa-brands-400.woff2",
        "fa-brands-400.ttf",
        "fa-regular-400.woff2",
        "fa-regular-400.ttf"
    ]
    
    for v_dir in vendor_dirs:
        for url, filename in assets:
            download_file(url, os.path.join(v_dir, filename))
            
        for font in webfonts:
            url = f"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/webfonts/{font}"
            download_file(url, os.path.join(v_dir, "webfonts", font))

if __name__ == "__main__":
    main()
