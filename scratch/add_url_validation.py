import os

html_path = "frontend/dashboard.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Update the HTML block
old_html = """                <div class="import-url-input-group">
                    <input type="text" placeholder="Paste job URL from LinkedIn, Naukri, I">
                    <button class="btn-import">Import</button>
                </div>
                <div class="import-supports">Supports LinkedIn, Naukri, Indeed, Glassdoor</div>"""

new_html = """                <div class="import-url-input-group">
                    <input type="text" id="jobUrlInput" placeholder="Paste job URL from LinkedIn, Naukri, I">
                    <button class="btn-import" onclick="importJobUrl()">Import</button>
                </div>
                <div id="urlErrorMsg" style="color: #ef4444; font-size: 0.75rem; margin-top: 4px; display: none; font-weight: 600;">Invalid URL</div>
                <div class="import-supports">Supports LinkedIn, Naukri, Indeed, Glassdoor</div>"""

html = html.replace(old_html, new_html)

# 2. Append JS function before closing script tag
js_snippet = """
        // ✅ IMPORT JOB URL VALIDATION
        function importJobUrl() {
            const urlInput = document.getElementById("jobUrlInput");
            const errorMsg = document.getElementById("urlErrorMsg");
            const url = urlInput.value.trim();
            
            if (!url) {
                errorMsg.innerText = "Please enter a URL";
                errorMsg.style.display = "block";
                urlInput.style.outline = "1px solid #ef4444";
                return;
            }

            try {
                new URL(url); // Validates URL format
                
                // Extra check for http/https
                if (!url.startsWith("http://") && !url.startsWith("https://")) {
                    throw new Error("Invalid scheme");
                }

                // If valid:
                errorMsg.style.display = "none";
                urlInput.style.outline = "none";
                
                // Simulate success (we don't have a backend scraper for this yet)
                alert("URL accepted! Background scraping would start here for:\\n" + url);
                
            } catch (e) {
                errorMsg.innerText = "Invalid URL";
                errorMsg.style.display = "block";
                urlInput.style.outline = "1px solid #ef4444";
            }
        }
"""

last_script_end = html.rfind("</script>")
if last_script_end != -1:
    html = html[:last_script_end] + js_snippet + html[last_script_end:]

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("URL validation logic added successfully.")
