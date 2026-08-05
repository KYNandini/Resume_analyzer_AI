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

// 1. Send OTP for Signup
app.post("/send-otp", async (req, res) => {
  const { name, email, password } = req.body;
  if (!name || !email || !password) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  try {
    const existingUser = await User.findOne({ email });
    if (existingUser) {
      return res.status(400).json({ error: "Email already registered" });
    }

    // Generate 6-digit OTP
    const otp = Math.floor(100000 + Math.random() * 900000).toString();
    
    // Delete any existing OTP for this email, then create fresh
    await Otp.deleteOne({ email });
    const otpDoc = new Otp({
      email,
      otp,
      name,
      password,
      expiresAt: new Date(Date.now() + 5 * 60 * 1000)
    });
    try {
      await otpDoc.save();
      console.log("OTP saved to DB for:", email, "OTP:", otp);
    } catch (saveErr) {
      console.error("❌ CRITICAL: OTP save failed:", saveErr.message, saveErr.code);
      return res.status(500).json({ error: "Failed to save OTP: " + saveErr.message });
    }

    // Send email
    const mailOptions = {
      from: process.env.EMAIL_USER,
      to: email,
      subject: "Your OTP for Resume Analyzer AI",
      text: `Your One Time Password (OTP) for registration is: ${otp}\nThis code will expire in 5 minutes.`,
      html: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 14px; background: #ffffff;">
          <div style="text-align: center; margin-bottom: 24px;">
            <h2 style="color: #2bbbad; margin: 0; font-size: 24px; font-weight: 800;">Resume Analyzer AI</h2>
          </div>
          <div style="padding: 24px; background: #f8fafc; border-radius: 12px; border: 1px solid #f1f5f9;">
            <h3 style="color: #1a1a2e; margin-top: 0; font-size: 18px;">Welcome, ${name}!</h3>
            <p style="color: #475569; font-size: 15px; line-height: 1.6;">Thank you for registering with us. Please use the following One Time Password (OTP) to complete your sign-up process:</p>
            <div style="background: #ffffff; padding: 20px; text-align: center; border-radius: 8px; margin: 24px 0; border: 2px dashed #2bbbad;">
              <span style="font-size: 36px; font-weight: bold; color: #2bbbad; letter-spacing: 8px; display: block; margin-left: 8px;">${otp}</span>
            </div>
            <p style="color: #94a3b8; font-size: 13px; margin-bottom: 0;">This code will expire in <strong>5 minutes</strong>. If you didn't request this code, you can safely ignore this email.</p>
          </div>
        </div>
      `
    };

    transporter.sendMail(mailOptions, (error, info) => {
      if (error) {
        console.error("Error sending email:", error);
        return res.status(500).json({ error: "Failed to send OTP email" });
      }
      
      const previewUrl = nodemailer.getTestMessageUrl(info);
      if (previewUrl) {
        console.log("OTP Email sent! Preview URL: %s", previewUrl);
      } else {
        console.log("OTP Email successfully sent to:", email);
      }
      
      return res.status(200).json({ 
          message: "OTP sent successfully", 
          previewUrl: previewUrl || null 
      });
    });
  } catch (error) {
    console.error("Send OTP error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

// 1.5 Verify OTP and Complete Signup
app.post("/signup", async (req, res) => {
  const { email, otp } = req.body;
  if (!email || !otp) {
    return res.status(400).json({ error: "Missing email or OTP" });
  }

  try {
    const storedData = await Otp.findOne({ email });
    console.log("Signup attempt - email:", email, "otp entered:", otp, "storedData:", storedData);
    if (!storedData) {
      return res.status(400).json({ error: "No pending signup found for this email, or OTP has expired." });
    }

    // Check manual expiry (5 minutes)
    if (storedData.expiresAt && new Date() > storedData.expiresAt) {
      await Otp.deleteOne({ email });
      return res.status(400).json({ error: "OTP has expired. Please request a new one." });
    }

    if (storedData.otp !== otp.trim()) {
      return res.status(400).json({ error: "Invalid OTP" });
    }

    // Proceed with registration
    const hashedPassword = generatePassword(storedData.password);
    const safeName = encodeURIComponent(storedData.name);
    const userDoc = new User({
      name: storedData.name,
      email,
      password: hashedPassword,
      role: "Senior Software Engineer",
      dob: "01-01-2005",
      profileImage: `https://api.dicebear.com/7.x/initials/svg?seed=${safeName}`,
      history: []
    });

    await userDoc.save();
    console.log("✅ User registered and saved to MongoDB:", email);
    await Otp.deleteOne({ email }); // Clear OTP after success
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
      history: user.history
    });
  } catch (error) {
    console.error("Get profile error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

// 4. Update Profile
app.post("/update_profile", async (req, res) => {
  const { email, name, role, dob, profileImage } = req.body;
  if (!email) {
    return res.status(400).json({ error: "Email required" });
  }

  try {
    const updateFields = {};
    if (name !== undefined) updateFields.name = name;
    if (role !== undefined) updateFields.role = role;
    if (dob !== undefined) updateFields.dob = dob;
    if (profileImage !== undefined) updateFields.profileImage = profileImage;

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

// 6. Analyze Resume
app.post("/analyze", upload.single("resume"), async (req, res) => {
  console.log("BODY:", req.body);
  console.log("FILE:", req.file);

  if (!req.file || !req.file.mimetype.includes("pdf")) {
    return res.status(400).send("Please upload a PDF file");
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