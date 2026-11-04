
from pathlib import Path
import joblib

MODEL_DIR = Path("ml_results/models")

print("\n========== MODEL INSPECTION ==========\n")

model_files = list(MODEL_DIR.glob("*.joblib"))

if not model_files:
    print("No .joblib model files found.")
    raise SystemExit

for model_path in model_files:

    print("\nModel:", model_path.name)

    model = joblib.load(model_path)

    print("Python class:", type(model))

    # Check sklearn-style feature names
    feature_names = getattr(
        model,
        "feature_names_in_",
        None
    )

    if feature_names is not None:
        print("Feature names:")
        for feature in feature_names:
            print(" -", feature)

    # Check XGBoost booster feature names
    if hasattr(model, "get_booster"):

        booster = model.get_booster()

        print("Number of features:", booster.num_features())

        print("XGBoost feature names:")

        print(booster.feature_names)

    # Check number of input features
    if hasattr(model, "n_features_in_"):
        print("Input feature count:", model.n_features_in_)

    # Check pipeline components
    if hasattr(model, "named_steps"):

        print("Pipeline steps:")

        for name, step in model.named_steps.items():
            print(name, ":", type(step))

print("\n========== INSPECTION COMPLETE ==========")
