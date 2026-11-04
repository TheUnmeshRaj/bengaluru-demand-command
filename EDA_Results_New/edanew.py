# ============================================================
# REAL-TIME RIDE-HAILING DEMAND PREDICTION
# EDA FOR SYNTHETIC BENGALURU RIDE DATASET
# ============================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ------------------------------------------------------------
# 1. PATHS
# ------------------------------------------------------------

FILE_PATH = r"C:\Users\lalwa\Desktop\SPA EL\synthetic_bengaluru_rides.csv"

OUTPUT_DIR = r"C:\Users\lalwa\Desktop\SPA EL\EDA_Results_New"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 70)
print("BENGALURU RIDE-HAILING DATASET - EDA")
print("=" * 70)


# ------------------------------------------------------------
# 2. LOAD DATA
# ------------------------------------------------------------

df = pd.read_csv(FILE_PATH)

print("\nDataset loaded successfully.")

print("\nShape:")
print(df.shape)

print("\nColumns:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head())


# ------------------------------------------------------------
# 3. BASIC INFORMATION
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("3. BASIC DATASET INFORMATION")
print("=" * 70)

print("\nData types:")
print(df.dtypes)

print("\nMissing values:")
print(df.isnull().sum())

print("\nDuplicate rows:")
print(df.duplicated().sum())

print("\nDuplicate Request IDs:")
print(df["Request_ID"].duplicated().sum())


# Save basic information
basic_info = pd.DataFrame({
    "Column": df.columns,
    "Data_Type": df.dtypes.astype(str),
    "Missing_Count": df.isnull().sum().values,
    "Unique_Count": df.nunique().values
})

basic_info.to_csv(
    os.path.join(OUTPUT_DIR, "01_basic_information.csv"),
    index=False
)


# ------------------------------------------------------------
# 4. TIMESTAMP VALIDATION
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("4. TIMESTAMP VALIDATION")
print("=" * 70)

df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

print("\nInvalid timestamps:")
print(df["Timestamp"].isna().sum())

print("\nDate range:")
print(df["Timestamp"].min())
print(df["Timestamp"].max())

# Sort chronologically
df = df.sort_values("Timestamp").reset_index(drop=True)

# Check whether Date/Time/Hour match Timestamp
df["Derived_Date"] = df["Timestamp"].dt.date
df["Derived_Time"] = df["Timestamp"].dt.strftime("%H:%M:%S")
df["Derived_Hour"] = df["Timestamp"].dt.hour

date_mismatch = (
    df["Date"].astype(str) != df["Derived_Date"].astype(str)
).sum()

time_mismatch = (
    df["Time"].astype(str) != df["Derived_Time"].astype(str)
).sum()

hour_mismatch = (
    pd.to_numeric(df["Hour"], errors="coerce") != df["Derived_Hour"]
).sum()

print("\nDate mismatches:", date_mismatch)
print("Time mismatches:", time_mismatch)
print("Hour mismatches:", hour_mismatch)

df.drop(
    columns=["Derived_Date", "Derived_Time", "Derived_Hour"],
    inplace=True
)


# ------------------------------------------------------------
# 5. UNIQUE VALUES / CATEGORICAL DISTRIBUTIONS
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("5. UNIQUE VALUES")
print("=" * 70)

print("\nNumber of pickup zones:")
print(df["Pickup_Zone_ID"].nunique())

print("\nNumber of pickup zone names:")
print(df["Pickup_Zone"].nunique())

print("\nNumber of drop zones:")
print(df["Drop_Zone_ID"].nunique())

print("\nVehicle types:")
print(df["Vehicle_Type"].value_counts())

print("\nWeather:")
print(df["Weather"].value_counts())

print("\nEvents:")
print(df["Event_Flag"].value_counts())


# ------------------------------------------------------------
# 6. DEMAND PER DAY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("6. DAILY DEMAND")
print("=" * 70)

daily_demand = (
    df.groupby(df["Timestamp"].dt.date)
      .size()
      .reset_index(name="Ride_Count")
)

daily_demand.columns = ["Date", "Ride_Count"]

print("\nDaily statistics:")
print(daily_demand["Ride_Count"].describe())

daily_demand.to_csv(
    os.path.join(OUTPUT_DIR, "02_daily_demand.csv"),
    index=False
)

plt.figure(figsize=(15, 6))

plt.plot(
    pd.to_datetime(daily_demand["Date"]),
    daily_demand["Ride_Count"]
)

plt.title("Daily Ride Demand")
plt.xlabel("Date")
plt.ylabel("Number of Rides")
plt.xticks(rotation=45)
plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "01_daily_demand.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 7. HOURLY DEMAND
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("7. HOURLY DEMAND")
print("=" * 70)

df["Hour_Calc"] = df["Timestamp"].dt.hour

hourly_demand = (
    df.groupby("Hour_Calc")
      .size()
      .reset_index(name="Ride_Count")
)

print(hourly_demand)

hourly_demand.to_csv(
    os.path.join(OUTPUT_DIR, "03_hourly_demand.csv"),
    index=False
)

plt.figure(figsize=(12, 6))

sns.barplot(
    data=hourly_demand,
    x="Hour_Calc",
    y="Ride_Count"
)

plt.title("Ride Demand by Hour")
plt.xlabel("Hour of Day")
plt.ylabel("Number of Rides")
plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "02_hourly_demand.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 8. 15-MINUTE DEMAND
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("8. 15-MINUTE DEMAND")
print("=" * 70)

df["15_Minute"] = df["Timestamp"].dt.floor("15min")

demand_15min = (
    df.groupby("15_Minute")
      .size()
      .reset_index(name="Ride_Count")
)

print(demand_15min.head())

print("\n15-minute demand statistics:")
print(demand_15min["Ride_Count"].describe())

demand_15min.to_csv(
    os.path.join(OUTPUT_DIR, "04_15min_demand.csv"),
    index=False
)

plt.figure(figsize=(16, 6))

plt.plot(
    demand_15min["15_Minute"],
    demand_15min["Ride_Count"],
    linewidth=0.8
)

plt.title("15-Minute Ride Demand")
plt.xlabel("Time")
plt.ylabel("Ride Count")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "03_15min_demand.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 9. 5-MINUTE DEMAND
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("9. 5-MINUTE DEMAND")
print("=" * 70)

df["5_Minute"] = df["Timestamp"].dt.floor("5min")

demand_5min = (
    df.groupby("5_Minute")
      .size()
      .reset_index(name="Ride_Count")
)

print("\n5-minute demand statistics:")
print(demand_5min["Ride_Count"].describe())

demand_5min.to_csv(
    os.path.join(OUTPUT_DIR, "05_5min_demand.csv"),
    index=False
)

plt.figure(figsize=(16, 6))

plt.plot(
    demand_5min["5_Minute"],
    demand_5min["Ride_Count"],
    linewidth=0.7
)

plt.title("5-Minute Ride Demand")
plt.xlabel("Time")
plt.ylabel("Ride Count")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "04_5min_demand.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 10. DAY OF WEEK DEMAND
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("10. DAY OF WEEK DEMAND")
print("=" * 70)

df["Day_Name"] = df["Timestamp"].dt.day_name()

day_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

day_counts = (
    df["Day_Name"]
    .value_counts()
    .reindex(day_order)
)

print(day_counts)

day_counts.to_csv(
    os.path.join(OUTPUT_DIR, "06_day_of_week_demand.csv")
)

plt.figure(figsize=(10, 6))

sns.barplot(
    x=day_counts.index,
    y=day_counts.values
)

plt.title("Ride Demand by Day of Week")
plt.xlabel("Day")
plt.ylabel("Number of Rides")
plt.xticks(rotation=30)

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "05_day_of_week_demand.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 11. AVERAGE DEMAND PER DAY BY DAY OF WEEK
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("11. AVERAGE DAILY DEMAND BY DAY OF WEEK")
print("=" * 70)

daily_temp = df.copy()

daily_temp["Date_Only"] = daily_temp["Timestamp"].dt.date
daily_temp["Day_Name"] = daily_temp["Timestamp"].dt.day_name()

daily_counts = (
    daily_temp.groupby(["Date_Only", "Day_Name"])
              .size()
              .reset_index(name="Ride_Count")
)

avg_day_demand = (
    daily_counts.groupby("Day_Name")["Ride_Count"]
                .mean()
                .reindex(day_order)
)

print(avg_day_demand)

plt.figure(figsize=(10, 6))

sns.barplot(
    x=avg_day_demand.index,
    y=avg_day_demand.values
)

plt.title("Average Daily Ride Demand by Day of Week")
plt.xlabel("Day")
plt.ylabel("Average Rides per Day")
plt.xticks(rotation=30)

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "06_average_daily_demand_by_day.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 12. WEEKDAY VS WEEKEND
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("12. WEEKDAY VS WEEKEND")
print("=" * 70)

df["Day_Type"] = np.where(
    df["Timestamp"].dt.dayofweek < 5,
    "Weekday",
    "Weekend"
)

weekday_weekend = df["Day_Type"].value_counts()

print(weekday_weekend)

avg_weekday_weekend = (
    df.groupby(["Day_Type", df["Timestamp"].dt.date])
      .size()
      .groupby(level=0)
      .mean()
)

print("\nAverage rides per day:")
print(avg_weekday_weekend)

plt.figure(figsize=(8, 6))

sns.barplot(
    x=avg_weekday_weekend.index,
    y=avg_weekday_weekend.values
)

plt.title("Average Daily Demand: Weekday vs Weekend")
plt.xlabel("")
plt.ylabel("Average Rides per Day")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "07_weekday_vs_weekend.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 13. PICKUP ZONE DEMAND
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("13. PICKUP ZONE DEMAND")
print("=" * 70)

zone_demand = (
    df.groupby(["Pickup_Zone_ID", "Pickup_Zone"])
      .size()
      .reset_index(name="Ride_Count")
      .sort_values("Ride_Count", ascending=False)
)

print("\nTop 20 pickup zones:")
print(zone_demand.head(20))

zone_demand.to_csv(
    os.path.join(OUTPUT_DIR, "07_pickup_zone_demand.csv"),
    index=False
)

plt.figure(figsize=(12, 8))

top20 = zone_demand.head(20)

sns.barplot(
    data=top20,
    y="Pickup_Zone",
    x="Ride_Count"
)

plt.title("Top 20 Pickup Zones")
plt.xlabel("Number of Rides")
plt.ylabel("Pickup Zone")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "08_top_20_pickup_zones.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 14. ZONE DEMAND DISTRIBUTION
# ------------------------------------------------------------

plt.figure(figsize=(12, 6))

sns.histplot(
    zone_demand["Ride_Count"],
    bins=20,
    kde=True
)

plt.title("Distribution of Ride Demand Across Pickup Zones")
plt.xlabel("Total Rides per Zone")
plt.ylabel("Number of Zones")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "09_zone_demand_distribution.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 15. ZONE × HOUR HEATMAP
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("15. ZONE × HOUR DEMAND")
print("=" * 70)

zone_hour = pd.crosstab(
    df["Pickup_Zone"],
    df["Hour_Calc"]
)

zone_hour.to_csv(
    os.path.join(OUTPUT_DIR, "08_zone_hour_matrix.csv")
)

plt.figure(figsize=(16, 14))

sns.heatmap(
    zone_hour,
    cmap="YlOrRd"
)

plt.title("Pickup Zone × Hour Demand Heatmap")
plt.xlabel("Hour of Day")
plt.ylabel("Pickup Zone")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "10_zone_hour_heatmap.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 16. NORMALIZED ZONE × HOUR HEATMAP
# ------------------------------------------------------------

# Normalize each zone by its own total demand
zone_hour_normalized = zone_hour.div(
    zone_hour.sum(axis=1),
    axis=0
)

zone_hour_normalized.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "09_normalized_zone_hour_matrix.csv"
    )
)

plt.figure(figsize=(16, 14))

sns.heatmap(
    zone_hour_normalized,
    cmap="YlOrRd"
)

plt.title("Normalized Pickup Zone × Hour Demand")
plt.xlabel("Hour of Day")
plt.ylabel("Pickup Zone")

plt.tight_layout()

plt.savefig(
    os.path.join(
        OUTPUT_DIR,
        "11_normalized_zone_hour_heatmap.png"
    ),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 17. DAY × ZONE HEATMAP
# ------------------------------------------------------------

day_zone = pd.crosstab(
    df["Pickup_Zone"],
    df["Day_Name"]
)

day_zone = day_zone.reindex(columns=day_order)

day_zone.to_csv(
    os.path.join(OUTPUT_DIR, "10_day_zone_matrix.csv")
)

plt.figure(figsize=(12, 14))

sns.heatmap(
    day_zone,
    cmap="YlOrRd"
)

plt.title("Pickup Zone × Day of Week Demand")
plt.xlabel("Day")
plt.ylabel("Pickup Zone")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "12_day_zone_heatmap.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 18. HOURLY DEMAND: WEEKDAY VS WEEKEND
# ------------------------------------------------------------

hour_daytype = (
    df.groupby(["Day_Type", "Hour_Calc"])
      .size()
      .reset_index(name="Ride_Count")
)

plt.figure(figsize=(14, 6))

sns.lineplot(
    data=hour_daytype,
    x="Hour_Calc",
    y="Ride_Count",
    hue="Day_Type",
    marker="o"
)

plt.title("Hourly Demand: Weekday vs Weekend")
plt.xlabel("Hour")
plt.ylabel("Ride Count")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "13_hourly_weekday_weekend.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 19. VEHICLE TYPE DISTRIBUTION
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("19. VEHICLE TYPE")
print("=" * 70)

vehicle_counts = df["Vehicle_Type"].value_counts()

print(vehicle_counts)

vehicle_counts.to_csv(
    os.path.join(OUTPUT_DIR, "11_vehicle_type_distribution.csv")
)

plt.figure(figsize=(8, 6))

sns.barplot(
    x=vehicle_counts.index,
    y=vehicle_counts.values
)

plt.title("Vehicle Type Distribution")
plt.xlabel("Vehicle Type")
plt.ylabel("Number of Rides")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "14_vehicle_type_distribution.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 20. RIDE DISTANCE DISTRIBUTION
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("20. RIDE DISTANCE")
print("=" * 70)

print(df["Ride_Distance_KM"].describe())

plt.figure(figsize=(12, 6))

sns.histplot(
    df["Ride_Distance_KM"],
    bins=50,
    kde=True
)

plt.title("Ride Distance Distribution")
plt.xlabel("Ride Distance (km)")
plt.ylabel("Number of Rides")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "15_ride_distance_distribution.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 21. DISTANCE BY VEHICLE TYPE
# ------------------------------------------------------------

plt.figure(figsize=(10, 6))

sns.boxplot(
    data=df,
    x="Vehicle_Type",
    y="Ride_Distance_KM"
)

plt.title("Ride Distance by Vehicle Type")
plt.xlabel("Vehicle Type")
plt.ylabel("Distance (km)")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "16_distance_by_vehicle.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 22. TOP OD PAIRS
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("22. ORIGIN → DESTINATION ANALYSIS")
print("=" * 70)

od_pairs = (
    df.groupby(
        ["Pickup_Zone", "Drop_Zone"]
    )
    .size()
    .reset_index(name="Ride_Count")
    .sort_values("Ride_Count", ascending=False)
)

print("\nTop 20 OD pairs:")
print(od_pairs.head(20))

od_pairs.to_csv(
    os.path.join(OUTPUT_DIR, "12_od_pairs.csv"),
    index=False
)


# ------------------------------------------------------------
# 23. SELF-ZONE RIDES
# ------------------------------------------------------------

self_zone = (
    df["Pickup_Zone_ID"] == df["Drop_Zone_ID"]
)

self_zone_percentage = self_zone.mean() * 100

print(
    f"\nSame pickup/drop zone rides: "
    f"{self_zone.sum():,} "
    f"({self_zone_percentage:.2f}%)"
)


# ------------------------------------------------------------
# 24. OD HEATMAP
# ------------------------------------------------------------

od_matrix = pd.crosstab(
    df["Pickup_Zone"],
    df["Drop_Zone"]
)

od_matrix.to_csv(
    os.path.join(OUTPUT_DIR, "13_od_matrix.csv")
)

plt.figure(figsize=(18, 15))

sns.heatmap(
    od_matrix,
    cmap="YlOrRd"
)

plt.title("Pickup → Drop Zone Demand")
plt.xlabel("Drop Zone")
plt.ylabel("Pickup Zone")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "17_od_heatmap.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 25. WEATHER DISTRIBUTION
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("25. WEATHER")
print("=" * 70)

weather_counts = df["Weather"].value_counts()

print(weather_counts)

plt.figure(figsize=(8, 6))

sns.barplot(
    x=weather_counts.index,
    y=weather_counts.values
)

plt.title("Weather Distribution")
plt.xlabel("Weather")
plt.ylabel("Number of Rides")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "18_weather_distribution.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 26. RAIN INTENSITY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("26. RAIN INTENSITY")
print("=" * 70)

print(df["Rain_Intensity"].describe())

plt.figure(figsize=(10, 6))

sns.histplot(
    df["Rain_Intensity"],
    bins=30,
    kde=True
)

plt.title("Rain Intensity Distribution")
plt.xlabel("Rain Intensity")
plt.ylabel("Number of Rides")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "19_rain_intensity.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 27. WEATHER × DEMAND
# ------------------------------------------------------------

weather_demand = (
    df.groupby("Weather")
      .size()
      .sort_values(ascending=False)
)

weather_demand.to_csv(
    os.path.join(OUTPUT_DIR, "14_weather_demand.csv")
)

plt.figure(figsize=(10, 6))

sns.barplot(
    x=weather_demand.index,
    y=weather_demand.values
)

plt.title("Ride Demand by Weather Condition")
plt.xlabel("Weather")
plt.ylabel("Number of Rides")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "20_weather_demand.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 28. EVENT ANALYSIS
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("28. EVENT ANALYSIS")
print("=" * 70)

event_counts = df["Event_Flag"].value_counts()

print(event_counts)

event_demand = (
    df.groupby("Event_Flag")
      .size()
      .sort_values(ascending=False)
)

event_demand.to_csv(
    os.path.join(OUTPUT_DIR, "15_event_demand.csv")
)

plt.figure(figsize=(10, 6))

sns.barplot(
    x=event_demand.index,
    y=event_demand.values
)

plt.title("Demand by Event Condition")
plt.xlabel("Event")
plt.ylabel("Number of Rides")

plt.xticks(rotation=30)

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "21_event_demand.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 29. DEMAND STATISTICS
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("29. DEMAND STATISTICS")
print("=" * 70)

mean_demand = demand_15min["Ride_Count"].mean()
std_demand = demand_15min["Ride_Count"].std()

cv = std_demand / mean_demand

peak_demand = demand_15min["Ride_Count"].max()

peak_average_ratio = peak_demand / mean_demand

print(f"Mean 15-min demand       : {mean_demand:.2f}")
print(f"Std 15-min demand        : {std_demand:.2f}")
print(f"Coefficient of Variation : {cv:.3f}")
print(f"Peak 15-min demand       : {peak_demand}")
print(f"Peak / Average ratio     : {peak_average_ratio:.2f}")


# ------------------------------------------------------------
# 30. TEMPORAL AUTOCORRELATION
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("30. TEMPORAL AUTOCORRELATION")
print("=" * 70)

autocorr_1 = demand_15min["Ride_Count"].autocorr(lag=1)
autocorr_4 = demand_15min["Ride_Count"].autocorr(lag=4)
autocorr_96 = demand_15min["Ride_Count"].autocorr(lag=96)

print(f"Autocorrelation lag 1  (15 min) : {autocorr_1:.4f}")
print(f"Autocorrelation lag 4  (1 hour) : {autocorr_4:.4f}")
print(f"Autocorrelation lag 96 (1 day)  : {autocorr_96:.4f}")


# ------------------------------------------------------------
# 31. AUTOCORRELATION PLOT
# ------------------------------------------------------------

lags = range(1, 97)

autocorrelations = [
    demand_15min["Ride_Count"].autocorr(lag=i)
    for i in lags
]

plt.figure(figsize=(14, 6))

plt.plot(
    list(lags),
    autocorrelations,
    marker="."
)

plt.axhline(0, linestyle="--")

plt.title("15-Minute Demand Autocorrelation")
plt.xlabel("Lag (15-minute intervals)")
plt.ylabel("Autocorrelation")

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "22_autocorrelation.png"),
    dpi=300
)

plt.show()


# ------------------------------------------------------------
# 32. ZONE DEMAND VARIABILITY
# ------------------------------------------------------------

zone_stats = (
    df.groupby("Pickup_Zone")
      .agg(
          Total_Rides=("Request_ID", "count"),
          Mean_Distance=("Ride_Distance_KM", "mean"),
          Std_Distance=("Ride_Distance_KM", "std")
      )
      .reset_index()
)

zone_stats["Demand_Share"] = (
    zone_stats["Total_Rides"] /
    zone_stats["Total_Rides"].sum()
)

zone_stats = zone_stats.sort_values(
    "Total_Rides",
    ascending=False
)

zone_stats.to_csv(
    os.path.join(OUTPUT_DIR, "16_zone_statistics.csv"),
    index=False
)

print("\nZone statistics:")
print(zone_stats.head(20))


# ------------------------------------------------------------
# 33. TOP 10% ZONE CONCENTRATION
# ------------------------------------------------------------

zone_sorted = zone_stats.sort_values(
    "Total_Rides",
    ascending=False
)

n_top = max(1, int(len(zone_sorted) * 0.10))

top_10_share = (
    zone_sorted.head(n_top)["Total_Rides"].sum()
    / zone_sorted["Total_Rides"].sum()
)

print(
    f"\nTop 10% zones account for "
    f"{top_10_share * 100:.2f}% of all rides."
)


# ------------------------------------------------------------
# 34. HOURLY × ZONE VARIABILITY
# ------------------------------------------------------------

hour_zone_stats = (
    df.groupby(["Pickup_Zone", "Hour_Calc"])
      .size()
      .reset_index(name="Demand")
)

zone_hour_variability = (
    hour_zone_stats.groupby("Pickup_Zone")["Demand"]
                   .agg(["mean", "std", "min", "max"])
)

zone_hour_variability["CV"] = (
    zone_hour_variability["std"] /
    zone_hour_variability["mean"]
)

zone_hour_variability = (
    zone_hour_variability
    .sort_values("CV", ascending=False)
)

zone_hour_variability.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "17_zone_hour_variability.csv"
    )
)


# ------------------------------------------------------------
# 35. FINAL DATASET SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("FINAL DATASET SUMMARY")
print("=" * 70)

print(f"Total rides              : {len(df):,}")
print(f"Number of pickup zones   : {df['Pickup_Zone_ID'].nunique()}")
print(f"Number of drop zones     : {df['Drop_Zone_ID'].nunique()}")
print(f"Date range               : {df['Timestamp'].min()} → {df['Timestamp'].max()}")
print(f"Vehicle types            : {df['Vehicle_Type'].nunique()}")
print(f"Weather categories       : {df['Weather'].nunique()}")
print(f"Event categories         : {df['Event_Flag'].nunique()}")

print("\nEDA completed.")

print("\nAll results saved to:")
print(OUTPUT_DIR)

print("=" * 70)