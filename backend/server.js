const express = require("express");
const cors = require("cors");
const multer = require("multer");
const pdfParse = require("pdf-parse");
const fs = require("fs");
const path = require("path");
const { exec } = require("child_process");
const mongoose = require("mongoose");
const crypto = require("crypto");
require("dotenv").config();

const app = express();

// CORS middleware configurations
app.use(cors({
  origin: "*",
  methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"]
}));

app.use(express.urlencoded({ extended: true, limit: "50mb" }));
app.use(express.json({ limit: "50mb" }));

// MongoDB connection
const mongoUri = process.env.MONGO_URI || "mongodb://localhost:27017/resume_analyzer";
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
  email: String,
  filename: String,
  file_data: Buffer,
  timestamp: { type: Date, default: Date.now }
});

const User = mongoose.model("User", userSchema);
const Resume = mongoose.model("Resume", resumeSchema);

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

// 1. Signup
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
    
    // Store raw binary resume in MongoDB resumes collection
    if (email) {
      const resumeDoc = new Resume({
        email: email,
        filename: req.file.originalname,
        file_data: fileBuffer
      });
      await resumeDoc.save().catch(e => console.error("Error saving resume binary to DB:", e));
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
          const parsedResult = JSON.parse(stdout);
          const score = parsedResult.score || 0;
          const matched = parsedResult.matched || [];
          const missing = parsedResult.missing || [];

          // Format analysis result exactly as the frontend dashboard expects it
          const matchPercent = score;
          const missingPercent = 100 - matchPercent;
          const efficiencyPercent = Math.min(matchPercent + 10, 100);

          const suggestionsObj = {};
          missing.forEach((skill, idx) => {
            if (idx < 5) {
              suggestionsObj[skill] = `Add projects related to ${skill}`;
            }
          });

          const responseData = {
            matchPercent: matchPercent,
            missingPercent: missingPercent,
            efficiencyPercent: efficiencyPercent,
            matchingSkills: matched,
            missingSkills: missing,
            totalSkills: matched.length + missing.length,
            matchedCount: matched.length,
            suggestions: suggestionsObj
          };

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