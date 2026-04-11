# The "Smart Dictionary" of common aliases and variations.
# Maps what people type -> to the official name in mega_skills.json
ALIAS_MAP = {
    # The .js offenders
    "react.js": "react",
    "reactjs": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "vue.js": "vue",
    "vuejs": "vue",
    "angular.js": "angular",
    "angularjs": "angular",
    "nextjs": "next.js",

    # Common abbreviations
    "postgres": "postgresql",
    "golang": "go",
    "c plus plus": "c++",
    "c sharp": "c#",
    "amazon web services": "aws",
    "google cloud platform": "gcp",
    "k8s": "kubernetes",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "dl": "deep learning",
    "nlp": "natural language processing"  # Maps to nlp which is in our DB
}


def normalize_skill(skill):
    """
    Intercepts a skill, cleans it up, and checks if it's a known alias.
    If it is, it translates it. If not, it returns the clean original.
    """
    clean_skill = skill.lower().strip()
    # .get() looks for the alias. If not found, it defaults back to clean_skill
    return ALIAS_MAP.get(clean_skill, clean_skill)


def calculate_match_score(student_skills, job_required_skills):
    """
    Compares student skills against job skills using Smart Alias Mapping.
    Returns the match percentage and a list of missing skills.
    """

    # Step 1: Normalize everything before doing the math!
    # If a student has "React.js" and the job asks for "react", both become "react" here.
    student_set = set([normalize_skill(skill) for skill in student_skills])
    job_set = set([normalize_skill(skill) for skill in job_required_skills])

    if not job_set:
        return 0.0, []  # Avoid division by zero

    # Step 2: The lightning-fast mathematical intersection
    matched_skills = job_set.intersection(student_set)

    # Step 3: Calculate percentage
    match_percentage = (len(matched_skills) / len(job_set)) * 100

    # Step 4: Find what the student is missing
    missing_skills = list(job_set - student_set)

    return round(match_percentage, 2), missing_skills