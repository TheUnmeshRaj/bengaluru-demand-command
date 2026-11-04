
"""
Build the zone-level 5-minute ML dataset and validation outputs.

INPUTS:
    rides_contextual_synthetic.csv
    weather_data.csv
    bengaluru_events.csv

OUTPUTS:
    zone_demand_5min.csv
    validation_summary.csv
    validation_hourly_demand.png
    validation_zone_hour_heatmap.png
    validation_rain_vs_demand.png
    validation_event_phase_vs_demand.png

FORECAST DEFINITION:

    Each row represents a zone at a prediction origin.

    Demand_Last_5min:
        Demand observed in the immediately completed 5-minute interval.

    Historical lag features:
        Demand from earlier completed intervals.

    Target_Next_15min:
        Total ride requests during the following three 5-minute intervals.

All historical features use information available at the
prediction origin. Future demand is used only as the target.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# 1. CONFIGURATION
# ============================================================

RIDES_FILE = Path("rides_contextual_synthetic.csv")
WEATHER_FILE = Path("weather_data.csv")
EVENTS_FILE = Path("bengaluru_events.csv")

OUTPUT_DIR = Path(".")

FREQ = "5min"

EVENT_PRE_HOURS = 2
EVENT_POST_HOURS = 2


# ============================================================
# 2. LOAD AND VALIDATE INPUTS
# ============================================================

def load_inputs():

    for path in (
        RIDES_FILE,
        WEATHER_FILE,
        EVENTS_FILE
    ):

        if not path.exists():

            raise FileNotFoundError(
                f"Missing file: {path.resolve()}"
            )

    print("Loading ride dataset...")

    rides = pd.read_csv(
        RIDES_FILE,
        low_memory=False,
        parse_dates=["Timestamp"]
    )

    print("Loading weather dataset...")

    weather = pd.read_csv(
        WEATHER_FILE,
        low_memory=False,
        parse_dates=["Timestamp"]
    )

    print("Loading event dataset...")

    events = pd.read_csv(
        EVENTS_FILE,
        low_memory=False,
        parse_dates=["Start_Time", "End_Time"]
    )

    required_ride_columns = {
        "Request_ID",
        "Timestamp",
        "Pickup_Zone_ID",
        "Pickup_Zone"
    }

    missing = (
        required_ride_columns - set(rides.columns)
    )

    if missing:

        raise ValueError(
            f"Missing ride columns: {sorted(missing)}"
        )

    required_event_columns = {
        "Event_ID",
        "Venue_Zone_ID",
        "Impact_Zone_IDs",
        "Start_Time",
        "End_Time",
        "Event_Type",
        "Event_Intensity"
    }

    missing_events = (
        required_event_columns - set(events.columns)
    )

    if missing_events:

        raise ValueError(
            f"Missing event columns: {sorted(missing_events)}"
        )

    if rides["Timestamp"].isna().any():

        raise ValueError(
            "Invalid ride timestamps found."
        )

    if rides["Request_ID"].duplicated().any():

        raise ValueError(
            "Duplicate Request_ID values found."
        )

    if weather["Timestamp"].duplicated().any():

        raise ValueError(
            "Duplicate weather timestamps found."
        )

    if events["Event_ID"].duplicated().any():

        raise ValueError(
            "Duplicate Event_ID values found."
        )

    print(
        f"Loaded {len(rides):,} contextual ride events."
    )

    print(
        f"Loaded {len(weather):,} weather observations."
    )

    print(
        f"Loaded {len(events):,} simulated events."
    )

    return rides, weather, events


# ============================================================
# 3. CREATE EVENT FEATURES
# ============================================================

def make_event_features(
    events: pd.DataFrame,
    prediction_times: pd.DatetimeIndex
) -> pd.DataFrame:

    """
    Generate event-related features for all affected zones.

    Event features cover:
        2 hours before event
        Event duration
        2 hours after event

    These are known event-calendar features, not future ride counts.
    """

    rows = []

    for event in events.itertuples(index=False):

        start = pd.Timestamp(event.Start_Time)

        end = pd.Timestamp(event.End_Time)

        lo = (
            start -
            pd.Timedelta(hours=EVENT_PRE_HOURS)
        )

        hi = (
            end +
            pd.Timedelta(hours=EVENT_POST_HOURS)
        )

        times = prediction_times[
            (prediction_times >= lo) &
            (prediction_times < hi)
        ]

        impact_zones = (
            str(event.Impact_Zone_IDs).split("|")
        )

        for zone_id in impact_zones:

            for ts in times:

                if ts < start:

                    phase = "pre"

                elif ts < end:

                    phase = "during"

                else:

                    phase = "post"

                rows.append({

                    "Timestamp": ts,

                    "Zone_ID": str(zone_id),

                    "Event_Active": int(
                        start <= ts < end
                    ),

                    "Event_Impact": 1,

                    "Event_ID": event.Event_ID,

                    "Event_Type": event.Event_Type,

                    "Event_Phase": phase,

                    "Event_Intensity": int(
                        event.Event_Intensity
                    )

                })

    columns = [
        "Timestamp",
        "Zone_ID",
        "Event_Active",
        "Event_Impact",
        "Event_ID",
        "Event_Type",
        "Event_Phase",
        "Event_Intensity"
    ]

    result = pd.DataFrame(
        rows,
        columns=columns
    )

    if not result.empty:

        if result.duplicated(
            ["Timestamp", "Zone_ID"]
        ).any():

            raise ValueError(
                "Multiple event records mapped to the same "
                "zone and prediction timestamp."
            )

    return result


# ============================================================
# 4. BUILD THE ML DATASET
# ============================================================

def build_ml_dataset(
    rides: pd.DataFrame,
    weather: pd.DataFrame,
    events: pd.DataFrame
) -> pd.DataFrame:

    rides = rides.copy()

    rides["Pickup_Zone_ID"] = (
        rides["Pickup_Zone_ID"].astype(str)
    )

    rides["Pickup_Zone"] = (
        rides["Pickup_Zone"].astype(str)
    )

    # --------------------------------------------------------
    # STEP A: CREATE ZONE MASTER
    # --------------------------------------------------------

    zone_master = (
        rides[
            ["Pickup_Zone_ID", "Pickup_Zone"]
        ]
        .drop_duplicates()
        .copy()
    )

    if zone_master["Pickup_Zone_ID"].duplicated().any():

        raise ValueError(
            "A zone ID maps to multiple zone names."
        )

    zone_master = (
        zone_master
        .sort_values("Pickup_Zone_ID")
        .reset_index(drop=True)
    )

    zones = zone_master[
        "Pickup_Zone_ID"
    ].tolist()

    # --------------------------------------------------------
    # STEP B: CREATE COMPLETE 5-MINUTE CALENDAR
    # --------------------------------------------------------

    # Generate all 5-minute windows for the full date range.

    first_day = (
        rides["Timestamp"].min().floor("D")
    )

    last_day = (
        rides["Timestamp"].max().floor("D")
    )

    window_starts = pd.date_range(
        start=first_day,
        end=(
            last_day +
            pd.Timedelta(days=1) -
            pd.Timedelta(minutes=5)
        ),
        freq=FREQ
    )

    # Every zone must have a row for every interval.

    full_index = pd.MultiIndex.from_product(
        [zones, window_starts],
        names=[
            "Zone_ID",
            "Window_Start"
        ]
    )

    # Assign each ride to its 5-minute interval.

    rides["Window_Start"] = (
        rides["Timestamp"].dt.floor(FREQ)
    )

    observed = (
        rides
        .groupby(
            [
                "Pickup_Zone_ID",
                "Window_Start"
            ]
        )
        .size()
        .rename("Ride_Count")
    )

    frame = (
        observed
        .reindex(
            full_index,
            fill_value=0
        )
        .reset_index()
    )

    # Attach readable zone names.

    frame = frame.merge(
        zone_master.rename(
            columns={
                "Pickup_Zone_ID": "Zone_ID",
                "Pickup_Zone": "Zone_Name"
            }
        ),
        on="Zone_ID",
        how="left",
        validate="many_to_one"
    )

    # Prediction origin is the END of the completed window.

    frame["Timestamp"] = (
        frame["Window_Start"] +
        pd.Timedelta(minutes=5)
    )

    frame = (
        frame
        .sort_values(
            ["Zone_ID", "Timestamp"]
        )
        .reset_index(drop=True)
    )

    print(
        f"Created complete demand grid: {len(frame):,} rows."
    )

    # --------------------------------------------------------
    # STEP C: HISTORICAL DEMAND FEATURES
    # --------------------------------------------------------

    # Each row represents one completed 5-minute interval.
    #
    # Current row:
    #   Ride_Count = latest completed 5-minute demand.
    #
    # shift(1):
    #   Previous 5-minute interval.
    #
    # shift(2):
    #   Previous 10-minute interval.
    #
    # shift(3):
    #   Previous 15-minute interval.
    #
    # shift(6):
    #   Previous 30-minute interval.
    #
    # shift(12):
    #   Previous 60-minute interval.

    grouped = frame.groupby(
        "Zone_ID",
        sort=False
    )["Ride_Count"]

    frame["Demand_Last_5min"] = (
        frame["Ride_Count"]
    )

    frame["Demand_Lag_5min"] = (
        grouped.shift(1)
    )

    frame["Demand_Lag_10min"] = (
        grouped.shift(2)
    )

    frame["Demand_Lag_15min"] = (
        grouped.shift(3)
    )

    frame["Demand_Lag_30min"] = (
        grouped.shift(6)
    )

    frame["Demand_Lag_60min"] = (
        grouped.shift(12)
    )

    # --------------------------------------------------------
    # STEP D: ROLLING DEMAND FEATURES
    # --------------------------------------------------------

    # These rolling means include the latest completed interval.
    # This information is available at the prediction origin.

    frame["Rolling_Mean_15min"] = (
        frame.groupby(
            "Zone_ID",
            sort=False
        )["Ride_Count"]
        .transform(
            lambda s: s.rolling(
                window=3,
                min_periods=3
            ).mean()
        )
    )

    frame["Rolling_Mean_30min"] = (
        frame.groupby(
            "Zone_ID",
            sort=False
        )["Ride_Count"]
        .transform(
            lambda s: s.rolling(
                window=6,
                min_periods=6
            ).mean()
        )
    )

    frame["Rolling_Mean_60min"] = (
        frame.groupby(
            "Zone_ID",
            sort=False
        )["Ride_Count"]
        .transform(
            lambda s: s.rolling(
                window=12,
                min_periods=12
            ).mean()
        )
    )

    # --------------------------------------------------------
    # STEP E: CREATE NEXT 15-MINUTE TARGET
    # --------------------------------------------------------

    # At prediction origin T, the target is demand during:
    #
    # T to T+5
    # T+5 to T+10
    # T+10 to T+15

    g = frame.groupby(
        "Zone_ID",
        sort=False
    )["Ride_Count"]

    frame["Target_Next_15min"] = (

        g.shift(-1) +
        g.shift(-2) +
        g.shift(-3)

    )

    # --------------------------------------------------------
    # STEP F: TIME FEATURES
    # --------------------------------------------------------

    frame["Hour"] = (
        frame["Timestamp"].dt.hour
    )

    frame["Day_Of_Week"] = (
        frame["Timestamp"].dt.dayofweek
    )

    frame["Is_Weekend"] = (
        frame["Day_Of_Week"]
        .isin([5, 6])
        .astype(int)
    )

    hour_fraction = (
        2 * np.pi *
        frame["Hour"] / 24.0
    )

    frame["Hour_Sin"] = (
        np.sin(hour_fraction)
    )

    frame["Hour_Cos"] = (
        np.cos(hour_fraction)
    )

    # --------------------------------------------------------
    # STEP G: WEATHER FEATURES
    # --------------------------------------------------------

    # The original generator creates hourly weather observations.
    # Align each prediction origin with the weather available
    # for that hour.

    weather = weather.copy()

    weather["Timestamp"] = (
        pd.to_datetime(weather["Timestamp"])
        .dt.floor("h")
    )

    weather = weather.rename(
        columns={
            "Timestamp": "Weather_Hour",
            "Weather": "Weather_Condition"
        }
    )

    frame["Weather_Hour"] = (
        frame["Timestamp"].dt.floor("h")
    )

    frame = frame.merge(
        weather[
            [
                "Weather_Hour",
                "Weather_Condition",
                "Rain_Intensity"
            ]
        ],
        on="Weather_Hour",
        how="left",
        validate="many_to_one"
    )

    frame["Weather_Condition"] = (
        frame["Weather_Condition"].fillna("Unknown")
    )

    frame["Rain_Intensity"] = (
        pd.to_numeric(
            frame["Rain_Intensity"],
            errors="coerce"
        )
        .fillna(0.0)
    )

    # --------------------------------------------------------
    # STEP H: EVENT FEATURES
    # --------------------------------------------------------

    prediction_times = pd.DatetimeIndex(
        frame["Timestamp"]
        .drop_duplicates()
        .sort_values()
    )

    event_features = make_event_features(
        events,
        prediction_times
    )

    frame = frame.merge(
        event_features,
        on=["Timestamp", "Zone_ID"],
        how="left",
        validate="one_to_one"
    )

    frame["Event_Active"] = (
        frame["Event_Active"]
        .fillna(0)
        .astype(int)
    )

    frame["Event_Impact"] = (
        frame["Event_Impact"]
        .fillna(0)
        .astype(int)
    )

    frame["Event_ID"] = (
        frame["Event_ID"].fillna("None")
    )

    frame["Event_Type"] = (
        frame["Event_Type"].fillna("None")
    )

    frame["Event_Phase"] = (
        frame["Event_Phase"].fillna("None")
    )

    frame["Event_Intensity"] = (
        pd.to_numeric(
            frame["Event_Intensity"],
            errors="coerce"
        )
        .fillna(0)
        .astype(int)
    )

    # --------------------------------------------------------
    # STEP I: REMOVE INCOMPLETE TRAINING ROWS
    # --------------------------------------------------------

    # First 12 intervals do not have a complete 60-minute history.
    # Last 3 intervals do not have a complete future 15-minute target.

    frame = frame.dropna(
        subset=[
            "Demand_Lag_60min",
            "Rolling_Mean_60min",
            "Target_Next_15min"
        ]
    ).copy()

    # --------------------------------------------------------
    # STEP J: FINAL COLUMN ORGANISATION
    # --------------------------------------------------------

    frame = frame.drop(
        columns=[
            "Window_Start",
            "Ride_Count",
            "Weather_Hour"
        ]
    )

    ordered_columns = [

        "Timestamp",

        "Zone_ID",
        "Zone_Name",

        "Hour",
        "Day_Of_Week",
        "Is_Weekend",
        "Hour_Sin",
        "Hour_Cos",

        "Demand_Last_5min",

        "Demand_Lag_5min",
        "Demand_Lag_10min",
        "Demand_Lag_15min",
        "Demand_Lag_30min",
        "Demand_Lag_60min",

        "Rolling_Mean_15min",
        "Rolling_Mean_30min",
        "Rolling_Mean_60min",

        "Weather_Condition",
        "Rain_Intensity",

        "Event_Active",
        "Event_Impact",
        "Event_ID",
        "Event_Type",
        "Event_Phase",
        "Event_Intensity",

        "Target_Next_15min"

    ]

    frame = frame[
        ordered_columns
    ].copy()

    frame = (
        frame
        .sort_values(
            ["Timestamp", "Zone_ID"]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # STEP K: DATA INTEGRITY CHECKS
    # --------------------------------------------------------

    if frame.duplicated(
        ["Timestamp", "Zone_ID"]
    ).any():

        raise AssertionError(
            "Duplicate zone-time records found."
        )

    if frame["Target_Next_15min"].isna().any():

        raise AssertionError(
            "Missing future demand targets found."
        )

    if frame["Target_Next_15min"].lt(0).any():

        raise AssertionError(
            "Negative future demand found."
        )

    if frame["Event_Impact"].sum() == 0:

        raise AssertionError(
            "No event features were mapped to the ML dataset."
        )

    print(
        f"Final ML dataset contains {len(frame):,} rows."
    )

    return frame


# ============================================================
# 5. VALIDATION AND VISUALISATION
# ============================================================

def create_validation_outputs(
    ml: pd.DataFrame,
    output_dir: Path
) -> pd.DataFrame:

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    summaries = []

    def add_metric(name, value):
        summaries.append({
            "Metric": name,
            "Value": value
        })

    add_metric(
        "ML rows",
        len(ml)
    )

    add_metric(
        "Zones",
        ml["Zone_ID"].nunique()
    )

    add_metric(
        "Prediction origins",
        ml["Timestamp"].nunique()
    )

    add_metric(
        "Duplicate zone-time rows",
        ml.duplicated(
            ["Timestamp", "Zone_ID"]
        ).sum()
    )

    add_metric(
        "Missing values",
        int(ml.isna().sum().sum())
    )

    add_metric(
        "Zero last-5min demand rows (%)",
        round(
            100 * (
                ml["Demand_Last_5min"] == 0
            ).mean(),
            3
        )
    )

    add_metric(
        "Rain rows (%)",
        round(
            100 * (
                ml["Weather_Condition"] == "Rain"
            ).mean(),
            3
        )
    )

    add_metric(
        "Event-impact rows (%)",
        round(
            100 * (
                ml["Event_Impact"] == 1
            ).mean(),
            3
        )
    )

    add_metric(
        "Event-active rows (%)",
        round(
            100 * (
                ml["Event_Active"] == 1
            ).mean(),
            3
        )
    )

    add_metric(
        "Mean target next 15min",
        round(
            ml["Target_Next_15min"].mean(),
            3
        )
    )

    add_metric(
        "Maximum target next 15min",
        int(
            ml["Target_Next_15min"].max()
        )
    )

    add_metric(
        "Minimum target next 15min",
        int(
            ml["Target_Next_15min"].min()
        )
    )

    add_metric(
        "Total event-impacted observations",
        int(
            ml["Event_Impact"].sum()
        )
    )

    summary = pd.DataFrame(
        summaries
    )

    summary.to_csv(
        output_dir / "validation_summary.csv",
        index=False
    )

    # --------------------------------------------------------
    # PLOT 1: HOURLY DEMAND
    # --------------------------------------------------------

    hourly = (
        ml.groupby("Hour")["Demand_Last_5min"]
        .mean()
        .reindex(range(24))
    )

    fig, ax = plt.subplots(
        figsize=(10, 4)
    )

    hourly.plot(
        kind="bar",
        ax=ax
    )

    ax.set_title(
        "Average Zone Demand in Latest 5-Minute Window by Hour"
    )

    ax.set_xlabel("Hour")

    ax.set_ylabel(
        "Mean rides / zone / 5 min"
    )

    fig.tight_layout()

    fig.savefig(
        output_dir / "validation_hourly_demand.png",
        dpi=150
    )

    plt.close(fig)

    # --------------------------------------------------------
    # PLOT 2: ZONE-HOUR HEATMAP
    # --------------------------------------------------------

    heat = ml.pivot_table(
        index="Zone_Name",
        columns="Hour",
        values="Demand_Last_5min",
        aggfunc="mean"
    )

    fig, ax = plt.subplots(
        figsize=(13, 10)
    )

    im = ax.imshow(
        heat.fillna(0).values,
        aspect="auto"
    )

    ax.set_yticks(
        range(len(heat.index))
    )

    ax.set_yticklabels(
        heat.index,
        fontsize=7
    )

    ax.set_xticks(
        range(24)
    )

    ax.set_xticklabels(
        list(heat.columns)
    )

    ax.set_title(
        "Mean 5-Minute Demand by Zone and Hour"
    )

    ax.set_xlabel("Hour")

    ax.set_ylabel("Pickup Zone")

    fig.colorbar(
        im,
        ax=ax,
        label="Mean rides / 5 min"
    )

    fig.tight_layout()

    fig.savefig(
        output_dir / "validation_zone_hour_heatmap.png",
        dpi=150
    )

    plt.close(fig)

    # --------------------------------------------------------
    # PLOT 3: WEATHER VS DEMAND
    # --------------------------------------------------------

    rain = (
        ml.groupby(
            "Weather_Condition"
        )["Demand_Last_5min"]
        .mean()
        .sort_index()
    )

    fig, ax = plt.subplots(
        figsize=(7, 4)
    )

    rain.plot(
        kind="bar",
        ax=ax
    )

    ax.set_title(
        "Average Observed Demand by Weather Condition"
    )

    ax.set_xlabel("Weather")

    ax.set_ylabel(
        "Mean rides / zone / 5 min"
    )

    fig.tight_layout()

    fig.savefig(
        output_dir / "validation_rain_vs_demand.png",
        dpi=150
    )

    plt.close(fig)

    # --------------------------------------------------------
    # PLOT 4: EVENT PHASE VS DEMAND
    # --------------------------------------------------------

    event_data = ml.copy()

    event_data["Event_Group"] = np.where(
        event_data["Event_Impact"] == 1,
        event_data["Event_Phase"],
        "normal"
    )

    event_means = (
        event_data
        .groupby(
            "Event_Group"
        )["Demand_Last_5min"]
        .mean()
        .reindex([
            "normal",
            "pre",
            "during",
            "post"
        ])
        .dropna()
    )

    fig, ax = plt.subplots(
        figsize=(7, 4)
    )

    event_means.plot(
        kind="bar",
        ax=ax
    )

    ax.set_title(
        "Average Demand by Event Phase "
        "(Event-Affected Zones)"
    )

    ax.set_xlabel("Event Phase")

    ax.set_ylabel(
        "Mean rides / zone / 5 min"
    )

    fig.tight_layout()

    fig.savefig(
        output_dir / "validation_event_phase_vs_demand.png",
        dpi=150
    )

    plt.close(fig)

    return summary


# ============================================================
# 6. MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("\n" + "=" * 55)
    print("BENGALURU RIDE DEMAND - ML DATASET PREPARATION")
    print("=" * 55)

    rides, weather, events = load_inputs()

    ml = build_ml_dataset(
        rides,
        weather,
        events
    )

    output_file = (
        OUTPUT_DIR / "zone_demand_5min.csv"
    )

    ml.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nSaved ML dataset: {output_file}"
    )

    summary = create_validation_outputs(
        ml,
        OUTPUT_DIR
    )

    print("\n" + "=" * 55)
    print("VALIDATION SUMMARY")
    print("=" * 55)

    print(
        summary.to_string(index=False)
    )

    print("\nGenerated validation graphs:")

    print("1. validation_hourly_demand.png")
    print("2. validation_zone_hour_heatmap.png")
    print("3. validation_rain_vs_demand.png")
    print("4. validation_event_phase_vs_demand.png")

    print("\nML dataset preparation completed.")


if __name__ == "__main__":
    main()
