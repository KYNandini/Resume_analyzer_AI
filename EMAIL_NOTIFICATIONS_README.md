# Resume Analyzer AI - Email & Notifications Guide

This document explains the automated email and notification features built into the **Resume Analyzer AI** backend, as well as the underlying technologies, modules, and techniques used to achieve this functionality.

## Overview
The application uses Python's built-in `smtplib` to send automated, styled HTML emails to registered users. It currently supports three main types of email notifications:
1. **Welcome Emails:** Sent when a user successfully signs up.
2. **Instant Scorecard Reports:** Sent immediately after a user uploads and analyzes a resume.
3. **Daily Reminders:** Sent automatically every day at 9:30 PM to encourage users to improve their score.

---

## Technical Implementation: Modules & Techniques

This feature relies heavily on built-in Python modules to avoid unnecessary external dependencies (like `Celery` or `schedule`), keeping the backend lightweight.

### 1. Modules Used
- **`smtplib`**: The core Python module used to handle the actual transmission of the emails via the Simple Mail Transfer Protocol (SMTP). We connect specifically to Gmail's SMTP server (`smtp.gmail.com` on port `587`).
- **`email.mime.text.MIMEText` & `email.mime.multipart.MIMEMultipart`**: Used to construct the email messages. `MIMEMultipart` acts as the container for the email (handling headers like From, To, Subject), while `MIMEText` allows us to parse raw HTML strings and attach them to the email body so the notifications look professional and styled.
- **`threading`**: Essential for concurrency. Sending an email via SMTP can take a few seconds because it requires a network handshake with Google's servers. By utilizing the `threading` module, we offload the email sending process to background threads, ensuring the main Flask HTTP thread returns immediately and the frontend UI doesn't freeze.
- **`datetime` & `time`**: Used within the daily daemon job to calculate the exact time difference (in seconds) between "now" and the target time of 9:30 PM, and then execute `time.sleep()` to pause the background thread without consuming CPU cycles.

### 2. Core Techniques
- **Asynchronous Background Threads (Fire-and-Forget)**: 
  When a user hits the `/analyze` endpoint, the heavy NLP work finishes and the scorecard is generated. Before returning the JSON response to the user, the backend executes:
  `threading.Thread(target=send_scorecard_email, args=(...)).start()`
  This technique ensures the email is processed completely asynchronously in the background.
- **Daemon Threads for Cron-like Scheduling**: 
  Instead of relying on OS-level cron jobs or heavy task queues, the server initiates a daemon thread upon startup:
  `threading.Thread(target=daily_reminder_job, daemon=True).start()`
  Setting `daemon=True` ensures that this infinite-loop background thread will gracefully terminate when the main Flask application is stopped.
- **Conditional Template Rendering**:
  The `send_scorecard_email` function accepts an `is_daily_reminder` boolean flag. This single function handles both the instant post-analysis emails and the daily reminders by dynamically swapping the HTML strings (Subject, Header, and Call-to-Action) based on the context in which it was called.

---

## 1. Instant Scorecard Reports
When a user uploads a resume and a job description, the backend performs the analysis. As soon as the analysis completes:
- The system fetches the user's registered email from the MongoDB database.
- A background thread is spawned so the frontend dashboard loads instantly without waiting for the email to send.
- The user receives an email titled **"Your Resume ATS Scorecard – Resume Analyzer AI"**.
- **What's included:**
  - The overall ATS Match Score (%).
  - General feedback based on their score.
  - Number of matched vs. missing skills.
  - A list of the top missing skills to add.

---

## 2. Daily Reminders (9:30 PM)
To keep users engaged and actively improving their job prospects, the system features a **Daily Reminder Daemon**.
- **How it works:** When the backend server (`server.py`) starts, it launches a continuous background thread (`daily_reminder_job`).
- **Timing:** The thread calculates the exact time remaining until **9:30 PM (21:30)** and sleeps until that time.
- **Execution:** At exactly 9:30 PM, it wakes up, queries the MongoDB database for all registered users, and checks their history.
- **The Email:** If a user has previously analyzed a resume, it grabs their most recent scorecard data and sends a custom reminder email titled **"Keep Improving Your Resume!"**. The email encourages them to address their missing skills and re-upload an improved version of their resume to the dashboard.

---

## Environment Setup Requirements
For the email system to function, you **must** configure your `.env` file in the `backend/` directory with a valid Gmail account and an App Password. 

### `.env` Configuration
Create or edit the `.env` file in the backend folder and include these lines:
```env
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_16_character_app_password
```

### How to get a Gmail App Password
Standard Gmail passwords will not work due to Google's security policies. You must use an App Password:
1. Go to your Google Account -> **Security**.
2. Ensure **2-Step Verification** is turned ON.
3. Search for **App passwords**.
4. Create a new App Password (name it "Resume Analyzer AI").
5. Copy the 16-character password generated and paste it into `EMAIL_PASS` in your `.env` file without any spaces.
