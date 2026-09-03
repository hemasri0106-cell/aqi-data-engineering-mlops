import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database.connection import get_engine
from src.database.models import Station, HourlyAirQuality, DailyAQI, DailyCityAQI

def verify():
    engine = get_engine()
    
    with Session(engine) as session:
        # Station count
        st_count = session.query(Station).count()
        
        # Hourly verification
        hr_count = session.query(HourlyAirQuality).count()
        hr_distinct = session.execute(text("SELECT COUNT(DISTINCT (station_id, timestamp_utc)) FROM hourly_air_quality")).scalar()
        
        # Daily verification
        d_count = session.query(DailyAQI).count()
        d_distinct = session.execute(text("SELECT COUNT(DISTINCT (station_id, date)) FROM daily_aqi")).scalar()
        
        # City daily verification
        c_count = session.query(DailyCityAQI).count()
        
        print("\n--- DATABASE VERIFICATION REPORT ---")
        print(f"Stations count: {st_count}")
        print(f"Hourly count: {hr_count} (Distinct: {hr_distinct})")
        print(f"Daily count: {d_count} (Distinct: {d_distinct})")
        print(f"City Daily count: {c_count}")
        
        if hr_count == hr_distinct and hr_count > 0:
            print("Hourly unique constraints passed.")
        else:
            print("ERROR: Hourly unique constraints failed!")
            
        if d_count == d_distinct and d_count > 0:
            print("Daily unique constraints passed.")
        else:
            print("ERROR: Daily unique constraints failed!")
            
        print("\n--- DATA QUALITY CHECK ---")
        null_pm25 = session.query(DailyCityAQI).filter(DailyCityAQI.pm25.is_(None)).count()
        print(f"City days with missing PM2.5: {null_pm25}")
        
        null_aqi = session.query(DailyCityAQI).filter(DailyCityAQI.aqi.is_(None)).count()
        print(f"City days with missing AQI: {null_aqi}")

if __name__ == "__main__":
    verify()
