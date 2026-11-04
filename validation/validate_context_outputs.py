import pandas as pd

original = pd.read_csv("synthetic_bengaluru_rides.csv")
contextual = pd.read_csv("rides_contextual_synthetic.csv")
weather = pd.read_csv("weather_data.csv")
events = pd.read_csv("bengaluru_events.csv")
impacts = pd.read_csv("event_impact_by_hour.csv")

original["Timestamp"] = pd.to_datetime(original["Timestamp"])
contextual["Timestamp"] = pd.to_datetime(contextual["Timestamp"])
weather["Timestamp"] = pd.to_datetime(weather["Timestamp"])
events["Start_Time"] = pd.to_datetime(events["Start_Time"])
events["End_Time"] = pd.to_datetime(events["End_Time"])

print("\n--- RIDE VALIDATION ---")
print("Original rows:", len(original))
print("Contextual rows:", len(contextual))
print("Additional rows:", len(contextual) - len(original))
print("Percentage increase:",
      round((len(contextual) - len(original)) / len(original) * 100, 4))
print("Unique contextual Request IDs:",
      contextual["Request_ID"].nunique())
print("Contextual duplicate IDs:",
      contextual["Request_ID"].duplicated().sum())
print("Original IDs preserved:",
      original["Request_ID"].isin(
          contextual["Request_ID"]
      ).all())

print("\n--- WEATHER VALIDATION ---")
expected_hours = int(
    (original["Timestamp"].max().floor("h")
     - original["Timestamp"].min().floor("h")
    ).total_seconds() / 3600
) + 1

print("Expected hourly records:", expected_hours)
print("Actual weather records:", len(weather))
print("Duplicate weather timestamps:",
      weather["Timestamp"].duplicated().sum())
print("Weather distribution:")
print(weather["Weather"].value_counts())
print("Rain intensity range:")
print(weather["Rain_Intensity"].describe())

print("\n--- EVENT VALIDATION ---")
print("Total events:", len(events))
print("Total event impact rows:", len(impacts))
print("Unique affected zones:", impacts["Pickup_Zone_ID"].nunique())
print("Event duration in hours:")
print(
    (events["End_Time"] - events["Start_Time"])
    .dt.total_seconds()
    .div(3600)
    .describe()
)

print("\nEvents by type:")
print(events["Event_Type"].value_counts())

print("\n--- ADDED EVENT RIDES ---")
event_types = ["Sports", "Concert", "Festival", "Exhibition"]

new_rows = contextual[
    contextual["Event_Flag"].isin(event_types)
]

print("Event-tagged ride records, including original rides:",
      len(new_rows))
print("Event-tagged records by type:")
print(new_rows["Event_Flag"].value_counts())

print("\n--- EVENT IMPACT COVERAGE ---")
days = (
    original["Timestamp"].max().date()
    - original["Timestamp"].min().date()
).days + 1

total_zone_hours = original["Pickup_Zone_ID"].nunique() * days * 24

print("Total zone-hour combinations:", total_zone_hours)
print("Affected zone-hours:", len(impacts))
print(
    "Affected percentage:",
    round(len(impacts) / total_zone_hours * 100, 4)
)