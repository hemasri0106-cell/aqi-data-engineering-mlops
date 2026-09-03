import unittest
import pandas as pd
import numpy as np
from src.transformation.cleaner import clean_pollution_data, clean_weather_data
from src.validation.validator import DataValidator
from src.transformation.aggregator import calculate_naqi_subindex
import os

class TestPhase3Transformation(unittest.TestCase):

    def test_pollutant_normalization(self):
        data = {
            'station': ['StatA', 'StatB'],
            'timestamp_utc': ['2026-09-02T10:00:00Z', '2026-09-02T11:00:00Z'],
            'pollutant': ['PM 2.5', 'NO2'],
            'unit': ['g/m', 'PPM']
        }
        df = pd.DataFrame(data)
        cleaned = clean_pollution_data(df)
        
        self.assertEqual(cleaned['pollutant'].iloc[0], 'pm25')
        self.assertEqual(cleaned['pollutant'].iloc[1], 'no2')
        self.assertEqual(cleaned['unit'].iloc[1], 'ppm')

    def test_duplicate_removal(self):
        data = {
            'station': ['StatA', 'StatA', 'StatB'],
            'timestamp_utc': ['2026-09-02T10:00:00Z', '2026-09-02T10:00:00Z', '2026-09-02T11:00:00Z'],
            'pollutant': ['pm25', 'pm25', 'no2'],
            'unit': ['ug/m3', 'ug/m3', 'ug/m3']
        }
        df = pd.DataFrame(data)
        cleaned = clean_pollution_data(df)
        self.assertEqual(len(cleaned), 2)

    def test_validation_negative_values(self):
        data = {
            'city': ['Delhi', 'Delhi'],
            'station': ['StatA', 'StatB'],
            'timestamp_utc': ['2026-09-02T10:00:00Z', '2026-09-02T11:00:00Z'],
            'timestamp_local': ['2026-09-02T15:30:00', '2026-09-02T16:30:00'],
            'pollutant': ['pm25', 'pm10'],
            'value': [15.5, -5.0]
        }
        df = pd.DataFrame(data)
        
        # Write to a dummy rejected dir
        validator = DataValidator(rejected_dir='dummy_rejected')
        valid_df = validator.validate_pollution_data(df)
        
        self.assertEqual(len(valid_df), 1)
        self.assertEqual(valid_df['value'].iloc[0], 15.5)
        
        # Cleanup
        if os.path.exists('dummy_rejected/rejected_records.csv'):
            os.remove('dummy_rejected/rejected_records.csv')
            os.rmdir('dummy_rejected')

    def test_naqi_calculation(self):
        # PM2.5 of 45 -> AQI between 51 and 100
        # Breakpoint: (31, 60, 51, 100)
        # formula: ((100-51)/(60-31)) * (45-31) + 51 = (49/29) * 14 + 51 = 23.65 + 51 = 74.65
        aqi = calculate_naqi_subindex('pm25', 45)
        self.assertAlmostEqual(aqi, 74.655, places=2)
        
    def test_weather_join(self):
        from src.transformation.aggregator import aggregate_and_join
        # Mock cleaned pollution
        poll = pd.DataFrame({
            'city': ['Delhi'],
            'station': ['StatA'],
            'timestamp_utc_hr': [pd.to_datetime('2026-09-02T10:00:00Z', utc=True)],
            'pollutant': ['pm25'],
            'value': [50.0]
        })
        # Mock cleaned weather with different timestamp
        weather = pd.DataFrame({
            'city': ['Delhi'],
            'timestamp_utc_hr': [pd.to_datetime('2026-09-02T11:00:00Z', utc=True)],
            'temperature_c': [30.0],
            'humidity_pct': [70.0],
            'precipitation_mm': [0.0],
            'wind_speed_kmh': [10.0]
        })
        
        # Test left join
        hourly, _ = aggregate_and_join(poll, weather, 'dummy_cleaned')
        self.assertEqual(len(hourly), 1) # Only pollution row is kept with null weather
        
        # Cleanup
        if os.path.exists('dummy_cleaned/cleaned_hourly.csv'):
            os.remove('dummy_cleaned/cleaned_hourly.csv')
            os.remove('dummy_cleaned/cleaned_daily.csv')
            os.rmdir('dummy_cleaned')

if __name__ == '__main__':
    unittest.main()
