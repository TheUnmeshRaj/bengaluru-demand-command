BENGALURU RIDE-DEMAND ML INFERENCE STAGE
========================================

WHAT THIS PACKAGE DOES
----------------------
These are clean, isolated scripts for the next experiment. They do NOT delete,
format, or modify the already-tested topics `ride_requests` and
`zone_demand_5min`.

1. kafka_ride_producer_ml.py
   Replays rides_contextual_synthetic.csv into ride_requests_ml.
   It refuses to publish if the topic already contains messages.

2. kafka_demand_aggregator_ml.py
   Reads ride_requests_ml and writes five-minute counts for all 52 zones to
   zone_demand_5min_ml. This remains a finite replay/batch aggregation test.
   The output topic has one partition to preserve global window order.

3. kafka_ml_inference.py
   Reads the ordered 5-minute windows, maintains 13 observations per zone,
   loads XGBoost_historical.joblib, and writes 15-minute predictions to
   demand_predictions_ml.

4. verify_demand_predictions.py
   Reads the prediction topic from the beginning and validates complete
   52-zone windows, chronological origins, uniqueness, and forecast horizon.

REQUIREMENTS
------------
Run from the project root, where these already exist:
  rides_contextual_synthetic.csv
  ml_results/models/XGBoost_historical.joblib

Python packages:
  python -m pip install confluent-kafka pandas numpy joblib scikit-learn xgboost

KAFKA TOPICS
------------
Keep the Kafka broker running in its existing terminal.
Open a NEW PowerShell terminal and run:

  cd C:\kafka\kafka_2.13-4.3.1
  .\bin\windows\kafka-topics.bat --bootstrap-server 127.0.0.1:9092 --create --if-not-exists --topic ride_requests_ml --partitions 6 --replication-factor 1
  .\bin\windows\kafka-topics.bat --bootstrap-server 127.0.0.1:9092 --create --if-not-exists --topic zone_demand_5min_ml --partitions 1 --replication-factor 1
  .\bin\windows\kafka-topics.bat --bootstrap-server 127.0.0.1:9092 --create --if-not-exists --topic demand_predictions_ml --partitions 1 --replication-factor 1

COPY FILES
-----------
Copy the four .py files into:
  C:\Users\lalwa\Desktop\SPA EL

RUN ORDER
---------
Terminal 1: Keep the Kafka broker running.

Terminal 2: From the project folder, publish the complete CSV once:
  cd "C:\Users\lalwa\Desktop\SPA EL"
  python kafka_ride_producer_ml.py --limit 0 --speedup 0

Wait for the producer summary to show that all messages were delivered.
Do NOT run the producer a second time on ride_requests_ml. The script refuses
non-empty topics to protect against duplicate ride IDs.

Terminal 3: After the producer finishes, run the aggregator:
  cd "C:\Users\lalwa\Desktop\SPA EL"
  python kafka_demand_aggregator_ml.py --max-messages 0 --idle-timeout 30

Wait until it reports aggregation completed successfully.

Terminal 4: Run model inference:
  cd "C:\Users\lalwa\Desktop\SPA EL"
  python kafka_ml_inference.py --idle-timeout 30

EXPECTED LOGIC
--------------
- Every completed window contains 52 zone records, including zero-demand zones.
- The model's prediction origin is window_end, matching build_ml_dataset.py.
- 13 interval observations are kept per zone: current interval plus 12 previous
  intervals. This is necessary because Demand_Lag_60min uses shift(12).
- The model uses the 17 historical features in the exact order inspected from
  XGBoost_historical.joblib. DayOfWeek_Sin/Cos are calculated as in train_model.py.
- The output has one record per zone per eligible prediction origin.
- The model predicts the aggregate number of rides over [T, T+15 minutes).

IMPORTANT LIMITATIONS
---------------------
- The aggregation script is still a finite replay/batch event-time aggregation
  stage, not a production-grade continuous streaming processor with watermarks
  and late-event handling.
- This run uses synthetic data and validates pipeline mechanics; it does not
  establish real-world Bengaluru demand accuracy.
- Inference and aggregation use fresh, dedicated topics. Do not delete or
  reformat Kafka storage to run this experiment.
- These scripts have been syntax-checked, but cannot be integration-tested here
  against your Windows Kafka broker, local CSV, or local model artifact.
