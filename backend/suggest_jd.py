import os
import sys
import re
from dotenv import load_dotenv

load_dotenv()

def generate_jd(resume_text: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    if not api_key:
        return "Error: GEMINI_API_KEY not found in backend/.env. Please configure it to use this feature."
        
    try:
        import importlib
        genai_mod = importlib.import_module("google.genai")
        client = genai_mod.Client(api_key=api_key)

        prompt = (
            "You are an expert technical recruiter and hiring manager. I will provide you with a resume text. "
            "Your task is to generate EXACTLY 3 distinct, professional, realistic, and comprehensive Job Descriptions (JDs) that match the candidate's skills and experience level found in the resume. "
            "The 3 job descriptions should represent different potential roles or career paths the candidate could take based on their profile. "
            "Format the output clearly. For each JD, use a prominent header (e.g., '# Option 1: [Job Title]'), and include exactly these sections: About the Role, Key Responsibilities, Required Experience, and Required Qualifications/Skills. "
            "Separate each of the 3 Job Descriptions with a horizontal line (---). Make them look like real job postings. "
            "Here is the resume text:\n\n"
            f"{resume_text[:25000]}" # cap for speed and token limits
        )
        
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        import sys
        print(f"[Gemini] Error generating JD: {e}", file=sys.stderr)
        return f"Error: Could not generate JD due to an AI service error. Details: {str(e)}"

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
