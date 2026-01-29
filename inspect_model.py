from ultralytics import YOLO
import os

# Load the model
model_path = os.path.join("ml_engine", "models", "best.pt")
print(f"Loading model from: {model_path}")
try:
    model = YOLO(model_path)
    # Write to file
    with open("classes_out.txt", "w", encoding="utf-8") as f:
        for k, v in model.names.items():
            f.write(f"{k}: {v}\n")
    print("Done writing classes_out.txt")
except Exception as e:
    print(f"Error: {e}")
