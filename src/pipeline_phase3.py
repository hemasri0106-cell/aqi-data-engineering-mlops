import os
import sys
import logging
from src.transformation.staging import stage_pollution_data, stage_weather_data
from src.validation.validator import DataValidator
from src.transformation.cleaner import clean_pollution_data, clean_weather_data, identify_missing_periods
from src.transformation.aggregator import aggregate_and_join

# Setup logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'transformation.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Also print to console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

logger = logging.getLogger('pipeline_phase3')

def main():
    logger.info("Starting Phase 3 Transformation Pipeline...")
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    raw_pollution_dir = os.path.join(base_dir, 'data', 'raw', 'pollution')
    raw_weather_dir = os.path.join(base_dir, 'data', 'raw', 'weather')
    staging_dir = os.path.join(base_dir, 'data', 'staging')
    rejected_dir = os.path.join(base_dir, 'data', 'rejected')
    cleaned_dir = os.path.join(base_dir, 'data', 'cleaned')
    
    # 1. Staging
    poll_staged = stage_pollution_data(raw_pollution_dir, os.path.join(staging_dir, 'pollution'))
    weather_staged = stage_weather_data(raw_weather_dir, os.path.join(staging_dir, 'weather'))
    
    # 2. Validation
    validator = DataValidator(rejected_dir)
    poll_valid = validator.validate_pollution_data(poll_staged)
    weather_valid = validator.validate_weather_data(weather_staged)
    
    # 3. Cleaning
    poll_clean = clean_pollution_data(poll_valid)
    weather_clean = clean_weather_data(weather_valid)
    
    # Identify missing periods (Hourly expected)
    if not poll_clean.empty:
        identify_missing_periods(poll_clean, 'timestamp_utc_hr', ['station', 'pollutant'], freq='h')
        
    if not weather_clean.empty:
        identify_missing_periods(weather_clean, 'timestamp_utc_hr', ['city'], freq='h')
        
    # 4. Aggregation and Joins
    hourly_df, daily_df = aggregate_and_join(poll_clean, weather_clean, cleaned_dir)
    
    logger.info("Phase 3 Pipeline completed successfully.")
    
    # Print report
    print("\n--- PHASE 3 SUMMARY REPORT ---")
    print(f"Raw Pollution Records Read (Staged): {len(poll_staged)}")
    print(f"Pollution Records Rejected: {len(poll_staged) - len(poll_valid)}")
    print(f"Pollution Records Duplicates Dropped: {len(poll_valid) - len(poll_clean)}")
    print(f"Cleaned Pollution Records (Long format): {len(poll_clean)}")
    print(f"Raw Weather Records Read (Staged): {len(weather_staged)}")
    print(f"Weather Records Rejected: {len(weather_staged) - len(weather_valid)}")
    print(f"Cleaned Weather Records: {len(weather_clean)}")
    print(f"Final Hourly Joined Records: {len(hourly_df)}")
    print(f"Final Daily Aggregated Records: {len(daily_df)}")
    if 'aqi' in daily_df.columns:
        valid_aqi_count = daily_df['aqi'].notna().sum()
        print(f"Successfully calculated AQI for {valid_aqi_count} daily records.")
    
if __name__ == "__main__":
    main()
