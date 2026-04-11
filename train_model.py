import spacy
from spacy.training.example import Example
import random
import json
import os
import warnings

warnings.filterwarnings("ignore")


def generate_clean_dataset():
    """Generates a hyper-clean, localized dataset since the public one is corrupted."""
    print("🛠️ Generating clean local dataset...")

    # We provide the exact character spans for the skills
    raw_data = [
        # --- POSITIVE EXAMPLES (TECH & BUSINESS SKILLS) ---
        ("Proficient in Python and Java programming.", [(14, 20, "SKILL"), (25, 29, "SKILL")]),
        ("Expertise in Financial Modeling and Corporate Finance.", [(13, 31, "SKILL"), (36, 53, "SKILL")]),
        ("Built cloud apps using Docker, Kubernetes, and AWS.",
         [(23, 29, "SKILL"), (31, 41, "SKILL"), (47, 50, "SKILL")]),
        ("Strong knowledge of Digital Marketing and SEO strategies.", [(20, 37, "SKILL"), (42, 45, "SKILL")]),
        ("Developed backends with Node.js, Express, and MongoDB.",
         [(24, 31, "SKILL"), (33, 40, "SKILL"), (46, 53, "SKILL")]),
        ("Managed Talent Acquisition and HRIS systems.", [(8, 26, "SKILL"), (31, 35, "SKILL")]),
        ("Implemented Agile and Scrum methodologies.", [(12, 17, "SKILL"), (22, 27, "SKILL")]),
        ("Experience with React, Tailwind CSS, and TypeScript.",
         [(16, 21, "SKILL"), (23, 35, "SKILL"), (41, 51, "SKILL")]),
        ("Performed Market Research and Supply Chain Management.", [(10, 25, "SKILL"), (30, 53, "SKILL")]),
        ("Data visualization using Tableau and Power BI.", [(25, 32, "SKILL"), (37, 45, "SKILL")]),
        ("Specialized in Machine Learning and Deep Learning.", [(15, 31, "SKILL"), (36, 49, "SKILL")]),
        ("Utilized Salesforce CRM for Lead Generation.", [(9, 19, "SKILL"), (20, 23, "SKILL"), (28, 43, "SKILL")]),
        ("Setup CI/CD pipelines using Jenkins and GitHub Actions.",
         [(6, 11, "SKILL"), (28, 35, "SKILL"), (40, 54, "SKILL")]),
        ("Knowledge of Risk Management and Portfolio Management.", [(13, 28, "SKILL"), (33, 53, "SKILL")]),
        ("Used LangChain and ChromaDB for AI projects.", [(5, 14, "SKILL"), (19, 27, "SKILL")]),
        ("Strategic Planning and Business Intelligence expert.", [(0, 18, "SKILL"), (23, 44, "SKILL")]),
        ("Frontend skills in HTML, CSS, and Javascript.", [(19, 23, "SKILL"), (25, 28, "SKILL"), (34, 44, "SKILL")]),
        ("Experienced in Auditing and Taxation services.", [(15, 23, "SKILL"), (28, 36, "SKILL")]),
        ("Deployed models on Google Cloud and Microsoft Azure.", [(19, 31, "SKILL"), (36, 51, "SKILL")]),
        ("Proficient in Lean Manufacturing and Six Sigma.", [(14, 32, "SKILL"), (37, 46, "SKILL")]),

        # --- NEGATIVE EXAMPLES (TEACHING IT TO IGNORE DIRT) ---
        ("I have a Bachelor of Computer Applications degree.", []),
        ("I am a highly motivated individual with a GPA of 3.8.", []),
        ("Managed cross-functional teams and improved efficiency.", []),
        ("References available upon request.", []),
        ("I am currently living in Ghaziabad, Uttar Pradesh.", []),
        ("Seeking a challenging role in a dynamic organization.", []),
        ("Awarded Best Student in the final year project.", []),
        ("Looking for internships in the tech industry.", []),
        ("Monitoring GPU Memory Usage and Inference Efficiency.", []),  # Targeting specific dirt from before
        ("Education M.Tech in Artificial Intelligence.", [(23, 46, "SKILL")]),  # Only AI is a skill, M.Tech is not
        ("Personal details and contact information.", []),
        ("Interests include photography and traveling.", [])
    ]

    # We duplicate and shuffle the data to simulate a larger dataset for the neural network
    spacy_data = []
    for _ in range(5):  # Multiply our 15 core sentences into 75 training steps
        for text, entities in raw_data:
            spacy_data.append((text, {"entities": entities}))

    # Save a hard copy so you can see what ML training data looks like
    with open("clean_training_data.json", "w") as f:
        json.dump(spacy_data, f, indent=4)

    return spacy_data


def train_ner_model(training_data, output_dir="en_pipeline_custom", iterations=15):
    """Fine-tunes a grammar-aware English model on our clean data."""
    print("🚀 Loading pre-trained English Foundation Model (Grammar Brain)...")

    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("❌ Error: Foundation model not found. Run 'python -m spacy download en_core_web_sm' first.")
        return

    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
    else:
        ner = nlp.get_pipe("ner")

    # Add our custom label
    for _, annotations in training_data:
        for ent in annotations.get("entities"):
            ner.add_label(ent[2])

    print(f"🧠 Fine-Tuning model for {iterations} Epochs...")

    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.resume_training()

        for itn in range(iterations):
            random.shuffle(training_data)
            losses = {}

            for text, annotations in training_data:
                doc = nlp.make_doc(text)
                example = Example.from_dict(doc, annotations)
                nlp.update([example], drop=0.35, sgd=optimizer, losses=losses)

            print(f"   Epoch {itn + 1}/{iterations} | Loss: {losses.get('ner', 0):.2f}")

    print(f"💾 Saving production-ready model to directory: {output_dir}")
    nlp.to_disk(output_dir)
    print("🎉 AI Model Training Complete!")


if __name__ == "__main__":
    # 1. Generate our hyper-clean local dataset
    train_data = generate_clean_dataset()

    # 2. Train the model
    train_ner_model(train_data, iterations=15)