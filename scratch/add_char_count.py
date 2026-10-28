import os

html_path = "frontend/dashboard.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Add the character counter logic right before the closing </script> tag at the end of the file.
js_snippet = """
        // ✅ CHARACTER COUNTER FOR JOB DESCRIPTION
        const jobDescInput = document.getElementById("jobDesc");
        if (jobDescInput) {
            jobDescInput.addEventListener("input", function() {
                const text = this.value;
                const count = text.length;
                const countEl = document.getElementById("charCount");
                const neededEl = document.getElementById("charNeeded");
                
                if (countEl) countEl.innerText = count;
                if (neededEl) {
                    const needed = Math.max(0, 50 - count);
                    neededEl.innerText = needed;
                    if (count >= 50) {
                        neededEl.parentElement.innerHTML = "Sufficient length<br>for matching";
                    } else {
                        neededEl.parentElement.innerHTML = `<span id="charNeeded">${needed}</span> more needed<br>for matching`;
                    }
                }
            });
        }
"""

# Find the last </script> tag
last_script_end = html.rfind("</script>")
if last_script_end != -1:
    new_html = html[:last_script_end] + js_snippet + html[last_script_end:]
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_html)
    print("Added char counter JS successfully")
