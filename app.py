from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from pypdf import PdfReader
import io
import os
import re

app = Flask(__name__)
CORS(app)

# Extended skills database with categories
SKILLS_DB = {
    "Programming Languages": ["python", "java", "c++", "c#", "javascript", "typescript", "ruby", "go", "rust", "kotlin", "swift", "scala", "r", "matlab", "php"],
    "Web Technologies": ["html", "css", "react", "angular", "vue", "node.js", "django", "flask", "fastapi", "spring boot", "rest api", "graphql"],
    "Data & ML": ["machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "nlp", "computer vision", "data analysis", "tableau", "power bi"],
    "Databases": ["sql", "mysql", "postgresql", "mongodb", "redis", "cassandra", "elasticsearch", "sqlite", "oracle"],
    "Cloud & DevOps": ["aws", "azure", "gcp", "docker", "kubernetes", "ci/cd", "terraform", "jenkins", "git", "linux", "devops"],
    "Soft Skills": ["leadership", "communication", "teamwork", "problem solving", "agile", "scrum", "project management", "collaboration"],
}

SECTION_KEYWORDS = {
    "education": ["education", "university", "college", "degree", "bachelor", "master", "phd", "b.tech", "m.tech", "b.e", "m.e"],
    "experience": ["experience", "internship", "work history", "employment", "worked at", "company", "organization"],
    "projects": ["project", "built", "developed", "created", "designed", "implemented", "deployed"],
    "certifications": ["certification", "certified", "certificate", "course", "training", "credential"],
    "achievements": ["award", "achievement", "honor", "recognition", "won", "rank", "top", "best"],
}

ACTION_VERBS = ["developed", "built", "designed", "implemented", "managed", "led", "created", "improved",
                "optimized", "delivered", "collaborated", "architected", "launched", "analyzed", "automated"]


def extract_text_from_bytes(file_bytes):
    text = ""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""
    return text


def calculate_ats_score(text):
    text_lower = text.lower()
    score = 0
    breakdown = {}

    all_skills = [s for group in SKILLS_DB.values() for s in group]
    found_skills_count = sum(1 for skill in all_skills if skill in text_lower)
    skill_score = min(30, found_skills_count * 2)
    score += skill_score
    breakdown["Skills"] = {"score": skill_score, "max": 30, "found": found_skills_count}

    sections_found = []
    for section, keywords in SECTION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            sections_found.append(section)
    section_score = min(25, len(sections_found) * 5)
    score += section_score
    breakdown["Sections"] = {"score": section_score, "max": 25, "found": sections_found}

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

    verbs_found = [v for v in ACTION_VERBS if v in text_lower]
    verb_score = min(15, len(verbs_found) * 3)
    score += verb_score
    breakdown["Action Verbs"] = {"score": verb_score, "max": 15, "found": verbs_found}

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


def calculate_job_match(resume_text, job_desc_text):
    job_words = set(re.findall(r'\b\w+\b', job_desc_text.lower()))
    resume_words = set(re.findall(r'\b\w+\b', resume_text.lower()))

    matches = job_words.intersection(resume_words)
    match_score = len(matches) / len(job_words) * 100 if job_words else 0

    all_skills = [s for group in SKILLS_DB.values() for s in group]
    job_skills = [s for s in all_skills if s in job_desc_text]
    resume_skills = [s for s in all_skills if s in resume_text]
    skill_matches = set(job_skills).intersection(set(resume_skills))
    skill_match_score = len(skill_matches) / len(job_skills) * 100 if job_skills else 0

    return {
        "overall_match": min(100, match_score),
        "skill_match": min(100, skill_match_score),
        "matched_keywords": list(matches)[:20],
        "missing_skills": list(set(job_skills) - set(resume_skills))
    }


def analyze_resume(text, job_desc=None):
    text_lower = text.lower()

    found_skills = {}
    for category, skills in SKILLS_DB.items():
        matched = [s for s in skills if s in text_lower]
        if matched:
            found_skills[category] = matched

    word_count = len(text.split())
    ats_score, breakdown = calculate_ats_score(text)

    job_match = None
    if job_desc:
        job_match = calculate_job_match(text_lower, job_desc.lower())

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

    return found_skills, word_count, suggestions, ats_score, breakdown, job_match


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    if request.method == "POST":
        file = request.files.get("resume")
        job_desc = request.form.get("job_desc", "").strip()
        if file and file.filename.endswith(".pdf"):
            file_bytes = file.read()
            text = extract_text_from_bytes(file_bytes)
            if text.strip():
                skills, count, suggestions, ats_score, breakdown, job_match = analyze_resume(text, job_desc if job_desc else None)
                result = {
                    "skills": skills,
                    "count": count,
                    "suggestions": suggestions,
                    "ats_score": ats_score,
                    "breakdown": breakdown,
                    "job_match": job_match,
                    "filename": file.filename,
                }
            else:
                error = "Could not extract text from the PDF. Please ensure it's a valid PDF with selectable text."
        else:
            error = "Please upload a valid PDF file."

    return render_template("index.html", result=result, error=error)


if __name__ == "__main__":
    app.run(debug=True)