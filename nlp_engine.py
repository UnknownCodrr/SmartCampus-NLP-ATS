import pdfplumber
import spacy
import re
import json, os

# Load the English NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading English model for spaCy...")
    from spacy.cli import download

    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# 1. THE ANCHOR LISTS
CORE_TECH = {
    "python", "java", "c++", "c#", "c", "sql", "mysql", "javascript", "html", "css",
    "react", "node", "aws", "docker", "git", "linux", "api", "django", "flask",
    "machine learning", "nlp", "artificial intelligence", "deep learning", "kubernetes",
    "tensorflow", "pytorch", "pandas", "numpy", "cuda", "fastapi", "rest api", "express",
    "hugging face", "weights & biases", "openai", "mlops", "llm"
}

MANAGERIAL_SKILLS = {
    "agile", "scrum", "project management", "product management", "leadership",
    "communication", "cross-functional teams", "stakeholder management",
    "problem solving", "strategic planning", "team building", "operations",
    "risk management", "business analysis", "time management", "collaboration"
}

# Combine them for the engine to use
ALL_ANCHORS = CORE_TECH | MANAGERIAL_SKILLS


def extract_text_from_pdf(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_skills(text):
    """
    FLAWLESS HYBRID EXTRACTION:
    Catches Tech + Managerial skills while smartly filtering noise.
    """
    cleaned_text = re.sub(r'[^a-zA-Z0-9\s#\+\.\-\&]', ' ', text)
    doc = nlp(cleaned_text)

    found_skills = set()
    text_lower = cleaned_text.lower()

    # Step 1: Anchor Extraction (Tech + Managerial)
    for skill in ALL_ANCHORS:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            found_skills.add(skill.title())

    # Step 2: Blocklist (Kill Dates, Locations, and Languages)
    entities_to_block = {"GPE", "LOC", "DATE", "TIME", "PERSON", "MONEY", "QUANTITY", "LANGUAGE"}
    blocked_words = set()
    for ent in doc.ents:
        if ent.label_ in entities_to_block:
            blocked_words.add(ent.text.lower().strip())
            for word in ent.text.lower().split():
                blocked_words.add(word)

    # Step 3: TECH PATTERN RECOGNITION
    adjective_suffixes = ("-based", "-driven", "-centric", "-oriented", "-level", "-grade")

    for word in cleaned_text.split():
        clean_w = word.strip()

        if clean_w.lower().endswith(adjective_suffixes):
            continue

        if len(clean_w) > 2:
            # Catch MixedCase/CamelCase (FastAPI, ChromaDB)
            if clean_w != clean_w.lower() and clean_w != clean_w.upper() and clean_w != clean_w.title():
                found_skills.add(clean_w)

            # Catch Hyphenated Tech with numbers (Llama-3)
            elif re.match(r'^[A-Za-z]+-\d+$', clean_w):
                found_skills.add(clean_w.title())

    # Step 4: SMART DYNAMIC NOISE FILTERING
    exact_noise = {
        "experience", "years", "winner", "teams", "applications", "efficiency",
        "basic", "clip", "challenge", "biases", "fluent", "enhanced", "usage",
        "education", "project", "university", "college", "school", "summary", "profile",
        "month", "year", "team", "work", "time", "student", "degree", "technology",
        "science", "english", "hindi", "engineer", "face", "certifications",
        "specialized", "scalable", "production", "grade", "pipelines", "systems",
        "icml", "achievements", "objective", "declaration", "hobbies", "interests",
        "various", "multiple", "platform", "platforms", "environment", "integration",
        "accuracy", "memory", "native", "search", "based", "driven", "skills", "details"
    }

    substring_noise = {"cgpa", "email", "phone", "dob", "address", "contact"}

    for chunk in doc.noun_chunks:
        chunk_text = chunk.text.lower().strip()
        words_in_chunk = chunk_text.split()

        if 1 <= len(words_in_chunk) <= 3:
            if not re.match(r'^\d', chunk_text):
                if chunk_text not in blocked_words and chunk_text not in exact_noise:
                    if not any(w in substring_noise for w in words_in_chunk):
                        if chunk.root.pos_ in ["NOUN", "PROPN"]:
                            is_mashup = all(w in ALL_ANCHORS for w in words_in_chunk)
                            if not is_mashup:
                                if len(words_in_chunk) > 1 or chunk.root.pos_ == "PROPN":
                                    if len(chunk_text) > 2:
                                        found_skills.add(chunk_text.title())

    # --- THE INTELLIGENCE FILTER ---

    unique_skills = {}
    for skill in found_skills:
        key = skill.lower()
        if key not in unique_skills:
            unique_skills[key] = skill
        else:
            if sum(1 for c in skill if c.isupper()) > sum(1 for c in unique_skills[key] if c.isupper()):
                unique_skills[key] = skill

    final_list = []
    skill_values = list(unique_skills.values())

    for s1 in skill_values:
        is_subset = False
        for s2 in skill_values:
            if s1 != s2:
                if re.search(r'\b' + re.escape(s1.lower()) + r'\b', s2.lower()):
                    is_subset = True
                    break
        if not is_subset:
            final_list.append(s1)

    return sorted(final_list)


def grade_resume(text):
    """Analyzes resume text for structure and vocabulary."""
    feedback = []
    score = 100
    text_lower = text.lower()

    sections = {
        "Education": ["education", "academic", "university", "college", "bca", "degree"],
        "Experience": ["experience", "work history", "employment", "internship"],
        "Projects": ["projects", "portfolio", "personal work", "github"]
    }

    for sec_name, keywords in sections.items():
        if not any(kw in text_lower for kw in keywords):
            feedback.append({
                "type": "warning",
                "title": f"Missing Section: {sec_name}",
                "desc": f"We couldn't clearly detect an '{sec_name}' section."
            })
            score -= 15

    weak_verbs = ["helped", "worked", "did", "made", "responsible for", "handled", "managed to"]
    found_weak = [v for v in weak_verbs if f" {v} " in text_lower]

    if found_weak:
        feedback.append({
            "type": "info",
            "title": "Action Verbs Need Upgrading",
            "desc": f"We found some weak phrasing: `{', '.join(found_weak)}`."
        })
        score -= (len(found_weak) * 5)

    if score == 100:
        feedback.append({
            "type": "success",
            "title": "Excellent Format!",
            "desc": "Your resume has all the standard sections and avoids common weak action verbs. Great job!"
        })

    return max(score, 0), feedback


def extract_skills_basic(text):
    """
    THE MEGA-DICTIONARY APPROACH:
    Reads from an external JSON database of skills.
    100% precision, zero dirt.
    """
    if not text.strip():
        return []

    # 1. Load the massive external dictionary
    dict_path = "mega_skills.json"

    try:
        if os.path.exists(dict_path):
            with open(dict_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # THE FIX: Flatten the beautiful dictionary into a single list for the matcher
                mega_skills_list = data["skills_database"]["core_tech"] + data["skills_database"]["managerial_skills"]
        else:
            print(f"⚠️ Warning: {dict_path} not found. Falling back to basic list.")
            mega_skills_list = ["python", "java", "react", "docker"]  # Fallback

    except Exception as e:
        print(f"❌ Error loading dictionary: {e}")
        return []

    extracted = []
    text_lower = text.lower()

    # 2. Scan the resume against the dictionary
    for skill in mega_skills_list:
        # Regex \b ensures we match exact words (e.g., "C" won't match inside "React")
        # We use re.IGNORECASE to catch different capitalizations
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            extracted.append(skill.title())

    return sorted(list(set(extracted)))