from flask import Flask, request, jsonify
from flask_cors import CORS
import spacy
import fitz  # PyMuPDF
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Enable comprehensive CORS for all origins and headers
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# MongoDB Setup
try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client["resume_analyzer"]
    users_collection = db["users"]
    resumes_collection = db["resumes"]
    # Test connection
    client.server_info()
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Could not connect to MongoDB: {e}")

nlp = spacy.load("en_core_web_sm")

from spacy.lang.en.stop_words import STOP_WORDS as SPACY_STOP

CUSTOM_STOP = {
    "experience", "work", "project", "role",
    "developer", "software", "application", "using",
    "knowledge", "skills", "ability",
    "system", "data", "service"
}

def extract_keywords(doc):
    return set([
        token.lemma_.lower()
        for token in doc
        if token.is_alpha
        and len(token.text) > 2
        and token.pos_ in ["NOUN", "PROPN"]
        and token.lemma_.lower() not in CUSTOM_STOP
        and token.lemma_.lower() not in SPACY_STOP
    ])

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
        
    hashed_password = generate_password_hash(password)
    
    # Create user document with default profile fields & empty history
    user_doc = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "role": "Senior Software Engineer",
        "dob": "01-01-2005",
        "profileImage": "",
        "history": []
    }
    users_collection.insert_one(user_doc)
    
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

    resume_doc = nlp(resume_text.lower())
    job_doc = nlp(job_text.lower())

    resume_words = list(extract_keywords(resume_doc))
    job_words = list(extract_keywords(job_doc))

    # remove duplicates
    resume_words = list(set(resume_words))
    job_words = list(set(job_words))

    if not resume_words:
        result = {
            "matchPercent": 0,
            "missingPercent": 100,
            "efficiencyPercent": 10,
            "matchingSkills": [],
            "missingSkills": job_words[:10],
            "totalSkills": len(job_words),
            "matchedCount": 0,
            "suggestions": {}
        }
    elif not job_words:
        job_words = list(set([
            token.lemma_.lower()
            for token in job_doc
            if token.is_alpha and token.pos_ in ["NOUN", "PROPN"]
        ]))
        if not job_words:
            result = {
                "matchPercent": 0,
                "missingPercent": 100,
                "efficiencyPercent": 10,
                "matchingSkills": [],
                "missingSkills": [],
                "totalSkills": 0,
                "matchedCount": 0,
                "suggestions": {}
            }
        else:
            matched = sorted(list(set(resume_words) & set(job_words)))
            missing = sorted(list(set(job_words) - set(resume_words)))
            match_percent = int((len(matched) / len(job_words)) * 100) if job_words else 0
            result = {
                "matchPercent": match_percent,
                "missingPercent": 100 - match_percent,
                "efficiencyPercent": min(match_percent + 10, 100),
                "matchingSkills": matched[:8],
                "missingSkills": missing[:8],
                "totalSkills": len(job_words),
                "matchedCount": len(matched),
                "suggestions": { skill: f"Add projects related to {skill}" for skill in missing[:5] }
            }
    else:
        # 🔥 FAST MATCHING
        matched = sorted(list(set(resume_words) & set(job_words)))
        missing = sorted(list(set(job_words) - set(resume_words)))
        match_percent = int((len(matched) / len(job_words)) * 100)
        result = {
            "matchPercent": match_percent,
            "missingPercent": 100 - match_percent,
            "efficiencyPercent": min(match_percent + 10, 100),
            "matchingSkills": matched[:8],
            "missingSkills": missing[:8],
            "totalSkills": len(job_words),
            "matchedCount": len(matched),
            "suggestions": { skill: f"Add projects related to {skill}" for skill in missing[:5] }
        }

    # Save to user's history in MongoDB
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
    # Bind to 0.0.0.0 so it accepts both IPv4 (127.0.0.1) and IPv6 (localhost) connections flawlessly!
    app.run(host="0.0.0.0", port=3000, debug=True)