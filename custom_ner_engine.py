import spacy


def extract_skills(text):
    """
    CUSTOM NER MODEL ENGINE (Option B)
    This will eventually load a custom-trained spaCy model
    that we train on thousands of Kaggle resumes.
    """
    if not text.strip():
        return []

    try:
        # NOTE: 'en_pipeline_custom' is a placeholder name for the model we will train later.
        # For now, if the model isn't built yet, we return a placeholder message.
        nlp = spacy.load("en_pipeline_custom")

        doc = nlp(text)
        extracted = []

        # In a trained NER model, you look for the specific labels you taught it (e.g., "SKILL")
        for ent in doc.ents:
            if ent.label_ == "SKILL":
                extracted.append(ent.text.title())

        return sorted(list(set(extracted)))

    except OSError:
        # If the model hasn't been trained and saved to the folder yet, catch the error smoothly.
        return ["Error: Custom Model Not Trained Yet. Please run the training script."]
    except Exception as e:
        print(f"❌ NER Error: {e}")
        return ["Error: NER Extraction Failed"]