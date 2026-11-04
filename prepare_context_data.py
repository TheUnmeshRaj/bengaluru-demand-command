"""Prepare separate weather/event tables and an event-enriched ride file.

This script EXTENDS an existing ride dataset. It does not overwrite it.

Inputs:
    synthetic_bengaluru_rides.csv

Outputs:
    weather_data.csv
    bengaluru_events.csv
    rides_contextual_synthetic.csv
    event_impact_by_hour.csv
    context_generation_report.csv

Important:
- Weather is extracted from the existing ride data because the original generator
  already simulates rain and applies a 1.3 demand multiplier during rainy hours.
- Events are explicitly synthetic scenarios. Their demand effects are transparent
  simulation assumptions, not measured Bengaluru behavioural effects.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


# ----------------------------- CONFIGURATION -----------------------------

INPUT_RIDES = Path("synthetic_bengaluru_rides.csv")
OUTPUT_DIR = Path(".")

RANDOM_SEED = 43
NUM_EVENTS = 36

PRE_EVENT_HOURS = 2
POST_EVENT_HOURS = 2


# These are venue zones already present in the user's 52-zone generator.
# No geographic-neighbour effect is assumed because the original dataset
# does not contain zone coordinates or geographical polygons.
# Each event has one venue zone and two additional
# zones included in the simulation influence area.
#
# These are manually defined simulation relationships.
# They are not verified GIS adjacency relationships.

EVENT_VENUES = [
    ("Z01", "Whitefield", ("Z05", "Z06")),
    ("Z02", "Electronic City", ("Z50", "Z04")),
    ("Z03", "Manyata Tech Park", ("Z47", "Z29")),

    ("Z30", "Indiranagar", ("Z32", "Z33")),
    ("Z31", "Koramangala", ("Z12", "Z13")),
    ("Z32", "MG Road", ("Z33", "Z35")),
    ("Z33", "Brigade Road", ("Z32", "Z35")),
    ("Z35", "Church Street", ("Z32", "Z33")),

    ("Z38", "Majestic (KBS)", ("Z41", "Z42")),
    ("Z41", "KSR Bengaluru", ("Z38", "Z42")),

    ("Z46", "KIAL Airport", ("Z48", "Z47")),
]
EVENT_TYPES = [
    "Sports",
    "Concert",
    "Festival",
    "Exhibition"
]

EVENT_NAMES = {
    "Sports": "Simulated Sports Event",
    "Concert": "Simulated Concert",
    "Festival": "Simulated Festival",
    "Exhibition": "Simulated Exhibition",
}


# Illustrative simulation settings.
# Multiplier = 1 + phase_effect * intensity.
# Intensity ranges from 1 to 3.

PHASE_EFFECT = {
    "pre": 0.05,
    "during": 0.10,
    "post": 0.15
}


RIDE_COLUMNS_REQUIRED = {
    "Request_ID",
    "Timestamp",
    "Pickup_Zone_ID",
    "Pickup_Zone",
    "Drop_Zone_ID",
    "Drop_Zone",
    "Vehicle_Type",
    "Ride_Distance_KM",
    "Weather",
    "Rain_Intensity"
}


# ----------------------------- VALIDATION -----------------------------


def validate_input(df: pd.DataFrame) -> pd.DataFrame:

    missing = RIDE_COLUMNS_REQUIRED - set(df.columns)

    if missing:
        raise ValueError(
            f"Input file is missing required columns: {sorted(missing)}"
        )

    df = df.copy()

    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"],
        errors="coerce"
    )

    if df["Timestamp"].isna().any():
        raise ValueError(
            "Some Timestamp values could not be parsed."
        )

    if df["Request_ID"].duplicated().any():
        raise ValueError(
            "Request_ID is not unique in the original ride dataset."
        )

    df["Pickup_Zone_ID"] = df["Pickup_Zone_ID"].astype(str)
    df["Pickup_Zone"] = df["Pickup_Zone"].astype(str)

    return df


# ----------------------------- WEATHER DATASET -----------------------------


def extract_weather_table(rides: pd.DataFrame) -> pd.DataFrame:

    """
    Extract one weather observation per hour from the original
    synthetic ride dataset.

    The original generator assigns a common weather state to all zones
    during each hour.
    """

    tmp = rides.assign(
        Hour_Timestamp=rides["Timestamp"].dt.floor("h")
    )

    consistency = tmp.groupby("Hour_Timestamp").agg(
        weather_nunique=(
            "Weather",
            lambda s: s.nunique(dropna=False)
        ),
        rain_nunique=(
            "Rain_Intensity",
            lambda s: s.nunique(dropna=False)
        )
    )

    bad = consistency[
        (consistency["weather_nunique"] > 1) |
        (consistency["rain_nunique"] > 1)
    ]

    if not bad.empty:

        raise ValueError(
            "Weather values are not consistent within every hour. "
            "Inspect the source generator before extracting weather_data.csv."
        )

    weather = tmp.groupby(
        "Hour_Timestamp",
        as_index=False
    ).agg(
        Weather=("Weather", "first"),
        Rain_Intensity=("Rain_Intensity", "first")
    )

    weather = weather.rename(
        columns={"Hour_Timestamp": "Timestamp"}
    )

    # Fill completely empty hours in the calendar.
    # This is only a fallback.

    full_hours = pd.date_range(
        rides["Timestamp"].min().floor("h"),
        rides["Timestamp"].max().floor("h"),
        freq="h",
        name="Timestamp"
    )

    weather = (
        weather
        .set_index("Timestamp")
        .reindex(full_hours)
        .reset_index()
    )

    missing = weather["Weather"].isna()

    weather.loc[missing, "Weather"] = "Clear"

    weather.loc[missing, "Rain_Intensity"] = 0.0

    weather["Rain_Intensity"] = pd.to_numeric(
        weather["Rain_Intensity"],
        errors="coerce"
    ).fillna(0.0)

    weather["Is_Synthetic"] = True

    weather["Weather_Provenance"] = (
        "Extracted from original synthetic ride generator"
    )

    weather["Demand_Rain_Multiplier_In_Source"] = np.where(
        weather["Weather"].eq("Rain"),
        1.3,
        1.0
    )

    return weather


# ----------------------------- EVENT GENERATION -----------------------------


def generate_event_calendar(
    start: pd.Timestamp,
    end: pd.Timestamp
) -> pd.DataFrame:

    rng = np.random.default_rng(RANDOM_SEED)

    start_day = start.floor("D")
    end_day = end.floor("D")

    total_days = max(
        1,
        (end_day - start_day).days + 1
    )

    rows = []
    attempts = 0

    while (
        len(rows) < NUM_EVENTS
        and attempts < NUM_EVENTS * 200
    ):

        attempts += 1

        event_type = str(
            rng.choice(EVENT_TYPES)
        )

        venue_id, venue_name, secondary_zones = (
            EVENT_VENUES[
                int(rng.integers(0, len(EVENT_VENUES)))
            ]
        )

        impact_zones = tuple(
            dict.fromkeys(
                [venue_id, *secondary_zones]
            )
        )

        day_offset = int(
            rng.integers(0, total_days)
        )

        day = start_day + pd.Timedelta(
            days=day_offset
        )

        if event_type in ("Sports", "Concert"):

            start_hour = int(
                rng.integers(17, 21)
            )

        elif event_type == "Festival":

            start_hour = int(
                rng.integers(10, 16)
            )

        else:

            start_hour = int(
                rng.integers(11, 17)
            )

        start_time = (
            day + pd.Timedelta(hours=start_hour)
        )

        duration = int(
            rng.integers(2, 5)
        )

        end_time = (
            start_time + pd.Timedelta(hours=duration)
        )

        influence_start = (
            start_time -
            pd.Timedelta(hours=PRE_EVENT_HOURS)
        )

        influence_end = (
            end_time +
            pd.Timedelta(hours=POST_EVENT_HOURS)
        )

        # Check that the complete influence period
        # lies within the dataset.

        if influence_start < start.floor("h"):
            continue

        if influence_end > end.ceil("h"):
            continue

        # Avoid overlapping events affecting the same zones.

        overlap_found = False

        for prior in rows:

            prior_zones = set(
                prior["Impact_Zone_IDs"].split("|")
            )

            current_zones = set(impact_zones)

            common_zones = (
                prior_zones & current_zones
            )

            if not common_zones:
                continue

            prior_start = (
                prior["Start_Time"]
                - pd.Timedelta(hours=PRE_EVENT_HOURS)
            )

            prior_end = (
                prior["End_Time"]
                + pd.Timedelta(hours=POST_EVENT_HOURS)
            )

            if (
                influence_start < prior_end
                and influence_end > prior_start
            ):

                overlap_found = True
                break

        if overlap_found:
            continue

        intensity = int(
            rng.integers(1, 4)
        )

        event_number = len(rows) + 1

        rows.append({
            "Event_ID": f"EV{event_number:03d}",

            "Event_Name": (
                f"{EVENT_NAMES[event_type]} "
                f"{event_number:02d}"
            ),

            "Event_Type": event_type,

            "Venue_Zone_ID": venue_id,

            "Venue_Zone": venue_name,

            "Impact_Zone_IDs": "|".join(
                impact_zones
            ),

            "Start_Time": start_time,

            "End_Time": end_time,

            "Event_Intensity": intensity,

            "Is_Synthetic": True,

            "Source_Description": (
                "Simulated event scenario; "
                "not a historical event claim"
            )
        })

    if len(rows) != NUM_EVENTS:

        raise RuntimeError(
            f"Generated only {len(rows)} events "
            f"out of requested {NUM_EVENTS}. "
            "Check zone mappings and overlap restrictions."
        )

    return (
        pd.DataFrame(rows)
        .sort_values("Start_Time")
        .reset_index(drop=True)
    )# ----------------------------- EVENT IMPACT TABLE -----------------------------

def build_hourly_event_impacts(
    events: pd.DataFrame
) -> pd.DataFrame:

    rows = []

    for event in events.itertuples(index=False):

        start = pd.Timestamp(event.Start_Time)
        end = pd.Timestamp(event.End_Time)

        impact_zones = (
            str(event.Impact_Zone_IDs).split("|")
        )

        hours = pd.date_range(
            start - pd.Timedelta(hours=PRE_EVENT_HOURS),

            end + pd.Timedelta(hours=POST_EVENT_HOURS)
            - pd.Timedelta(hours=1),

            freq="h"
        )

        for zone_id in impact_zones:

            for hour in hours:

                if hour < start:
                    phase = "pre"

                elif hour < end:
                    phase = "during"

                else:
                    phase = "post"

                multiplier = (
                    1.0
                    + PHASE_EFFECT[phase]
                    * int(event.Event_Intensity)
                )

                rows.append({

                    "Hour_Timestamp": hour,

                    "Pickup_Zone_ID": zone_id,

                    "Venue_Zone_ID": event.Venue_Zone_ID,

                    "Event_ID": event.Event_ID,

                    "Event_Type": event.Event_Type,

                    "Event_Phase": phase,

                    "Event_Intensity": int(
                        event.Event_Intensity
                    ),

                    "Event_Multiplier": float(
                        multiplier
                    )
                })

    impacts = pd.DataFrame(rows)

    if impacts.duplicated(
        ["Hour_Timestamp", "Pickup_Zone_ID"]
    ).any():

        raise ValueError(
            "Overlapping event impacts found."
        )

    return (
        impacts
        .sort_values([
            "Hour_Timestamp",
            "Pickup_Zone_ID"
        ])
        .reset_index(drop=True)
    )
# ----------------------------- EVENT-ENRICHED RIDES -----------------------------


def create_event_enriched_rides(
    rides: pd.DataFrame,
    impacts: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:

    """
    Add synthetic event-related request rows while preserving
    all original ride records.
    """

    rng = np.random.default_rng(RANDOM_SEED + 1)

    base = rides.copy()

    base["Hour_Timestamp"] = (
        base["Timestamp"].dt.floor("h")
    )

    # Attach event metadata to original rides in affected zone/hour.

    base = base.merge(
        impacts,
        how="left",
        on=["Hour_Timestamp", "Pickup_Zone_ID"],
        validate="many_to_one"
    )

    base["Event_Flag"] = (
        base["Event_Type"].fillna("None")
    )

    # Position lookup to sample a ride template from the same zone/hour.

    group_indices = (
        rides.assign(
            Hour_Timestamp=rides["Timestamp"].dt.floor("h")
        )
        .groupby(
            ["Hour_Timestamp", "Pickup_Zone_ID"],
            sort=False
        )
        .indices
    )

    extra_frames = []

    total_extra = 0

    for impact in impacts.itertuples(index=False):

        key = (
            impact.Hour_Timestamp,
            impact.Pickup_Zone_ID
        )

        source_idx = group_indices.get(key)

        if source_idx is None or len(source_idx) == 0:

            # Do not invent a ride for a zone/hour with no baseline activity.
            continue

        baseline_count = len(source_idx)

        expected_extra = (
            baseline_count
            * (float(impact.Event_Multiplier) - 1.0)
        )

        extra_count = int(
            rng.poisson(expected_extra)
        )

        if extra_count <= 0:
            continue

        chosen = rng.choice(
            source_idx,
            size=extra_count,
            replace=True
        )

        extra = (
            rides.iloc[chosen]
            .copy()
            .reset_index(drop=True)
        )

        seconds = rng.integers(
            0,
            3600,
            size=extra_count
        )

        extra["Timestamp"] = (
            pd.Timestamp(impact.Hour_Timestamp)
            + pd.to_timedelta(seconds, unit="s")
        )

        extra["Event_ID"] = impact.Event_ID
        extra["Event_Type"] = impact.Event_Type
        extra["Event_Phase"] = impact.Event_Phase
        extra["Event_Intensity"] = int(
            impact.Event_Intensity
        )

        extra["Event_Flag"] = impact.Event_Type

        extra_frames.append(extra)

        total_extra += extra_count

    # Original rides retain their original request attributes and IDs.

    base["Event_ID"] = base["Event_ID"].fillna("")

    base["Event_Type"] = (
        base["Event_Type"].fillna("None")
    )

    base["Event_Phase"] = (
        base["Event_Phase"].fillna("None")
    )

    base["Event_Intensity"] = pd.to_numeric(
        base["Event_Intensity"],
        errors="coerce"
    ).fillna(0).astype(int)

    if extra_frames:

        extras = pd.concat(
            extra_frames,
            ignore_index=True
        )

        first_new_id = len(rides) + 1

        extras["Request_ID"] = [
            f"R{i:08d}"
            for i in range(
                first_new_id,
                first_new_id + len(extras)
            )
        ]

        enriched = pd.concat(
            [base, extras],
            ignore_index=True,
            sort=False
        )

    else:
        enriched = base

    # Rebuild derived time columns.

    enriched["Timestamp"] = pd.to_datetime(
        enriched["Timestamp"]
    )

    enriched["Date"] = (
        enriched["Timestamp"].dt.strftime("%Y-%m-%d")
    )

    enriched["Time"] = (
        enriched["Timestamp"].dt.strftime("%H:%M:%S")
    )

    enriched["Hour"] = (
        enriched["Timestamp"].dt.hour
    )

    enriched["Day_of_Week"] = (
        enriched["Timestamp"].dt.dayofweek
    )

    enriched = (
        enriched
        .sort_values("Timestamp")
        .reset_index(drop=True)
    )

    enriched["Timestamp"] = (
        enriched["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    )

    enriched = enriched.drop(
        columns=["Hour_Timestamp", "Event_Multiplier"],
        errors="ignore"
    )

    # Keep the original 15 columns at the front.

    original_cols = [
        "Request_ID",
        "Timestamp",
        "Date",
        "Time",
        "Hour",
        "Day_of_Week",
        "Pickup_Zone_ID",
        "Pickup_Zone",
        "Drop_Zone_ID",
        "Drop_Zone",
        "Vehicle_Type",
        "Ride_Distance_KM",
        "Weather",
        "Rain_Intensity",
        "Event_Flag"
    ]

    extra_cols = [
        c for c in [
            "Event_ID",
            "Event_Type",
            "Event_Phase",
            "Event_Intensity"
        ]
        if c in enriched.columns
    ]

    enriched = enriched[
        original_cols + extra_cols
    ]

    if enriched["Request_ID"].duplicated().any():

        raise AssertionError(
            "Generated contextual ride dataset contains duplicate Request_ID values."
        )

    report = pd.DataFrame([
        {
            "Metric": "Original ride rows",
            "Value": len(rides)
        },
        {
            "Metric": "Added synthetic event-related ride rows",
            "Value": total_extra
        },
        {
            "Metric": "Contextual ride rows",
            "Value": len(enriched)
        },
        {
            "Metric": "Added row percentage",
            "Value": round(
                100 * total_extra / max(1, len(rides)),
                3
            )
        },
        {
            "Metric": "Event count",
            "Value": impacts["Event_ID"].nunique()
        },
        {
            "Metric": "Weather hours",
            "Value": "see weather_data.csv"
        },
        {
            "Metric": "Rain demand multiplier in original generator",
            "Value": 1.3
        }
    ])

    return enriched, report


# ----------------------------- MAIN -----------------------------


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not INPUT_RIDES.exists():

        raise FileNotFoundError(
            f"Could not find {INPUT_RIDES.resolve()}. "
            "Put this script beside your original CSV."
        )

    print(
        f"Reading original dataset: {INPUT_RIDES}"
    )

    raw = pd.read_csv(INPUT_RIDES)

    rides = validate_input(raw)

    print(
        f"Loaded {len(rides):,} ride records."
    )

    # 1. Generate weather table.

    weather = extract_weather_table(rides)

    weather.to_csv(
        OUTPUT_DIR / "weather_data.csv",
        index=False
    )

    print(
        f"Saved weather_data.csv ({len(weather):,} hourly rows)."
    )

    # 2. Generate synthetic event calendar.

    events = generate_event_calendar(
        rides["Timestamp"].min(),
        rides["Timestamp"].max()
    )

    events.to_csv(
        OUTPUT_DIR / "bengaluru_events.csv",
        index=False
    )

    print(
        f"Saved bengaluru_events.csv ({len(events):,} synthetic events)."
    )

    # 3. Build event impact table.

    impacts = build_hourly_event_impacts(events)

    impacts.to_csv(
        OUTPUT_DIR / "event_impact_by_hour.csv",
        index=False
    )

    print(
        f"Saved event_impact_by_hour.csv ({len(impacts):,} zone-hour impact rows)."
    )

    # 4. Add synthetic event-related ride records.

    contextual, report = create_event_enriched_rides(
        rides,
        impacts
    )

    contextual.to_csv(
        OUTPUT_DIR / "rides_contextual_synthetic.csv",
        index=False
    )

    report.to_csv(
        OUTPUT_DIR / "context_generation_report.csv",
        index=False
    )

    print(
        f"Saved rides_contextual_synthetic.csv ({len(contextual):,} rows)."
    )

    print(
        "Original synthetic_bengaluru_rides.csv was not modified."
    )

    print("\nContext generation report:")

    print(
        report.to_string(index=False)
    )


if __name__ == "__main__":
    main()