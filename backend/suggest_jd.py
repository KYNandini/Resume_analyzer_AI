import os
import sys
import random
from analyzer import extract_skills, TECH_SKILLS

def generate_jd(resume_text: str) -> str:
    # 1. Extract skills locally using the existing offline engine
    skills_data = extract_skills(resume_text)
    skills = [s['skill'].title() for s in skills_data]
    
    # If no skills found, use some generic fallbacks
    if not skills:
        skills = ["Communication", "Problem Solving", "Teamwork", "Time Management", "Project Management"]
        
    # Categorize skills to figure out the primary domain
    categories = {}
    for skill in skills:
        cat = TECH_SKILLS.get(skill.lower())
        if cat:
            categories[cat] = categories.get(cat, 0) + 1
            
    # Sort categories by count
    sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
    primary_domain = sorted_cats[0][0] if sorted_cats else "Technology"
    
    # Select top skills to feature prominently
    top_skills = skills[:8]
    if len(top_skills) < 8:
        # Pad if not enough skills extracted
        top_skills += ["Agile/Scrum", "Git", "Testing", "CI/CD", "System Design"][:8-len(top_skills)]
        
    skills_str = ", ".join(top_skills[:3])
    
    # Template Generation
    templates = []
    
    # Generate 3 options based on the skills
    titles = [
        f"Senior {primary_domain} Engineer / Specialist",
        f"{primary_domain} Consultant & Analyst",
        f"Lead Technical Solutions Architect ({primary_domain})"
    ]
    
    cats_only = [c for c, _ in sorted_cats]
    if "Programming" in cats_only:
        titles[0] = "Senior Software Engineer"
        titles[1] = "Full Stack Developer"
    elif "Data" in cats_only:
        titles[0] = "Data Scientist / Machine Learning Engineer"
        titles[1] = "Senior Data Analyst"
    elif "Cloud" in cats_only or "DevOps" in cats_only:
        titles[0] = "Senior Cloud / DevOps Engineer"
        titles[1] = "Site Reliability Engineer (SRE)"
        
    for i, title in enumerate(titles):
        # Shuffle slightly to make them distinct
        random.shuffle(top_skills)
        core_reqs = "\n".join([f"- Proficiency in {s}" for s in top_skills[:4]])
        bonus_reqs = "\n".join([f"- Experience with {s} is a plus" for s in top_skills[4:6]])
        
        template = f"""# Option {i+1}: {title}

**About the Role**
We are seeking an experienced and highly motivated {title} to join our dynamic team. You will be responsible for driving technical excellence, collaborating with cross-functional teams, and leveraging your expertise in {skills_str} to deliver high-quality solutions.

**Key Responsibilities**
- Design, develop, and implement scalable solutions within the {primary_domain} domain.
- Collaborate with product managers, designers, and other stakeholders to understand business requirements.
- Leverage your expertise in {top_skills[0]} and {top_skills[1]} to optimize system performance and reliability.
- Mentor junior team members and conduct code/architecture reviews.
- Drive best practices in deployment, testing, and continuous integration.

**Required Experience**
- 3+ years of professional experience in a related {primary_domain} role.
- Demonstrated ability to lead projects from conception to deployment.
- Strong analytical and problem-solving capabilities in high-stakes environments.

**Required Qualifications/Skills**
{core_reqs}
{bonus_reqs}
- Excellent communication and teamwork skills.
- Bachelor's degree in Computer Science, Engineering, or a related field (or equivalent practical experience)."""
        templates.append(template)
        
    return "\n\n---\n\n".join(templates)

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
