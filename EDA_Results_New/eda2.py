import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================
# 1. PATHS
# ============================================================

file_path = r"C:\Users\lalwa\Desktop\SPA EL\Bookings_data.xlsx"

output_dir = r"C:\Users\lalwa\Desktop\SPA EL\EDA_Results"

os.makedirs(output_dir, exist_ok=True)


# ============================================================
# 2. LOAD DATA
# ============================================================

df = pd.read_excel(file_path)

print("=" * 70)
print("DATASET LOADED")
print("=" * 70)

print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns)}")


# ============================================================
# 3. CREATE TIMESTAMP
# ============================================================

df["Timestamp"] = pd.to_datetime(
    df["Date"].astype(str) + " " + df["Time"].astype(str),
    errors="coerce"
)

df = df.dropna(subset=["Timestamp"])

df["Hour"] = df["Timestamp"].dt.hour
df["DayOfWeek"] = df["Timestamp"].dt.day_name()


# ============================================================
# 4. FIND TOP PICKUP LOCATIONS
# ============================================================

top_locations = (
    df["Pickup_Location"]
    .value_counts()
    .head(20)
    .index
    .tolist()
)

print("\n" + "=" * 70)
print("TOP 20 PICKUP LOCATIONS")
print("=" * 70)

for i, location in enumerate(top_locations, 1):
    print(f"{i:2}. {location}")


# ============================================================
# 5. FILTER TO TOP 20 LOCATIONS
# ============================================================

top_df = df[
    df["Pickup_Location"].isin(top_locations)
].copy()


# ============================================================
# 6. HOURLY DEMAND BY LOCATION
# ============================================================

hourly_location = (
    top_df
    .groupby(["Pickup_Location", "Hour"])
    .size()
    .reset_index(name="Bookings")
)

# Save raw results
hourly_location.to_csv(
    os.path.join(
        output_dir,
        "hourly_demand_by_location.csv"
    ),
    index=False
)


# ============================================================
# 7. CREATE HOURLY × LOCATION MATRIX
# ============================================================

hourly_matrix = (
    hourly_location
    .pivot(
        index="Pickup_Location",
        columns="Hour",
        values="Bookings"
    )
    .fillna(0)
)

# Ensure all 24 hours exist
hourly_matrix = hourly_matrix.reindex(
    columns=range(24),
    fill_value=0
)

# Save matrix
hourly_matrix.to_csv(
    os.path.join(
        output_dir,
        "hourly_location_matrix.csv"
    )
)


# ============================================================
# 8. HEATMAP — RAW DEMAND
# ============================================================

plt.figure(figsize=(16, 10))

sns.heatmap(
    hourly_matrix,
    cmap="YlOrRd",
    annot=False,
    linewidths=0.2
)

plt.title(
    "Hourly Ride Demand by Pickup Location",
    fontsize=16
)

plt.xlabel("Hour of Day")
plt.ylabel("Pickup Location")

plt.xticks(
    range(24),
    range(24)
)

plt.tight_layout()

plt.savefig(
    os.path.join(
        output_dir,
        "13_hourly_demand_location_heatmap.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 9. NORMALIZED HOURLY DEMAND
# ============================================================
#
# Why?
#
# Banashankari may have 2200 total rides
# another location may have 2000.
#
# Raw counts can hide the shape of the pattern.
#
# We therefore calculate:
#
#     Hourly demand / total demand of location
#
# This lets us compare the SHAPE of demand.
# ============================================================

normalized_matrix = hourly_matrix.div(
    hourly_matrix.sum(axis=1),
    axis=0
)

# Convert to percentage
normalized_matrix = normalized_matrix * 100

normalized_matrix.to_csv(
    os.path.join(
        output_dir,
        "normalized_hourly_location_matrix.csv"
    )
)


# ============================================================
# 10. NORMALIZED HEATMAP
# ============================================================

plt.figure(figsize=(16, 10))

sns.heatmap(
    normalized_matrix,
    cmap="YlOrRd",
    annot=False,
    linewidths=0.2
)

plt.title(
    "Normalized Hourly Demand Pattern by Pickup Location",
    fontsize=16
)

plt.xlabel("Hour of Day")
plt.ylabel("Pickup Location")

plt.xticks(
    range(24),
    range(24)
)

plt.tight_layout()

plt.savefig(
    os.path.join(
        output_dir,
        "14_normalized_hourly_location_heatmap.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 11. TOP LOCATIONS — LINE CHART
# ============================================================

# Select 6 representative locations
selected_locations = top_locations[:6]

selected_df = hourly_location[
    hourly_location["Pickup_Location"]
    .isin(selected_locations)
].copy()


plt.figure(figsize=(14, 7))

sns.lineplot(
    data=selected_df,
    x="Hour",
    y="Bookings",
    hue="Pickup_Location",
    marker="o"
)

plt.title(
    "Hourly Demand Patterns for Top Pickup Locations",
    fontsize=16
)

plt.xlabel("Hour of Day")
plt.ylabel("Number of Bookings")

plt.xticks(range(24))

plt.legend(
    title="Pickup Location",
    bbox_to_anchor=(1.02, 1),
    loc="upper left"
)

plt.tight_layout()

plt.savefig(
    os.path.join(
        output_dir,
        "15_hourly_demand_top_locations.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 12. DAY OF WEEK × LOCATION
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

day_location = (
    top_df
    .groupby(["Pickup_Location", "DayOfWeek"])
    .size()
    .reset_index(name="Bookings")
)

day_location_matrix = (
    day_location
    .pivot(
        index="Pickup_Location",
        columns="DayOfWeek",
        values="Bookings"
    )
    .fillna(0)
)

day_location_matrix = day_location_matrix.reindex(
    columns=day_order
)

day_location_matrix.to_csv(
    os.path.join(
        output_dir,
        "day_of_week_location_matrix.csv"
    )
)


# ============================================================
# 13. DAY × LOCATION HEATMAP
# ============================================================

plt.figure(figsize=(14, 9))

sns.heatmap(
    day_location_matrix,
    cmap="YlOrRd",
    annot=True,
    fmt=".0f",
    linewidths=0.2
)

plt.title(
    "Ride Demand by Pickup Location and Day of Week",
    fontsize=16
)

plt.xlabel("Day of Week")
plt.ylabel("Pickup Location")

plt.tight_layout()

plt.savefig(
    os.path.join(
        output_dir,
        "16_day_location_heatmap.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 14. CALCULATE TEMPORAL VARIABILITY
# ============================================================

variability_results = []

for location in top_locations:

    location_data = hourly_matrix.loc[location]

    mean_demand = location_data.mean()
    std_demand = location_data.std()

    coefficient_variation = (
        std_demand / mean_demand
        if mean_demand != 0
        else 0
    )

    variability_results.append({
        "Pickup_Location": location,
        "Mean_Hourly_Demand": mean_demand,
        "Std_Hourly_Demand": std_demand,
        "Coefficient_of_Variation": coefficient_variation
    })


variability_df = pd.DataFrame(
    variability_results
)

variability_df = variability_df.sort_values(
    "Coefficient_of_Variation",
    ascending=False
)

print("\n" + "=" * 70)
print("TEMPORAL VARIABILITY BY LOCATION")
print("=" * 70)

print(variability_df)

variability_df.to_csv(
    os.path.join(
        output_dir,
        "location_temporal_variability.csv"
    ),
    index=False
)


# ============================================================
# 15. OVERALL RESULT
# ============================================================

print("\n" + "=" * 70)
print("EDA COMPLETED")
print("=" * 70)

print("\nFiles generated:")

files = [
    "hourly_demand_by_location.csv",
    "hourly_location_matrix.csv",
    "normalized_hourly_location_matrix.csv",
    "13_hourly_demand_location_heatmap.png",
    "14_normalized_hourly_location_heatmap.png",
    "15_hourly_demand_top_locations.png",
    "day_of_week_location_matrix.csv",
    "16_day_location_heatmap.png",
    "location_temporal_variability.csv"
]

for file in files:
    print(" -", file)

print("\nSaved to:")
print(output_dir)