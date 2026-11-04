from __future__ import annotations

import argparse
import json
import math
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from confluent_kafka import Consumer
from confluent_kafka.admin import AdminClient

# Import the exact dataset loading and chronological split used for training.
from train_model import load_dataset, chronological_split

KAFKA_SERVER = "127.0.0.1:9092"
PREDICTION_TOPIC = "demand_predictions_ml"
OUTPUT_DIR = Path("ml_results")
OFFLINE_TEST_PREDICTIONS = OUTPUT_DIR / "test_predictions.csv"


def local_naive_timestamp(value: Any) -> pd.Timestamp:
    """Normalize naive local timestamps and aware timestamps to IST wall time."""
    ts = pd.Timestamp(value)
    if pd.isna(ts):
        raise ValueError("Missing prediction timestamp")
    if ts.tzinfo is not None:
        ts = ts.tz_convert("Asia/Kolkata").tz_localize(None)
    return ts


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    errors = y_pred - y_true
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    denominator = float(np.sum(np.abs(y_true)))
    wape = float(np.sum(np.abs(errors)) / denominator * 100.0) if denominator else float("nan")
    return {
        "MAE": mae,
        "RMSE": rmse,
        "WAPE_percent": wape,
        "Mean_Error_Predicted_Minus_Actual": float(np.mean(errors)),
    }


def inspect_topic(topic: str) -> int:
    admin = AdminClient({"bootstrap.servers": KAFKA_SERVER})
    metadata = admin.list_topics(topic=topic, timeout=15)
    info = metadata.topics.get(topic)
    if info is None or info.error is not None:
        raise RuntimeError(f"Cannot access Kafka topic '{topic}'.")
    partition_count = len(info.partitions)
    if partition_count != 1:
        raise RuntimeError(
            f"Expected {topic} to have one partition for ordered prediction records; "
            f"found {partition_count}."
        )
    return partition_count


def load_expected_test_rows() -> pd.DataFrame:
    print("Loading the original ML dataset using train_model.py ...")
    df = load_dataset()
    _train, _validation, test, split_metadata = chronological_split(df)

    expected = test[["Timestamp", "Zone_ID", "Target_Next_15min"]].copy()
    expected["Timestamp"] = expected["Timestamp"].map(local_naive_timestamp)
    expected["Zone_ID"] = expected["Zone_ID"].astype(str)
    expected = expected.rename(columns={"Target_Next_15min": "Actual_Next_15min"})

    if expected.duplicated(["Timestamp", "Zone_ID"]).any():
        raise RuntimeError("Training test split contains duplicate timestamp-zone keys.")

    print("\nOriginal chronological test split:")
    print(json.dumps(split_metadata, indent=2))
    print(f"Expected test rows for evaluation: {len(expected):,}")
    return expected


def read_kafka_test_predictions(
    expected: pd.DataFrame,
    idle_timeout: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    expected_lookup = {
        (row.Timestamp, str(row.Zone_ID)): float(row.Actual_Next_15min)
        for row in expected.itertuples(index=False)
    }

    group_id = f"kafka-prediction-evaluation-{uuid.uuid4().hex[:10]}"
    consumer = Consumer({
        "bootstrap.servers": KAFKA_SERVER,
        "client.id": "bengaluru-kafka-prediction-evaluator",
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "enable.partition.eof": False,
        "session.timeout.ms": 30_000,
        "max.poll.interval.ms": 600_000,
    })

    matched: dict[tuple[pd.Timestamp, str], dict[str, Any]] = {}
    total_records = 0
    horizon_counts: dict[int, int] = {}
    run_ids: set[str] = set()
    invalid_records = 0
    last_message_time = time.monotonic()

    print(f"\nReading {PREDICTION_TOPIC} from the beginning...")
    consumer.subscribe([PREDICTION_TOPIC])

    try:
        while True:
            message = consumer.poll(1.0)
            if message is None:
                if time.monotonic() - last_message_time >= idle_timeout:
                    break
                continue
            if message.error():
                raise RuntimeError(f"Kafka read error: {message.error()}")

            last_message_time = time.monotonic()
            total_records += 1

            try:
                record = json.loads(message.value().decode("utf-8"))
                origin = local_naive_timestamp(record["prediction_origin"])
                zone_id = str(record["pickup_zone_id"])
                value = float(record["predicted_demand_15min"])
                rounded = int(record["predicted_demand_rounded"])
                horizon = int(record["forecast_horizon_minutes"])
                run_id = str(record.get("prediction_run_id", ""))
                if not math.isfinite(value) or value < 0:
                    raise ValueError("Prediction must be finite and non-negative")
                if horizon != 15:
                    raise ValueError(f"Unexpected forecast horizon: {horizon}")

                horizon_counts[horizon] = horizon_counts.get(horizon, 0) + 1
                run_ids.add(run_id)
                key = (origin, zone_id)
                if key in expected_lookup:
                    if key in matched:
                        raise RuntimeError(
                            f"Duplicate Kafka prediction for {origin} zone {zone_id}."
                        )
                    matched[key] = {
                        "Timestamp": origin,
                        "Zone_ID": zone_id,
                        "Actual_Next_15min": expected_lookup[key],
                        "Kafka_XGBoost_prediction": value,
                        "Kafka_XGBoost_rounded": rounded,
                    }
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                invalid_records += 1
                raise RuntimeError(
                    f"Invalid prediction record at partition {message.partition()}, "
                    f"offset {message.offset()}: {exc}"
                ) from exc

            if total_records % 100_000 == 0:
                print(f"Read {total_records:,} prediction records...")
    finally:
        consumer.close()

    info = {
        "total_kafka_records": total_records,
        "matched_test_records": len(matched),
        "expected_test_records": len(expected_lookup),
        "invalid_records": invalid_records,
        "forecast_horizon_counts": horizon_counts,
        "prediction_run_ids": sorted(run_ids),
        "evaluation_consumer_group": group_id,
    }

    if len(run_ids) > 1:
        raise RuntimeError(f"More than one prediction run ID found: {sorted(run_ids)}")
    if len(matched) != len(expected_lookup):
        missing = len(expected_lookup) - len(matched)
        raise RuntimeError(
            f"Kafka predictions do not fully cover the original test split: "
            f"matched {len(matched):,}/{len(expected_lookup):,}; missing {missing:,}."
        )

    aligned = pd.DataFrame(matched.values())
    aligned = aligned.sort_values(["Timestamp", "Zone_ID"]).reset_index(drop=True)
    return aligned, info


def add_offline_comparison(aligned: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    comparison_rows: list[dict[str, Any]] = []
    if not OFFLINE_TEST_PREDICTIONS.exists():
        print(
            f"\nOffline comparison file not found: {OFFLINE_TEST_PREDICTIONS}. "
            "Kafka accuracy will still be evaluated against actual test targets."
        )
        return aligned, comparison_rows

    offline = pd.read_csv(OFFLINE_TEST_PREDICTIONS, low_memory=False, parse_dates=["Timestamp"])
    required = {"Timestamp", "Zone_ID", "Actual_Next_15min", "XGBoost_historical_prediction"}
    missing = required - set(offline.columns)
    if missing:
        print(f"\nOffline prediction file lacks columns {sorted(missing)}; skipping offline comparison.")
        return aligned, comparison_rows

    optional_predictions = [
        column for column in ["Persistence_baseline_prediction"]
        if column in offline.columns
    ]
    offline = offline[
        ["Timestamp", "Zone_ID", "Actual_Next_15min", "XGBoost_historical_prediction"]
        + optional_predictions
    ].copy()
    offline["Timestamp"] = offline["Timestamp"].map(local_naive_timestamp)
    offline["Zone_ID"] = offline["Zone_ID"].astype(str)
    offline = offline.rename(columns={
        "Actual_Next_15min": "Offline_File_Actual_Next_15min",
        "XGBoost_historical_prediction": "Offline_XGBoost_prediction",
    })
    if "Persistence_baseline_prediction" in offline.columns:
        offline = offline.rename(columns={
            "Persistence_baseline_prediction": "Offline_Persistence_baseline_prediction"
        })

    aligned = aligned.merge(offline, on=["Timestamp", "Zone_ID"], how="left", validate="one_to_one")
    if aligned["Offline_XGBoost_prediction"].notna().all():
        actual_diff = np.max(np.abs(
            aligned["Actual_Next_15min"].to_numpy(dtype=float)
            - aligned["Offline_File_Actual_Next_15min"].to_numpy(dtype=float)
        ))
        kafka_values = aligned["Kafka_XGBoost_prediction"].to_numpy(dtype=float)
        offline_values = aligned["Offline_XGBoost_prediction"].to_numpy(dtype=float)
        difference = np.abs(kafka_values - offline_values)
        comparison_rows.append({
            "Comparison": "Kafka XGBoost vs saved offline XGBoost",
            "Test_Rows": int(len(aligned)),
            "Max_Absolute_Prediction_Difference": float(np.max(difference)),
            "Mean_Absolute_Prediction_Difference": float(np.mean(difference)),
            "Rows_Difference_Above_1e-5": int(np.sum(difference > 1e-5)),
            "Max_Actual_Target_Difference": float(actual_diff),
        })
    else:
        print("\nSome offline test prediction rows did not match; exact comparison skipped.")
    return aligned, comparison_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate Kafka XGBoost predictions on the original chronological test split."
    )
    parser.add_argument("--idle-timeout", type=int, default=30,
                        help="Seconds without Kafka records before the read is considered complete.")
    args = parser.parse_args()
    if args.idle_timeout <= 0:
        parser.error("--idle-timeout must be positive.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    inspect_topic(PREDICTION_TOPIC)
    expected = load_expected_test_rows()
    aligned, kafka_info = read_kafka_test_predictions(expected, args.idle_timeout)
    aligned, offline_comparison = add_offline_comparison(aligned)

    metric_rows = [
        {"Model": "Kafka_XGBoost_raw", **metrics(
            aligned["Actual_Next_15min"].to_numpy(),
            aligned["Kafka_XGBoost_prediction"].to_numpy(),
        )},
        {"Model": "Kafka_XGBoost_rounded", **metrics(
            aligned["Actual_Next_15min"].to_numpy(),
            aligned["Kafka_XGBoost_rounded"].to_numpy(),
        )},
    ]

    if "Offline_XGBoost_prediction" in aligned.columns and aligned["Offline_XGBoost_prediction"].notna().all():
        metric_rows.append({"Model": "Offline_XGBoost_saved_test", **metrics(
            aligned["Actual_Next_15min"].to_numpy(),
            aligned["Offline_XGBoost_prediction"].to_numpy(),
        )})
    if (
        "Offline_Persistence_baseline_prediction" in aligned.columns
        and aligned["Offline_Persistence_baseline_prediction"].notna().all()
    ):
        metric_rows.append({"Model": "Persistence_baseline_saved_test", **metrics(
            aligned["Actual_Next_15min"].to_numpy(),
            aligned["Offline_Persistence_baseline_prediction"].to_numpy(),
        )})

    metrics_df = pd.DataFrame(metric_rows)
    output_predictions = OUTPUT_DIR / "kafka_test_predictions_aligned.csv"
    output_metrics = OUTPUT_DIR / "kafka_test_evaluation_metrics.csv"
    output_metadata = OUTPUT_DIR / "kafka_test_evaluation_metadata.json"
    output_comparison = OUTPUT_DIR / "kafka_vs_offline_comparison.csv"

    aligned.to_csv(output_predictions, index=False)
    metrics_df.to_csv(output_metrics, index=False)
    pd.DataFrame(offline_comparison).to_csv(output_comparison, index=False)
    metadata = {
        **kafka_info,
        "evaluation_basis": "Exact chronological test split from train_model.py",
        "test_rows": int(len(aligned)),
        "test_start": str(aligned["Timestamp"].min()),
        "test_end": str(aligned["Timestamp"].max()),
        "prediction_horizon_minutes": 15,
        "metrics_use": "Unrounded Kafka prediction field predicted_demand_15min",
        "files": {
            "aligned_predictions": str(output_predictions),
            "metrics": str(output_metrics),
            "offline_comparison": str(output_comparison),
        },
    }
    output_metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("\n========== KAFKA TEST-SET EVALUATION ==========")
    print(f"Kafka prediction records read : {kafka_info['total_kafka_records']:,}")
    print(f"Original test rows             : {len(expected):,}")
    print(f"Matched Kafka test predictions : {len(aligned):,}")
    print(f"Prediction run IDs             : {kafka_info['prediction_run_ids']}")
    print(f"Prediction horizon counts      : {kafka_info['forecast_horizon_counts']}")
    print("\nMetrics (test split only):")
    print(metrics_df.to_string(index=False, float_format=lambda value: f"{value:.6f}"))

    if offline_comparison:
        print("\nKafka vs saved offline model:")
        print(pd.DataFrame(offline_comparison).to_string(index=False, float_format=lambda value: f"{value:.10f}"))
        diff = offline_comparison[0]["Max_Absolute_Prediction_Difference"]
        if diff <= 1e-5:
            print("\nSUCCESS: Kafka predictions match saved offline XGBoost predictions within 1e-5.")
        else:
            print("\nWARNING: Kafka and saved offline predictions differ. Investigate feature/timestamp alignment.")
    else:
        print("\nNOTE: No exact offline prediction comparison was available.")

    print("\nSaved evaluation files:")
    print(f"1. {output_predictions}")
    print(f"2. {output_metrics}")
    print(f"3. {output_metadata}")
    print(f"4. {output_comparison}")


if __name__ == "__main__":
    main()
