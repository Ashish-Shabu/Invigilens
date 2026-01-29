import os
import sys
import argparse
import pandas as pd
from deepface import DeepFace
from pymongo import MongoClient
import cv2

# Adjust path to find backend
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
if not MONGO_URI:
    print("Error: MONGO_URI not found in .env")
    exit(1)

def connect_db():
    client = MongoClient(MONGO_URI)
    db = client.get_database('invigilens') # Default db name unless specified in URI path
    # If URI implies a DB, use that.
    return db

def import_students(excel_path, images_dir):
    print(f"Reading Excel: {excel_path}")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    db = connect_db()
    students_coll = db['students']

    success_count = 0
    fail_count = 0

    # Ensure Collection has index on rollNo
    students_coll.create_index("rollNo", unique=True)

    print("Starting Import...")

    for index, row in df.iterrows():
        try:
            roll_no = str(row['RollNo']).strip()
            name = str(row['Name']).strip()
            image_file = str(row['ImageFile']).strip()

            image_path = os.path.join(images_dir, image_file)
            
            if not os.path.exists(image_path):
                print(f"[SKIP] Image not found for {name} ({roll_no}): {image_path}")
                fail_count += 1
                continue

            print(f"Processing {name} ({roll_no})...")

            # Generate Embedding using DeepFace (FaceNet model is robust)
            # This returns a list of embeddings. We take the first face found.
            # Using 'Facenet' model for good balance of speed/accuracy
            embeddings = DeepFace.represent(img_path=image_path, model_name="Facenet", enforce_detection=False)
            
            if not embeddings:
                print(f"[SKIP] No face detected in {image_file}")
                fail_count += 1
                continue

            embedding_vector = embeddings[0]['embedding']

            # UPSERT (Update if exists, Insert if new)
            student_doc = {
                "rollNo": roll_no,
                "name": name,
                "embedding": embedding_vector,
                "photoPath": image_file, # Optional: In a real app, upload this to S3
                "registeredAt": pd.Timestamp.now()
            }

            students_coll.update_one(
                {"rollNo": roll_no},
                {"$set": student_doc},
                upsert=True
            )
            
            print(f"[OK] Saved {name}")
            success_count += 1

        except Exception as e:
            print(f"[ERROR] Failed row {index}: {e}")
            fail_count += 1

    print("-" * 30)
    print(f"Import Complete.\nSuccess: {success_count}\nFailed: {fail_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk Import Students for InvigiLens")
    parser.add_argument("--excel", required=True, help="Path to Excel/CSV file")
    parser.add_argument("--images", required=True, help="Path to folder containing student images")
    
    args = parser.parse_args()
    
    import_students(args.excel, args.images)
