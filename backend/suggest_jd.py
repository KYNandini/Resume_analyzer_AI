import os
import sys
import re
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from analyzer import extract_skills, TECH_SKILLS
except ImportError:
    from backend.analyzer import extract_skills, TECH_SKILLS

def detect_experience(resume_text: str) -> str:
    """Extract experience range or years from resume text.
    If no professional experience is found, returns 'Fresher'.
    """
    text_lower = resume_text.lower()

    # 1. Check for explicit Fresher / Entry-Level keywords
    fresher_indicators = [
        r'\bfresher\b',
        r'\bentry[\s-]level\b',
        r'\bfresh\s+graduate\b',
        r'\brecent\s+graduate\b',
        r'\bstudent\b',
        r'\bundergraduate\b',
        r'\b0\s*(?:-|to|\+)?\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b',
        r'\bexperience\s*:\s*0\s*(?:years?|yrs?)?\b',
        r'\bno\s+experience\b',
        r'\bno\s+prior\s+experience\b'
    ]
    for pattern in fresher_indicators:
        if re.search(pattern, text_lower):
            # Check if there is also contradictory strong multi-year experience
            strong_exp = re.findall(r'(\b[1-9]\d?)\s*(?:\+|plus|\s*-\s*\d{1,2})\s*(?:years?|yrs?)\s+(?:of\s+)?(?:work\s+|industry\s+|professional\s+)?experience\b', text_lower)
            if not strong_exp:
                return "Fresher"

    # 2. Look for explicit year statements (e.g., "3+ years of experience", "2 to 4 years experience", "Experience: 5 years")
    explicit_exp_patterns = [
        r'(\b\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s*(?:years?|yrs?)(?:\s+of)?\s+(?:work\s+|professional\s+|industry\s+)?experience\b',
        r'(\b\d{1,2})\s*(?:\+|plus)\s*(?:years?|yrs?)(?:\s+of)?\s+(?:work\s+|professional\s+|industry\s+)?experience\b',
        r'(?:total\s+)?experience\s*:\s*(\b\d{1,2})\s*(?:-|to|\+)?\s*(\d{1,2})?\s*(?:years?|yrs?)\b',
        r'(\b\d{1,2})\s*(?:years?|yrs?)\s+of\s+(?:work\s+|professional\s+|industry\s+)?experience\b'
    ]

    for pat in explicit_exp_patterns:
        matches = re.findall(pat, text_lower)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    min_yr = match[0]
                    max_yr = match[1] if len(match) > 1 and match[1] else None
                else:
                    min_yr = match
                    max_yr = None
                
                try:
                    val_min = int(min_yr)
                except ValueError:
                    continue

                if val_min == 0:
                    return "Fresher"
                if max_yr:
                    try:
                        val_max = int(max_yr)
                        if val_max == 0:
                            return "Fresher"
                        return f"{val_min} to {val_max} Years"
                    except ValueError:
                        pass
                
                if val_min >= 5:
                    return f"{val_min} to {val_min + 3} Years"
                elif val_min >= 2:
                    return f"{val_min} to {val_min + 2} Years"
                elif val_min == 1:
                    return "1 to 2 Years"

    # 3. Check for dedicated Work Experience / Employment section
    # Freshers typically only have Education, Projects, Skills, Certifications
    exp_section_headers = r'(?:work\s+experience|professional\s+experience|employment\s+history|work\s+history|experience\s*:)'
    has_exp_section = re.search(exp_section_headers, text_lower)

    if has_exp_section:
        # Extract content of experience section (up to next section like Education/Projects/Skills)
        exp_pos = has_exp_section.start()
        exp_subtext = text_lower[exp_pos:exp_pos + 1500]

        # Exclude education keywords inside subtext
        year_ranges = re.findall(r'\b(20\d{2}|19\d{2})\s*(?:-|–|to)\s*(20\d{2}|present|current)\b', exp_subtext)
        if year_ranges:
            total_years = 0
            current_year = 2026
            for start_str, end_str in year_ranges:
                start_yr = int(start_str)
                end_yr = current_year if end_str in ["present", "current"] else int(end_str)
                diff = max(0, min(15, end_yr - start_yr))
                total_years = max(total_years, diff)
            
            if total_years >= 4:
                return f"{max(3, total_years - 2)} to {total_years + 2} Years"
            elif total_years >= 2:
                return f"{total_years} to {total_years + 2} Years"
            elif total_years >= 1:
                return "1 to 3 Years"

    # 4. If no work experience is mentioned anywhere, candidate is a Fresher
    return "Fresher"


def generate_jd(resume_text: str) -> str:
    # Extract skills locally using the offline engine
    skills_data = extract_skills(resume_text)
    skills = [s['skill'].title() for s in skills_data]
    
    if not skills:
        skills = ["Python", "JavaScript", "React", "Node.js", "SQL", "Git", "REST APIs", "Machine Learning"]
        
    # Categorize skills
    categories = {}
    for skill in skills:
        cat = TECH_SKILLS.get(skill.lower())
        if cat:
            categories[cat] = categories.get(cat, 0) + 1
            
    # Detected experience
    detected_exp = detect_experience(resume_text)
    is_fresher = (detected_exp.lower() == "fresher" or "fresher" in detected_exp.lower())
    exp_display = "Fresher" if is_fresher else detected_exp
    
    # Ensure unique list of detected project skills
    unique_skills = []
    for s in skills:
        if s not in unique_skills:
            unique_skills.append(s)
            
    skills_lower_set = {s.lower() for s in unique_skills}
    
    # Curate project skills display list
    project_skills_list = unique_skills[:14]
    if len(project_skills_list) < 8:
        defaults = ["Python", "JavaScript", "React", "Node.js", "Django", "Flask", "SQL", "Machine Learning", "Pandas", "NumPy", "PyTorch", "TensorFlow", "Kubernetes", "Selenium"]
        for d in defaults:
            if d not in project_skills_list and len(project_skills_list) < 14:
                project_skills_list.append(d)
                
    project_skills_str = ", ".join(project_skills_list)

    # Define Comprehensive Archetypes with skill triggers
    archetypes = [
        {
            "id": "full_stack",
            "fresher_title": "Junior Full Stack Developer",
            "exp_title": "Full Stack Developer",
            "triggers": ["react", "react.js", "reactjs", "node", "node.js", "nodejs", "express", "javascript", "typescript", "html", "css", "django", "flask", "mongodb", "mysql", "postgresql", "rest apis", "rest", "next.js", "vue"],
            "category_affinity": ["Frontend", "Backend"],
            "summary_tpl": "We are looking for an enthusiastic {title} with skills in {skills} to develop responsive frontend interfaces and robust backend services.",
            "relevance_tpl": "This role directly aligns with your demonstrated hands-on technical skills in {skills}, enabling you to contribute across the entire web application stack.",
            "responsibilities": [
                "Develop responsive, user-friendly frontend web interfaces and interactive components.",
                "Build server-side REST APIs and implement secure data communication routes.",
                "Design and manage database models (SQL / NoSQL) and optimize queries.",
                "Write clean, modular, and maintainable code with automated unit tests.",
                "Collaborate with peers to review code, troubleshoot issues, and enhance application performance."
            ],
            "base_req": ["JavaScript", "HTML5", "CSS3", "REST APIs", "Git", "SQL"],
            "base_pref": ["React.js", "Node.js / Express", "MongoDB or PostgreSQL", "Docker Basics", "Responsive Web Design"]
        },
        {
            "id": "frontend",
            "fresher_title": "Associate Frontend Developer",
            "exp_title": "Frontend Engineer",
            "triggers": ["react", "react.js", "reactjs", "vue", "vue.js", "angular", "javascript", "typescript", "html", "html5", "css", "css3", "tailwind", "tailwind css", "bootstrap", "sass", "next.js", "redux"],
            "category_affinity": ["Frontend"],
            "summary_tpl": "We are looking for an {title} to craft modern, responsive, and pixel-perfect web interfaces leveraging {skills}.",
            "relevance_tpl": "This role is designed for developers passionate about UI engineering, client-side performance, and modern styling with {skills}.",
            "responsibilities": [
                "Build responsive, pixel-perfect user interface components according to design standards.",
                "Ensure smooth cross-browser compatibility and mobile responsiveness.",
                "Integrate client-side applications with backend JSON REST APIs.",
                "Optimize client-side performance, page load times, and rendering efficiency.",
                "Maintain reusable UI component libraries and design tokens."
            ],
            "base_req": ["JavaScript", "HTML5", "CSS3", "Responsive Design", "Git"],
            "base_pref": ["React.js", "TypeScript", "Tailwind CSS", "UI/UX Principles", "Web Performance Optimization"]
        },
        {
            "id": "python_backend",
            "fresher_title": "Junior Python Developer",
            "exp_title": "Python / Backend Developer",
            "triggers": ["python", "django", "flask", "fastapi", "sql", "postgresql", "mysql", "sqlite", "redis", "rest apis", "rest", "pandas", "numpy"],
            "category_affinity": ["Backend", "Programming"],
            "summary_tpl": "We are looking for a {title} to build scalable server-side logic, data pipelines, and RESTful endpoints using {skills}.",
            "relevance_tpl": "This position matches your Python programming strengths and backend skills in {skills}, providing a direct path to core software engineering.",
            "responsibilities": [
                "Write clean, efficient, and well-documented Python code for backend modules.",
                "Build and test RESTful API services connecting database models.",
                "Perform database operations, write optimized SQL queries, and manage data schemas.",
                "Implement input validation, authentication, and error handling mechanisms.",
                "Write automated unit tests and participate in code reviews."
            ],
            "base_req": ["Python", "SQL", "REST APIs", "Git", "Object-Oriented Programming"],
            "base_pref": ["Django or Flask or FastAPI", "PostgreSQL / MySQL", "Postman", "Linux Commands", "Data Structures"]
        },
        {
            "id": "java_backend",
            "fresher_title": "Junior Java Developer",
            "exp_title": "Java Backend Developer",
            "triggers": ["java", "spring", "spring boot", "hibernate", "microservices", "mysql", "postgresql", "maven", "jdbc", "c++", "c"],
            "category_affinity": ["Backend", "Programming"],
            "summary_tpl": "We are looking for a motivated {title} to develop enterprise server components and reliable backend microservices with {skills}.",
            "relevance_tpl": "This role matches your core programming skills in {skills}, focusing on robust architecture and object-oriented software development.",
            "responsibilities": [
                "Develop enterprise backend services and microservices using Java.",
                "Design relational database schemas and write efficient persistence queries.",
                "Build RESTful APIs and integrate external third-party services.",
                "Participate in unit testing, debugging, and performance profiling.",
                "Adhere to clean coding principles and design patterns."
            ],
            "base_req": ["Java", "Object-Oriented Design", "SQL", "Git", "REST APIs"],
            "base_pref": ["Spring Boot", "MySQL / PostgreSQL", "Maven or Gradle", "Microservices Concepts", "Unit Testing (JUnit)"]
        },
        {
            "id": "ai_ml",
            "fresher_title": "Junior AI / ML Engineer",
            "exp_title": "AI / ML Engineer",
            "triggers": ["machine learning", "deep learning", "artificial intelligence", "pytorch", "tensorflow", "keras", "scikit-learn", "opencv", "nlp", "pandas", "numpy", "python", "google collab", "google colab", "computer vision"],
            "category_affinity": ["AI/ML", "Data Engineering"],
            "summary_tpl": "We are looking for an enthusiastic {title} with expertise in {skills} to develop intelligent algorithms, dataset pipelines, and machine learning components.",
            "relevance_tpl": "This role directly aligns with your project experience and technical foundations in {skills} for predictive modeling and data extraction.",
            "responsibilities": [
                "Assist in building, evaluating, and fine-tuning machine learning models and NLP algorithms.",
                "Prepare, clean, and preprocess structured and unstructured text datasets.",
                "Develop Python scripts and REST API endpoints to integrate ML components.",
                "Test model accuracy, evaluate prediction results, and document experimental findings.",
                "Collaborate with software engineers to deploy and monitor AI features."
            ],
            "base_req": ["Python", "Machine Learning Fundamentals", "Pandas", "NumPy", "Git"],
            "base_pref": ["scikit-learn", "PyTorch or TensorFlow", "REST APIs", "Data Preprocessing", "Model Evaluation"]
        },
        {
            "id": "data_analyst",
            "fresher_title": "Associate Data Analyst",
            "exp_title": "Data Analyst / Data Scientist",
            "triggers": ["data analysis", "pandas", "numpy", "sql", "excel", "tableau", "power bi", "matplotlib", "seaborn", "statistics", "data visualization", "python", "r"],
            "category_affinity": ["Data Engineering", "AI/ML"],
            "summary_tpl": "We are looking for an {title} to analyze datasets, uncover actionable insights, and build interactive reports using {skills}.",
            "relevance_tpl": "This role leverages your strong analytical abilities, SQL querying, and data manipulation skills in {skills}.",
            "responsibilities": [
                "Perform exploratory data analysis (EDA) and visualize key trends.",
                "Write SQL queries and Python scripts to extract, clean, and validate data.",
                "Support engineering teams in feature engineering and test dataset creation.",
                "Create clear summary reports and interactive dashboard charts.",
                "Ensure data integrity and adhere to quality assurance standards."
            ],
            "base_req": ["SQL", "Python", "Data Analysis", "Pandas", "NumPy", "Git"],
            "base_pref": ["Matplotlib / Seaborn", "Tableau / Power BI", "Statistical Modeling", "Excel / Spreadsheets", "Communication Skills"]
        },
        {
            "id": "cloud_devops",
            "fresher_title": "Junior Cloud / DevOps Engineer",
            "exp_title": "Cloud / DevOps Engineer",
            "triggers": ["aws", "aws cloud", "azure", "gcp", "docker", "kubernetes", "ci/cd", "terraform", "linux", "bash", "ansible", "jenkins", "git", "cloud"],
            "category_affinity": ["DevOps", "Cloud", "Tools"],
            "summary_tpl": "We are looking for a {title} to support cloud infrastructure hosting, automated deployment pipelines, and environment setup using {skills}.",
            "relevance_tpl": "This role matches your foundational skills in {skills}, offering an exciting path into cloud computing, containerization, and CI/CD operations.",
            "responsibilities": [
                "Assist in maintaining cloud environments and automated deployment scripts.",
                "Work with container tools like Docker to containerize applications.",
                "Monitor system metrics, log aggregation, and alert configurations.",
                "Write automation scripts using Python, Bash, or PowerShell.",
                "Collaborate with developers to streamline deployment and testing environments."
            ],
            "base_req": ["Linux / Shell Scripting", "Git", "Cloud Fundamentals", "Networking Basics"],
            "base_pref": ["Docker", "AWS / Azure / GCP", "CI/CD Concepts", "Python Scripting", "Infrastructure as Code"]
        },
        {
            "id": "database_engineer",
            "fresher_title": "Associate Database / Data Engineer",
            "exp_title": "Database / Data Engineer",
            "triggers": ["mysql", "mongodb", "postgresql", "oracle", "sqlite", "redis", "cassandra", "sql", "mariadb", "dynamodb", "database design", "etl"],
            "category_affinity": ["Database", "Data Engineering"],
            "summary_tpl": "We are looking for a {title} to design, query, and maintain high-performance database architectures with {skills}.",
            "relevance_tpl": "This position directly utilizes your technical skills in {skills} to ensure data integrity, query optimization, and storage reliability.",
            "responsibilities": [
                "Design and manage relational and NoSQL database schemas.",
                "Write optimized SQL queries, stored procedures, and data indexes.",
                "Assist in database migration, backup routines, and consistency checks.",
                "Integrate database connections with backend services and APIs.",
                "Monitor query latency and implement performance tuning."
            ],
            "base_req": ["SQL", "Database Design", "MySQL or PostgreSQL", "Git"],
            "base_pref": ["MongoDB or Redis", "Database Optimization", "Python Scripting", "ETL Fundamentals", "Data Modeling"]
        },
        {
            "id": "systems_cpp",
            "fresher_title": "Junior C/C++ Software Engineer",
            "exp_title": "C/C++ Systems Software Engineer",
            "triggers": ["c", "c++", "data structures", "algorithms", "linux", "multithreading", "embedded", "operating systems"],
            "category_affinity": ["Programming"],
            "summary_tpl": "We are looking for a {title} to develop high-performance software modules and core computing algorithms utilizing {skills}.",
            "relevance_tpl": "This role matches your low-level programming foundation and algorithmic problem solving in {skills}.",
            "responsibilities": [
                "Write modular, high-efficiency C / C++ code for core system components.",
                "Implement and optimize data structures and memory management routines.",
                "Perform unit testing, debugging, and code profiling on Linux platforms.",
                "Collaborate with engineering teams to integrate hardware and software components.",
                "Ensure code robustness, thread safety, and resource efficiency."
            ],
            "base_req": ["C / C++", "Data Structures & Algorithms", "Memory Management", "Git"],
            "base_pref": ["Linux Environment", "Multithreading", "Object-Oriented Design", "Debugging (GDB)", "System Programming"]
        },
        {
            "id": "software_engineer",
            "fresher_title": "Graduate Software Engineer",
            "exp_title": "Software Engineer",
            "triggers": ["git", "github", "vs code", "pycharm", "intellij", "latex", "problem solving", "communication skills", "leadership", "team work and collaboration"],
            "category_affinity": ["Tools", "Programming"],
            "summary_tpl": "We are looking for a {title} to contribute to full software development lifecycles, application features, and testing with {skills}.",
            "relevance_tpl": "This entry-level position is designed for graduates to apply coding fundamentals in {skills} toward enterprise software delivery.",
            "responsibilities": [
                "Develop and maintain software components under mentorship of senior engineers.",
                "Implement unit tests and participate in quality assurance validation.",
                "Participate in sprint planning, standups, and technical problem solving.",
                "Adopt modern development tools, Git workflows, and coding standards.",
                "Troubleshoot bug reports and enhance application reliability."
            ],
            "base_req": ["Computer Science Fundamentals", "Data Structures", "Git", "Problem Solving"],
            "base_pref": ["Web Development Basics", "Database Basics", "Agile / Scrum Awareness", "Clean Code Practices"],
            "edu_req": "Bachelor's degree in Computer Science, Information Technology, Engineering, Computer Applications (BCA/MCA), or a related technical field."
        },
        {
            "id": "financial_analyst",
            "fresher_title": "Junior Financial Analyst / Accountant",
            "exp_title": "Financial Analyst / Accountant",
            "triggers": [
                "accounting", "accountancy", "financial accounting", "cost accounting", "corporate finance",
                "auditing", "audit", "internal audit", "taxation", "gst", "vat", "income tax", "tally",
                "tally prime", "tally erp", "quickbooks", "sap fico", "financial modeling", "financial reporting",
                "balance sheet", "cash flow", "budgeting", "cpa", "acca", "reconciliation", "payroll"
            ],
            "category_affinity": ["Finance", "Finance & Accounting"],
            "summary_tpl": "We are looking for an analytical and detail-oriented {title} with strengths in {skills} to manage financial reporting, ledger reconciliation, and budget modeling.",
            "relevance_tpl": "This role matches your foundational competence in {skills}, offering an excellent career path in corporate accounting, taxation, and financial analysis.",
            "responsibilities": [
                "Prepare, analyze, and maintain general ledger entries, balance sheets, and cash flow statements.",
                "Perform bank reconciliations, accounts payable/receivable, and routine audit checks.",
                "Assist in statutory tax filings (GST, VAT, Corporate Tax) and regulatory compliance.",
                "Build dynamic spreadsheet models for financial forecasting and budget variances.",
                "Generate management reports and support external audit coordination."
            ],
            "base_req": ["Financial Accounting", "Tally / QuickBooks or SAP", "Excel / Spreadsheets", "Taxation Basics", "Reconciliation"],
            "base_pref": ["Financial Modeling", "GST / VAT Compliance", "Cost Accounting", "Auditing Principles", "Analytical Thinking"],
            "edu_req": "Bachelor's or Master's degree in Commerce (B.Com / M.Com), Finance, Accounting, Business Administration (BBA / MBA), or professional certifications (CA / ACCA / CPA)."
        },
        {
            "id": "business_analyst",
            "fresher_title": "Associate Business Analyst",
            "exp_title": "Business Analyst / Consultant",
            "triggers": [
                "business analysis", "requirements gathering", "stakeholder management", "project management",
                "agile", "scrum", "jira", "process improvement", "business intelligence", "sql", "excel",
                "tableau", "power bi", "flowcharts", "gap analysis", "swot"
            ],
            "category_affinity": ["Business & Management", "Data Engineering", "Soft Skills"],
            "summary_tpl": "We are looking for a proactive {title} with skills in {skills} to bridge business objectives with technical solutions and deliver data-backed insights.",
            "relevance_tpl": "This role leverages your strong analytical thinking, stakeholder collaboration, and requirements mapping abilities in {skills}.",
            "responsibilities": [
                "Liaise with business stakeholders to elicit, analyze, and document functional and technical requirements.",
                "Create user stories, acceptance criteria, and workflow diagrams (BPMN / UML).",
                "Analyze operational datasets using SQL and Excel to uncover growth and efficiency opportunities.",
                "Collaborate with engineering and product teams across Agile sprint cycles.",
                "Design reporting dashboards to track key performance indicators (KPIs)."
            ],
            "base_req": ["Business Requirements Documentation", "Agile / Scrum Fundamentals", "SQL Basics", "Data Analysis (Excel)", "Communication Skills"],
            "base_pref": ["JIRA / Confluence", "Tableau or Power BI", "Process Flow Mapping", "UML Diagrams", "Stakeholder Presentation"],
            "edu_req": "Bachelor's or Master's degree in Business Administration (BBA / MBA), Information Systems, Economics, Commerce, or related quantitative field."
        },
        {
            "id": "hr_talent",
            "fresher_title": "HR & Talent Acquisition Associate",
            "exp_title": "Human Resources Specialist / Recruiter",
            "triggers": [
                "human resources", "recruitment", "talent acquisition", "sourcing", "screening",
                "employee onboarding", "employee engagement", "hr policies", "payroll administration",
                "performance management", "interpersonal skills", "ats", "interviewing", "hr"
            ],
            "category_affinity": ["HR & Operations", "Soft Skills"],
            "summary_tpl": "We are looking for an energetic {title} with skills in {skills} to drive talent acquisition, coordinate employee engagement, and manage HR operations.",
            "relevance_tpl": "This position matches your interpersonal strengths and organizational abilities in {skills} to support people operations and talent pipelines.",
            "responsibilities": [
                "Source, screen, and interview candidates across multiple recruitment channels.",
                "Coordinate interview schedules, candidate communications, and end-to-end recruitment lifecycle.",
                "Facilitate seamless new hire onboarding and orientation programs.",
                "Maintain confidential employee records, attendance, and leave management.",
                "Assist in organizing employee engagement initiatives and internal HR wellness programs."
            ],
            "base_req": ["Talent Sourcing", "Interview Coordination", "Communication Skills", "HR Documentation", "MS Office / Google Workspace"],
            "base_pref": ["ATS Software", "Employee Engagement", "Labor Law Basics", "Payroll Systems", "Conflict Resolution"],
            "edu_req": "Bachelor's or Master's degree in Human Resources, Psychology, Business Administration (BBA / MBA), Humanities, or related discipline."
        },
        {
            "id": "digital_marketing",
            "fresher_title": "Digital Marketing & SEO Associate",
            "exp_title": "Digital Marketing Specialist",
            "triggers": [
                "digital marketing", "seo", "sem", "social media marketing", "content marketing",
                "google analytics", "email marketing", "copywriting", "campaign management", "crm",
                "hubspot", "canva", "figma", "branding", "lead generation"
            ],
            "category_affinity": ["Marketing & Growth", "Tools"],
            "summary_tpl": "We are looking for a creative {title} with skills in {skills} to plan and execute multi-channel digital campaigns that drive brand awareness and inbound leads.",
            "relevance_tpl": "This role matches your creative communication, analytical orientation, and campaign strategies in {skills}.",
            "responsibilities": [
                "Execute search engine optimization (SEO) audits and on-page keyword optimizations.",
                "Manage social media calendar, copywriting, and creative asset publication.",
                "Track traffic, conversions, and campaign metrics using Google Analytics.",
                "Build targeted email marketing sequences and newsletters.",
                "Collaborate with design and content creators to optimize campaign conversion rates."
            ],
            "base_req": ["SEO Fundamentals", "Social Media Marketing", "Content Copywriting", "Google Analytics Basics", "Canva / Design Basics"],
            "base_pref": ["Google Ads / PPC", "Email Marketing Tools (Mailchimp/HubSpot)", "Keyword Research Tools", "A/B Testing", "CRM Management"],
            "edu_req": "Bachelor's degree in Marketing, Mass Communication, Business Administration, Media, or related field."
        },
        {
            "id": "embedded_iot",
            "fresher_title": "Junior Embedded & IoT Engineer",
            "exp_title": "Embedded Systems / IoT Engineer",
            "triggers": [
                "embedded", "embedded systems", "microcontrollers", "arduino", "raspberry pi", "iot",
                "circuit design", "pcb design", "vlsi", "verilog", "vhdl", "plc", "scada",
                "power systems", "matlab", "sensors", "c", "c++"
            ],
            "category_affinity": ["Core Engineering", "Programming"],
            "summary_tpl": "We are looking for a hands-on {title} with skills in {skills} to develop embedded firmware, circuit schematics, and connected IoT hardware devices.",
            "relevance_tpl": "This position matches your core engineering foundation and low-level firmware problem solving in {skills}.",
            "responsibilities": [
                "Write and debug low-level firmware for microcontrollers (ARM, AVR, ESP32, STM32).",
                "Design and simulate circuit schematics and PCB layouts.",
                "Interface hardware sensors, actuators, and wireless modules (Bluetooth, Wi-Fi, LoRa).",
                "Perform bench testing, oscilloscopes/logic analyzer debugging, and hardware validation.",
                "Collaborate with software engineers to integrate cloud telemetry with edge hardware."
            ],
            "base_req": ["Embedded C / C++", "Microcontroller Architectures", "Circuit Troubleshooting", "Git", "Hardware Protocols (I2C, SPI, UART)"],
            "base_pref": ["PCB Design (KiCAD/Eagle)", "RTOS Fundamentals", "MATLAB / Simulink", "IoT Networking Protocols (MQTT)", "Soldering & Prototyping"],
            "edu_req": "Bachelor's degree in Electrical & Electronics Engineering (EEE), Electronics & Communication (ECE), Embedded Systems, or related engineering branch."
        }
    ]

    # Calculate match score for each archetype based strictly on candidate's skills
    scored_archetypes = []
    for arch in archetypes:
        score = 0
        matched_candidate_skills = []
        
        for trig in arch["triggers"]:
            if trig in skills_lower_set:
                score += 3
                # Find original casing
                for s in unique_skills:
                    if s.lower() == trig and s not in matched_candidate_skills:
                        matched_candidate_skills.append(s)
                        
        for aff in arch["category_affinity"]:
            score += categories.get(aff, 0) * 1.5
            
        scored_archetypes.append({
            "archetype": arch,
            "score": score,
            "matched_skills": matched_candidate_skills
        })

    # Sort archetypes by score descending
    scored_archetypes.sort(key=lambda x: x["score"], reverse=True)
    
    # Pick Top 4 distinct archetypes
    selected = scored_archetypes[:4]
    
    # Generate role data objects
    roles_data = []
    signal_scores = [9, 8, 7, 6]
    
    for idx, item in enumerate(selected):
        arch = item["archetype"]
        matched_s = item["matched_skills"]
        
        if matched_s:
            skills_str = ", ".join(matched_s[:5])
        else:
            skills_str = ", ".join(unique_skills[:3]) if unique_skills else "modern software technologies"
            
        title = arch["fresher_title"] if is_fresher else arch["exp_title"]
        summary = arch["summary_tpl"].format(title=title, skills=skills_str)
        relevance = arch["relevance_tpl"].format(title=title, skills=skills_str)
        
        # Build required skills: candidate's actual matched skills first, then base requirements
        req_skills_list = []
        for s in matched_s:
            if s not in req_skills_list:
                req_skills_list.append(s)
        for s in arch["base_req"]:
            if s not in req_skills_list:
                req_skills_list.append(s)
                
        pref_skills_list = [s for s in arch["base_pref"] if s not in req_skills_list]
        
        roles_data.append({
            "title": title,
            "signals": signal_scores[idx] if idx < len(signal_scores) else 6,
            "summary": summary,
            "relevance": relevance,
            "responsibilities": arch["responsibilities"],
            "req_skills": req_skills_list[:8],
            "pref_skills": pref_skills_list[:6],
            "edu_req": arch.get("edu_req", "Bachelor's degree in Computer Science, Information Technology, Engineering, Data Science, or a related technical field.")
        })

    # Build the multi-page Markdown output
    # Page 1: Overview
    overview_page = f"""# Suitable Job Descriptions
Based on the uploaded resume, detected skills, and relevant industry job roles

**Detected experience:** {exp_display}
**Detected project skills:** {project_skills_str}

## How this report helps
These recommendations are tailored directly from the uploaded resume's skills and experience level. Use the highest-ranked role as the primary target, then use the required and preferred skills to improve resume keywords, projects, and interview preparation.

## Project-focused priorities
• Tailored to candidate's actual extracted skills and career stage
• Semantic job matching and ATS keyword alignment
• Practical skill benchmarks for technical interviews
• Clear, measurable recommendations for career advancement"""

    role_pages = []
    for idx, r in enumerate(roles_data, 1):
        dedup_req = []
        for s in r["req_skills"]:
            if s and not any(s.lower() == existing.lower() for existing in dedup_req):
                dedup_req.append(s)
        
        dedup_pref = []
        for s in r["pref_skills"]:
            if s and not any(s.lower() == existing.lower() for existing in dedup_req) and not any(s.lower() == existing.lower() for existing in dedup_pref):
                dedup_pref.append(s)

        req_skills_str = "\n".join([f"• {s}" for s in dedup_req])
        pref_skills_str = "\n".join([f"• {s}" for s in dedup_pref])
        resp_str = "\n".join([f"• {resp}" for resp in r["responsibilities"]])

        role_page = f"""# {idx}. {r['title']} | Match signals: {r['signals']}

## Job Summary
{r['summary']}

## Role Relevance
{r['relevance']}

## Key Responsibilities
{resp_str}

## Required Technical Skills
{req_skills_str}

## Preferred Skills
{pref_skills_str}

## Educational Qualifications
{r['edu_req']}

## Experience Level
{exp_display}

## Employment Type
Full-time"""
        role_pages.append(role_page)

    full_output = overview_page + "\n\n---\n\n" + "\n\n---\n\n".join(role_pages)
    return full_output


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Missing resume text file path")
        sys.exit(1)
        
    resume_path = sys.argv[1]
    
    try:
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()
            
        jd = generate_jd(resume_text)
        print(jd)
    except Exception as e:
        import traceback
        print(f"Error reading or processing file: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)

