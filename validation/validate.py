import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def validate_dataset(file_path):
    print("Loading data for validation... (this might take a moment for 2.2M rows)")
    df = pd.read_csv(file_path)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df.set_index('Timestamp', inplace=True)

    # Plot 1: Overall Hourly Demand (Check Condition A)
    plt.figure(figsize=(10, 4))
    df.groupby('Hour').size().plot(kind='bar', color='steelblue')
    plt.title("1. Overall Demand by Hour of Day (Non-uniform)")
    plt.ylabel("Ride Requests")
    plt.show()

    # Plot 2: Demand by Day of Week (Check Condition D)
    plt.figure(figsize=(8, 4))
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    df.groupby('Day_of_Week').size().plot(kind='bar', color='coral')
    plt.title("2. Demand by Day of Week")
    plt.xticks(ticks=range(7), labels=days, rotation=0)
    plt.show()

    # Plot 3: Zone Archetype Temporal Behavior (Check Conditions B, C, F)
    # We will pick 3 distinct zones to show different curves
    plt.figure(figsize=(12, 5))
    sample_zones = ['Whitefield', 'Jayanagar', 'Indiranagar']
    for zone in sample_zones:
        zone_data = df[df['Pickup_Zone'] == zone].groupby('Hour').size()
        plt.plot(zone_data.index, zone_data.values, label=zone, marker='o')
    plt.title("3. Distinct Hourly Patterns by Zone (IT vs Res vs Nightlife)")
    plt.xlabel("Hour of Day")
    plt.ylabel("Rides")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()

    # Plot 4: Temporal Autocorrelation (Check Condition E, I)
    plt.figure(figsize=(10, 4))
    # Resample to 1-hour total demand
    ts_demand = df.resample('1h').size()
    pd.plotting.autocorrelation_plot(ts_demand.head(24*14)) # Show 2 weeks
    plt.title("4. Temporal Autocorrelation (1-hour windows over 2 weeks)")
    plt.show()

    # Plot 5: Zone x Hour Heatmap
    plt.figure(figsize=(14, 10))
    pivot = df.pivot_table(index='Pickup_Zone', columns='Hour', aggfunc='size', fill_value=0)
    # Row normalize to show behavior independent of volume
    pivot_norm = pivot.div(pivot.max(axis=1), axis=0)
    sns.heatmap(pivot_norm, cmap="YlGnBu", cbar_kws={'label': 'Normalized Demand'})
    plt.title("5. Normalized Zone x Hour Heatmap")
    plt.show()

if __name__ == "__main__":
    validate_dataset("synthetic_bengaluru_rides.csv")