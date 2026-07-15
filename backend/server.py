from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

def send_welcome_email(to_email, user_name):
    sender_email = os.getenv("EMAIL_USER")
    sender_pass = os.getenv("EMAIL_PASS")
    
    if not sender_email or not sender_pass or sender_email == "your-email@gmail.com":
        print("Email configuration missing or using placeholders. Skipping email sending.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = "Welcome to Resume Analyzer AI!"
        
        body = f"<h2>Welcome {user_name}!</h2><p>Thank you for signing up for Resume Analyzer AI.</p><p>We are excited to help you optimize your resume and land your dream job!</p><br><p>Best Regards,</p><p>The Resume Analyzer AI Team</p>"
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"Welcome email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {str(e)}")

# Import the upgraded analyzer engine
from analyzer import extract_skills, match_skills, get_gemini_suggestions

load_dotenv()

app = Flask(__name__)
# Enable comprehensive CORS for all origins and headers
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# MongoDB Setup
try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client["resumeanalyzer"]
    users_collection = db["users"]
    resumes_collection = db["resumes"]
    # Test connection
    client.server_info()
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Could not connect to MongoDB: {e}")


def extract_text_from_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text


@app.route("/signup", methods=["POST", "OPTIONS"])
def signup():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data format"}), 400

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    if users_collection.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 400

    import urllib.parse
    hashed_password = generate_password_hash(password)

    safe_name = urllib.parse.quote(name)
    user_doc = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "role": "Senior Software Engineer",
        "dob": "01-01-2005",
        "profileImage": f"https://api.dicebear.com/7.x/initials/svg?seed={safe_name}",
        "history": []
    }
    users_collection.insert_one(user_doc)

    # Send welcome email in a separate thread so it doesn't block the response
    threading.Thread(target=send_welcome_email, args=(email, name)).start()

    return jsonify({"message": "Account created successfully"}), 201


@app.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data format"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    user = users_collection.find_one({"email": email})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid login credentials"}), 401

    return jsonify({
        "message": "Login successful",
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "Senior Software Engineer"),
        "dob": user.get("dob", "01-01-2005"),
        "profileImage": user.get("profileImage", ""),
        "history": user.get("history", [])
    }), 200


@app.route("/get_profile", methods=["GET", "OPTIONS"])
def get_profile():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email required"}), 400

    user = users_collection.find_one({"email": email})
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "Senior Software Engineer"),
        "dob": user.get("dob", "01-01-2005"),
        "profileImage": user.get("profileImage", ""),
        "history": user.get("history", [])
    }), 200


@app.route("/update_profile", methods=["POST", "OPTIONS"])
def update_profile():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data format"}), 400

    email = data.get("email")
    if not email:
        return jsonify({"error": "Email required"}), 400

    update_fields = {}
    if "name" in data: update_fields["name"] = data["name"]
    if "role" in data: update_fields["role"] = data["role"]
    if "dob" in data: update_fields["dob"] = data["dob"]
    if "profileImage" in data: update_fields["profileImage"] = data["profileImage"]

    if update_fields:
        users_collection.update_one({"email": email}, {"$set": update_fields})

    return jsonify({"message": "Profile updated successfully in MongoDB"}), 200


@app.route("/analyze", methods=["POST", "OPTIONS"])
def analyze():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    resume_file = request.files.get("resume")
    job_text = request.form.get("jobText", "")
    email = request.form.get("email")

    if not resume_file or not job_text:
        return jsonify({"error": "Resume and job description are required"}), 400

    try:
        file_bytes = resume_file.read()

        # Store raw binary resume in MongoDB resumes collection
        if email:
            resumes_collection.insert_one({
                "email": email,
                "filename": resume_file.filename,
                "file_data": file_bytes,
                "timestamp": datetime.datetime.utcnow()
            })

        resume_text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return jsonify({"error": "Invalid PDF file"}), 400

    # ── UPGRADED: Two-layer skill extraction ──────────────────────────────
    resume_skills = extract_skills(resume_text)
    job_skills    = extract_skills(job_text)

    # ── UPGRADED: Semantic matching with all-mpnet-base-v2 ───────────────
    result = match_skills(resume_skills, job_skills, threshold=0.72)

    # ── UPGRADED: Gemini AI suggestions for missing skills ────────────────
    job_context = job_text[:300]
    suggestions = get_gemini_suggestions(result["missingSkills"], job_context)

    # Attach suggestions to missing skills
    for skill_obj in result["missingSkills"]:
        skill_name = skill_obj["skill"]
        skill_obj["suggestion"] = suggestions.get(skill_name,
            suggestions.get(skill_name.lower(), f"Research and add {skill_name} to your skill set."))

    # Attach generic suggestions to matched skills too (for display)
    result["suggestions"] = {
        s["skill"]: s.get("suggestion", "") for s in result["missingSkills"]
    }

    # Overall feedback
    match_pct = result["matchPercent"]
    if match_pct >= 80:
        result["overallFeedback"] = "Excellent match! Your resume is ATS-optimized and closely aligned to this role."
    elif match_pct >= 60:
        result["overallFeedback"] = "Good alignment. Adding a few missing skills will significantly boost your ATS score."
    elif match_pct >= 40:
        result["overallFeedback"] = "Fair match. Focus on the high-priority missing skills to strengthen your application."
    else:
        result["overallFeedback"] = "Your resume needs targeted improvements. Prioritize the missing skills listed below."

    # ── Save to user's history in MongoDB ────────────────────────────────
    if email:
        import time
        import base64
        file_data_url = f"data:application/pdf;base64,{base64.b64encode(file_bytes).decode('utf-8')}"
        first_line_job = job_text.split("\n")[0][:50] + ("..." if len(job_text) > 50 else "")

        history_item = {
            "id": f"hist-{int(time.time()*1000)}",
            "timestamp": datetime.datetime.now().strftime("%b %d, %Y, %I:%M %p"),
            "fileName": resume_file.filename,
            "fileSize": f"{len(file_bytes)/(1024*1024):.2f} MB",
            "fileType": resume_file.filename.split('.')[-1].upper() if '.' in resume_file.filename else "PDF",
            "fileDataUrl": file_data_url,
            "jobTitle": first_line_job or "Target Job Description",
            "data": result
        }

        users_collection.update_one(
            {"email": email},
            {"$push": {"history": {"$each": [history_item], "$position": 0}}}
        )

    return jsonify(result)


@app.route("/delete_history", methods=["POST", "OPTIONS"])
def delete_history():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    if not data: return jsonify({"error": "Invalid data format"}), 400
    email = data.get("email")
    item_id = data.get("id")

    if email and item_id:
        users_collection.update_one(
            {"email": email},
            {"$pull": {"history": {"id": item_id}}}
        )
        return jsonify({"message": "History item deleted successfully from MongoDB"}), 200
    return jsonify({"error": "Missing email or id"}), 400


if __name__ == "__main__":
    print("Loading NLP models (first start may take ~30s to download all-mpnet-base-v2)...")
    # Pre-warm models at startup to avoid first-request latency
    from analyzer import get_nlp, get_sbert
    get_nlp()
    get_sbert()
    print("Models loaded! Server starting on http://0.0.0.0:3000")
    app.run(host="0.0.0.0", port=3000, debug=False)