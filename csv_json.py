import csv
import json


def convert_csv_to_json():
    # 1. Update these variables based on your downloaded file
    csv_file_path = 'downloaded_kaggle_skills.csv'
    column_name = 'Skill_Name'  # Change this to whatever the column is actually called

    skills_list = set()  # Use a set to automatically remove any duplicates

    try:
        # 2. Open and read the CSV
        with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                skill = row.get(column_name)
                if skill:
                    # Clean it up: lowercase it and strip extra spaces
                    skills_list.add(skill.strip().lower())

        # 3. Sort the list alphabetically
        final_list = sorted(list(skills_list))

        # 4. Save it to your mega_skills.json file
        with open('mega_skills.json', 'w', encoding='utf-8') as json_file:
            json.dump(final_list, json_file, indent=4)

        print(f"✅ Success! Saved {len(final_list)} skills to mega_skills.json")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    convert_csv_to_json()