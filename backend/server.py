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
import random
import time
from email_validator import validate_email, EmailNotValidError

# Temporary in-memory store for password-reset OTPs: {email: {otp, expires}}
_reset_otps = {}

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

def send_scorecard_email(to_email, user_name, result, is_daily_reminder=False):
    sender_email = os.getenv("EMAIL_USER")
    sender_pass = os.getenv("EMAIL_PASS")
    
    if not sender_email or not sender_pass or sender_email == "your-email@gmail.com":
        print("Email configuration missing. Skipping scorecard email.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = "Your Daily ATS Scorecard Reminder!" if is_daily_reminder else "Your Resume ATS Scorecard – Resume Analyzer AI"
        
        match_pct = result.get('matchPercent', 0)
        feedback = result.get('overallFeedback', '')
        matched = result.get('matchedCount', 0)
        total = result.get('totalSkills', 0)
        missing = total - matched
        
        missing_skills_html = ""
        if result.get('missingSkills'):
            skills = [s.get('skill') for s in result['missingSkills'][:5]]
            missing_skills_html = f"<p><strong>Top Skills to Add:</strong> {', '.join(skills)}</p>"
        
        if is_daily_reminder:
            header_text = "Keep Improving Your Resume!"
            intro_text = "This is your daily reminder to keep pushing your ATS score higher! Review your missing skills below, update your resume, and re-upload the improved version to our dashboard."
            cta_text = "Log back into your dashboard to re-upload your improved resume and track your progress!"
        else:
            header_text = "Your Resume Analysis is Ready!"
            intro_text = "We've successfully analyzed your resume against the provided job description."
            cta_text = "Log back into your dashboard to view the full detailed report, including AI-generated suggestions to improve your missing skills!"

        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;border:1px solid #ddd;border-radius:10px;">
          <h2 style="color:#00a896;">{header_text}</h2>
          <p>Hi <strong>{user_name}</strong>,</p>
          <p>{intro_text}</p>
          
          <div style="background:#f0fdfa;border:1px solid #14b8a6;padding:15px;border-radius:8px;margin:20px 0;">
              <h3 style="margin-top:0;color:#0f766e;text-align:center;">Current ATS Match Score: {match_pct}%</h3>
              <p style="text-align:center;color:#0f172a;margin-bottom:0;">{feedback}</p>
          </div>
          
          <p><strong>Matched Skills:</strong> {matched} / {total}</p>
          <p><strong>Missing Skills:</strong> {missing}</p>
          {missing_skills_html}
          
          <p>{cta_text}</p>
          <br>
          <p>— The Resume Analyzer AI Team</p>
        </div>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"Scorecard email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send scorecard email to {to_email}: {str(e)}")

# Import the upgraded analyzer engine
from analyzer import extract_skills, match_skills, get_gemini_suggestions

load_dotenv()

app = Flask(__name__)
# Enable comprehensive CORS for all origins and headers
CORS(app, resources={r"/*": {"origins": "*"}})

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

    try:
        validation = validate_email(email, check_deliverability=True)
        email = validation.normalized
    except EmailNotValidError as e:
        return jsonify({"error": f"Email not found or invalid: {str(e)}"}), 400

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
    if not user:
        return jsonify({"error": "Email not found"}), 404
    if not check_password_hash(user["password"], password):
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
    if "dob" in data:
        dob_val = data["dob"]
        import re
        if re.match(r"^(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[012])-(19|20)\d\d$", dob_val):
            update_fields["dob"] = dob_val
        else:
            return jsonify({"error": "Invalid date of birth format (must be DD-MM-YYYY)"}), 400
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

    if not resume_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a valid PDF document (.pdf). Image files (like JPEG or PNG) are not supported for text parsing."}), 400

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

        user = users_collection.find_one({"email": email})
        user_name = user.get("name", "there") if user else "there"
        threading.Thread(target=send_scorecard_email, args=(email, user_name, result)).start()

    return jsonify(result)


@app.route("/suggest-jd", methods=["POST", "OPTIONS"])
def suggest_jd():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    resume_file = request.files.get("resume")
    if not resume_file:
        return jsonify({"error": "Resume is required"}), 400

    if not resume_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a valid PDF document (.pdf)."}), 400

    try:
        file_bytes = resume_file.read()
        resume_text = extract_text_from_pdf(file_bytes)
        
        from suggest_jd import generate_jd
        jd = generate_jd(resume_text)
        
        return jsonify({"suggestedJD": jd})
    except Exception as e:
        print(f"Error suggesting JD: {e}")
        return jsonify({"error": "Failed to suggest JD"}), 500


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


@app.route("/forgot-password", methods=["POST", "OPTIONS"])
def forgot_password():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data format"}), 400

    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = users_collection.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}})
    if not user:
        # Generic message to prevent email enumeration
        return jsonify({"message": "If this email is registered, an OTP has been sent."}), 200

    otp = str(random.randint(100000, 999999))
    expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    _reset_otps[email] = {"otp": otp, "expires": expires}

    sender_email = os.getenv("EMAIL_USER")
    sender_pass = os.getenv("EMAIL_PASS")

    def send_reset_otp():
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = user["email"]
            msg['Subject'] = "Password Reset OTP – Resume Analyzer AI"
            body = f"""
            <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:30px;border:1px solid #e0e0e0;border-radius:10px;">
              <h2 style="color:#00a896;">Password Reset Request</h2>
              <p>Hi <strong>{user.get('name','there')}</strong>,</p>
              <p>Use the OTP below to reset your password. It is valid for <strong>10 minutes</strong>.</p>
              <div style="font-size:2rem;font-weight:bold;letter-spacing:8px;text-align:center;
                          background:#f0f2f5;padding:16px;border-radius:8px;margin:20px 0;color:#1a1a2e;">
                {otp}
              </div>
              <p style="color:#888;font-size:0.82rem;">If you did not request this, please ignore this email.</p>
              <p>— The Resume Analyzer AI Team</p>
            </div>
            """
            msg.attach(MIMEText(body, 'html'))
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, user["email"], msg.as_string())
            server.quit()
            print(f"Password reset OTP sent to {user['email']}")
        except Exception as e:
            print(f"Failed to send reset OTP: {e}")

    threading.Thread(target=send_reset_otp).start()
    return jsonify({"message": "If this email is registered, an OTP has been sent."}), 200


@app.route("/verify-reset-otp", methods=["POST", "OPTIONS"])
def verify_reset_otp():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data format"}), 400

    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    record = _reset_otps.get(email)
    if not record:
        return jsonify({"error": "No OTP was requested for this email"}), 400
    if datetime.datetime.utcnow() > record["expires"]:
        del _reset_otps[email]
        return jsonify({"error": "OTP has expired. Please request a new one."}), 400
    if record["otp"] != otp:
        return jsonify({"error": "Incorrect OTP. Please try again."}), 400

    return jsonify({"message": "OTP verified successfully"}), 200


@app.route("/reset-password", methods=["POST", "OPTIONS"])
def reset_password():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data format"}), 400

    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()
    new_password = data.get("newPassword", "").strip()

    if not email or not otp or not new_password:
        return jsonify({"error": "Email, OTP, and new password are required"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    record = _reset_otps.get(email)
    if not record:
        return jsonify({"error": "No OTP was requested for this email"}), 400
    if datetime.datetime.utcnow() > record["expires"]:
        del _reset_otps[email]
        return jsonify({"error": "OTP has expired. Please request a new one."}), 400
    if record["otp"] != otp:
        return jsonify({"error": "Incorrect OTP. Please try again."}), 400

    hashed = generate_password_hash(new_password)
    users_collection.update_one(
        {"email": {"$regex": f"^{email}$", "$options": "i"}},
        {"$set": {"password": hashed}}
    )
    del _reset_otps[email]
    return jsonify({"message": "Password reset successfully!"}), 200


def daily_reminder_job():
    while True:
        now = datetime.datetime.now()
        target = now.replace(hour=21, minute=30, second=0, microsecond=0)
        
        if now >= target:
            target += datetime.timedelta(days=1)
            
        sleep_seconds = (target - now).total_seconds()
        print(f"Daily reminder thread sleeping until {target.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(sleep_seconds)
        
        print("Executing daily scorecard reminders...")
        try:
            users = users_collection.find({})
            for user in users:
                history = user.get("history", [])
                if history and len(history) > 0:
                    latest = history[0]
                    result = latest.get("data")
                    if result:
                        send_scorecard_email(user["email"], user.get("name", "there"), result, is_daily_reminder=True)
        except Exception as e:
            print(f"Error in daily reminder job: {e}")

if __name__ == "__main__":
    threading.Thread(target=daily_reminder_job, daemon=True).start()
    print("Loading NLP models (first start may take ~30s to download all-mpnet-base-v2)...")
    # Pre-warm models at startup to avoid first-request latency
    from analyzer import get_nlp, get_sbert
    get_nlp()
    get_sbert()
    print("Models loaded! Server starting on http://0.0.0.0:3000")
    app.run(host="0.0.0.0", port=3000, debug=False)