import pdfplumber
import requests
import json
import re

# Configuration for your local Ollama instance
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma:2b"


def extract_text_from_pdf(pdf_file):
    """Reads a PDF file and extracts raw text."""
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_skills(text):
    """
    EXPERIMENTAL LLM EXTRACTION:
    Uses an Elite ATS System Persona and Few-Shot Prompting to force
    a 2B parameter model to perform like an enterprise AI.
    """
    if not text.strip():
        return []

    # --- THE ELITE ATS 'FEW-SHOT' PROMPT ---
    prompt = f"""You are an elite, highly strict Applicant Tracking System (ATS) for a university placement cell. 
Your ONLY job is to extract a comprehensive, exhaustive list of technical skills, programming languages, databases, cloud platforms, and frameworks from the provided resume.

CRITICAL RULES:
1. DO NOT summarize. You must extract EVERY single technical tool mentioned, even niche ones.
2. Ignore soft skills (e.g., "teamwork") and sentence fragments (e.g., "GPU memory usage").
3. You must output ONLY a comma-separated list of skills. Absolutely zero conversational text.

EXAMPLE INPUT: "Developed an AI pipeline using Python, LangChain, Llama-3, and ChromaDB on AWS."
EXAMPLE OUTPUT: Python, LangChain, Llama-3, ChromaDB, AWS

ACTUAL RESUME TEXT TO PROCESS:
{text}

OUTPUT:"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            # The "Zero Temperature" Freeze: Forces strict factual extraction, no creativity.
            "temperature": 0.0,
            "top_p": 0.9
        }
    }

    try:
        print(f"🧠 Sending resume to Ollama ({OLLAMA_MODEL}) with Elite ATS Prompt...")
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()

        # Get the raw text reply from the AI
        ai_reply = response.json().get("response", "")

        # --- THE SANITIZATION LAYER ---

        # 1. AI sometimes ignores the comma rule and uses newlines or bullet points.
        # Convert all newlines and asterisks into commas first.
        ai_reply = ai_reply.replace('\n', ',').replace('*', ',').replace('-', ',')

        raw_skills = ai_reply.split(',')
        cleaned_skills = []

        # Words we know are just AI conversational garbage
        ai_garbage = {"sure", "here", "extracted", "skills", "resume", "text", "the", "are", "is", "list", "below",
                      "from", "certainly"}

        for skill in raw_skills:
            # Clean up leading/trailing spaces and weird punctuation
            clean_w = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9\+]+$', '', skill.strip()).title()

            # 2. Kill empty fragments or single letters
            if len(clean_w) <= 1:
                continue

            # 3. Kill conversational sentences (e.g., "Here Are The Skills" is 4 words. Skills are rarely > 3 words)
            if len(clean_w.split()) > 3:
                continue

            # 4. Kill isolated polite words
            if clean_w.lower() in ai_garbage:
                continue

            cleaned_skills.append(clean_w)

        # Remove duplicates and sort alphabetically
        final_skills = sorted(list(set(cleaned_skills)))

        return final_skills

    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to Ollama.")
        return ["Error: Ollama Not Running"]
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return ["Error: Extraction Failed"]


# --- STANDALONE TESTING BLOCK ---
if __name__ == "__main__":
    print("🧪 Ollama Resume Parser Test 🧪")

    # Hardcoded test text to simulate a resume without needing a PDF
    test_text = """
    Rohan Mehta - AI Engineer
    Experience: 3.5 years of experience deploying scalable AI systems. Specialized in LLM fine-tuning and production-grade MLOps pipelines.
    Skills: PyTorch, TensorFlow, LangChain, Hugging Face, ChromaDB, Docker, Kubernetes, QLoRA, Pinecone.
    Managerial: Led cross-functional teams, implemented Agile methodologies, and drove strategic planning for product launches.
    """

    print("\nExtracting skills from test text...")
    extracted = extract_skills(test_text)

    print("\n✅ Extraction Complete!")
    print(json.dumps(extracted, indent=2))