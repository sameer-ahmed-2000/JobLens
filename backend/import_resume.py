import sys
import os
import json
import secrets
import hashlib
from app.repositories.uow import UnitOfWork

def import_resume(file_path: str, user_id: str) -> bool:
    if not os.path.exists(file_path):
        print(f"Error: Resume file not found at {file_path}")
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: Failed to parse JSON from {file_path}: {e}")
        return False

    with UnitOfWork() as uow:
        # Check if user exists, if not create one with a secure token
        user = uow.users.get_by_id(user_id)
        if not user:
            print(f"User {user_id} not found. Creating a new user...")
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            user = uow.users.create(
                name=f"User {user_id}",
                email=f"{user_id}@joblens.ai",
                user_id=user_id,
                token_hash=token_hash
            )
            print("==================================================================")
            print("!!! IMPORTANT: A NEW USER HAS BEEN CREATED !!!")
            print(f"User ID: {user_id}")
            print(f"Raw API Token: {raw_token}")
            print("Keep this token safe. You must pass it in the Authorization header:")
            print(f"Authorization: Bearer {raw_token}")
            print("==================================================================")

        # Upsert the resume (this will compute embeddings and save raw_text/parsed_skills)
        print("Migrating/Seeding resume structure and computing embeddings...")
        uow.resumes.upsert_resume(
            user_id=user_id,
            title=data.get("title", "AI Engineer"),
            years_experience=data.get("years_experience", 0.0),
            skills=data.get("skills", []),
            projects=data.get("projects", [])
        )
        uow.commit()

    print(f"Successfully imported and active-seeded resume for user {user_id}!")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python import_resume.py <path_to_resume.json> <user_id>")
        sys.exit(1)
    
    # Set backend in path in case running from root
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    import_resume(sys.argv[1], sys.argv[2])
