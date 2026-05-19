const signUpButton = document.getElementById('signUp');
const signInButton = document.getElementById('signIn');
const container = document.getElementById('container');

if (signUpButton && signInButton && container) {
signUpButton.addEventListener('click', () => {
container.classList.add("right-panel-active");
});

signInButton.addEventListener('click', () => {
    container.classList.remove("right-panel-active");
});

}

// =====================
// SIGN UP
// =====================
const signUpForm = document.querySelector(".sign-up-container form");

if (signUpForm) {
signUpForm.addEventListener("submit", async function(e) {
    e.preventDefault();

    const name = signUpForm.querySelector('input[type="text"]').value.trim();
    const email = signUpForm.querySelector('input[type="email"]').value.trim();
    const password = signUpForm.querySelector('input[type="password"]').value.trim();

    if (!name || name.length < 2) return alert("Enter valid name");
    if (!email.includes("@")) return alert("Enter valid email");
    if (password.length < 6) return alert("Password must be at least 6 characters");

    try {
        const res = await fetch("http://127.0.0.1:3000/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password })
        });
        
        const data = await res.json();
        
        if (!res.ok) {
            return alert(data.error || "Failed to sign up");
        }
        
        alert("Account created successfully!");
        container.classList.remove("right-panel-active");
    } catch (error) {
        console.error(error);
        alert("Server error. Ensure backend is running.");
    }
});
}

// =====================
// SIGN IN
// =====================
const signInForm = document.querySelector(".sign-in-container form");

if (signInForm) {
signInForm.addEventListener("submit", async function(e) {
    e.preventDefault();

    const email = signInForm.querySelector('input[type="email"]').value.trim();
    const password = signInForm.querySelector('input[type="password"]').value.trim();

    if (!email || !password) return alert("Enter email and password");

    try {
        const res = await fetch("http://127.0.0.1:3000/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        
        const data = await res.json();
        
        if (!res.ok) {
            return alert(data.error || "Invalid login credentials");
        }
        
        localStorage.setItem("loggedIn", "true");
        localStorage.setItem("userName", data.name);
        localStorage.setItem("userEmail", email);
        
        window.location.href = "../analysis-dashboard/index.html";
    } catch (error) {
        console.error(error);
        alert("Server error. Ensure backend is running.");
    }
});
}

// =====================
// SUGGESTIONS FUNCTION
// =====================
function showSuggestions(matchingSkills, missingSkills, matchPercent) {
const section = document.getElementById("suggestionsSection");
if (!section) return;

section.style.display = "block";

const jobList = document.getElementById("jobRolesList");
const courseList = document.getElementById("coursesList");

if (jobList) jobList.innerHTML = "";
if (courseList) courseList.innerHTML = "";

const skills = (matchingSkills || []).map(s => s.toLowerCase());

if (skills.includes("python")) jobList.innerHTML += "<li>Python Developer</li>";
if (skills.includes("javascript")) jobList.innerHTML += "<li>Frontend Developer</li>";
if (skills.includes("sql")) jobList.innerHTML += "<li>Data Analyst</li>";

if (jobList.innerHTML === "") {
    jobList.innerHTML = "<li>Software Developer</li>";
}

(missingSkills || []).forEach(skill => {
    courseList.innerHTML += `<li>Learn ${skill} (Udemy / Coursera)</li>`;
});
```

}

// =====================
// MAIN ANALYSIS FUNCTION
// =====================
async function analyzeResume() {
const fileInput = document.getElementById("resume");
const jobText = document.getElementById("jobText").value;

// Validate file
if (!fileInput || !fileInput.files[0]) {
    alert("Please upload a resume first");
    return;
}

// Loader show
const loader = document.querySelector(".loading-text");
if (loader) loader.style.display = "block";

const formData = new FormData();
formData.append("resume", fileInput.files[0]);
formData.append("jobText", jobText);

const userEmail = localStorage.getItem("userEmail");
if (userEmail) {
    formData.append("email", userEmail);
}

try {
    const res = await fetch("http://127.0.0.1:3000/analyze", {
        method: "POST",
        body: formData
    });

    if (!res.ok) {
        throw new Error("Server error");
    }

    const data = await res.json();

    // Update stats safely
    if (document.getElementById("matchPercent"))
        document.getElementById("matchPercent").innerText = data.matchPercent + "%";

    if (document.getElementById("missingPercent"))
        document.getElementById("missingPercent").innerText = data.missingPercent + "%";

    if (document.getElementById("efficiencyPercent"))
        document.getElementById("efficiencyPercent").innerText = data.efficiencyPercent + "%";

    if (document.getElementById("skillCount"))
        document.getElementById("skillCount").innerText =
            `${data.matchedCount} of ${data.totalSkills} skills found`;

    if (document.getElementById("missingCount"))
        document.getElementById("missingCount").innerText =
            `${data.missingSkills.length} skills to improve`;

    // Matching skills
    const matchList = document.getElementById("matchingList");
    if (matchList) {
        matchList.innerHTML = "";
        (data.matchingSkills || []).forEach(skill => {
            matchList.innerHTML += `<li>✔ ${skill}</li>`;
        });
    }

    // Missing skills
    const missingList = document.getElementById("missingList");
    if (missingList) {
        missingList.innerHTML = "";
        (data.missingSkills || []).forEach(skill => {
            missingList.innerHTML += `
                <div class="missing-card">
                    <p>● ${skill}</p>
                    <small>${data.suggestions?.[skill] || ""}</small>
                </div>
            `;
        });
    }

    // Final message
    const finalMsg = document.getElementById("finalMessage");
    if (finalMsg) {
        finalMsg.innerText = "Good job! Your resume has a strong foundation.";
    }

    // Suggestions
    showSuggestions(data.matchingSkills, data.missingSkills, data.matchPercent);

} catch (error) {
    console.error(error);
    alert("Server error. Make sure backend is running.");
} finally {
    if (loader) loader.style.display = "none";
}

}
