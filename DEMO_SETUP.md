# Bengaluru demand demo

## What is implemented

The project now has a Docker Compose demo with these services:

1. **Kafka** on `localhost:9092`
2. **Streaming service** on `localhost:8000`
   - Consumes the `ride_requests` topic
   - Closes five-minute zone windows
   - Loads the trained Random Forest contextual model
   - Predicts `Target_Next_15min`
   - Publishes predictions to the `predictions` topic
   - Exposes live state at `/state`
3. **Replay producer**
   - Reads `rides_contextual_synthetic.csv`
   - Publishes ride events to Kafka
   - The Compose demo is bounded to 100,000 events
4. **Next.js dashboard** on `localhost:3000`
   - Uses live streaming state when the API is connected
   - Shows a clear Kafka live/offline status when the API is unavailable
   - Includes hotspot map, driver view, mock drivers, browser location, predictions, and Kafka logs

The dashboard uses a **five-minute aggregation window** and predicts demand for
the **next 15 minutes**. Five minutes is not the prediction horizon.

## Start the demo

Run this from the project root:

```powershell
docker compose up --build
```

This command stays attached because the web, streaming, and Kafka services keep
running. The producer exits after its configured replay completes. Use
`Ctrl+C` to stop the attached Compose session.

Open:

- Dashboard: http://localhost:3000
- Streaming health: http://localhost:8000/health
- Streaming state: http://localhost:8000/state

## Run in the background

For a prompt that returns immediately:

```powershell
docker compose up --build -d
```

Follow service logs:

```powershell
docker compose logs -f
```

Follow only the Kafka pipeline:

```powershell
docker compose logs -f kafka streaming producer
```

Check running containers:

```powershell
docker compose ps
```

Stop the demo:

```powershell
docker compose down
```

## Important note

The live Docker demo loads `ml_results/models/RandomForest_contextual.joblib`.
The model runtime is pinned to scikit-learn 1.6.1, matching the model artifact.
remain in `ml_results/models/` for the offline training and evaluation path.
The large source datasets are mounted only where needed and are excluded from
the web image. No Git LFS configuration is used.
