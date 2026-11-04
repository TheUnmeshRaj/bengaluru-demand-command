
"""
GROUP PERMUTATION IMPORTANCE
Bengaluru Ride-Hailing Demand Prediction

Purpose:
Measure the predictive contribution of:
1. Weather features
2. Event features
3. All contextual features together

Uses:
- Existing trained XGBoost contextual model
- Same chronological validation split as train_models.py
- Validation data only; test data remains untouched

Outputs:
    ml_results/group_permutation_repeats.csv
    ml_results/group_permutation_summary.csv
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import train_model as tm


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_FILE = (
    Path("ml_results")
    / "models"
    / "XGBoost_contextual.joblib"
)

OUTPUT_DIR = Path("ml_results")

N_REPEATS = 10
RANDOM_SEED = 42


# Feature groups: shuffle all columns in each group together.

FEATURE_GROUPS = {
    "Weather": [
        "Weather_Condition",
        "Rain_Intensity"
    ],

    "Events": [
        "Event_Active",
        "Event_Impact",
        "Event_Intensity",
        "Event_Type",
        "Event_Phase"
    ]
}

FEATURE_GROUPS["All_Context"] = (
    FEATURE_GROUPS["Weather"]
    + FEATURE_GROUPS["Events"]
)


# ============================================================
# VALIDATION TIMESTAMP BLOCKS
# ============================================================

def create_timestamp_mapping(
    validation,
    rng
):
    """
    Shuffle complete timestamp blocks rather than individual rows.

    Each block contains all 52 zones at one prediction timestamp.

    Blocks are shuffled only within the same:
        - Hour of day
        - Weekday/weekend category

    This preserves the spatial arrangement of contextual
    observations and reduces distortion of daily demand patterns.
    """

    meta = (
        validation
        .groupby("Timestamp", sort=True)
        .agg(
            Hour=("Hour", "first"),
            Is_Weekend=("Is_Weekend", "first")
        )
        .reset_index()
    )

    n_times = len(meta)

    mapping = np.arange(n_times)

    strata = meta.groupby(
        ["Hour", "Is_Weekend"],
        sort=False
    ).indices

    for positions in strata.values():

        positions = np.asarray(
            positions,
            dtype=int
        )

        if len(positions) > 1:

            mapping[positions] = rng.permutation(
                positions
            )

    return mapping, n_times


# ============================================================
# GROUP PERMUTATION
# ============================================================

def permute_feature_group(
    X,
    group_columns,
    mapping,
    n_zones,
    n_times
):
    """
    Move the entire context snapshot from one timestamp
    to another timestamp in the same time-of-day stratum.

    All features in a group use the same permutation,
    preserving relationships within the group.
    """

    X_permuted = X.copy()

    values = X[group_columns].to_numpy()

    expected_rows = n_times * n_zones

    if len(values) != expected_rows:

        raise ValueError(
            "Validation data does not contain a complete "
            "zone block for every timestamp."
        )

    # Shape:
    # timestamps x zones x features

    blocks = values.reshape(
        n_times,
        n_zones,
        len(group_columns)
    )

    shuffled_blocks = blocks[mapping]

    shuffled_values = shuffled_blocks.reshape(
        -1,
        len(group_columns)
    )

    # Assign each column separately to preserve its data type.

    for index, column in enumerate(group_columns):

        column_values = shuffled_values[:, index]

        if pd.api.types.is_numeric_dtype(
            X[column].dtype
        ):

            X_permuted[column] = (
                pd.to_numeric(
                    pd.Series(
                        column_values,
                        index=X.index
                    ),
                    errors="raise"
                ).astype(X[column].dtype)
            )

        else:

            X_permuted[column] = pd.Series(
                column_values,
                index=X.index,
                dtype=X[column].dtype
            )

    return X_permuted


# ============================================================
# MAIN EXPERIMENT
# ============================================================

def main():

    print("\n" + "=" * 65)
    print("GROUP PERMUTATION IMPORTANCE")
    print("=" * 65)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not MODEL_FILE.exists():

        raise FileNotFoundError(
            f"Trained model not found: {MODEL_FILE.resolve()}"
        )

    # --------------------------------------------------------
    # STEP 1: Load the same dataset and chronological split
    # --------------------------------------------------------

    df = tm.load_dataset()

    _, validation, _, split_metadata = (
        tm.chronological_split(df)
    )

    validation = (
        validation
        .sort_values(
            ["Timestamp", "Zone_ID"]
        )
        .reset_index(drop=True)
    )

    print(
        f"\nValidation rows: {len(validation):,}"
    )

    # --------------------------------------------------------
    # STEP 2: Verify complete timestamp blocks
    # --------------------------------------------------------

    zones = sorted(
        validation["Zone_ID"].unique()
    )

    n_zones = len(zones)

    zone_counts = (
        validation
        .groupby("Timestamp")["Zone_ID"]
        .nunique()
    )

    if not (zone_counts == n_zones).all():

        raise ValueError(
            "Some prediction timestamps do not contain "
            "all geographical zones."
        )

    if validation.duplicated(
        ["Timestamp", "Zone_ID"]
    ).any():

        raise ValueError(
            "Duplicate timestamp-zone combinations found."
        )

    print(
        f"Zones per timestamp: {n_zones}"
    )

    # --------------------------------------------------------
    # STEP 3: Load trained contextual XGBoost model
    # --------------------------------------------------------

    print("\nLoading trained contextual XGBoost model...")

    model = joblib.load(MODEL_FILE)

    feature_sets = tm.make_feature_sets()

    numeric_features, categorical_features = (
        feature_sets["contextual"]
    )

    feature_columns = (
        numeric_features
        + categorical_features
    )

    X_validation = validation[
        feature_columns
    ].copy()

    y_validation = validation[
        tm.TARGET_COLUMN
    ].to_numpy(dtype=float)

    base_predictions = np.maximum(
        model.predict(X_validation),
        0.0
    )

    baseline_metrics = tm.calculate_metrics(
        y_validation,
        base_predictions
    )

    print("\nOriginal validation performance:")

    for metric, value in baseline_metrics.items():

        print(
            f"{metric}: {value:.6f}"
        )

    # --------------------------------------------------------
    # STEP 4: Prepare timestamp metadata
    # --------------------------------------------------------

    meta = (
        validation
        .groupby("Timestamp", sort=True)
        .agg(
            Hour=("Hour", "first"),
            Is_Weekend=("Is_Weekend", "first")
        )
        .reset_index()
    )

    n_times = len(meta)

    if len(validation) != n_times * n_zones:

        raise ValueError(
            "Unexpected validation block dimensions."
        )

    # --------------------------------------------------------
    # STEP 5: Run permutation experiments
    # --------------------------------------------------------

    all_results = []

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    for group_name, group_columns in (
        FEATURE_GROUPS.items()
    ):

        print("\n" + "-" * 65)

        print(
            f"Permuting feature group: {group_name}"
        )

        for column in group_columns:

            if column not in X_validation.columns:

                raise ValueError(
                    f"Feature {column} is not present in the "
                    "contextual XGBoost model inputs."
                )

        for repeat in range(1, N_REPEATS + 1):

            mapping, _ = create_timestamp_mapping(
                validation,
                rng
            )

            X_permuted = permute_feature_group(
                X_validation,
                group_columns,
                mapping,
                n_zones,
                n_times
            )

            permuted_predictions = np.maximum(
                model.predict(X_permuted),
                0.0
            )

            metrics = tm.calculate_metrics(
                y_validation,
                permuted_predictions
            )

            result = {

                "Feature_Group": group_name,

                "Repeat": repeat,

                "MAE": metrics["MAE"],

                "RMSE": metrics["RMSE"],

                "WAPE_percent": (
                    metrics["WAPE_percent"]
                ),

                "Delta_MAE": (
                    metrics["MAE"]
                    - baseline_metrics["MAE"]
                ),

                "Delta_RMSE": (
                    metrics["RMSE"]
                    - baseline_metrics["RMSE"]
                ),

                "Delta_WAPE": (
                    metrics["WAPE_percent"]
                    - baseline_metrics["WAPE_percent"]
                )
            }

            all_results.append(result)

            print(
                f"Repeat {repeat:02d}/{N_REPEATS} | "
                f"MAE: {metrics['MAE']:.5f} | "
                f"Delta MAE: {result['Delta_MAE']:+.5f}"
            )

    # --------------------------------------------------------
    # STEP 6: Save individual experiment results
    # --------------------------------------------------------

    results_df = pd.DataFrame(
        all_results
    )

    repeat_file = (
        OUTPUT_DIR
        / "group_permutation_repeats.csv"
    )

    results_df.to_csv(
        repeat_file,
        index=False
    )

    # --------------------------------------------------------
    # STEP 7: Calculate average importance
    # --------------------------------------------------------

    summary = (
        results_df
        .groupby("Feature_Group")
        .agg(
            Mean_Delta_MAE=("Delta_MAE", "mean"),
            Std_Delta_MAE=("Delta_MAE", "std"),

            Mean_Delta_RMSE=("Delta_RMSE", "mean"),
            Std_Delta_RMSE=("Delta_RMSE", "std"),

            Mean_Delta_WAPE=("Delta_WAPE", "mean"),
            Std_Delta_WAPE=("Delta_WAPE", "std")
        )
        .reset_index()
    )

    # Positive values indicate that shuffling the group
    # increased prediction error.

    summary["Importance_Ratio"] = (
        summary["Mean_Delta_MAE"]
        / baseline_metrics["MAE"]
        * 100.0
    )

    summary = summary.sort_values(
        "Mean_Delta_MAE",
        ascending=False
    )

    summary_file = (
        OUTPUT_DIR
        / "group_permutation_summary.csv"
    )

    summary.to_csv(
        summary_file,
        index=False
    )

    # --------------------------------------------------------
    # STEP 8: Display final results
    # --------------------------------------------------------

    print("\n" + "=" * 65)

    print("BASELINE VALIDATION METRICS")

    print("=" * 65)

    print(
        pd.Series(
            baseline_metrics
        ).to_string()
    )

    print("\n" + "=" * 65)

    print("GROUP PERMUTATION IMPORTANCE")

    print("=" * 65)

    print(
        summary.to_string(index=False)
    )

    print("\nSaved files:")

    print(repeat_file)

    print(summary_file)

    print(
        "\nExperiment completed. "
        "The held-out test dataset was not used."
    )


if __name__ == "__main__":
    main()
