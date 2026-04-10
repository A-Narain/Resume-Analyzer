from flask import Flask, request, render_template, jsonify
import PyPDF2
import os
import re

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Extended skills database with categories
SKILLS_DB = {
    "Programming Languages": ["python", "java", "c++", "c#", "javascript", "typescript", "ruby", "go", "rust", "kotlin", "swift", "scala", "r", "matlab", "php"],
    "Web Technologies": ["html", "css", "react", "angular", "vue", "node.js", "django", "flask", "fastapi", "spring boot", "rest api", "graphql"],
    "Data & ML": ["machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "nlp", "computer vision", "data analysis", "tableau", "power bi"],
    "Databases": ["sql", "mysql", "postgresql", "mongodb", "redis", "cassandra", "elasticsearch", "sqlite", "oracle"],
    "Cloud & DevOps": ["aws", "azure", "gcp", "docker", "kubernetes", "ci/cd", "terraform", "jenkins", "git", "linux", "devops"],
    "Soft Skills": ["leadership", "communication", "teamwork", "problem solving", "agile", "scrum", "project management", "collaboration"],
}

# Keywords for scoring
SECTION_KEYWORDS = {
    "education": ["education", "university", "college", "degree", "bachelor", "master", "phd", "b.tech", "m.tech", "b.e", "m.e"],
    "experience": ["experience", "internship", "work history", "employment", "worked at", "company", "organization"],
    "projects": ["project", "built", "developed", "created", "designed", "implemented", "deployed"],
    "certifications": ["certification", "certified", "certificate", "course", "training", "credential"],
    "achievements": ["award", "achievement", "honor", "recognition", "won", "rank", "top", "best"],
}

ACTION_VERBS = ["developed", "built", "designed", "implemented", "managed", "led", "created", "improved",
                "optimized", "delivered", "collaborated", "architected", "launched", "analyzed", "automated"]


def extract_text(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
    return text


def calculate_ats_score(text):
    text_lower = text.lower()
    score = 0
    breakdown = {}

    # 1. Skills presence (30 pts)
    all_skills = [s for group in SKILLS_DB.values() for s in group]
    found_skills_count = sum(1 for skill in all_skills if skill in text_lower)
    skill_score = min(30, found_skills_count * 2)
    score += skill_score
    breakdown["Skills"] = {"score": skill_score, "max": 30, "found": found_skills_count}

    # 2. Sections coverage (25 pts)
    sections_found = []
    for section, keywords in SECTION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            sections_found.append(section)
    section_score = min(25, len(sections_found) * 5)
    score += section_score
    breakdown["Sections"] = {"score": section_score, "max": 25, "found": sections_found}

    # 3. Word count / length (15 pts)
    word_count = len(text.split())
    if word_count >= 400:
        length_score = 15
    elif word_count >= 250:
        length_score = 10
    elif word_count >= 150:
        length_score = 5
    else:
        length_score = 0
    score += length_score
    breakdown["Length"] = {"score": length_score, "max": 15, "words": word_count}

    # 4. Action verbs (15 pts)
    verbs_found = [v for v in ACTION_VERBS if v in text_lower]
    verb_score = min(15, len(verbs_found) * 3)
    score += verb_score
    breakdown["Action Verbs"] = {"score": verb_score, "max": 15, "found": verbs_found}

    # 5. Contact info (10 pts)
    contact_score = 0
    if re.search(r'[\w.-]+@[\w.-]+\.\w+', text):
        contact_score += 5
    if re.search(r'(\+?\d[\d\s\-]{8,}\d)', text):
        contact_score += 3
    if re.search(r'linkedin\.com', text_lower):
        contact_score += 2
    score += contact_score
    breakdown["Contact Info"] = {"score": contact_score, "max": 10}

    return min(100, score), breakdown


def analyze_resume(text):
    text_lower = text.lower()

    # Categorized skills
    found_skills = {}
    for category, skills in SKILLS_DB.items():
        matched = [s for s in skills if s in text_lower]
        if matched:
            found_skills[category] = matched

    word_count = len(text.split())
    ats_score, breakdown = calculate_ats_score(text)

    # Suggestions
    suggestions = []

    if word_count < 300:
        suggestions.append({"type": "warning", "icon": "📝", "text": "Resume is too short. Aim for 400–700 words with detailed descriptions."})
    elif word_count > 1000:
        suggestions.append({"type": "info", "icon": "✂️", "text": "Resume may be too long. Consider trimming to 1–2 pages for better ATS parsing."})

    total_skills = sum(len(v) for v in found_skills.values())
    if total_skills < 5:
        suggestions.append({"type": "warning", "icon": "🛠️", "text": "Add more technical skills. Include tools, frameworks, and languages you know."})

    if not re.search(r'[\w.-]+@[\w.-]+\.\w+', text):
        suggestions.append({"type": "error", "icon": "📧", "text": "No email address detected. Add your professional email to the resume."})

    if not re.search(r'(\+?\d[\d\s\-]{8,}\d)', text):
        suggestions.append({"type": "warning", "icon": "📞", "text": "Phone number not found. Recruiters need a way to contact you."})

    if not any(kw in text_lower for kw in SECTION_KEYWORDS["experience"]):
        suggestions.append({"type": "warning", "icon": "💼", "text": "No work experience section detected. Add internships, part-time, or freelance work."})

    if not any(kw in text_lower for kw in SECTION_KEYWORDS["projects"]):
        suggestions.append({"type": "info", "icon": "🚀", "text": "Add a Projects section showcasing real-world applications of your skills."})

    if not any(kw in text_lower for kw in SECTION_KEYWORDS["certifications"]):
        suggestions.append({"type": "info", "icon": "🎓", "text": "Consider adding certifications (AWS, Google, Coursera, etc.) to boost credibility."})

    if not re.search(r'linkedin\.com', text_lower):
        suggestions.append({"type": "info", "icon": "🔗", "text": "Include your LinkedIn profile URL for professional presence."})

    verbs_found = [v for v in ACTION_VERBS if v in text_lower]
    if len(verbs_found) < 3:
        suggestions.append({"type": "warning", "icon": "⚡", "text": f"Use more action verbs like: {', '.join(ACTION_VERBS[:6])}... to make bullet points impactful."})

    if not suggestions:
        suggestions.append({"type": "success", "icon": "🌟", "text": "Great resume! Well-structured with good content coverage."})

    return found_skills, word_count, suggestions, ats_score, breakdown


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        file = request.files.get("resume")
        if file and file.filename.endswith(".pdf"):
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            text = extract_text(path)
            skills, count, suggestions, ats_score, breakdown = analyze_resume(text)
            result = {
                "skills": skills,
                "count": count,
                "suggestions": suggestions,
                "ats_score": ats_score,
                "breakdown": breakdown,
                "filename": file.filename,
            }

    return render_template("index.html", result=result)


if __name__ == "__main__":
    app.run(debug=True)