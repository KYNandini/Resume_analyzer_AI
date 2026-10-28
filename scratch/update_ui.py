import os

html_path = "frontend/dashboard.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

start_idx = html.find('        <!-- LEFT PANEL -->')
if start_idx == -1:
    start_idx = html.find('        <!-- LEFT PANEL (PERFECTLY FIXED IN SINGLE WINDOW SIZE) -->')

end_idx = html.find('        <!-- RIGHT PANEL')

new_sidebar_html = """        <!-- LEFT PANEL -->
        <div class="sidebar">
            <h2 class="sidebar-title">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="sidebar-icon">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                AI Resume Analyzer
            </h2>

            <h3 class="section-heading dark-text">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
                Profile Dashboard
            </h3>

            <div class="profile-card">
                <img id="profileImage" src="logo.png" class="profile-avatar" alt="Profile" onclick="openProfileModal()">
                <div class="profile-info-new">
                    <div class="profile-name-row">
                        <span id="userName" class="profile-name">---</span>
                        <button class="btn-edit-badge" onclick="openProfileModal()"><span style="color: #f97316;">✏️</span> Edit</button>
                    </div>
                    <div id="userRole" class="profile-role">💻 ---</div>
                    <div id="userEmail" class="profile-email">---</div>
                    <div id="userDOB" class="profile-dob">---</div>
                </div>
                <input type="file" id="imageUpload" hidden>
            </div>

            <!-- Upload Resume -->
            <h3 class="section-heading dark-text" style="margin-top: 4px;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="17 8 12 3 7 8"></polyline>
                    <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                Upload Resume
            </h3>

            <div class="upload-container">
                <input type="file" id="resumeInput" accept=".pdf,.doc,.docx" onchange="handleFileChange(this)" hidden>
                <label for="resumeInput" class="upload-dropzone" id="dropBoxContainer">
                    <div class="upload-icon-box">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                            <polyline points="13 2 13 9 20 9"></polyline>
                            <path d="M12 11v6"></path>
                            <path d="M9.5 14.5L12 12l2.5 2.5"></path>
                        </svg>
                    </div>
                    <div class="upload-title">Drag and drop a file here</div>
                    <div class="upload-btn">Browse</div>
                    <div class="upload-formats">Files we can read: DOC, DOCX, PDF, HTML, RTF, TXT</div>
                </label>
            </div>
            <p id="fileName" class="file-name-display">No file selected</p>

            <!-- Job Description -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                <h3 class="section-heading dark-text" style="margin-bottom: 0;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                    Job Description
                </h3>
            </div>

            <textarea id="jobDesc" class="job-desc-textarea" placeholder="Strong hands-on experience in Python development with the ability to build complete features, libraries, and modules independently.&#10;Strong knowledge of Python fundamentals, including typing, async/await, decorators, context managers, generators, and standard library modules."></textarea>

            <div class="jd-info-box">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0; margin-top: 2px;"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>
                <div style="font-size: 0.75rem; color: #64748b; line-height: 1.4;">Copy and paste the complete job description from any job posting. Our AI will compare it with your resume to understand the required skills, experience, and keywords.</div>
            </div>

            <div class="jd-hint">
                <span class="lightbulb">💡</span> Paste a complete job description with at least 50 characters for accurate AI analysis
            </div>

            <div class="char-counter-container">
                <div class="char-counter-box">
                    <div class="char-counter-left">
                        <span id="charCount">0</span>
                        <div class="char-label">characters</div>
                    </div>
                    <div class="char-counter-right">
                        <span id="charNeeded">50</span> more needed<br>for matching
                    </div>
                </div>
                <div class="char-counter-text">Add the job description<br>to continue</div>
            </div>

            <div class="import-url-section">
                <div class="import-url-link">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
                    Or import from URL <span class="arrow">^</span>
                </div>
                <div class="import-url-input-group">
                    <input type="text" placeholder="Paste job URL from LinkedIn, Naukri, I">
                    <button class="btn-import">Import</button>
                </div>
                <div class="import-supports">Supports LinkedIn, Naukri, Indeed, Glassdoor</div>
            </div>

            <button id="analyzeBtn" class="btn-analyze" onclick="analyzeResume()">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                </svg>
                Analyze Resume
            </button>
            <div id="loadingBox" style="display:none; text-align: center; margin-top: 8px;">
                <div class="spinner" style="border: 3px solid #f3f3f3; border-top: 3px solid #0d9488; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; margin: 0 auto;"></div>
                <p class="loading-text" style="color: #0d9488; font-weight: 600; font-size: 0.85rem; margin-top: 8px;">AI is analyzing your resume...</p>
            </div>
        </div>
"""

if start_idx != -1 and end_idx != -1:
    new_html = html[:start_idx] + new_sidebar_html + html[end_idx:]
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_html)
    print("HTML updated successfully")
else:
    print(f"Could not find replacement points. Start: {start_idx}, End: {end_idx}")


css_path = "frontend/dashboard.css"
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

start_idx = css.find('/* LEFT PANEL */')
end_idx = css.find('/* RIGHT PANEL (INDEPENDENTLY SCROLLABLE) */')

new_sidebar_css = """/* LEFT PANEL */
.sidebar {
    width: 380px;
    background: #f8fafc;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    display: flex;
    flex-direction: column;
    gap: 16px;
    height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
    flex-shrink: 0;
}

.sidebar > * {
    flex-shrink: 0; /* Prevents flexbox from squishing contents */
}

/* CUSTOM SLEEK SCROLLBARS FOR SIDEBAR */
.sidebar::-webkit-scrollbar {
    width: 6px;
}
.sidebar::-webkit-scrollbar-track {
    background: transparent;
}
.sidebar::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 10px;
}
.sidebar::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}

.sidebar-title {
    font-size: 1.25rem;
    font-weight: 800;
    color: #0d9488; /* Teal color */
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}

.section-heading {
    font-size: 1rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}
.section-heading.teal-text {
    color: #0d9488;
}
.section-heading.dark-text {
    color: #0f172a;
}

.profile-card {
    background: #ffffff;
    border: 1px solid #f1f5f9;
    border-radius: 12px;
    padding: 16px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    position: relative;
    overflow: hidden;
    min-height: 100px;
}
.profile-card::before {
    content: '';
    position: absolute;
    left: -20px;
    top: 0;
    bottom: 0;
    width: 80px;
    background: linear-gradient(to right, #e0f2fe, transparent);
    z-index: 0;
    border-radius: 12px 0 0 12px;
}

.profile-avatar {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    object-fit: cover;
    z-index: 1;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    cursor: pointer;
    background: #ffffff;
}

.profile-info-new {
    display: flex;
    flex-direction: column;
    z-index: 1;
    width: 100%;
}

.profile-name-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.profile-name {
    font-size: 0.95rem;
    font-weight: 800;
    color: #0f172a;
}

.btn-edit-badge {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    padding: 4px 10px;
    border-radius: 16px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #475569;
    cursor: pointer;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    display: flex;
    align-items: center;
    gap: 4px;
}

.profile-role {
    font-size: 0.8rem;
    font-weight: 700;
    color: #0d9488;
    margin-top: 2px;
}

.profile-email, .profile-dob {
    font-size: 0.75rem;
    color: #94a3b8;
    margin-top: 2px;
}

/* Upload Container */
.upload-container {
    border: 2px dashed #cbd5e1;
    border-radius: 12px;
    padding: 24px 12px;
    background: #ffffff;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
}
.upload-container:hover {
    border-color: #3b82f6;
    background: #f8fafc;
}
.upload-icon-box {
    background: #eff6ff;
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
}
.upload-icon-box svg {
    width: 24px;
    height: 24px;
    stroke: #1e3a8a; /* dark blue icon */
}
.upload-title {
    font-size: 0.9rem;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 12px;
}
.upload-btn {
    background: #1e3a8a; /* dark blue */
    color: white;
    padding: 8px 32px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 700;
    margin-bottom: 12px;
    box-shadow: 0 2px 4px rgba(30, 58, 138, 0.2);
}
.upload-formats {
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 600;
}
.file-name-display {
    text-align: center;
    font-size: 0.75rem;
    color: #64748b;
    margin-top: -8px;
    margin-bottom: 4px;
}

/* Job Description */
.job-desc-textarea {
    width: 100%;
    height: 120px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 12px;
    font-size: 0.85rem;
    color: #475569;
    resize: none;
    font-family: inherit;
}
.jd-info-box {
    background: #eff6ff;
    border-radius: 8px;
    padding: 12px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
}
.jd-hint {
    font-size: 0.75rem;
    color: #94a3b8;
    display: flex;
    align-items: center;
    gap: 6px;
}
.lightbulb {
    font-size: 0.9rem;
}

.char-counter-container {
    display: flex;
    align-items: center;
    gap: 12px;
}
.char-counter-box {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    display: flex;
    gap: 12px;
    align-items: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.char-counter-left {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding-right: 12px;
    border-right: 1px solid #e2e8f0;
}
.char-counter-left span {
    font-size: 1.1rem;
    font-weight: 800;
    color: #0f172a;
    line-height: 1;
}
.char-label {
    font-size: 0.7rem;
    font-weight: 700;
    color: #0f172a;
}
.char-counter-right {
    font-size: 0.75rem;
    color: #64748b;
    line-height: 1.2;
}
.char-counter-text {
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 600;
    line-height: 1.2;
}

.import-url-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 4px;
}
.import-url-link {
    font-size: 0.8rem;
    color: #3b82f6;
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
}
.import-url-input-group {
    display: flex;
    background: #1e293b;
    border-radius: 8px;
    overflow: hidden;
}
.import-url-input-group input {
    flex: 1;
    background: transparent;
    border: none;
    padding: 10px 12px;
    color: #cbd5e1;
    font-size: 0.8rem;
    outline: none;
}
.import-url-input-group button {
    background: #60a5fa;
    color: white;
    border: none;
    padding: 0 16px;
    font-weight: 600;
    font-size: 0.85rem;
    cursor: pointer;
}
.import-supports {
    font-size: 0.7rem;
    color: #94a3b8;
}

.btn-analyze {
    background: #0d9488;
    color: white;
    border: none;
    padding: 14px;
    border-radius: 12px;
    font-size: 1.05rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: pointer;
    width: 100%;
    box-shadow: 0 4px 12px rgba(13, 148, 136, 0.2);
    margin-top: 8px;
    margin-bottom: 20px;
}
.btn-analyze:hover {
    background: #0f766e;
}

"""

if start_idx != -1 and end_idx != -1:
    new_css = css[:start_idx] + new_sidebar_css + css[end_idx:]
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(new_css)
    print("CSS updated successfully")
else:
    print(f"Could not find CSS replacement points. Start: {start_idx}, End: {end_idx}")

