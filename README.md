# Bengaluru ride-demand command center

This project demonstrates real-time, zone-level ride-demand prediction for
Bengaluru using the supplied synthetic ride, weather, event, and ML outputs.

## Dashboard

The Next.js dashboard includes:

- OpenStreetMap hotspot visualization for the 52 project zones
- Browser location and clearly labeled simulated driver markers
- Simple mobile driver plan with hotspot recommendations and alerts
- Prediction register for the next 15 minutes
- Dedicated Kafka pipeline page with live service counters and logs

## Streaming architecture

```text
rides_contextual_synthetic.csv
  -> Kafka ride_requests topic
  -> five-minute zone aggregation
  -> next-15-minute persistence baseline
  -> Kafka predictions topic
  -> streaming API
  -> Next.js dashboard
```

The live Docker service uses the project-defined persistence baseline
(`3 × rolling 15-minute mean`) so the demo remains lightweight. The trained
contextual model files remain available under `ml_results/models/` for the
offline training and evaluation workflow.

## Run

```powershell
docker compose up --build -d
```

Open the dashboard at <http://localhost:3000>. Follow the actual pipeline with:

```powershell
docker compose logs -f kafka streaming producer
```

The supplied event file contains synthetic scenarios. It does not contain a
Diwali event, so the dashboard does not present Diwali as a project fact.
