from flask import Flask, request, jsonify, send_from_directory
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
import subprocess
import uuid
import sys
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Temporary in-memory store for password-reset OTPs: {email: {otp, expires}}
_reset_otps = {}
# Temporary in-memory store for signup registration OTPs: {email: {otp, expires, name, password}}
_signup_otps = {}

def is_online():
    import socket
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2)
        return True
    except OSError:
        return False

def send_signup_otp_email(to_email, user_name, otp):
    sender_email = os.getenv("EMAIL_USER")
    sender_pass = os.getenv("EMAIL_PASS")
    
    if not sender_email or not sender_pass or sender_email == "your-email@gmail.com":
        print(f"[Email] Skipping signup OTP to {to_email}: EMAIL_USER or EMAIL_PASS not configured.", flush=True)
        return

    sender_pass = sender_pass.strip().replace(" ", "")

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = "Account Verification OTP – Resume Analyzer AI"
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:30px;border:1px solid #e0e0e0;border-radius:10px;">
          <h2 style="color:#00a896;">Verify Your Account</h2>
          <p>Hi <strong>{user_name}</strong>,</p>
          <p>Thank you for registering with Resume Analyzer AI. Please use the verification OTP below to complete your registration. It is valid for <strong>10 minutes</strong>.</p>
          <div style="font-size:2rem;font-weight:bold;letter-spacing:8px;text-align:center;
                      background:#f0f2f5;padding:16px;border-radius:8px;margin:20px 0;color:#1a1a2e;">
            {otp}
          </div>
          <p style="color:#888;font-size:0.82rem;">If you did not request this account, please ignore this email.</p>
          <p>— The Resume Analyzer AI Team</p>
        </div>
        """
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"✅ Registration OTP email sent successfully to {to_email}", flush=True)
    except Exception as e:
        print(f"❌ Failed to send registration OTP email to {to_email}: {e}", flush=True)

def send_reset_otp_email(to_email, otp):
    sender_email = os.getenv("EMAIL_USER")
    sender_pass = os.getenv("EMAIL_PASS")
    
    if not sender_email or not sender_pass or sender_email == "your-email@gmail.com":
        print(f"[Email] Skipping password reset email to {to_email}: EMAIL_USER or EMAIL_PASS not configured.", flush=True)
        return

    sender_pass = sender_pass.strip().replace(" ", "")

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = "Password Reset OTP – Resume Analyzer AI"
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:30px;border:1px solid #e0e0e0;border-radius:10px;">
          <h2 style="color:#00a896;">Password Reset Request</h2>
          <p>We received a request to reset your password. Use the verification OTP below. It is valid for <strong>10 minutes</strong>.</p>
          <div style="font-size:2rem;font-weight:bold;letter-spacing:8px;text-align:center;
                      background:#f0f2f5;padding:16px;border-radius:8px;margin:20px 0;color:#1a1a2e;">
            {otp}
          </div>
          <p style="color:#888;font-size:0.82rem;">If you did not request a password reset, please ignore this email.</p>
          <p>— The Resume Analyzer AI Team</p>
        </div>
        """
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"✅ Reset OTP email sent successfully to {to_email}", flush=True)
    except Exception as e:
        print(f"❌ Failed to send reset OTP email to {to_email}: {e}", flush=True)

def send_welcome_email(to_email, user_name):
    sender_email = os.getenv("EMAIL_USER")
    sender_pass = os.getenv("EMAIL_PASS")
    
    if not sender_email or not sender_pass or sender_email == "your-email@gmail.com":
        return

    sender_pass = sender_pass.strip().replace(" ", "")

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = "Welcome to Resume Analyzer AI!"
        
        body = f"<h2>Welcome {user_name}!</h2><p>Thank you for signing up for Resume Analyzer AI.</p><p>We are excited to help you optimize your resume and land your dream job!</p><br><p>Best Regards,</p><p>The Resume Analyzer AI Team</p>"
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"✅ Welcome email sent to {to_email}", flush=True)
    except Exception as e:
        print(f"❌ Failed to send welcome email to {to_email}: {e}", flush=True)
        print(f"Welcome email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {str(e)}")

def send_scorecard_email(to_email, user_name, result, is_daily_reminder=False):
    sender_email = os.getenv("EMAIL_USER")
    sender_pass = os.getenv("EMAIL_PASS")
    
    if not sender_email or not sender_pass or sender_email == "your-email@gmail.com":
        print(f"[Email] Skipping scorecard email to {to_email}: EMAIL_USER not configured.", flush=True)
        return

    sender_pass = sender_pass.strip().replace(" ", "")

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
        
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"Scorecard email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send scorecard email to {to_email}: {str(e)}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from analyzer import extract_skills, match_skills, get_gemini_suggestions, generate_tailored_resume
except ImportError:
    from backend.analyzer import extract_skills, match_skills, get_gemini_suggestions, generate_tailored_resume

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path) if os.path.exists(env_path) else load_dotenv()

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
# Enable comprehensive CORS for all origins and headers
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/")
def serve_index():
    return send_from_directory(frontend_dir, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    file_path = os.path.join(frontend_dir, path)
    if os.path.exists(file_path):
        return send_from_directory(frontend_dir, path)
    return jsonify({"error": "Not found"}), 404

# MongoDB Setup
try:
    import certifi
    ca = certifi.where()
except Exception:
    ca = None

try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    if ca and ("mongodb+srv://" in mongo_uri or "ssl=true" in mongo_uri.lower() or "tls=true" in mongo_uri.lower()):
        client = MongoClient(mongo_uri, tlsCAFile=ca)
    else:
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
    
    # If standard text extraction yielded almost nothing, the PDF is a scanned image or photo!
    if len(text.strip()) < 30:
        print("[PDF Extract] Text layer is empty or scanned image. Invoking Gemini Vision OCR fallback...")
        try:
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-3.8-flash")
                ocr_texts = []
                for page in doc:
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    resp = model.generate_content([
                        {"mime_type": "image/png", "data": img_bytes},
                        "Extract all text from this resume image accurately, preserving table contents and sections in clean text."
                    ])
                    if resp and resp.text:
                        ocr_texts.append(resp.text)
                if ocr_texts:
                    text = "\n\n".join(ocr_texts)
                    print(f"[PDF Extract] Gemini Vision OCR extracted {len(text)} characters!")
        except Exception as ocr_err:
            print(f"[PDF Extract] OCR error: {ocr_err}")
            
    return text


@app.route("/signup-otp", methods=["POST", "OPTIONS"])
def signup_otp():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data format"}), 400

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not name or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        validation = validate_email(email, check_deliverability=True)
        email = validation.normalized.lower()
    except EmailNotValidError as e:
        return jsonify({"error": f"Email not found or invalid: {str(e)}"}), 400

    if users_collection.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}}):
        return jsonify({"error": "Email is already registered. Please sign in."}), 400

    otp = str(random.randint(100000, 999999))
    expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    _signup_otps[email] = {
        "otp": otp,
        "expires": expires,
        "name": name,
        "password": password
    }

    # Always display OTP prominently in the terminal
    print("\n" + "="*50, flush=True)
    print(f"🔑 [SIGNUP REGISTRATION OTP] For: {email} ({name})", flush=True)
    print(f"👉 OTP CODE: {otp} (Valid for 10 minutes)", flush=True)
    print("="*50 + "\n", flush=True)

    threading.Thread(target=send_signup_otp_email, args=(email, name, otp)).start()
    return jsonify({"message": f"OTP sent to {email}. Please verify to complete registration.", "otp": otp if not is_online() else None}), 200


@app.route("/verify-signup-otp", methods=["POST", "OPTIONS"])
def verify_signup_otp():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data format"}), 400

    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    record = _signup_otps.get(email)
    if not record:
        return jsonify({"error": "OTP expired or not found. Please request a new OTP."}), 400

    if datetime.datetime.utcnow() > record["expires"]:
        del _signup_otps[email]
        return jsonify({"error": "OTP has expired. Please request a new OTP."}), 400

    if record["otp"] != otp:
        return jsonify({"error": "Invalid OTP. Please check and try again."}), 400

    import urllib.parse
    name = record["name"]
    raw_password = record["password"]
    hashed_password = generate_password_hash(raw_password)
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
    del _signup_otps[email]

    print(f"✅ [REGISTRATION COMPLETE] Account successfully created for: {email}\n", flush=True)

    # Send welcome email in background
    threading.Thread(target=send_welcome_email, args=(email, name)).start()

    return jsonify({"message": "Account created successfully"}), 201


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
        "shortBio": user.get("shortBio", ""),
        "preferredJobTitle": user.get("preferredJobTitle", ""),
        "preferredLocation": user.get("preferredLocation", ""),
        "workArrangement": user.get("workArrangement", ""),
        "employmentType": user.get("employmentType", ""),
        "history": user.get("history", [])
    }), 200


@app.route("/forgot-password", methods=["POST", "OPTIONS"])
def forgot_password():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = users_collection.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}})
    if not user:
        return jsonify({"error": "No account found with this email"}), 404

    otp = str(random.randint(100000, 999999))
    expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    _reset_otps[email] = {"otp": otp, "expires": expires}

    print(f"🔑 [PASSWORD RESET OTP] For: {email} | Code: {otp}", flush=True)
    threading.Thread(target=send_reset_otp_email, args=(email, otp)).start()
    return jsonify({"message": "Password reset OTP sent to email."}), 200


@app.route("/verify-reset-otp", methods=["POST", "OPTIONS"])
def verify_reset_otp():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    record = _reset_otps.get(email)
    if not record:
        return jsonify({"error": "No OTP request found for this email"}), 400
    if datetime.datetime.utcnow() > record["expires"]:
        del _reset_otps[email]
        return jsonify({"error": "OTP has expired. Please request a new one."}), 400
    if record["otp"] != otp:
        return jsonify({"error": "Invalid OTP code"}), 400

    return jsonify({"message": "OTP verified successfully"}), 200


@app.route("/reset-password", methods=["POST", "OPTIONS"])
def reset_password():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()
    new_password = data.get("newPassword", "").strip()

    if not email or not otp or not new_password:
        return jsonify({"error": "Missing required fields"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    record = _reset_otps.get(email)
    if not record:
        return jsonify({"error": "No OTP request found for this email"}), 400
    if datetime.datetime.utcnow() > record["expires"]:
        del _reset_otps[email]
        return jsonify({"error": "OTP has expired. Please request a new one."}), 400
    if record["otp"] != otp:
        return jsonify({"error": "Invalid OTP code"}), 400

    hashed_password = generate_password_hash(new_password)
    users_collection.update_one({"email": {"$regex": f"^{email}$", "$options": "i"}}, {"$set": {"password": hashed_password}})
    del _reset_otps[email]
    print(f"✅ Password successfully reset for: {email}", flush=True)
    return jsonify({"message": "Password reset successfully"}), 200


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
        "shortBio": user.get("shortBio", ""),
        "preferredJobTitle": user.get("preferredJobTitle", ""),
        "preferredLocation": user.get("preferredLocation", ""),
        "workArrangement": user.get("workArrangement", ""),
        "employmentType": user.get("employmentType", ""),
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
    if "shortBio" in data: update_fields["shortBio"] = data["shortBio"]
    if "preferredJobTitle" in data: update_fields["preferredJobTitle"] = data["preferredJobTitle"]
    if "preferredLocation" in data: update_fields["preferredLocation"] = data["preferredLocation"]
    if "workArrangement" in data: update_fields["workArrangement"] = data["workArrangement"]
    if "employmentType" in data: update_fields["employmentType"] = data["employmentType"]

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
            "fullJobDesc": job_text,
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


@app.route("/build-resume", methods=["POST", "OPTIONS"])
def build_resume():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    resume_file = request.files.get("resume")
    job_text = request.form.get("jobText", "")

    if not resume_file or not job_text:
        return jsonify({"error": "Resume and job description are required"}), 400

    if not resume_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a valid PDF document (.pdf)."}), 400

    short_bio = request.form.get("shortBio", "")
    pref_title = request.form.get("prefTitle", "")
    pref_loc = request.form.get("prefLoc", "")
    template = request.form.get("template", "modern")
    
    extra_missing_skills = []
    missing_skills_raw = request.form.get("missingSkills", "")
    if missing_skills_raw:
        try:
            extra_missing_skills = json.loads(missing_skills_raw)
        except Exception as ex:
            print(f"[build-resume] JSON parse error on missingSkills: {ex}")

    print(f"[build-resume] Received {len(extra_missing_skills)} missing skills, template: {template}, jobText length: {len(job_text)}")

    try:
        file_bytes = resume_file.read()
        resume_text = extract_text_from_pdf(file_bytes)
        
        import importlib
        try:
            import analyzer
            importlib.reload(analyzer)
            gen_func = analyzer.generate_tailored_resume
        except Exception:
            from analyzer import generate_tailored_resume
            gen_func = generate_tailored_resume

        tailored_resume = gen_func(resume_text, job_text, short_bio, pref_title, pref_loc, extra_missing_skills=extra_missing_skills, template=template)
        
        return jsonify({"tailoredResume": tailored_resume})
    except Exception as e:
        print(f"Error building tailored resume: {e}")
        return jsonify({"error": "Failed to build tailored resume: " + str(e)}), 500


@app.route("/build-resume-latex", methods=["POST", "OPTIONS"])
def build_resume_latex():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    resume_file = request.files.get("resume")
    job_text = request.form.get("jobText", "")

    if not resume_file or not job_text:
        return jsonify({"error": "Resume and job description are required"}), 400

    if not resume_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a valid PDF document (.pdf)."}), 400

    short_bio = request.form.get("shortBio", "")
    pref_title = request.form.get("prefTitle", "")
    pref_loc = request.form.get("prefLoc", "")
    template = request.form.get("template", "modern")
    
    extra_missing_skills = []
    missing_skills_raw = request.form.get("missingSkills", "")
    if missing_skills_raw:
        try:
            extra_missing_skills = json.loads(missing_skills_raw)
        except Exception as ex:
            print(f"[build-resume-latex] JSON parse error on missingSkills: {ex}")

    print(f"[build-resume-latex] Received {len(extra_missing_skills)} missing skills, template: {template}, jobText length: {len(job_text)}")

    try:
        file_bytes = resume_file.read()
        resume_text = extract_text_from_pdf(file_bytes)
        
        import importlib
        try:
            import analyzer
            importlib.reload(analyzer)
            gen_latex_func = analyzer.generate_tailored_resume_latex
        except Exception:
            from analyzer import generate_tailored_resume_latex
            gen_latex_func = generate_tailored_resume_latex

        latex_code = gen_latex_func(resume_text, job_text, short_bio, pref_title, pref_loc, extra_missing_skills=extra_missing_skills, template=template)
        
        # Write to temporary file
        temp_dir = os.path.join(os.path.dirname(__file__), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        job_id = str(uuid.uuid4())
        tex_path = os.path.join(temp_dir, f"{job_id}.tex")
        pdf_path = os.path.join(temp_dir, f"{job_id}.pdf")
        
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_code)
            
        # Compile with pdflatex (sanitize PATH to prevent MiKTeX path attribute resolution issues on Windows)
        env = os.environ.copy()
        if "PATH" in env:
            env["PATH"] = ";".join([p for p in env["PATH"].split(";") if p and os.path.isdir(p)])
        subprocess.run(["pdflatex", "-interaction=nonstopmode", f"{job_id}.tex"], cwd=temp_dir, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Read the generated PDF
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        import base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        return jsonify({"pdfData": f"data:application/pdf;base64,{pdf_base64}"})
    except subprocess.CalledProcessError as e:
        print(f"LaTeX Compilation Error: {e.stdout.decode('utf-8', errors='ignore')}")
        return jsonify({"error": "Failed to compile LaTeX to PDF"}), 500
    except Exception as e:
        print(f"Error building LaTeX resume: {e}")
        return jsonify({"error": "Failed to build LaTeX resume: " + str(e)}), 500


@app.route("/generate-cover-letter", methods=["POST", "OPTIONS"])
def api_generate_cover_letter():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    job_text = ""
    resume_text = ""
    company_name = ""
    role_title = ""

    if request.files.get("resume"):
        resume_file = request.files.get("resume")
        job_text = request.form.get("jobText", "")
        company_name = request.form.get("companyName", "")
        role_title = request.form.get("roleTitle", "")
        try:
            file_bytes = resume_file.read()
            resume_text = extract_text_from_pdf(file_bytes)
        except Exception as e:
            return jsonify({"error": f"Failed to extract resume text: {e}"}), 400
    elif request.is_json:
        data = request.json or {}
        resume_text = data.get("resumeText", "")
        job_text = data.get("jobText", "")
        company_name = data.get("companyName", "")
        role_title = data.get("roleTitle", "")
    else:
        resume_text = request.form.get("resumeText", "")
        job_text = request.form.get("jobText", "")
        company_name = request.form.get("companyName", "")
        role_title = request.form.get("roleTitle", "")

    if not resume_text or not job_text:
        return jsonify({"error": "Both resume and job description are required"}), 400

    try:
        import analyzer
        import importlib
        try:
            importlib.reload(analyzer)
            cl_func = analyzer.generate_cover_letter
        except Exception:
            from analyzer import generate_cover_letter
            cl_func = generate_cover_letter

        result = cl_func(resume_text, job_text, company_name=company_name, role_title=role_title)
        return jsonify(result), 200
    except Exception as e:
        print(f"Error generating cover letter: {e}")
        return jsonify({"error": f"Failed to generate cover letter: {e}"}), 500


@app.route("/build-cover-letter-latex", methods=["POST", "OPTIONS"])
def build_cover_letter_latex():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    cover_letter_text = request.form.get("coverLetterText", "")
    if not cover_letter_text and request.is_json:
        data = request.json or {}
        cover_letter_text = data.get("coverLetterText", "")

    if not cover_letter_text:
        return jsonify({"error": "Cover letter text is required"}), 400

    try:
        import analyzer
        import importlib
        try:
            importlib.reload(analyzer)
            gen_latex_cl = analyzer.generate_cover_letter_latex
        except Exception:
            from analyzer import generate_cover_letter_latex
            gen_latex_cl = generate_cover_letter_latex

        latex_code = gen_latex_cl(cover_letter_text)

        temp_dir = os.path.join(os.path.dirname(__file__), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        job_id = str(uuid.uuid4())
        tex_path = os.path.join(temp_dir, f"{job_id}.tex")
        pdf_path = os.path.join(temp_dir, f"{job_id}.pdf")

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_code)

        env = os.environ.copy()
        if "PATH" in env:
            env["PATH"] = ";".join([p for p in env["PATH"].split(";") if p and os.path.isdir(p)])
        subprocess.run(["pdflatex", "-interaction=nonstopmode", f"{job_id}.tex"], cwd=temp_dir, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        import base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        return jsonify({"pdfData": pdf_base64}), 200
    except Exception as e:
        print(f"Error compiling cover letter LaTeX: {e}")
        return jsonify({"error": f"Failed to build cover letter PDF: {e}"}), 500


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
        print(f"\n⚠️ [FORGOT PASSWORD] Email '{email}' is not registered in the database.\n", flush=True)
        return jsonify({"message": "If this email is registered, an OTP has been sent."}), 200

    otp = str(random.randint(100000, 999999))
    expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    _reset_otps[email] = {"otp": otp, "expires": expires}

    # Always display OTP prominently in the terminal
    print("\n" + "="*50, flush=True)
    print(f"🔑 [PASSWORD RESET OTP] For: {email}", flush=True)
    print(f"👉 OTP CODE: {otp} (Valid for 10 minutes)", flush=True)
    print("="*50 + "\n", flush=True)

    sender_email = os.getenv("EMAIL_USER")
    sender_pass = os.getenv("EMAIL_PASS")

    if not is_online():
        return jsonify({"message": f"Offline mode active. Your OTP is {otp}", "otp": otp}), 200

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
            print(f"Password reset OTP sent to {user['email']}", flush=True)
        except Exception as e:
            print(f"Failed to send reset OTP email: {e}", flush=True)

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

@app.route("/fetch-job-url", methods=["POST", "OPTIONS"])
def fetch_job_url():
    if request.method == "OPTIONS":
        return jsonify({}), 200
        
    data = request.json
    if not data or "url" not in data:
        return jsonify({"error": "Missing URL"}), 400
        
    url = data["url"].strip()
    
    if not is_online():
        return jsonify({"error": "You are offline. Please copy and paste the job description manually."}), 503
        
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        # Adding timeout to prevent hanging
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 403 or response.status_code == 429:
            return jsonify({"error": "Access denied by the website (anti-bot protection). Please copy and paste the job description manually."}), 403
            
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove scripts, styles, nav, footer, etc to get clean text
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.extract()
            
        text = soup.get_text(separator="\n")
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)
        
        # Truncate if insanely long (prevent abuse)
        if len(text) > 50000:
            text = text[:50000]
            
        return jsonify({"text": text}), 200
        
    except requests.exceptions.Timeout:
        return jsonify({"error": "Connection timed out. The website might be blocking scrapers."}), 504
    except Exception as e:
        return jsonify({"error": f"Failed to fetch URL: {str(e)}"}), 500

if __name__ == "__main__":
    threading.Thread(target=daily_reminder_job, daemon=True).start()
    print("Loading NLP models (first start may take ~30s to download all-mpnet-base-v2)...")
    # Pre-warm models at startup to avoid first-request latency
    from analyzer import get_nlp, get_sbert
    get_nlp()
    get_sbert()
    port = int(os.environ.get("PORT", 3000))
    print(f"Models loaded! Server starting on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)