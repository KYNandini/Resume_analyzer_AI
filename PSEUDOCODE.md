# Resume Analyzer AI - Complete Project Pseudocode

This document contains the complete, unified algorithmic pseudocode for the **Resume Analyzer AI** project, covering all modules from frontend user interaction, authentication, PDF parsing, NLP skill extraction, two-pass semantic matching, ATS scoring, Gemini AI recommendations, to LaTeX document compilation.

---

## 1. High-Level System Architecture Flow

```text
[User Client] ──(Upload PDF Resume + Target Job Description)──► [Web Frontend UI]
                                                                       │
                                                            POST /analyze (FormData)
                                                                       │
                                                                       ▼
                                                             [Flask API Server]
                                                                       │
             ┌─────────────────────────────────────────────────────────┴─────────────────────────────────────────┐
             ▼                                                                                                   ▼
   [PyMuPDF (fitz)]                                                                                     [spaCy (en_core_web_sm)]
Extract Raw Text from PDF Pages                                                                        Extract Skills & Categorize
             │                                                                                                   │
             └─────────────────────────────────────────┬─────────────────────────────────────────────────────────┘
                                                       ▼
                                            [Two-Pass Skill Matcher]
                                   Pass 1: Normalized Exact String Matching
                                   Pass 2: SBERT Cosine Similarity (MPNet) / Jaccard
                                                       │
                                                       ▼
                                             [ATS Scoring Engine]
                                    Match %, Missing %, Priority, Categories
                                                       │
                                                       ▼
                                          [Gemini AI / Heuristic Advisor]
                                    Generate Actionable Skill & Resume Advice
                                                       │
                                                       ▼
                                             [MongoDB History Store]
                                     Save Analysis Record to User Document
                                                       │
                                                       ▼
                                          [Return JSON Result to Client]
                                                       │
                                                       ▼
                                       [Dashboard Charts & PDF/LaTeX View]
```

---

## 2. Authentication & Verification Subsystem

```pascal
MODULE UserAuthentication

// Global in-memory cache for one-time verification tokens
GLOBAL SignupOtpStore  ← Map<Email, {otp, expires, name, passwordHash}>
GLOBAL ResetOtpStore   ← Map<Email, {otp, expires}>

// -------------------------------------------------------------
// STEP 2.1: Signup OTP Request
// -------------------------------------------------------------
FUNCTION RequestSignupOtp(userName, email, plainPassword):
    IF userName IS EMPTY OR email IS EMPTY OR plainPassword IS EMPTY THEN
        RETURN Response(Status: 400, Error: "Missing required fields")
    END IF

    // Validate email format and MX record deliverability
    IF NOT ValidateEmailAddress(email) THEN
        RETURN Response(Status: 400, Error: "Invalid or non-existent email address")
    END IF

    // Check if account already exists
    existingUser ← Database.Users.FindOne({ "email": Lowercase(email) })
    IF existingUser IS NOT NULL THEN
        RETURN Response(Status: 400, Error: "Email is already registered. Please sign in.")
    END IF

    // Generate 6-digit numeric OTP valid for 10 minutes
    otpCode ← GenerateRandomDigits(Length: 6)
    expiration ← CurrentTimestamp() + (10 * 60 Seconds)

    SignupOtpStore[Lowercase(email)] ← {
        "otp": otpCode,
        "expires": expiration,
        "name": userName,
        "passwordHash": HashPassword(plainPassword, Algorithm: BCRYPT_OR_SHA256)
    }

    // Dispatch OTP via SMTP email and local terminal output
    IF IsOnline() AND HasEmailConfig() THEN
        SendSmtpEmail(
            To: email,
            Subject: "Account Verification OTP – Resume Analyzer AI",
            Body: RenderEmailTemplate("signup_otp.html", { userName, otpCode })
        )
    END IF
    LogToConsole("[SIGNUP OTP] For: " + email + " Code: " + otpCode)

    RETURN Response(Status: 200, Message: "OTP sent successfully")
END FUNCTION


// -------------------------------------------------------------
// STEP 2.2: Verify OTP and Commit User Registration
// -------------------------------------------------------------
FUNCTION VerifySignupOtp(email, submittedOtp):
    record ← SignupOtpStore[Lowercase(email)]
    
    IF record IS NULL THEN
        RETURN Response(Status: 400, Error: "No pending registration found for this email")
    END IF

    IF CurrentTimestamp() > record.expires THEN
        DELETE SignupOtpStore[Lowercase(email)]
        RETURN Response(Status: 400, Error: "OTP has expired. Please request a new one.")
    END IF

    IF String(submittedOtp).Trim() != record.otp THEN
        RETURN Response(Status: 400, Error: "Invalid OTP code.")
    END IF

    // Persist new user in MongoDB
    newUser ← {
        "name": record.name,
        "email": Lowercase(email),
        "password": record.passwordHash,
        "createdAt": CurrentTimestamp(),
        "analyses": []
    }
    Database.Users.Insert(newUser)
    DELETE SignupOtpStore[Lowercase(email)]

    // Send Welcome Email asynchronously
    IF IsOnline() AND HasEmailConfig() THEN
        AsyncRun(SendWelcomeEmail(email, record.name))
    END IF

    RETURN Response(Status: 201, Message: "Registration successful")
END FUNCTION


// -------------------------------------------------------------
// STEP 2.3: User Login
// -------------------------------------------------------------
FUNCTION AuthenticateUser(email, plainPassword):
    userRecord ← Database.Users.FindOne({ "email": Lowercase(email) })
    
    IF userRecord IS NULL THEN
        RETURN Response(Status: 401, Error: "Invalid email or password")
    END IF

    IF NOT VerifyPasswordHash(plainPassword, userRecord.password) THEN
        RETURN Response(Status: 401, Error: "Invalid email or password")
    END IF

    sessionToken ← GenerateJwtOrSessionToken(userRecord.email)

    RETURN Response(Status: 200, Data: {
        "token": sessionToken,
        "user": {
            "name": userRecord.name,
            "email": userRecord.email
        }
    })
END FUNCTION

END MODULE
```

---

## 3. PDF Parsing & NLP Skill Extraction Subsystem

```pascal
MODULE ResumeParsingAndExtraction

// -------------------------------------------------------------
// STEP 3.1: Raw Text Extraction from PDF Stream
// -------------------------------------------------------------
FUNCTION ExtractTextFromPdfBytes(pdfFileBytes):
    TRY
        pdfDoc ← PyMuPDF.Open(Stream: pdfFileBytes, FileType: "pdf")
        extractedText ← ""
        
        FOR EACH page IN pdfDoc.Pages():
            extractedText ← extractedText + page.GetText() + "\n"
        END FOR

        RETURN NormalizeWhitespace(extractedText)
    CATCH Exception AS e
        Raise Error("Unable to parse PDF: " + e.Message)
    END TRY
END FUNCTION


// -------------------------------------------------------------
// STEP 3.2: Skill and Keyword Extraction
// -------------------------------------------------------------
FUNCTION ExtractSkillsFromText(rawText):
    normalizedText ← NormalizeToAsciiLower(rawText)
    nlpDoc ← SpaCyNLP.Process(normalizedText)   // en_core_web_sm pipeline

    extractedSkills ← []
    seenSkillNames ← Set()

    taxonomy ← LoadSkillTaxonomy() 
    // taxonomy contains:
    //   - Programming Languages (Python, JavaScript, C++, Java, Go, ...)
    //   - Frameworks & Libraries (React, Django, Flask, PyTorch, Node.js, ...)
    //   - Cloud & DevOps (AWS, Docker, Kubernetes, CI/CD, Azure, ...)
    //   - Databases (MongoDB, PostgreSQL, MySQL, Redis, ...)
    //   - Core Tech (REST API, Microservices, System Design, Data Structures, ...)
    //   - Soft/Non-Tech (Communication, Leadership, Agile, Problem Solving, ...)

    // Phase 1: Boundary-accurate Taxonomy Matching
    FOR EACH category, skillList IN taxonomy:
        FOR EACH skillItem IN skillList:
            pattern ← "\b" + EscapeRegex(skillItem.ToLower()) + "\b"
            IF RegexMatch(pattern, normalizedText) THEN
                IF skillItem NOT IN seenSkillNames THEN
                    seenSkillNames.Add(skillItem)
                    extractedSkills.Append({
                        "skill": skillItem,
                        "category": category
                    })
                END IF
            END IF
        END FOR
    END FOR

    // Phase 2: Grammatical Noun-Chunk & Entity Candidate Identification
    FOR EACH chunk IN nlpDoc.NounChunks:
        candidate ← CleanText(chunk.Text)
        IF IsSkillCandidate(candidate) AND candidate NOT IN seenSkillNames THEN
            category ← ClassifySkillCategory(candidate)
            seenSkillNames.Add(candidate)
            extractedSkills.Append({
                "skill": candidate,
                "category": category
            })
        END IF
    END FOR

    RETURN extractedSkills
END FUNCTION

END MODULE
```

---

## 4. Two-Pass Skill Matching & ATS Scoring Engine

```pascal
MODULE SkillMatchingAndScoring

// -------------------------------------------------------------
// STEP 4.1: Two-Pass Skill Matching (Exact + Semantic SBERT)
// -------------------------------------------------------------
FUNCTION MatchSkills(resumeSkills, jobSkills, threshold = 0.72):
    IF jobSkills IS EMPTY THEN
        RETURN GenerateEmptyResult()
    END IF

    resumeSkillNames ← Unique([s.skill FOR s IN resumeSkills])
    jobSkillNames    ← Unique([s.skill FOR s IN jobSkills])

    IF resumeSkillNames IS EMPTY THEN
        RETURN GenerateAllMissingResult(jobSkills)
    END IF

    matchedSkills ← []
    missingSkills ← []
    jobCategoryMap ← Map(jobSkills.skill -> jobSkills.category)

    sbertModel ← LoadSentenceTransformer("all-mpnet-base-v2")

    // Pre-calculate dense normalized embeddings if SBERT is present
    IF sbertModel IS AVAILABLE THEN
        resumeVectors ← sbertModel.Encode(resumeSkillNames, Normalize: TRUE)
        jobVectors    ← sbertModel.Encode(jobSkillNames, Normalize: TRUE)
    END IF

    resumeNameSet ← Set(resumeSkillNames)

    FOR index FROM 0 TO Length(jobSkillNames) - 1:
        jobSkill ← jobSkillNames[index]
        category ← jobCategoryMap.Get(jobSkill, Default: "General")

        // -----------------------------------------------------
        // PASS 1: Exact Match (Normalized Case-Insensitive)
        // -----------------------------------------------------
        IF jobSkill IN resumeNameSet THEN
            matchedSkills.Append({
                "skill": jobSkill,
                "category": category,
                "confidence": 100,
                "matchType": "exact"
            })
            CONTINUE
        END IF

        // -----------------------------------------------------
        // PASS 2: Semantic Similarity (SBERT or Jaccard Fallback)
        // -----------------------------------------------------
        IF sbertModel IS AVAILABLE THEN
            cosScores ← CosineSimilarity(jobVectors[index], resumeVectors)
            bestScore ← Max(cosScores)
            bestIdx   ← ArgMax(cosScores)
            cutoff    ← threshold // default 0.72
        ELSE
            // Token Jaccard Fallback
            jaccardScores ← [ComputeJaccard(jobSkill, r) FOR r IN resumeSkillNames]
            bestScore ← Max(jaccardScores)
            bestIdx   ← ArgMax(jaccardScores)
            cutoff    ← 0.30      // Jaccard threshold
        END IF

        IF bestScore >= cutoff THEN
            matchedSkills.Append({
                "skill": jobSkill,
                "category": category,
                "confidence": Round(bestScore * 100),
                "matchedWith": resumeSkillNames[bestIdx],
                "matchType": "semantic"
            })
        ELSE
            priority ← IF bestScore < 0.40 THEN "High" ELSE "Medium"
            missingSkills.Append({
                "skill": jobSkill,
                "category": category,
                "priority": priority,
                "closestMatch": IF bestScore > 0.25 THEN resumeSkillNames[bestIdx] ELSE NULL,
                "similarity": Round(bestScore * 100)
            })
        END IF
    END FOR

    // -----------------------------------------------------
    // STEP 4.2: Metrics and ATS Score Calculation
    // -----------------------------------------------------
    totalSkills   ← Length(jobSkillNames)
    matchedCount  ← Length(matchedSkills)

    rawMatchPct   ← Round((matchedCount / totalSkills) * 100)
    // Cap score at 97% to adhere to realistic ATS screening norms
    finalMatchPct ← Min(rawMatchPct, 97)
    missingPct    ← 100 - finalMatchPct
    efficiencyPct ← Min(finalMatchPct + 8, 97)

    // Category-specific Breakdown
    categoryStats ← {}
    FOR EACH s IN jobSkills:
        cat ← s.category
        IF cat NOT IN categoryStats THEN
            categoryStats[cat] ← { "total": 0, "matched": 0 }
        END IF
        categoryStats[cat].total ← categoryStats[cat].total + 1
    END FOR

    FOR EACH s IN matchedSkills:
        cat ← s.category
        IF cat IN categoryStats THEN
            categoryStats[cat].matched ← categoryStats[cat].matched + 1
        END IF
    END FOR

    overallFeedback ← GenerateOverallFeedback(finalMatchPct)

    RETURN {
        "matchPercent": finalMatchPct,
        "missingPercent": missingPct,
        "efficiencyPercent": efficiencyPct,
        "matchedCount": matchedCount,
        "totalSkills": totalSkills,
        "matchingSkills": matchedSkills,
        "missingSkills": missingSkills,
        "categoryBreakdown": categoryStats,
        "overallFeedback": overallFeedback
    }
END FUNCTION

END MODULE
```

---

## 5. Gemini AI Suggestions & LaTeX Resume Generator

```pascal
MODULE AISuggestionsAndLaTeX

// -------------------------------------------------------------
// STEP 5.1: AI Suggestions via Gemini (With Fallback)
// -------------------------------------------------------------
FUNCTION GetGeminiSuggestions(missingSkillsList, jobContext):
    IF GeminiApiKey IS CONFIGURED AND IsOnline() THEN
        TRY
            prompt ← BuildGeminiPrompt(missingSkillsList, jobContext)
            response ← GoogleGeminiApi.GenerateContent(
                Model: "gemini-1.5-flash",
                Prompt: prompt,
                MaxTokens: 800
            )
            RETURN ParseJsonOrBulletMap(response.Text)
        CATCH ApiException AS err
            LogWarning("Gemini API call failed, using heuristic suggestions: " + err.Message)
            RETURN GenerateStaticHeuristicSuggestions(missingSkillsList)
        END TRY
    ELSE
        RETURN GenerateStaticHeuristicSuggestions(missingSkillsList)
    END IF
END FUNCTION


// -------------------------------------------------------------
// STEP 5.2: Tailored Resume LaTeX Generation & Compilation
// -------------------------------------------------------------
FUNCTION GenerateTailoredResumeLatex(resumeText, jobText, templateName = "modern"):
    parsedSections ← ParseResumeSections(resumeText)
    // parsedSections contains: Contact, Bio, Education, WorkHistory, Skills, Projects

    // Identify gaps to address
    jobSkills    ← ExtractSkillsFromText(jobText)
    resumeSkills ← ExtractSkillsFromText(resumeText)
    metrics      ← MatchSkills(resumeSkills, jobSkills)

    // Synthesize tailored summary and insert missing keywords cleanly
    tailoredSummary ← FormatATSSummary(parsedSections.Bio, jobText)
    enrichedSkills  ← BlendKeywordsIntoSkills(parsedSections.Skills, metrics.missingSkills)

    // Load appropriate LaTeX template (Modern / Classic / Minimal)
    templateLatexCode ← ReadTemplateFile(templateName + "_template.tex")

    // Escape special characters: %, &, _, $, #, ~, ^
    safeData ← EscapeLatexEntities({
        "contact": parsedSections.Contact,
        "summary": tailoredSummary,
        "skills": enrichedSkills,
        "experience": parsedSections.WorkHistory,
        "education": parsedSections.Education,
        "projects": parsedSections.Projects
    })

    renderedLatex ← ReplacePlaceholders(templateLatexCode, safeData)

    // Compile to PDF
    pdfBinary ← CompileLatexEngine(renderedLatex, Engine: "tectonic") // or pdflatex

    RETURN {
        "latex": renderedLatex,
        "pdfBytes": pdfBinary
    }
END FUNCTION

END MODULE
```

---

## 6. End-to-End Backend Controller Pipeline (`server.py`)

```pascal
MODULE BackendServerPipeline

// -------------------------------------------------------------
// POST /analyze Endpoint
// -------------------------------------------------------------
ROUTER.POST("/analyze", FUNCTION(request):
    IF "resume" NOT IN request.Files THEN
        RETURN JsonResponse(Status: 400, Error: "Resume PDF file is required")
    END IF

    pdfFileBytes ← request.Files["resume"].Read()
    jobText      ← request.Form.Get("jobDescription", "").Trim()
    userEmail    ← request.Form.Get("email", "").Trim()

    IF Length(jobText) == 0 THEN
        RETURN JsonResponse(Status: 400, Error: "Job description is required")
    END IF

    // 1. Extract text from uploaded PDF
    resumeText ← ResumeParsingAndExtraction.ExtractTextFromPdfBytes(pdfFileBytes)

    // 2. Extract technical & non-technical skills from both inputs
    resumeSkills ← ResumeParsingAndExtraction.ExtractSkillsFromText(resumeText)
    jobSkills    ← ResumeParsingAndExtraction.ExtractSkillsFromText(jobText)

    // 3. Run two-pass matching and compute ATS metrics
    metrics ← SkillMatchingAndScoring.MatchSkills(resumeSkills, jobSkills)

    // 4. Generate AI recommendations for missing skills
    aiSuggestions ← AISuggestionsAndLaTeX.GetGeminiSuggestions(metrics.missingSkills, jobText)

    responsePayload ← {
        "matchPercent": metrics.matchPercent,
        "missingPercent": metrics.missingPercent,
        "efficiencyPercent": metrics.efficiencyPercent,
        "matchedCount": metrics.matchedCount,
        "totalSkills": metrics.totalSkills,
        "matchingSkills": metrics.matchingSkills,
        "missingSkills": metrics.missingSkills,
        "categoryBreakdown": metrics.categoryBreakdown,
        "overallFeedback": metrics.overallFeedback,
        "suggestions": aiSuggestions,
        "timestamp": CurrentTimestamp()
    }

    // 5. Store result in MongoDB user history if user is logged in
    IF userEmail IS NOT EMPTY THEN
        Database.Resumes.Insert({
            "email": Lowercase(userEmail),
            "jobSnippet": Truncate(jobText, 120),
            "analysis": responsePayload
        })

        // 6. Asynchronously trigger scorecard email notification
        IF IsOnline() THEN
            AsyncRun(SendScorecardEmail(userEmail, responsePayload))
        END IF
    END IF

    RETURN JsonResponse(Status: 200, Data: responsePayload)
END FUNCTION)

END MODULE
```

---

## 7. Frontend Client Flow (`frontend/script.js` & `analysis.html`)

```pascal
MODULE FrontendClientController

ON WindowLoaded():
    CheckUserSession()
    AttachEventHandlers()
END

FUNCTION OnAnalyzeButtonClicked():
    resumeFile ← Document.GetInputFile("resumeFileInput")
    jobDesc    ← Document.GetInputValue("jobDescriptionTextArea").Trim()

    IF resumeFile IS NULL THEN
        ShowErrorBanner("Please upload your Resume (PDF format).")
        RETURN
    END IF

    IF jobDesc IS EMPTY THEN
        ShowErrorBanner("Please paste the Target Job Description.")
        RETURN
    END IF

    // UI Loading state
    ShowLoadingSpinner("Analyzing resume against Job Description...")
    DisableSubmitButton()

    formData ← NEW FormData()
    formData.Append("resume", resumeFile)
    formData.Append("jobDescription", jobDesc)
    formData.Append("email", Session.Get("userEmail"))

    TRY
        httpResponse ← Fetch("http://127.0.0.1:3000/analyze", {
            Method: "POST",
            Body: formData
        })

        IF httpResponse.Status != 200 THEN
            errorData ← httpResponse.Json()
            THROW Error(errorData.error)
        END IF

        result ← httpResponse.Json()

        // 1. Render Radial ATS Score Gauge
        AnimateRadialGauge(ElementId: "scoreGauge", TargetValue: result.matchPercent)
        SetElementText("matchPercentLabel", result.matchPercent + "%")
        SetElementText("scoreFeedbackText", result.overallFeedback)

        // 2. Render Matched & Missing Skill Badges
        ClearElement("matchedSkillsList")
        FOR EACH skillItem IN result.matchingSkills:
            badge ← CreateBadge(skillItem.skill, Type: "success", Confidence: skillItem.confidence)
            AppendChild("matchedSkillsList", badge)
        END FOR

        ClearElement("missingSkillsList")
        FOR EACH skillItem IN result.missingSkills:
            badge ← CreateBadge(skillItem.skill, Type: "danger", Priority: skillItem.priority)
            AppendChild("missingSkillsList", badge)
        END FOR

        // 3. Render Categorical Bar Breakdown Chart
        RenderCategoryBarChart("categoryChartContainer", result.categoryBreakdown)

        // 4. Render AI Improvement Suggestions
        ClearElement("suggestionsContainer")
        FOR EACH skillName, advice IN result.suggestions:
            card ← CreateSuggestionCard(skillName, advice)
            AppendChild("suggestionsContainer", card)
        END FOR

        // 5. Scroll smoothly to results view
        ScrollToElement("resultsSection", Smooth: TRUE)

    CATCH Exception AS err
        ShowErrorBanner("Analysis failed: " + err.Message)
    FINALLY
        HideLoadingSpinner()
        EnableSubmitButton()
    END TRY
END FUNCTION

END MODULE
```
