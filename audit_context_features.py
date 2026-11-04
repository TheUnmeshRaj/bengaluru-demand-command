import pandas as pd

df = pd.read_csv(
    "zone_demand_5min.csv",
    low_memory=False
)

print("\n--- WEATHER VALUES ---")
print(
    df["Weather_Condition"]
    .value_counts(dropna=False)
)

print("\n--- EVENT TYPES ---")
print(
    df["Event_Type"]
    .value_counts(dropna=False)
)

print("\n--- EVENT PHASES ---")
print(
    df["Event_Phase"]
    .value_counts(dropna=False)
)

print("\n--- EVENT IMPACT VS EVENT TYPE ---")
print(
    pd.crosstab(
        df["Event_Impact"],
        df["Event_Type"],
        dropna=False
    )
)

print("\n--- EVENT IMPACT VS EVENT PHASE ---")
print(
    pd.crosstab(
        df["Event_Impact"],
        df["Event_Phase"],
        dropna=False
    )
)

print("\n--- MISSING CONTEXT VALUES ---")

columns = [
    "Weather_Condition",
    "Rain_Intensity",
    "Event_Impact",
    "Event_Active",
    "Event_Type",
    "Event_Phase",
    "Event_Intensity"
]

print(
    df[columns].isna().sum()
)

print("\n--- EVENT-AFFECTED DATA SHARE ---")

print(
    df.groupby("Event_Impact")["Target_Next_15min"]
    .agg(["count", "mean", "median", "std"])
)