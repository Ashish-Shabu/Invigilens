import torch
import os

model_path = os.path.join("ml_engine", "models", "best.pt")

print(f"Loading {model_path}...")
ckpt = torch.load(model_path, map_location='cpu', weights_only=False)

print("\n=== RAW TRAINING METRICS ===")
if 'train_metrics' in ckpt:
    metrics = ckpt['train_metrics']
    for k, v in metrics.items():
        print(f"{k}: {v}")
else:
    print("No train_metrics found.")

print("\n=== RAW TRAINING RESULTS ===")
if 'train_results' in ckpt:
    # Just print the last epoch's results, or the whole thing if it's small
    results = ckpt['train_results']
    print(results)
else:
    print("No train_results found.")
