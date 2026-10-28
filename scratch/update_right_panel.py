import os
import re

html_path = "frontend/dashboard.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Replace the HTML for the right panel
start_idx_content = html.find('        <!-- RIGHT PANEL')
end_idx_content = html.find('    </div>\n\n    <script>')

new_content_html = """        <!-- RIGHT PANEL -->
        <div class="content">
            <div class="top-nav">
                <button class="btn-lang"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg> English ⌄</button>
                <button class="btn-logout-nav" onclick="logout()">Logout</button>
            </div>

            <div class="welcome-banner">
                <h1>👋 👋 Welcome, <span id="welcomeUserName">---</span>!</h1>
                <p>Optimize your resume for applicant tracking systems (ATS) and align your skills with your dream job in seconds.</p>
            </div>

            <!-- RESUME ANALYSIS HISTORY SECTION (3 COLUMNS) -->
            <div class="section-title history-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
                Your Resume Analysis History
            </div>
            <div id="analysisHistoryContainer" class="history-grid"></div>

        </div>
"""

if start_idx_content != -1 and end_idx_content != -1:
    html = html[:start_idx_content] + new_content_html + html[end_idx_content:]

# Replace the renderAnalysisHistory function in JS
js_func_start = html.find('        // ✅ RENDER ANALYSIS HISTORY\n        function renderAnalysisHistory() {')
js_func_end = html.find('        // ✅ OPEN UPLOADED RESUME FILE')

new_js_func = """        // ✅ RENDER ANALYSIS HISTORY
        function renderAnalysisHistory() {
            const container = document.getElementById("analysisHistoryContainer");
            let history = JSON.parse(localStorage.getItem("analysisHistory")) || [];

            if (history.length === 0) {
                container.innerHTML = `
            <div class="empty-history-box">
                <p class="empty-history-title">📂 No Resumes Analyzed Yet</p>
                <p class="empty-history-subtitle">Upload your resume and paste a job description in the left panel to see AI insights here!</p>
            </div>
        `;
                return;
            }

            container.innerHTML = history.map((item) => {
                const matchPct = item.data?.matchPercent || item.data?.score || 0;
                const effPct = item.data?.efficiencyPercent || matchPct;
                const matched = item.data?.matchingSkills || item.data?.matched || [];
                const missing = item.data?.missingSkills || item.data?.missing || [];
                const fileType = item.fileType || (item.fileName ? item.fileName.split('.').pop().toUpperCase() : "PDF");
                const fileSize = item.fileSize || "1.8 MB";
                const targetJob = item.jobTitle || 'General Job Description';

                return `
            <div class="history-card">
                <div class="history-card-top">
                    <span class="badge-pdf">${fileType}</span>
                    <span class="badge-match">${matchPct}% Match</span>
                </div>

                <div class="history-card-body">
                    <h4 class="history-filename" title="${item.fileName}">${item.fileName}</h4>
                    <div class="history-meta">
                        <div><span class="meta-icon">🕒</span> Last uploaded: ${item.timestamp}</div>
                        <div><span class="meta-icon">💾</span> Size: ${fileSize}</div>
                    </div>
                    
                    <div class="history-target" title="${targetJob}">
                        <strong>Target:</strong> ${targetJob}
                    </div>
                    
                    <div class="history-skills-row">
                        <span class="skill-matched">✅ ${matched.length} Matched</span>
                        <span class="skill-missing">⚠️ ${missing.length} Missing</span>
                    </div>
                    
                    <div class="history-score-row">
                        <span class="score-icon">🚀</span> ${effPct}% ATS Score
                    </div>
                </div>

                <div class="history-card-actions">
                    <button class="btn-card-open" onclick="openHistoryFile('${item.id}')">
                        📄 Open File
                    </button>
                    <button class="btn-card-report" onclick="viewHistoricalReport('${item.id}')">
                        🔍 View Report
                    </button>
                    <button class="btn-card-delete" onclick="deleteHistoryItem('${item.id}')">
                        🗑️
                    </button>
                </div>
            </div>
        `;
            }).join("");
        }

"""

if js_func_start != -1 and js_func_end != -1:
    html = html[:js_func_start] + new_js_func + html[js_func_end:]

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)
print("HTML right panel updated successfully")


css_path = "frontend/dashboard.css"
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

start_idx_css = css.find('/* RIGHT PANEL (INDEPENDENTLY SCROLLABLE) */')

new_content_css = """/* RIGHT PANEL (INDEPENDENTLY SCROLLABLE) */
.content {
    width: 100%;
    background: #ffffff;
    border-radius: 12px;
    padding: 24px 32px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.03);
    display: flex;
    flex-direction: column;
    gap: 20px;
    height: 100%;
    overflow-y: auto;
    flex-grow: 1;
    min-width: 0;
}

/* CUSTOM SLEEK SCROLLBARS */
.content::-webkit-scrollbar {
    width: 8px;
}
.content::-webkit-scrollbar-track {
    background: transparent;
}
.content::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 10px;
}
.content::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}

/* Top Nav */
.top-nav {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-bottom: -10px;
}
.btn-lang {
    background: #0d9488;
    color: white;
    border: none;
    padding: 6px 16px;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
}
.btn-logout-nav {
    background: white;
    color: #0d9488;
    border: 1px solid #0d9488;
    padding: 6px 16px;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
}
.btn-logout-nav:hover {
    background: #f0fdfa;
}

/* Welcome Banner */
.welcome-banner {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    color: #ffffff;
    padding: 32px 36px;
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.2);
    position: relative;
    overflow: hidden;
    flex-shrink: 0;
}
.welcome-banner h1 {
    font-size: 1.6rem;
    font-weight: 800;
    margin-bottom: 8px;
    position: relative;
    z-index: 2;
    display: flex;
    align-items: center;
    gap: 10px;
}
.welcome-banner p {
    font-size: 0.9rem;
    color: #94a3b8;
    max-width: 90%;
    line-height: 1.5;
    position: relative;
    z-index: 2;
}

/* Section Title */
.section-title {
    font-size: 1.1rem;
    font-weight: 800;
    color: #0f172a;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}
.history-title {
    margin-top: 10px;
}

/* HISTORY CARDS */
.history-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    width: 100%;
    flex-shrink: 0;
}

.history-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
    display: flex;
    flex-direction: column;
    gap: 16px;
    transition: all 0.2s ease;
    min-width: 0;
}
.history-card:hover {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
    border-color: #cbd5e1;
}

.history-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.badge-pdf {
    background: #ef4444;
    color: white;
    font-size: 0.7rem;
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 6px;
}

.badge-match {
    background: #ffffff;
    color: #d97706;
    border: 1px solid #fde68a;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 16px;
}

.history-card-body {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.history-filename {
    font-size: 1rem;
    font-weight: 800;
    color: #0f172a;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 2px;
}

.history-meta {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 500;
}

.history-target {
    font-size: 0.75rem;
    color: #475569;
    background: #f8fafc;
    padding: 8px 12px;
    border-radius: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 4px;
}

.history-skills-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    font-weight: 700;
    margin-top: 4px;
}
.skill-matched {
    color: #10b981;
}
.skill-missing {
    color: #f59e0b;
}

.history-score-row {
    text-align: center;
    font-size: 0.8rem;
    font-weight: 700;
    color: #64748b;
    margin-top: 8px;
    margin-bottom: 4px;
}

.history-card-actions {
    display: flex;
    gap: 8px;
    margin-top: auto;
}

.btn-card-open {
    flex: 1;
    background: #f1f5f9;
    color: #0f172a;
    border: none;
    padding: 10px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
}
.btn-card-open:hover {
    background: #e2e8f0;
}

.btn-card-report {
    flex: 1.2;
    background: #0f172a;
    color: white;
    border: none;
    padding: 10px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
}
.btn-card-report:hover {
    background: #1e293b;
}

.btn-card-delete {
    background: #fee2e2;
    color: #ef4444;
    border: none;
    width: 38px;
    border-radius: 8px;
    font-size: 1rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    flex-shrink: 0;
}
.btn-card-delete:hover {
    background: #fecaca;
}

.empty-history-box {
    grid-column: 1 / -1;
    background: #f8fafc;
    border: 2px dashed #cbd5e1;
    padding: 40px;
    border-radius: 16px;
    text-align: center;
}
.empty-history-title {
    font-size: 1rem;
    color: #0f172a;
    font-weight: 700;
    margin-bottom: 8px;
}
.empty-history-subtitle {
    font-size: 0.8rem;
    color: #64748b;
}
"""

if start_idx_css != -1:
    css = css[:start_idx_css] + new_content_css
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css)
    print("CSS right panel updated successfully")
else:
    print("Could not find CSS replacement point")
