const express = require("express");
const cors = require("cors");
const multer = require("multer");
const pdfParse = require("pdf-parse");
const fs = require("fs");
const { exec } = require("child_process");

const app = express();
app.use(cors());
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

const upload = multer({ dest: "uploads/" });

app.post("/analyze", upload.single("resume"), async (req, res) => {

    console.log("BODY:", req.body);
    console.log("FILE:", req.file);

    // ✅ CORRECT PLACE
    if (!req.file || !req.file.mimetype.includes("pdf")) {
        return res.status(400).send("Please upload a PDF file");
    }

    const jobText = req.body.jobText;

    const pdfBuffer = fs.readFileSync(req.file.path);
    const pdfData = await pdfParse(pdfBuffer);

    const resumeText = pdfData.text;

    // ✅ safer command
    const command = `python analyzer.py ${JSON.stringify(resumeText)} ${JSON.stringify(jobText)}`;

    exec(command, (err, stdout, stderr) => {
        console.log("STDOUT:", stdout);
        console.log("STDERR:", stderr);

        if (err) return res.status(500).send("Error");

        try {
            const result = JSON.parse(stdout);
            res.json(result);
        } catch {
            res.status(500).send("Parse error");
        }
    });
});

app.get("/", (req, res) => {
  res.send("Server is running 🚀");
});

app.get("/upload", (req, res) => {
  res.send("Upload route is working!");
});

app.listen(3000, () => console.log("Server running on port 3000"));