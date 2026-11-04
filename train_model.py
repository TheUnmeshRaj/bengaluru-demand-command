"""Train and compare historical-only and context-aware demand models.

Input:
    zone_demand_5min.csv

Outputs (inside ml_results/):
    model_metrics.csv
    test_subgroup_metrics.csv
    test_predictions.csv
    feature_importance_*.csv
    split_metadata.txt
    fitted model files (*.joblib)

Forecast target:
    Target_Next_15min = ride requests from a zone during the next 15 minutes.

Split policy:
    Chronological 70% train / 15% validation / 15% test by prediction timestamp.
    A 15-minute purge is applied before train/validation and validation/test
    boundaries so that training labels do not extend into the next split.

Note:
    The data is synthetic. Metrics measure performance on the simulated data,
    not proven real-world Bengaluru ride-hailing accuracy.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# ============================================================
# 1. CONFIGURATION
# ============================================================

DATA_FILE = Path("zone_demand_5min.csv")
OUTPUT_DIR = Path("ml_results")
MODEL_DIR = OUTPUT_DIR / "models"

RANDOM_SEED = 42

TRAIN_FRACTION = 0.70
VALIDATION_FRACTION = 0.15
TEST_FRACTION = 0.15

# Forecast target covers the following 15 minutes.
TARGET_HORIZON_MINUTES = 15

# Set to True to train XGBoost as well as Random Forest.
TRAIN_XGBOOST = True

# Initial laptop-friendly configurations. Increase trees later only if useful.
RANDOM_FOREST_PARAMS = {
    "n_estimators": 100,
    "max_depth": 16,
    "min_samples_leaf": 3,
    "max_features": 0.8,
    "max_samples": 0.75,
    "n_jobs": -1,
    "random_state": RANDOM_SEED,
}

XGBOOST_PARAMS = {
    "n_estimators": 200,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "objective": "reg:squarederror",
    "eval_metric": "mae",
    "tree_method": "hist",
    "n_jobs": -1,
    "random_state": RANDOM_SEED,
}

TARGET_COLUMN = "Target_Next_15min"

# Model A: historical demand, time and zone only.
HISTORICAL_NUMERIC_FEATURES = [
    "Hour",
    "Day_Of_Week",
    "Is_Weekend",
    "Hour_Sin",
    "Hour_Cos",
    "DayOfWeek_Sin",
    "DayOfWeek_Cos",
    "Demand_Last_5min",
    "Demand_Lag_5min",
    "Demand_Lag_10min",
    "Demand_Lag_15min",
    "Demand_Lag_30min",
    "Demand_Lag_60min",
    "Rolling_Mean_15min",
    "Rolling_Mean_30min",
    "Rolling_Mean_60min",
]

HISTORICAL_CATEGORICAL_FEATURES = [
    "Zone_ID",
]

# Model B: all Model A features plus contextual information.
CONTEXT_NUMERIC_FEATURES = [
    "Rain_Intensity",
    "Event_Active",
    "Event_Impact",
    "Event_Intensity",
]

CONTEXT_CATEGORICAL_FEATURES = [
    "Weather_Condition",
    "Event_Type",
    "Event_Phase",
]


# ============================================================
# 2. INPUT VALIDATION AND FEATURE PREPARATION
# ============================================================


def load_dataset() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Cannot find {DATA_FILE.resolve()}. "
            "Run build_ml_dataset.py first and keep this script beside the CSV."
        )

    print(f"Reading {DATA_FILE} ...")
    df = pd.read_csv(
        DATA_FILE,
        low_memory=False,
        parse_dates=["Timestamp"],
    )

    # DayOfWeek_Sin/Cos are derived below, so they are not
    # required to already exist in the CSV.
    derived_features = {"DayOfWeek_Sin", "DayOfWeek_Cos"}
    source_historical_numeric = (
        set(HISTORICAL_NUMERIC_FEATURES) - derived_features
    )

    required = (
        {
            "Timestamp",
            "Zone_ID",
            "Target_Next_15min",
            "Event_Impact",
            "Weather_Condition",
        }
        | source_historical_numeric
        | set(HISTORICAL_CATEGORICAL_FEATURES)
        | set(CONTEXT_NUMERIC_FEATURES)
        | set(CONTEXT_CATEGORICAL_FEATURES)
    )

    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(
            "The ML dataset is missing required columns: " + ", ".join(missing)
        )

    if df["Timestamp"].isna().any():
        raise ValueError("Timestamp contains invalid or missing values.")

    if df.duplicated(["Timestamp", "Zone_ID"]).any():
        raise ValueError("Duplicate Timestamp + Zone_ID records found.")

    df["Zone_ID"] = df["Zone_ID"].astype(str)

    derived_features = {"DayOfWeek_Sin", "DayOfWeek_Cos"}
    numeric_columns = sorted(
        (
            set(HISTORICAL_NUMERIC_FEATURES)
            - derived_features
        )
        | set(CONTEXT_NUMERIC_FEATURES)
        | {TARGET_COLUMN}
    )

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    categorical_columns = sorted(
        set(
            HISTORICAL_CATEGORICAL_FEATURES
            + CONTEXT_CATEGORICAL_FEATURES
        )
    )

    # No-event periods are not missing information.
# Give them an explicit category.

    event_absence = df["Event_Impact"].eq(0)

    df.loc[event_absence, "Event_Type"] = (
        df.loc[event_absence, "Event_Type"].fillna("No_Event")
    )

    df.loc[event_absence, "Event_Phase"] = (
        df.loc[event_absence, "Event_Phase"].fillna("No_Event")
    )

    # Check that event-affected records contain event information.

    event_present = df["Event_Impact"].eq(1)

    if df.loc[event_present, ["Event_Type", "Event_Phase"]].isna().any().any():
        raise ValueError(
            "Event-affected records have missing event information."
    )

    for col in categorical_columns:
        df[col] = df[col].fillna("Unknown").astype(str)

    # Cyclical day-of-week features; Monday=0, Sunday=6.
    dow_angle = 2.0 * np.pi * df["Day_Of_Week"] / 7.0
    df["DayOfWeek_Sin"] = np.sin(dow_angle)
    df["DayOfWeek_Cos"] = np.cos(dow_angle)

    # Do not silently train after dropping arbitrary missing records.
    feature_columns = (
        HISTORICAL_NUMERIC_FEATURES
        + HISTORICAL_CATEGORICAL_FEATURES
        + CONTEXT_NUMERIC_FEATURES
        + CONTEXT_CATEGORICAL_FEATURES
        + [TARGET_COLUMN]
    )

    missing_counts = df[feature_columns].isna().sum()
    bad_missing = missing_counts[missing_counts > 0]
    if not bad_missing.empty:
        raise ValueError(
            "Missing values detected in model inputs/target:\n"
            + bad_missing.to_string()
            + "\nFix the ML dataset before training."
        )

    if (df[TARGET_COLUMN] < 0).any():
        raise ValueError("Forecast target contains negative values.")

    if not np.allclose(
        df[TARGET_COLUMN].to_numpy(),
        np.round(df[TARGET_COLUMN].to_numpy()),
    ):
        warnings.warn(
            "Target values are not all integers. This is allowed for regression, "
            "but verify the aggregation logic."
        )

    df = df.sort_values(["Timestamp", "Zone_ID"]).reset_index(drop=True)

    print(f"Loaded {len(df):,} rows across {df['Zone_ID'].nunique()} zones.")
    print(
        f"Prediction origins: {df['Timestamp'].nunique():,} | "
        f"Date range: {df['Timestamp'].min()} to {df['Timestamp'].max()}"
    )
    return df


# ============================================================
# 3. CHRONOLOGICAL SPLIT WITH LABEL PURGING
# ============================================================


def chronological_split(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, str]]:
    """Split on unique timestamps and purge labels crossing split boundaries."""

    timestamps = pd.DatetimeIndex(
        df["Timestamp"].drop_duplicates().sort_values()
    )

    n_times = len(timestamps)
    if n_times < 100:
        raise ValueError(
            f"Only {n_times} distinct prediction timestamps; too few for this split."
        )

    n_train = int(n_times * TRAIN_FRACTION)
    n_train_val = int(
        n_times * (TRAIN_FRACTION + VALIDATION_FRACTION)
    )

    train_boundary = timestamps[n_train]
    validation_boundary = timestamps[n_train_val]
    purge = pd.Timedelta(minutes=TARGET_HORIZON_MINUTES)

    ts = df["Timestamp"]

    # A training label at time T uses future demand through T+15 minutes.
    # Keep it only when its target horizon ends no later than the boundary.
    train_mask = ts < train_boundary
    train_mask &= ts + purge <= train_boundary

    validation_mask = ts >= train_boundary
    validation_mask &= ts < validation_boundary
    validation_mask &= ts + purge <= validation_boundary

    test_mask = ts >= validation_boundary

    train = df.loc[train_mask].copy()
    validation = df.loc[validation_mask].copy()
    test = df.loc[test_mask].copy()

    if min(len(train), len(validation), len(test)) == 0:
        raise ValueError("One of the chronological splits is empty.")

    metadata = {
        "unique_prediction_timestamps": str(n_times),
        "train_boundary": str(train_boundary),
        "validation_boundary": str(validation_boundary),
        "purge_minutes": str(TARGET_HORIZON_MINUTES),
        "train_rows": str(len(train)),
        "validation_rows": str(len(validation)),
        "test_rows": str(len(test)),
        "train_start": str(train["Timestamp"].min()),
        "train_end": str(train["Timestamp"].max()),
        "validation_start": str(validation["Timestamp"].min()),
        "validation_end": str(validation["Timestamp"].max()),
        "test_start": str(test["Timestamp"].min()),
        "test_end": str(test["Timestamp"].max()),
    }

    return train, validation, test, metadata


# ============================================================
# 4. METRICS AND BASELINE
# ============================================================


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    y_pred = np.maximum(y_pred, 0.0)

    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    denominator = float(np.sum(np.abs(y_true)))

    wape = (
        float(np.sum(np.abs(y_true - y_pred)) / denominator * 100.0)
        if denominator > 0
        else float("nan")
    )

    return {
        "MAE": float(mae),
        "RMSE": rmse,
        "WAPE_percent": wape,
    }


def persistence_baseline(df: pd.DataFrame) -> np.ndarray:
    """Predict next-15-min demand as 3 x the latest 15-min mean."""
    return np.maximum(
        0.0,
        3.0 * df["Rolling_Mean_15min"].to_numpy(dtype=float),
    )


# ============================================================
# 5. PREPROCESSING AND MODEL FACTORIES
# ============================================================


def make_one_hot_encoder() -> OneHotEncoder:
    """Support both newer and older scikit-learn parameter names."""
    try:
        return OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=True,
        )
    except TypeError:
        return OneHotEncoder(
            handle_unknown="ignore",
            sparse=True,
        )


def make_preprocessor(
    numeric_features: List[str],
    categorical_features: List[str],
) -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="constant", fill_value="Unknown"),
            ),
            ("onehot", make_one_hot_encoder()),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
        sparse_threshold=0.3,
    )


def make_feature_sets():
    historical_numeric = HISTORICAL_NUMERIC_FEATURES.copy()
    historical_categorical = HISTORICAL_CATEGORICAL_FEATURES.copy()

    contextual_numeric = (
        historical_numeric + CONTEXT_NUMERIC_FEATURES
    )
    contextual_categorical = (
        historical_categorical + CONTEXT_CATEGORICAL_FEATURES
    )

    return {
        "historical": (
            historical_numeric,
            historical_categorical,
        ),
        "contextual": (
            contextual_numeric,
            contextual_categorical,
        ),
    }


def make_random_forest_pipeline(
    numeric_features: List[str],
    categorical_features: List[str],
) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "preprocessor",
                make_preprocessor(
                    numeric_features,
                    categorical_features,
                ),
            ),
            (
                "model",
                RandomForestRegressor(**RANDOM_FOREST_PARAMS),
            ),
        ]
    )


def make_xgboost_pipeline(
    numeric_features: List[str],
    categorical_features: List[str],
) -> Pipeline:
    try:
        from xgboost import XGBRegressor
    except ImportError as exc:
        raise ImportError(
            "XGBoost is not installed. Run: pip install xgboost"
        ) from exc

    return Pipeline(
        steps=[
            (
                "preprocessor",
                make_preprocessor(
                    numeric_features,
                    categorical_features,
                ),
            ),
            (
                "model",
                XGBRegressor(**XGBOOST_PARAMS),
            ),
        ]
    )


# ============================================================
# 6. TRAIN, EVALUATE AND SAVE MODELS
# ============================================================


def evaluate_and_record(
    rows: List[dict],
    model_name: str,
    split_name: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> None:
    metrics = calculate_metrics(y_true, y_pred)
    rows.append(
        {
            "Model": model_name,
            "Split": split_name,
            "Rows": int(len(y_true)),
            **metrics,
        }
    )


def save_feature_importance(
    pipeline: Pipeline,
    output_file: Path,
) -> None:
    preprocessor = pipeline.named_steps["preprocessor"]
    estimator = pipeline.named_steps["model"]

    try:
        feature_names = preprocessor.get_feature_names_out()
        importances = estimator.feature_importances_
    except (AttributeError, ValueError) as exc:
        warnings.warn(f"Could not extract feature importance: {exc}")
        return

    importance_df = pd.DataFrame(
        {
            "Feature": feature_names,
            "Importance": importances,
        }
    ).sort_values("Importance", ascending=False)

    importance_df.to_csv(output_file, index=False)


def train_model_family(
    family_name: str,
    model_factory,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    feature_sets,
    metrics_rows: List[dict],
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    """Train the historical-only and contextual versions of one algorithm."""

    family_predictions = predictions.copy()
    y_train = train[TARGET_COLUMN].to_numpy(dtype=float)
    y_validation = validation[TARGET_COLUMN].to_numpy(dtype=float)
    y_test = test[TARGET_COLUMN].to_numpy(dtype=float)

    for feature_set_name, (numeric_features, categorical_features) in feature_sets.items():
        model_name = f"{family_name}_{feature_set_name}"

        feature_columns = numeric_features + categorical_features
        X_train = train[feature_columns]
        X_validation = validation[feature_columns]
        X_test = test[feature_columns]

        print("\n" + "=" * 65)
        print(f"Training {model_name}")
        print(f"Training rows: {len(train):,}")
        print(f"Validation rows: {len(validation):,}")
        print(f"Test rows: {len(test):,}")
        print("=" * 65)

        model = model_factory(
            numeric_features,
            categorical_features,
        )

        model.fit(X_train, y_train)

        validation_pred = np.maximum(
            0.0,
            model.predict(X_validation),
        )

        test_pred = np.maximum(
            0.0,
            model.predict(X_test),
        )

        evaluate_and_record(
            metrics_rows,
            model_name,
            "validation",
            y_validation,
            validation_pred,
        )

        evaluate_and_record(
            metrics_rows,
            model_name,
            "test",
            y_test,
            test_pred,
        )

        # Keep predictions in the output for direct model comparison.
        prediction_column = f"{model_name}_prediction"
        family_predictions[prediction_column] = test_pred

        # Save the fitted preprocessing + model pipeline.
        model_path = MODEL_DIR / f"{model_name}.joblib"
        joblib.dump(model, model_path)
        print(f"Saved model: {model_path}")

        # Feature importance is most useful for the contextual model.
        if feature_set_name == "contextual":
            importance_path = (
                OUTPUT_DIR / f"feature_importance_{family_name}_contextual.csv"
            )
            save_feature_importance(model, importance_path)
            print(f"Saved feature importance: {importance_path}")

    return family_predictions


# ============================================================
# 7. TEST SUBGROUP EVALUATION
# ============================================================


def create_subgroup_metrics(
    test: pd.DataFrame,
    test_predictions: pd.DataFrame,
) -> pd.DataFrame:
    """Report performance on event/normal and rain/clear test observations."""

    prediction_columns = [
        c for c in test_predictions.columns
        if c.endswith("_prediction")
    ]

    groups = {
        "all_test": np.ones(len(test), dtype=bool),
        "event_affected": test["Event_Impact"].to_numpy() == 1,
        "normal_period": test["Event_Impact"].to_numpy() == 0,
        "rain": test["Weather_Condition"].astype(str).to_numpy() == "Rain",
        "clear": test["Weather_Condition"].astype(str).to_numpy() == "Clear",
    }

    rows = []
    y_true_all = test[TARGET_COLUMN].to_numpy(dtype=float)

    for group_name, mask in groups.items():
        n = int(mask.sum())
        if n == 0:
            continue

        y_true = y_true_all[mask]

        for prediction_column in prediction_columns:
            model_name = prediction_column.removesuffix("_prediction")
            y_pred = test_predictions.loc[mask, prediction_column].to_numpy(dtype=float)
            rows.append(
                {
                    "Group": group_name,
                    "Model": model_name,
                    "Rows": n,
                    **calculate_metrics(y_true, y_pred),
                }
            )

    return pd.DataFrame(rows)


# ============================================================
# 8. MAIN
# ============================================================


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "#" * 70)
    print("BENGALURU RIDE-HAILING DEMAND - MODEL TRAINING")
    print("#" * 70)

    df = load_dataset()

    train, validation, test, split_metadata = chronological_split(df)

    print("\nChronological split:")
    print(json.dumps(split_metadata, indent=2))

    with open(OUTPUT_DIR / "split_metadata.txt", "w", encoding="utf-8") as f:
        f.write(json.dumps(split_metadata, indent=2))
        f.write("\n\nSplit policy: chronological 70/15/15 by prediction timestamp.\n")
        f.write("A 15-minute purge prevents target windows crossing split boundaries.\n")

    # The persistence baseline predicts the next 15 minutes using
    # three times the mean of the latest completed 15 minutes.
    metrics_rows: List[dict] = []

    validation_baseline = persistence_baseline(validation)
    test_baseline = persistence_baseline(test)

    evaluate_and_record(
        metrics_rows,
        "Persistence_baseline",
        "validation",
        validation[TARGET_COLUMN].to_numpy(dtype=float),
        validation_baseline,
    )

    evaluate_and_record(
        metrics_rows,
        "Persistence_baseline",
        "test",
        test[TARGET_COLUMN].to_numpy(dtype=float),
        test_baseline,
    )

    test_predictions = pd.DataFrame(
        {
            "Timestamp": test["Timestamp"].to_numpy(),
            "Zone_ID": test["Zone_ID"].to_numpy(),
            "Event_Impact": test["Event_Impact"].to_numpy(),
            "Event_Active": test["Event_Active"].to_numpy(),
            "Weather_Condition": test["Weather_Condition"].to_numpy(),
            "Actual_Next_15min": test[TARGET_COLUMN].to_numpy(),
            "Persistence_baseline_prediction": test_baseline,
        }
    )

    feature_sets = make_feature_sets()

    # Random Forest: historical-only and context-aware.
    test_predictions = train_model_family(
        family_name="RandomForest",
        model_factory=make_random_forest_pipeline,
        train=train,
        validation=validation,
        test=test,
        feature_sets=feature_sets,
        metrics_rows=metrics_rows,
        predictions=test_predictions,
    )

    # XGBoost: historical-only and context-aware.
    if TRAIN_XGBOOST:
        test_predictions = train_model_family(
            family_name="XGBoost",
            model_factory=make_xgboost_pipeline,
            train=train,
            validation=validation,
            test=test,
            feature_sets=feature_sets,
            metrics_rows=metrics_rows,
            predictions=test_predictions,
        )

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df = metrics_df.sort_values(
        ["Split", "MAE"]
    ).reset_index(drop=True)

    metrics_path = OUTPUT_DIR / "model_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False)

    predictions_path = OUTPUT_DIR / "test_predictions.csv"
    test_predictions.to_csv(predictions_path, index=False)

    subgroup_df = create_subgroup_metrics(
        test,
        test_predictions,
    )

    subgroup_path = OUTPUT_DIR / "test_subgroup_metrics.csv"
    subgroup_df.to_csv(subgroup_path, index=False)

    print("\n" + "#" * 70)
    print("MODEL METRICS")
    print("#" * 70)
    print(metrics_df.to_string(index=False))

    print("\n" + "#" * 70)
    print("TEST SUBGROUP METRICS")
    print("#" * 70)
    print(subgroup_df.to_string(index=False))

    print("\nSaved outputs:")
    print(f"1. {metrics_path}")
    print(f"2. {subgroup_path}")
    print(f"3. {predictions_path}")
    print(f"4. {OUTPUT_DIR / 'split_metadata.txt'}")
    print(f"5. Fitted models in {MODEL_DIR}/")
    print("6. Feature importance CSV files for contextual models")

    print("\nImportant: results describe performance on synthetic data only.")


if __name__ == "__main__":
    main()
