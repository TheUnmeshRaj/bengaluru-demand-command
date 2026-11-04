import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# ==========================================
# CONFIGURATION
# ==========================================
START_DATE = "2026-07-01"
NUM_DAYS = 60
RANDOM_SEED = 42
BASE_DEMAND_SCALE = 1.0 # Increase to generate more rows
OUTPUT_FILE = "synthetic_bengaluru_rides.csv"

np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

# ==========================================
# ZONE DEFINITIONS
# ==========================================
zone_data = [
    # IT/Office
    ("Z01", "Whitefield", "IT/Office", 40), ("Z02", "Electronic City", "IT/Office", 35),
    ("Z03", "Manyata Tech Park", "IT/Office", 30), ("Z04", "Bellandur", "IT/Office", 35),
    ("Z05", "Marathahalli", "IT/Office", 30), ("Z06", "Mahadevapura", "IT/Office", 25),
    ("Z07", "ITPL", "IT/Office", 25), ("Z08", "Silk Board", "IT/Office", 30),
    ("Z09", "RMZ Ecospace", "IT/Office", 25),
    # Residential
    ("Z10", "Jayanagar", "Residential", 25), ("Z11", "Banashankari", "Residential", 20),
    ("Z12", "BTM Layout", "Residential", 30), ("Z13", "HSR Layout", "Residential", 35),
    ("Z14", "JP Nagar", "Residential", 20), ("Z15", "Malleshwaram", "Residential", 15),
    ("Z16", "Basavanagudi", "Residential", 15), ("Z17", "Rajajinagar", "Residential", 20),
    ("Z18", "Sahakarnagar", "Residential", 10), ("Z19", "Yelahanka", "Residential", 15),
    ("Z20", "Vidyaranyapura", "Residential", 10), ("Z21", "RR Nagar", "Residential", 15),
    ("Z22", "Kengeri", "Residential", 10), ("Z23", "Padmanabhanagar", "Residential", 10),
    ("Z24", "Sadashivanagar", "Residential", 5), ("Z25", "Vijayanagar", "Residential", 20),
    ("Z26", "Sanjaynagar", "Residential", 15), ("Z27", "Kammanahalli", "Residential", 20),
    ("Z28", "HBR Layout", "Residential", 15), ("Z29", "RT Nagar", "Residential", 15),
    # Commercial/Nightlife
    ("Z30", "Indiranagar", "Nightlife", 45), ("Z31", "Koramangala", "Nightlife", 45),
    ("Z32", "MG Road", "Nightlife", 35), ("Z33", "Brigade Road", "Nightlife", 30),
    ("Z34", "Commercial Street", "Nightlife", 25), ("Z35", "Church Street", "Nightlife", 25),
    ("Z36", "UB City", "Nightlife", 15), ("Z37", "New BEL Road", "Nightlife", 20),
    # Transit
    ("Z38", "Majestic (KBS)", "Transit", 50), ("Z39", "Yeshwanthpur", "Transit", 30),
    ("Z40", "Cantonment", "Transit", 15), ("Z41", "KSR Bengaluru", "Transit", 40),
    ("Z42", "KR Market", "Transit", 35), ("Z43", "Shantinagar TTMC", "Transit", 20),
    ("Z44", "Shivajinagar", "Transit", 25), ("Z45", "KR Puram Rly Station", "Transit", 30),
    # Airport/Travel
    ("Z46", "KIAL Airport", "Airport", 40), ("Z47", "Hebbal", "Airport", 20),
    ("Z48", "Devanahalli", "Airport", 10),
    # Industrial
    ("Z49", "Peenya", "Industrial", 20), ("Z50", "Bommasandra", "Industrial", 15),
    ("Z51", "Rajajinagar Ind", "Industrial", 10), ("Z52", "Hoskote", "Industrial", 10)
]
df_zones = pd.DataFrame(zone_data, columns=["Zone_ID", "Zone_Name", "Archetype", "Base_Volume"])
df_zones["Base_Volume"] = df_zones["Base_Volume"] * BASE_DEMAND_SCALE

# ==========================================
# TEMPORAL PROFILES
# ==========================================
hourly_profiles = {
    "IT/Office":   [0.1, 0.1, 0.05, 0.05, 0.1, 0.3, 0.8, 1.5, 2.5, 2.8, 1.8, 1.0, 0.9, 0.9, 1.0, 1.2, 1.8, 2.5, 2.8, 2.0, 1.2, 0.8, 0.4, 0.2],
    "Residential": [0.2, 0.1, 0.1, 0.1, 0.2, 0.5, 1.2, 2.0, 2.2, 1.5, 1.0, 0.8, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0, 2.2, 1.8, 1.2, 0.8, 0.5, 0.3],
    "Nightlife":   [1.5, 1.0, 0.5, 0.2, 0.1, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5, 1.6, 1.5, 1.6, 1.8, 2.2, 2.8, 3.2, 3.5, 3.0, 2.5, 2.0],
    "Transit":     [0.5, 0.4, 0.3, 0.5, 1.2, 1.8, 2.0, 1.8, 1.5, 1.2, 1.0, 1.0, 1.0, 1.0, 1.2, 1.5, 1.8, 2.0, 1.8, 1.5, 1.2, 1.0, 0.8, 0.6],
    "Airport":     [1.2, 1.0, 0.8, 1.5, 2.0, 1.8, 1.5, 1.2, 1.0, 1.0, 1.0, 1.2, 1.5, 1.5, 1.2, 1.0, 1.2, 1.5, 1.8, 2.0, 1.8, 1.5, 1.5, 1.2],
    "Industrial":  [0.2, 0.1, 0.1, 0.2, 0.5, 1.5, 2.5, 1.5, 1.0, 0.8, 0.8, 0.8, 0.8, 1.0, 1.2, 1.5, 2.5, 1.8, 1.0, 0.6, 0.4, 0.3, 0.2, 0.2]
}

dow_profiles = {
    "IT/Office":   [1.1, 1.2, 1.2, 1.2, 1.1, 0.4, 0.3],
    "Residential": [1.0, 1.0, 1.0, 1.0, 1.1, 1.3, 1.2],
    "Nightlife":   [0.7, 0.8, 0.9, 1.0, 1.5, 1.8, 1.4],
    "Transit":     [1.1, 1.0, 1.0, 1.0, 1.2, 1.3, 1.2],
    "Airport":     [1.2, 1.0, 1.0, 1.0, 1.3, 1.4, 1.3],
    "Industrial":  [1.2, 1.2, 1.2, 1.2, 1.1, 0.6, 0.2]
}

def generate_dataset():
    print(f"Generating synthetic demand for {NUM_DAYS} days across {len(df_zones)} zones...")
    
    time_idx = pd.date_range(start=START_DATE, periods=NUM_DAYS * 24, freq="h")
    records = []
    
    zone_ids = df_zones['Zone_ID'].values
    latent_demand = {z: df_zones.loc[df_zones['Zone_ID']==z, 'Base_Volume'].values[0] for z in zone_ids}
    alpha = 0.75 
    
    for t in time_idx:
        h = t.hour
        dow = t.dayofweek
        
        weather = "Clear"
        rain_int = 0.0
        shock = 1.0
        event_flag = "None"
        if np.random.random() < 0.05: 
            weather = "Rain"
            rain_int = np.random.uniform(0.3, 1.0)
            shock = 1.3 
        
        for idx, row in df_zones.iterrows():
            z = row['Zone_ID']
            arch = row['Archetype']
            base = row['Base_Volume']
            
            target_demand = base * hourly_profiles[arch][h] * dow_profiles[arch][dow] * shock
            latent_demand[z] = (alpha * latent_demand[z]) + ((1 - alpha) * target_demand)
            final_lambda = max(0, latent_demand[z] * np.random.normal(1.0, 0.1))
            
            count = np.random.poisson(final_lambda)
            if count > 0:
                records.append({
                    "Date_Hour": t,
                    "Pickup_Zone_ID": z,
                    "Count": count,
                    "Weather": weather,
                    "Rain_Intensity": rain_int,
                    "Event_Flag": event_flag
                })

    df_counts = pd.DataFrame(records)
    print(f"Expanding {len(df_counts)} hourly aggregates into individual ride events...")
    
    df_events = df_counts.loc[df_counts.index.repeat(df_counts['Count'])].reset_index(drop=True)
    total_events = len(df_events)
    
    random_seconds = np.random.randint(0, 3600, size=total_events)
    df_events['Timestamp'] = df_events['Date_Hour'] + pd.to_timedelta(random_seconds, unit='s')
    df_events = df_events.sort_values('Timestamp').reset_index(drop=True)
    
    # Pre-format Timestamp to eliminate dateutil parsing warnings later
    df_events['Timestamp'] = df_events['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    df_events['Request_ID'] = ["R" + str(i).zfill(8) for i in range(1, total_events + 1)]
    df_events['Date'] = pd.to_datetime(df_events['Timestamp']).dt.date
    df_events['Time'] = pd.to_datetime(df_events['Timestamp']).dt.time
    df_events['Hour'] = pd.to_datetime(df_events['Timestamp']).dt.hour
    df_events['Day_of_Week'] = pd.to_datetime(df_events['Timestamp']).dt.dayofweek
    
    # 1st Merge: Origin Zone Name
    df_events = df_events.merge(df_zones[['Zone_ID', 'Zone_Name', 'Archetype']], left_on='Pickup_Zone_ID', right_on='Zone_ID')
    df_events.rename(columns={'Zone_Name': 'Pickup_Zone', 'Archetype': 'Origin_Archetype'}, inplace=True)
    df_events.drop(columns=['Zone_ID'], inplace=True) # Drop the redundant join key
    
    print("Assigning Destinations and Distances...")
    df_events['Drop_Zone_ID'] = np.random.choice(zone_ids, size=total_events) 
    
    vehicles = ['Mini', 'Prime', 'Auto', 'Bike']
    df_events['Vehicle_Type'] = np.random.choice(vehicles, size=total_events, p=[0.4, 0.2, 0.3, 0.1])
    
    df_events['Ride_Distance_KM'] = np.round(np.random.lognormal(mean=2.0, sigma=0.6, size=total_events), 1)
    df_events['Ride_Distance_KM'] = np.clip(df_events['Ride_Distance_KM'], 1.0, 45.0)

    # 2nd Merge: Destination Zone Name
    df_events = df_events.merge(df_zones[['Zone_ID', 'Zone_Name']], left_on='Drop_Zone_ID', right_on='Zone_ID')
    df_events.rename(columns={'Zone_Name': 'Drop_Zone'}, inplace=True)
    df_events.drop(columns=['Zone_ID'], inplace=True) # Drop the redundant join key

    final_cols = ['Request_ID', 'Timestamp', 'Date', 'Time', 'Hour', 'Day_of_Week', 
                  'Pickup_Zone_ID', 'Pickup_Zone', 'Drop_Zone_ID', 'Drop_Zone', 
                  'Vehicle_Type', 'Ride_Distance_KM', 'Weather', 'Rain_Intensity', 'Event_Flag']
    
    df_final = df_events[final_cols].sort_values('Timestamp').reset_index(drop=True)
    
    df_final.to_csv(OUTPUT_FILE, index=False)
    
    print("\n" + "="*40)
    print("DATASET GENERATION COMPLETE")
    print("="*40)
    print(f"Total rows: {len(df_final):,}")
    print(f"Date range: {df_final['Date'].min()} to {df_final['Date'].max()}")
    print(f"Number of zones: {df_final['Pickup_Zone_ID'].nunique()}")
    print(f"Average rides/day: {len(df_final) / NUM_DAYS:,.0f}")
    
    return df_final

if __name__ == "__main__":
    df = generate_dataset()