import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================
# 1. PATHS
# ============================================================

file_path = r"C:\Users\lalwa\Desktop\SPA EL\Bookings_data.xlsx"

# Create output folder
output_dir = r"C:\Users\lalwa\Desktop\SPA EL\EDA_Results"
os.makedirs(output_dir, exist_ok=True)

print("=" * 70)
print("OUTPUT FOLDER")
print("=" * 70)
print(output_dir)


# ============================================================
# 2. LOAD DATASET
# ============================================================

df = pd.read_excel(file_path)

print("\n" + "=" * 70)
print("DATASET LOADED")
print("=" * 70)

print(f"Rows    : {df.shape[0]:,}")
print(f"Columns : {df.shape[1]}")

print("\nColumn names:")
print(df.columns.tolist())


# ============================================================
# 3. BASIC INFORMATION
# ============================================================

print("\n" + "=" * 70)
print("DATA TYPES")
print("=" * 70)

print(df.dtypes)

df.dtypes.astype(str).to_csv(
    os.path.join(output_dir, "data_types.csv")
)


# ============================================================
# 4. FIRST / LAST ROWS
# ============================================================

print("\nFIRST 5 ROWS")
print(df.head())

print("\nLAST 5 ROWS")
print(df.tail())


# ============================================================
# 5. MISSING VALUES
# ============================================================

missing = df.isnull().sum()

missing_table = pd.DataFrame({
    "Missing_Count": missing,
    "Missing_Percentage": (missing / len(df)) * 100
})

missing_table = missing_table.sort_values(
    "Missing_Count",
    ascending=False
)

print("\n" + "=" * 70)
print("MISSING VALUES")
print("=" * 70)

print(missing_table)

missing_table.to_csv(
    os.path.join(output_dir, "missing_values.csv")
)


# ============================================================
# 6. DUPLICATES
# ============================================================

duplicate_count = df.duplicated().sum()

print("\n" + "=" * 70)
print("DUPLICATES")
print("=" * 70)

print(f"Duplicate rows: {duplicate_count:,}")


# ============================================================
# 7. UNIQUE VALUES
# ============================================================

unique_values = pd.DataFrame({
    "Column": df.columns,
    "Unique_Values": [
        df[column].nunique()
        for column in df.columns
    ]
})

print("\n" + "=" * 70)
print("UNIQUE VALUES")
print("=" * 70)

print(unique_values)

unique_values.to_csv(
    os.path.join(output_dir, "unique_values.csv"),
    index=False
)


# ============================================================
# 8. CREATE TIMESTAMP
# ============================================================

df["Timestamp"] = pd.to_datetime(
    df["Date"].astype(str) + " " + df["Time"].astype(str),
    errors="coerce"
)

invalid_timestamps = df["Timestamp"].isna().sum()

print("\n" + "=" * 70)
print("TIMESTAMP")
print("=" * 70)

print("Invalid timestamps:", invalid_timestamps)

print("Minimum:", df["Timestamp"].min())
print("Maximum:", df["Timestamp"].max())


# ============================================================
# 9. TIME FEATURES
# ============================================================

df["Hour"] = df["Timestamp"].dt.hour
df["Day"] = df["Timestamp"].dt.day
df["DayOfWeek"] = df["Timestamp"].dt.day_name()
df["WeekdayNumber"] = df["Timestamp"].dt.dayofweek
df["IsWeekend"] = df["WeekdayNumber"] >= 5

df["DateOnly"] = df["Timestamp"].dt.date


# ============================================================
# 10. BOOKING STATUS
# ============================================================

booking_status = (
    df["Booking_Status"]
    .value_counts()
    .reset_index()
)

booking_status.columns = [
    "Booking_Status",
    "Bookings"
]

booking_status["Percentage"] = (
    booking_status["Bookings"] /
    booking_status["Bookings"].sum() * 100
)

print("\n" + "=" * 70)
print("BOOKING STATUS")
print("=" * 70)

print(booking_status)

booking_status.to_csv(
    os.path.join(output_dir, "booking_status.csv"),
    index=False
)


# ---------------- GRAPH ----------------

plt.figure(figsize=(9, 6))

sns.barplot(
    data=booking_status,
    x="Booking_Status",
    y="Bookings"
)

plt.title("Booking Status Distribution")
plt.xlabel("Booking Status")
plt.ylabel("Number of Bookings")
plt.xticks(rotation=30)

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "01_booking_status.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 11. VEHICLE TYPE
# ============================================================

vehicle_type = (
    df["Vehicle_Type"]
    .value_counts()
    .reset_index()
)

vehicle_type.columns = [
    "Vehicle_Type",
    "Bookings"
]

print("\n" + "=" * 70)
print("VEHICLE TYPE")
print("=" * 70)

print(vehicle_type)

vehicle_type.to_csv(
    os.path.join(output_dir, "vehicle_type.csv"),
    index=False
)


plt.figure(figsize=(10, 6))

sns.barplot(
    data=vehicle_type,
    x="Vehicle_Type",
    y="Bookings"
)

plt.title("Bookings by Vehicle Type")
plt.xlabel("Vehicle Type")
plt.ylabel("Number of Bookings")
plt.xticks(rotation=30)

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "02_vehicle_type.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 12. PICKUP LOCATION DEMAND
# ============================================================

pickup_demand = (
    df["Pickup_Location"]
    .value_counts()
    .reset_index()
)

pickup_demand.columns = [
    "Pickup_Location",
    "Bookings"
]

print("\n" + "=" * 70)
print("TOP PICKUP LOCATIONS")
print("=" * 70)

print(pickup_demand.head(20))

pickup_demand.to_csv(
    os.path.join(output_dir, "pickup_location_demand.csv"),
    index=False
)


# ---------------- GRAPH ----------------

top_pickups = pickup_demand.head(20)

plt.figure(figsize=(12, 8))

sns.barplot(
    data=top_pickups,
    x="Bookings",
    y="Pickup_Location"
)

plt.title("Top 20 Pickup Locations by Ride Demand")
plt.xlabel("Number of Bookings")
plt.ylabel("Pickup Location")

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "03_top_pickup_locations.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 13. DROP LOCATION DEMAND
# ============================================================

drop_demand = (
    df["Drop_Location"]
    .value_counts()
    .reset_index()
)

drop_demand.columns = [
    "Drop_Location",
    "Bookings"
]

drop_demand.to_csv(
    os.path.join(output_dir, "drop_location_demand.csv"),
    index=False
)


# ============================================================
# 14. HOURLY DEMAND
# ============================================================

hourly_demand = (
    df.groupby("Hour")
    .size()
    .reset_index(name="Bookings")
)

print("\n" + "=" * 70)
print("HOURLY DEMAND")
print("=" * 70)

print(hourly_demand)

hourly_demand.to_csv(
    os.path.join(output_dir, "hourly_demand.csv"),
    index=False
)


plt.figure(figsize=(12, 6))

sns.barplot(
    data=hourly_demand,
    x="Hour",
    y="Bookings"
)

plt.title("Ride Demand by Hour of Day")
plt.xlabel("Hour of Day")
plt.ylabel("Number of Bookings")
plt.xticks(range(24))

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "04_hourly_demand.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 15. DAY OF WEEK DEMAND
# ============================================================

day_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

day_demand = (
    df.groupby("DayOfWeek")
    .size()
    .reindex(day_order)
    .reset_index()
)

day_demand.columns = [
    "DayOfWeek",
    "Bookings"
]

print("\n" + "=" * 70)
print("DEMAND BY DAY OF WEEK")
print("=" * 70)

print(day_demand)

day_demand.to_csv(
    os.path.join(output_dir, "day_of_week_demand.csv"),
    index=False
)


plt.figure(figsize=(10, 6))

sns.barplot(
    data=day_demand,
    x="DayOfWeek",
    y="Bookings"
)

plt.title("Ride Demand by Day of Week")
plt.xlabel("Day")
plt.ylabel("Number of Bookings")
plt.xticks(rotation=30)

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "05_day_of_week_demand.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 16. WEEKDAY VS WEEKEND
# ============================================================

weekend_demand = (
    df.groupby("IsWeekend")
    .size()
    .reset_index(name="Bookings")
)

weekend_demand["DayType"] = weekend_demand["IsWeekend"].map({
    False: "Weekday",
    True: "Weekend"
})

print("\n" + "=" * 70)
print("WEEKDAY VS WEEKEND")
print("=" * 70)

print(weekend_demand)

weekend_demand.to_csv(
    os.path.join(output_dir, "weekday_vs_weekend.csv"),
    index=False
)


plt.figure(figsize=(8, 6))

sns.barplot(
    data=weekend_demand,
    x="DayType",
    y="Bookings"
)

plt.title("Weekday vs Weekend Ride Demand")
plt.xlabel("")
plt.ylabel("Number of Bookings")

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "06_weekday_vs_weekend.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 17. HOURLY DEMAND: WEEKDAY VS WEEKEND
# ============================================================

hour_weekend = (
    df.groupby(["Hour", "IsWeekend"])
    .size()
    .reset_index(name="Bookings")
)

hour_weekend["DayType"] = hour_weekend["IsWeekend"].map({
    False: "Weekday",
    True: "Weekend"
})

hour_weekend.to_csv(
    os.path.join(output_dir, "hourly_weekday_vs_weekend.csv"),
    index=False
)


plt.figure(figsize=(12, 6))

sns.lineplot(
    data=hour_weekend,
    x="Hour",
    y="Bookings",
    hue="DayType",
    marker="o"
)

plt.title("Hourly Ride Demand: Weekday vs Weekend")
plt.xlabel("Hour of Day")
plt.ylabel("Number of Bookings")
plt.xticks(range(24))

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "07_hourly_weekday_vs_weekend.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 18. DAILY DEMAND
# ============================================================

daily_demand = (
    df.groupby("DateOnly")
    .size()
    .reset_index(name="Bookings")
)

daily_demand.to_csv(
    os.path.join(output_dir, "daily_demand.csv"),
    index=False
)


plt.figure(figsize=(14, 6))

plt.plot(
    daily_demand["DateOnly"],
    daily_demand["Bookings"],
    marker="o"
)

plt.title("Daily Ride Demand")
plt.xlabel("Date")
plt.ylabel("Number of Bookings")
plt.xticks(rotation=45)

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "08_daily_demand.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 19. 5-MINUTE DEMAND
# ============================================================

df["5_Minute_Window"] = df["Timestamp"].dt.floor("5min")

demand_5min = (
    df.groupby(
        ["5_Minute_Window", "Pickup_Location"]
    )
    .size()
    .reset_index(name="Demand")
)

demand_5min.to_csv(
    os.path.join(output_dir, "demand_5min_by_location.csv"),
    index=False
)

print("\n" + "=" * 70)
print("5-MINUTE DEMAND")
print("=" * 70)

print(demand_5min.head(20))


# ============================================================
# 20. OVERALL 5-MINUTE DEMAND
# ============================================================

overall_5min = (
    df.groupby("5_Minute_Window")
    .size()
    .reset_index(name="Bookings")
)

overall_5min.to_csv(
    os.path.join(output_dir, "overall_5min_demand.csv"),
    index=False
)


plt.figure(figsize=(14, 6))

plt.plot(
    overall_5min["5_Minute_Window"],
    overall_5min["Bookings"]
)

plt.title("Ride Demand in 5-Minute Windows")
plt.xlabel("Time")
plt.ylabel("Number of Bookings")

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "09_5min_demand.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 21. WINDOW COMPARISON
# ============================================================

window_results = []

for window in ["5min", "15min", "30min"]:

    temp = (
        df.set_index("Timestamp")
        .resample(window)
        .size()
    )

    window_results.append({
        "Window": window,
        "Mean_Bookings": temp.mean(),
        "Median_Bookings": temp.median(),
        "Minimum_Bookings": temp.min(),
        "Maximum_Bookings": temp.max(),
        "Zero_Windows": (temp == 0).sum(),
        "Total_Windows": len(temp)
    })


window_comparison = pd.DataFrame(window_results)

print("\n" + "=" * 70)
print("WINDOW COMPARISON")
print("=" * 70)

print(window_comparison)

window_comparison.to_csv(
    os.path.join(output_dir, "window_comparison.csv"),
    index=False
)


# ============================================================
# 22. RIDE DISTANCE DISTRIBUTION
# ============================================================

plt.figure(figsize=(10, 6))

sns.histplot(
    df["Ride_Distance"].dropna(),
    bins=50,
    kde=True
)

plt.title("Distribution of Ride Distance")
plt.xlabel("Ride Distance")
plt.ylabel("Frequency")

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "10_ride_distance_distribution.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 23. BOOKING VALUE DISTRIBUTION
# ============================================================

plt.figure(figsize=(10, 6))

sns.histplot(
    df["Booking_Value"].dropna(),
    bins=50,
    kde=True
)

plt.title("Distribution of Booking Value")
plt.xlabel("Booking Value")
plt.ylabel("Frequency")

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "11_booking_value_distribution.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 24. CORRELATION MATRIX
# ============================================================

numeric_columns = df.select_dtypes(
    include="number"
).columns

correlation_matrix = df[numeric_columns].corr()

correlation_matrix.to_csv(
    os.path.join(output_dir, "correlation_matrix.csv")
)


plt.figure(figsize=(12, 9))

sns.heatmap(
    correlation_matrix,
    annot=True,
    fmt=".2f",
    cmap="coolwarm"
)

plt.title("Correlation Matrix")

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "12_correlation_matrix.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 25. NUMERICAL SUMMARY
# ============================================================

numerical_summary = df.describe(
    include="number"
).T

numerical_summary.to_csv(
    os.path.join(output_dir, "numerical_summary.csv")
)


# ============================================================
# 26. FINAL SUMMARY
# ============================================================

summary = {
    "Total Records": len(df),
    "Total Columns": len(df.columns),
    "Unique Pickup Locations": df["Pickup_Location"].nunique(),
    "Unique Drop Locations": df["Drop_Location"].nunique(),
    "Unique Vehicle Types": df["Vehicle_Type"].nunique(),
    "Minimum Timestamp": df["Timestamp"].min(),
    "Maximum Timestamp": df["Timestamp"].max(),
    "Duplicate Rows": duplicate_count,
    "Invalid Timestamps": invalid_timestamps
}

summary_df = pd.DataFrame(
    summary.items(),
    columns=["Metric", "Value"]
)

summary_df.to_csv(
    os.path.join(output_dir, "eda_summary.csv"),
    index=False
)


# ============================================================
# 27. SAVE PROCESSED DATASET
# ============================================================

# This saves the dataset with the newly created time features.
# The original Excel file is NOT modified.

processed_path = os.path.join(
    output_dir,
    "Bookings_data_with_features.csv"
)

df.to_csv(
    processed_path,
    index=False
)


# ============================================================
# 28. FINISHED
# ============================================================

print("\n" + "=" * 70)
print("EDA COMPLETED")
print("=" * 70)

print(f"\nAll graphs and results saved to:")
print(output_dir)

print("\nGenerated graph files:")

for file in sorted(os.listdir(output_dir)):

    if file.endswith(".png"):
        print("  -", file)

print("\nGenerated CSV files:")

for file in sorted(os.listdir(output_dir)):

    if file.endswith(".csv"):
        print("  -", file)

print("\nOriginal dataset was NOT modified.")