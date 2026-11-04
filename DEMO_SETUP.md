# Ride-Heli: complete demo setup and implementation record

This file records the work completed for the Bengaluru real-time ride-demand
prediction demo.

## Project purpose

The project demonstrates zone-level ride-demand prediction for Bengaluru using
the supplied synthetic ride, weather, event, and machine-learning data.

The documented streaming flow is:

```text
rides_contextual_synthetic.csv
  -> Kafka ride_requests
  -> five-minute zone aggregation
  -> next-15-minute contextual prediction
  -> Kafka predictions
  -> streaming API
  -> Next.js driver dashboard
```

The five-minute value is the aggregation window. The forecast target is the
next 15 minutes, represented by three five-minute intervals.

## What has been built

### Dashboard

The Next.js dashboard provides:

- Ride-Heli branding
- Neo-brutalist visual styling with strong borders, shadows, color blocks, and
  large touch-friendly controls
- Responsive desktop and mobile layouts
- Demand command center overview
- Zone-level prediction register
- Hotspot ranking
- Driver-oriented planning view
- Alerts based on supplied event and weather data
- Evening peak and weekend guidance based on the project EDA
- Kannada text alongside simple English labels
- Live Kafka connection/offline status
- Dedicated Kafka operations page at `/kafka`

The interface does not use a canvas or mock map for the primary visualization.

### OpenStreetMap visualization

The map uses Leaflet with OpenStreetMap tiles:

```text
https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
```

It includes:

- Zone hotspot circles
- Zone selection and popups
- Demand intensity visualization
- Browser geolocation marker labelled as the driver’s location
- Clearly labelled simulated driver markers
- Driver actions such as selecting a hotspot and showing recommendations
- Geocoded zone coordinates from the project data

### Driver workflow

The driver plan is designed to be simple and action-oriented:

- Shows the strongest predicted zones for the next 15 minutes
- Provides a short list of places to try
- Allows a driver to select a zone and view it on the map
- Shows the evening peak guidance of 17:00–21:00, highest around 19:00
- Shows weekend demand guidance
- Shows synthetic event signals when supplied event data indicates them
- Shows supplied weather and rain signals
- Recommends checking the app after each five-minute update

The supplied event file does not contain Diwali. Therefore the application does
not claim a Diwali alert as a project result.

### Kafka operations page

The dedicated `/kafka` page shows:

- Broker status
- Input topic: `ride_requests`
- Output topic: `predictions`
- Five-minute aggregation window
- Fifteen-minute prediction horizon
- Events consumed
- Predictions published
- Consumer errors
- Pipeline stages
- Live producer and consumer log messages
- Kafka broker address and pipeline activity

The page displays live API state rather than pretending that static values are
live Kafka activity.

## Backend services

### Kafka

- Image: `apache/kafka:3.9.0`
- Host broker address: `localhost:9092`
- Internal Compose broker address: `kafka:9092`
- Single-node KRaft configuration
- Automatic topic creation enabled
- Three Kafka partitions configured
- Healthcheck verifies that the broker responds

The relevant topics are:

- `ride_requests`: incoming synthetic ride events
- `predictions`: zone-level next-15-minute predictions
- `pipeline_logs`: producer and pipeline observability messages

### Replay producer

`kafka_ride_producer.py`:

- Reads `rides_contextual_synthetic.csv`
- Converts rows into JSON ride events
- Publishes to `ride_requests`
- Uses idempotence and `acks=all`
- Reports delivered and failed messages
- Publishes producer progress to `pipeline_logs`
- Is bounded to 100,000 records in the Compose demo

The producer waits for the streaming service healthcheck, preventing it from
finishing before the consumer is ready.

### Streaming service

`streaming_service.py`:

- Consumes `ride_requests`
- Uses five-minute zone windows
- Maintains recent demand history for feature construction
- Builds time, zone, weather, and event features
- Loads `ml_results/models/RandomForest_contextual.joblib`
- Predicts `Target_Next_15min`
- Publishes predictions to `predictions`
- Consumes `pipeline_logs` for dashboard-visible logs
- Tracks consumed events, predictions, errors, zones, and recent logs
- Exposes `/health`
- Exposes `/state`
- Commits Kafka offsets after a completed window
- Uses `earliest` offsets so a fresh demo does not miss already-published replay
  events

The service listens on `0.0.0.0` inside its container so the host dashboard can
reach port 8000.

### Model runtime

The streaming image installs:

- `confluent-kafka`
- `pandas`
- `joblib`
- `scikit-learn`
- `fastapi`
- `uvicorn`

The scikit-learn runtime is pinned to `1.6.1` to match the serialized model
artifact. XGBoost and NVIDIA/NCCL dependencies are not needed by the live
Random Forest service.

## Docker Compose services

| Service | Purpose | Host access |
|---|---|---|
| `kafka` | Kafka broker | `localhost:9092` |
| `streaming` | Consumer, aggregation, prediction, API | `localhost:8000` |
| `producer` | Synthetic ride replay | Container logs |
| `web` | Next.js dashboard | `localhost:3000` |

The web image includes the Next.js standalone production output. The streaming
service mounts the model and dashboard data read-only. The producer mounts only
the replay script and ride dataset it needs.

## Run the demo

Run from the repository root.

### First build and start

```powershell
docker compose up --build -d
```

This builds the images, starts Kafka, waits for streaming health, starts the
producer replay, and starts the web dashboard.

### Normal start without rebuilding

```powershell
docker compose up -d
```

`docker compose down` removes the running containers but does not require a
rebuild next time unless source files or dependency manifests changed.

### Open the application

- Dashboard: http://localhost:3000
- Kafka operations: http://localhost:3000/kafka
- Streaming health: http://localhost:8000/health
- Streaming state: http://localhost:8000/state

### Inspect service status

```powershell
docker compose ps
```

### Follow all service logs

```powershell
docker compose logs -f
```

### Follow only the pipeline logs

```powershell
docker compose logs -f kafka streaming producer
```

### Stop the demo

```powershell
docker compose down
```

## Troubleshooting

### Kafka image not found

The unavailable `bitnami/kafka:3.9` image was replaced with:

```text
apache/kafka:3.9.0
```

### Dashboard says Offline

Check the API first:

```powershell
Invoke-WebRequest http://localhost:8000/health
```

Then inspect the streaming service:

```powershell
docker compose logs --tail=120 streaming
```

The streaming API must listen on `0.0.0.0` inside Docker. This is already
configured.

### Counts remain zero

Check that the producer is running or has completed successfully:

```powershell
docker compose logs producer
```

A healthy replay reports delivered messages and zero failures. The consumer is
configured with `earliest` offsets and the producer waits for streaming health,
so a fresh Compose startup can consume the replay reliably.

### Rebuild one service

For a web-only change:

```powershell
docker compose up --build -d web
```

For a streaming or model change:

```powershell
docker compose up --build -d streaming
```

For producer changes:

```powershell
docker compose up --build -d producer
```

## Validation completed

The following checks were run successfully:

```powershell
python -m py_compile streaming_service.py kafka_ride_producer.py
npx tsc --noEmit
docker compose config --quiet
```

The running service was also verified through:

- `docker compose ps`
- `http://localhost:8000/health`
- `http://localhost:8000/state`
- Kafka topic listing
- Producer delivery logs
- Streaming consumer state

The verified live state reached `connected`, consumed ride events, published
predictions, and reported zero consumer errors.

## Data and project integrity notes

- The project uses the supplied synthetic Bengaluru data.
- The project terminology remains zone, hotspot, five-minute aggregation, and
  next-15-minute prediction.
- No benchmark, algorithm, event, or result is invented in the dashboard.
- Weather and event alerts are labelled as supplied synthetic context.
- Diwali is not present in the supplied event file.
- OpenStreetMap attribution is shown in the dashboard footer.
- Git LFS is not used.
- Large source datasets are not copied into the web image.
- Model files remain under `ml_results/models/` and are mounted read-only for
  streaming inference.
