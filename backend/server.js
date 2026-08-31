const express = require("express");
const cors = require("cors");
const multer = require("multer");
const pdfParse = require("pdf-parse");
const fs = require("fs");
const path = require("path");
const { exec } = require("child_process");
const mongoose = require("mongoose");
const crypto = require("crypto");
const nodemailer = require("nodemailer");
require("dotenv").config({ path: path.join(__dirname, ".env"), override: true });

const app = express();

// Nodemailer configuration
let transporter;
async function initMailer() {
  if (process.env.EMAIL_USER && process.env.EMAIL_PASS && process.env.EMAIL_USER !== "your-email@gmail.com") {
    transporter = nodemailer.createTransport({
      service: "gmail",
      auth: {
        user: process.env.EMAIL_USER,
        pass: process.env.EMAIL_PASS
      }
    });
    console.log("Using Gmail SMTP");
  } else {
    console.log("No EMAIL_USER in .env. Falling back to Ethereal Email for testing...");
    let testAccount = await nodemailer.createTestAccount();
    transporter = nodemailer.createTransport({
      host: "smtp.ethereal.email",
      port: 587,
      secure: false, // true for 465, false for other ports
      auth: {
        user: testAccount.user,
        pass: testAccount.pass,
      },
    });
    console.log("Ethereal Email initialized.");
  }
}
initMailer();



// CORS middleware configurations
app.use(cors({
  origin: "*",
  methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"]
}));

app.use(express.urlencoded({ extended: true, limit: "50mb" }));
app.use(express.json({ limit: "50mb" }));

// MongoDB connection
const mongoUri = process.env.MONGO_URI || "mongodb://localhost:27017/resumeanalyzer";
mongoose.connect(mongoUri)
  .then(() => console.log("Connected to MongoDB via Mongoose successfully!"))
  .catch((err) => console.error("Could not connect to MongoDB:", err));

// Schemas & Models
const userSchema = new mongoose.Schema({
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
  role: { type: String, default: "Senior Software Engineer" },
  dob: { type: String, default: "01-01-2005" },
  profileImage: { type: String, default: "" },
  shortBio: { type: String, default: "" },
  preferredJobTitle: { type: String, default: "" },
  preferredLocation: { type: String, default: "" },
  workArrangement: { type: String, default: "" },
  employmentType: { type: String, default: "" },
  history: { type: Array, default: [] }
});

const resumeSchema = new mongoose.Schema({
  email: { type: String, required: true },
  filename: { type: String, required: true },
  file_data: Buffer,
  jobDescription: { type: String, default: "" },
  analysisResult: { type: Object, default: {} },
  timestamp: { type: Date, default: Date.now }
});

const otpSchema = new mongoose.Schema({
  email: { type: String, required: true, unique: true },
  otp: { type: String, required: true },
  name: { type: String, required: true },
  password: { type: String, required: true },
  expiresAt: { type: Date, default: () => new Date(Date.now() + 5 * 60 * 1000) }
});

const User = mongoose.model("User", userSchema);
const Resume = mongoose.model("Resume", resumeSchema);
const Otp = mongoose.model("Otp", otpSchema);

// Password Hashing and Checking helpers (Compatible with Flask's werkzeug pbkdf2:sha256)
function generatePassword(password) {
  const salt = crypto.randomBytes(8).toString("hex");
  const iterations = 600000;
  const hash = crypto.pbkdf2Sync(password, salt, iterations, 32, "sha256").toString("hex");
  return `pbkdf2:sha256:${iterations}$${salt}$${hash}`;
}

function checkPassword(password, hashedPassword) {
  if (!hashedPassword) return false;
  if (hashedPassword.startsWith("pbkdf2:sha256:")) {
    const parts = hashedPassword.split("$");
    if (parts.length === 3) {
      const [meta, salt, hash] = parts;
      const iterations = parseInt(meta.split(":")[2], 10);
      const calculatedHash = crypto.pbkdf2Sync(password, salt, iterations, 32, "sha256").toString("hex");
      return calculatedHash === hash;
    }
  }
  // Fallback to SHA256 if not pbkdf2
  const sha256Hash = crypto.createHash("sha256").update(password).digest("hex");
  return sha256Hash === hashedPassword;
}

// Multer Upload Configuration
const uploadDir = path.join(__dirname, "uploads");
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}
const upload = multer({ dest: "uploads/" });

// Routes

// 1. Direct Signup – register immediately & send welcome email
app.post("/signup", async (req, res) => {
  const { name, email, password } = req.body;
  if (!name || !email || !password) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  try {
    const existingUser = await User.findOne({ email });
    if (existingUser) {
      return res.status(400).json({ error: "Email already registered" });
    }

    // Register the user immediately
    const hashedPassword = generatePassword(password);
    const safeName = encodeURIComponent(name);
    const userDoc = new User({
      name,
      email,
      password: hashedPassword,
      role: "Senior Software Engineer",
      dob: "01-01-2005",
      profileImage: `https://api.dicebear.com/7.x/initials/svg?seed=${safeName}`,
      history: []
    });

    await userDoc.save();
    console.log("✅ User registered and saved to MongoDB:", email);

    // Send welcome notification email (non-blocking)
    const mailOptions = {
      from: process.env.EMAIL_USER,
      to: email,
      subject: "Welcome to Resume Analyzer AI 🎉",
      text: `Hi ${name},\n\nYour account has been created successfully!\n\nYou can now sign in and start analyzing your resume.\n\n— Resume Analyzer AI Team`,
      html: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 14px; background: #ffffff;">
          <div style="text-align: center; margin-bottom: 24px;">
            <h2 style="color: #2bbbad; margin: 0; font-size: 24px; font-weight: 800;">Resume Analyzer AI</h2>
          </div>
          <div style="padding: 24px; background: #f8fafc; border-radius: 12px; border: 1px solid #f1f5f9;">
            <h3 style="color: #1a1a2e; margin-top: 0; font-size: 18px;">Welcome aboard, ${name}! 🎉</h3>
            <p style="color: #475569; font-size: 15px; line-height: 1.6;">Your account has been created successfully. You can now sign in and start analyzing your resume against job descriptions using AI.</p>
            <div style="background: linear-gradient(135deg, #2bbbad, #00a896); padding: 16px 24px; text-align: center; border-radius: 10px; margin: 24px 0;">
              <span style="font-size: 16px; font-weight: 700; color: #ffffff; letter-spacing: 0.5px;">✅ Account Activated</span>
            </div>
            <p style="color: #94a3b8; font-size: 13px; margin-bottom: 0;">If you did not create this account, please contact our support team immediately.</p>
          </div>
        </div>
      `
    };

    transporter.sendMail(mailOptions, (error, info) => {
      if (error) {
        console.error("Welcome email send error (non-critical):", error);
      } else {
        const previewUrl = nodemailer.getTestMessageUrl(info);
        if (previewUrl) console.log("Welcome email preview:", previewUrl);
        else console.log("Welcome email sent to:", email);
      }
    });

    return res.status(201).json({ message: "Account created successfully" });
  } catch (error) {
    console.error("Signup error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});


// 2. Login
app.post("/login", async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ error: "Missing email or password" });
  }

  try {
    const user = await User.findOne({ email });
    if (!user || !checkPassword(password, user.password)) {
      return res.status(401).json({ error: "Invalid login credentials" });
    }

    return res.json({
      message: "Login successful",
      name: user.name,
      email: user.email,
      role: user.role,
      dob: user.dob,
      profileImage: user.profileImage,
      history: user.history
    });
  } catch (error) {
    console.error("Login error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

// 3. Get Profile
app.get("/get_profile", async (req, res) => {
  const email = req.query.email;
  if (!email) {
    return res.status(400).json({ error: "Email required" });
  }

  try {
    const user = await User.findOne({ email });
    if (!user) {
      return res.status(404).json({ error: "User not found" });
    }

    return res.json({
      name: user.name,
      email: user.email,
      role: user.role,
      dob: user.dob,
      profileImage: user.profileImage,
      shortBio: user.shortBio,
      preferredJobTitle: user.preferredJobTitle,
      preferredLocation: user.preferredLocation,
      workArrangement: user.workArrangement,
      employmentType: user.employmentType,
      history: user.history
    });
  } catch (error) {
    console.error("Get profile error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

// 4. Update Profile
app.post("/update_profile", async (req, res) => {
  const { email, name, role, dob, profileImage, shortBio, preferredJobTitle, preferredLocation, workArrangement, employmentType } = req.body;
  if (!email) {
    return res.status(400).json({ error: "Email required" });
  }

  try {
    const updateFields = {};
    if (name !== undefined) updateFields.name = name;
    if (role !== undefined) updateFields.role = role;
    if (dob !== undefined) updateFields.dob = dob;
    if (profileImage !== undefined) updateFields.profileImage = profileImage;
    if (shortBio !== undefined) updateFields.shortBio = shortBio;
    if (preferredJobTitle !== undefined) updateFields.preferredJobTitle = preferredJobTitle;
    if (preferredLocation !== undefined) updateFields.preferredLocation = preferredLocation;
    if (workArrangement !== undefined) updateFields.workArrangement = workArrangement;
    if (employmentType !== undefined) updateFields.employmentType = employmentType;

    const user = await User.findOneAndUpdate(
      { email },
      { $set: updateFields },
      { new: true }
    );

    if (!user) {
      return res.status(404).json({ error: "User not found" });
    }

    return res.json({ message: "Profile updated successfully in MongoDB" });
  } catch (error) {
    console.error("Update profile error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

// 5. Delete History Item
app.post("/delete_history", async (req, res) => {
  const { email, id } = req.body;
  if (!email || !id) {
    return res.status(400).json({ error: "Missing email or id" });
  }

  try {
    const user = await User.findOneAndUpdate(
      { email },
      { $pull: { history: { id } } },
      { new: true }
    );

    if (!user) {
      return res.status(404).json({ error: "User not found" });
    }

    return res.json({ message: "History item deleted successfully from MongoDB" });
  } catch (error) {
    console.error("Delete history error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

// 5.5 Suggest Job Description
app.post("/suggest-jd", upload.single("resume"), async (req, res) => {
  if (!req.file || (!req.file.mimetype.includes("pdf") && !req.file.originalname.toLowerCase().endsWith(".pdf"))) {
    return res.status(400).send("Please upload a valid PDF document (.pdf).");
  }

  try {
    const fileBuffer = fs.readFileSync(req.file.path);
    const pdfData = await pdfParse(fileBuffer);
    const resumeText = pdfData.text || "";

    const tempResumePath = path.join(uploadDir, `resume_suggest_${Date.now()}.txt`);
    fs.writeFileSync(tempResumePath, resumeText, "utf8");

    const checkPythonCmd = 'where py >nul 2>nul && echo py || echo python';
    exec(checkPythonCmd, (errCheck, stdoutCheck) => {
      const usesPyLauncher = stdoutCheck.trim() === "py";
      const pythonExec = usesPyLauncher ? "py -3.13" : "python";
      const command = `${pythonExec} "${path.join(__dirname, "suggest_jd.py")}" "${tempResumePath}"`;

      exec(command, { maxBuffer: 1024 * 1024 * 10 }, (err, stdout, stderr) => {
        try { fs.unlinkSync(tempResumePath); } catch (_) {}
        try { fs.unlinkSync(req.file.path); } catch (_) {}

        if (err) {
          console.error("Execution error during JD suggestion:", err);
          return res.status(500).send("Error executing JD suggestion");
        }
        
        return res.json({ suggestedJD: stdout.trim() });
      });
    });
  } catch (err) {
    console.error("PDF Parsing error in suggest JD:", err);
    try { fs.unlinkSync(req.file.path); } catch (_) {}
    return res.status(500).send("Error processing upload for JD suggestion");
  }
});

// 6. Analyze Resume
app.post("/analyze", upload.single("resume"), async (req, res) => {
  console.log("BODY:", req.body);
  console.log("FILE:", req.file);

  if (!req.file || (!req.file.mimetype.includes("pdf") && !req.file.originalname.toLowerCase().endsWith(".pdf"))) {
    return res.status(400).send("Please upload a valid PDF document (.pdf). Image files (like JPEG or PNG) are not supported for text parsing.");
  }

  const jobText = req.body.jobText || "";
  const email = req.body.email;

  try {
    const fileBuffer = fs.readFileSync(req.file.path);
    
    // Store raw binary resume + job description + analysis metadata in MongoDB
    if (email) {
      const resumeDoc = new Resume({
        email: email,
        filename: req.file.originalname,
        file_data: fileBuffer,
        jobDescription: jobText,
        analysisResult: {}
      });
      await resumeDoc.save()
        .then(() => console.log("✅ Resume saved to MongoDB for:", email, "|", req.file.originalname))
        .catch(e => console.error("❌ Error saving resume to DB:", e));
    } else {
      console.log("⚠️ No email provided - resume NOT saved to MongoDB");
    }

    // Extract text from PDF
    const pdfData = await pdfParse(fileBuffer);
    const resumeText = pdfData.text || "";

    // Write resume and job description to temp files to prevent shell escaping / length limit bugs (E2BIG)
    const tempResumePath = path.join(uploadDir, `resume_${Date.now()}.txt`);
    const tempJobPath = path.join(uploadDir, `job_${Date.now()}.txt`);

    fs.writeFileSync(tempResumePath, resumeText, "utf8");
    fs.writeFileSync(tempJobPath, jobText, "utf8");

    // Execute semantic analyzer script with python (supporting 3.13)
    const checkPythonCmd = 'where py >nul 2>nul && echo py || echo python';
    exec(checkPythonCmd, (errCheck, stdoutCheck) => {
      const usesPyLauncher = stdoutCheck.trim() === "py";
      const pythonExec = usesPyLauncher ? "py -3.13" : "python";
      const command = `${pythonExec} "${path.join(__dirname, "analyzer.py")}" "${tempResumePath}" "${tempJobPath}"`;

      console.log("Executing analyzer command:", command);
      exec(command, { maxBuffer: 1024 * 1024 * 10 }, async (err, stdout, stderr) => {
        // Cleanup temp files immediately
        try { fs.unlinkSync(tempResumePath); } catch (_) {}
        try { fs.unlinkSync(tempJobPath); } catch (_) {}
        // Cleanup uploaded PDF multer file
        try { fs.unlinkSync(req.file.path); } catch (_) {}

        console.log("STDOUT:", stdout);
        console.log("STDERR:", stderr);

        if (err) {
          console.error("Execution error during analysis:", err);
          return res.status(500).send("Error executing analyzer");
        }

        try {
          const responseData = JSON.parse(stdout);

          // Save to user's history in MongoDB if email is provided
          if (email) {
            const fileDataUrl = `data:application/pdf;base64,${fileBuffer.toString("base64")}`;
            const firstLineJob = jobText.split("\n")[0].substring(0, 50) + (jobText.length > 50 ? "..." : "");
            const fileSizeMB = `${(fileBuffer.length / (1024 * 1024)).toFixed(2)} MB`;
            const fileExtension = req.file.originalname.split(".").pop().toUpperCase() || "PDF";

            const historyItem = {
              id: `hist-${Date.now()}`,
              timestamp: new Date().toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit"
              }),
              fileName: req.file.originalname || "Uploaded_Resume.pdf",
              fileSize: fileSizeMB,
              fileType: fileExtension,
              fileDataUrl: fileDataUrl,
              jobTitle: firstLineJob || "Target Job Description",
              data: responseData
            };

            await User.findOneAndUpdate(
              { email },
              { $push: { history: { $each: [historyItem], $position: 0 } } }
            );
          }

          return res.json(responseData);
        } catch (parseError) {
          console.error("Parse error of python output:", parseError);
          return res.status(500).send("Parse error from analyzer execution");
        }
      });
    });

  } catch (err) {
    console.error("PDF Parsing / database save error:", err);
    // Cleanup uploaded PDF multer file in case of error
    try { fs.unlinkSync(req.file.path); } catch (_) {}
    return res.status(500).send("Error processing upload");
  }
});

// In-memory store for password-reset OTPs (email -> { otp, expiresAt })
const resetOtpStore = new Map();

// 7. Forgot Password – send reset OTP
app.post("/forgot-password", async (req, res) => {
  const { email } = req.body;
  if (!email) return res.status(400).json({ error: "Email required" });

  try {
    const user = await User.findOne({ email });
    if (!user) return res.status(404).json({ error: "No account found with that email" });

    const otp = Math.floor(100000 + Math.random() * 900000).toString();
    resetOtpStore.set(email, { otp, expiresAt: Date.now() + 10 * 60 * 1000 });

    const mailOptions = {
      from: process.env.EMAIL_USER,
      to: email,
      subject: "Password Reset OTP – Resume Analyzer AI",
      html: `
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:30px;border:1px solid #e2e8f0;border-radius:14px;">
          <h2 style="color:#2bbbad;">Resume Analyzer AI – Password Reset</h2>
          <p>Use the OTP below to reset your password. It expires in <strong>10 minutes</strong>.</p>
          <div style="text-align:center;padding:20px;background:#f8fafc;border-radius:8px;border:2px dashed #2bbbad;margin:20px 0;">
            <span style="font-size:36px;font-weight:bold;color:#2bbbad;letter-spacing:8px;">${otp}</span>
          </div>
          <p style="color:#94a3b8;font-size:13px;">If you did not request this, ignore this email.</p>
        </div>`
    };

    transporter.sendMail(mailOptions, (err, info) => {
      if (err) {
        console.error("Error sending reset OTP:", err);
        return res.status(500).json({ error: "Failed to send OTP email" });
      }
      const previewUrl = nodemailer.getTestMessageUrl(info);
      if (previewUrl) console.log("Reset OTP preview:", previewUrl);
      return res.json({ message: "OTP sent", previewUrl: previewUrl || null });
    });
  } catch (error) {
    console.error("Forgot password error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

// 8. Verify Reset OTP (pre-check before setting new password)
app.post("/verify-reset-otp", async (req, res) => {
  const { email, otp } = req.body;
  if (!email || !otp) return res.status(400).json({ error: "Email and OTP required" });

  const record = resetOtpStore.get(email);
  if (!record) return res.status(400).json({ error: "No OTP request found for this email" });
  if (Date.now() > record.expiresAt) {
    resetOtpStore.delete(email);
    return res.status(400).json({ error: "OTP has expired. Please request a new one." });
  }
  if (record.otp !== otp.trim()) return res.status(400).json({ error: "Invalid OTP" });

  return res.json({ message: "OTP verified" });
});

// 9. Reset Password
app.post("/reset-password", async (req, res) => {
  const { email, otp, newPassword } = req.body;
  if (!email || !otp || !newPassword) return res.status(400).json({ error: "Missing required fields" });
  if (newPassword.length < 6) return res.status(400).json({ error: "Password must be at least 6 characters" });

  const record = resetOtpStore.get(email);
  if (!record) return res.status(400).json({ error: "No OTP request found for this email" });
  if (Date.now() > record.expiresAt) {
    resetOtpStore.delete(email);
    return res.status(400).json({ error: "OTP has expired. Please request a new one." });
  }
  if (record.otp !== otp.trim()) return res.status(400).json({ error: "Invalid OTP" });

  try {
    const hashedPassword = generatePassword(newPassword);
    const user = await User.findOneAndUpdate({ email }, { $set: { password: hashedPassword } }, { new: true });
    if (!user) return res.status(404).json({ error: "User not found" });

    resetOtpStore.delete(email); // Clear OTP after successful reset
    console.log("✅ Password reset for:", email);
    return res.json({ message: "Password reset successfully" });
  } catch (error) {
    console.error("Reset password error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

// Root status routes
app.get("/", (req, res) => {
  res.send("Express Server with Mongoose Connection is running 🚀");
});

app.get("/upload", (req, res) => {
  res.send("Upload route is working!");
});

// Port binding
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));