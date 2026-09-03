import os
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger('validation.validator')

class DataValidator:
    def __init__(self, rejected_dir: str):
        self.rejected_dir = rejected_dir
        os.makedirs(self.rejected_dir, exist_ok=True)
        self.rejected_file = os.path.join(self.rejected_dir, 'rejected_records.csv')
        
        # Initialize rejected file with headers if it doesn't exist
        if not os.path.exists(self.rejected_file):
            pd.DataFrame(columns=[
                'rejected_at', 'original_record', 'validation_rule', 'rejection_reason', 'source'
            ]).to_csv(self.rejected_file, index=False)

    def _log_rejections(self, rejected_df: pd.DataFrame, rule: str, reason: str, source: str):
        if rejected_df.empty:
            return
            
        logger.warning(f"Validation rule '{rule}' failed for {len(rejected_df)} records. Reason: {reason}")
        
        records_to_log = []
        for _, row in rejected_df.iterrows():
            records_to_log.append({
                'rejected_at': datetime.now().isoformat(),
                'original_record': row.to_json(),
                'validation_rule': rule,
                'rejection_reason': reason,
                'source': source
            })
            
        reject_log = pd.DataFrame(records_to_log)
        reject_log.to_csv(self.rejected_file, mode='a', header=False, index=False)

    def validate_pollution_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validates pollution data, logs rejects, and returns valid DataFrame."""
        if df.empty: return df
        
        initial_count = len(df)
        valid_df = df.copy()
        
        # Rule 1: Missing timestamps
        mask_missing_ts = valid_df['timestamp_utc'].isna() | valid_df['timestamp_local'].isna()
        self._log_rejections(valid_df[mask_missing_ts], 'MISSING_TIMESTAMP', 'Timestamp is null', 'OpenAQ')
        valid_df = valid_df[~mask_missing_ts]
        
        # Rule 2: Missing city/station
        mask_missing_loc = valid_df['city'].isna() | valid_df['station'].isna()
        self._log_rejections(valid_df[mask_missing_loc], 'MISSING_LOCATION', 'City or station is null', 'OpenAQ')
        valid_df = valid_df[~mask_missing_loc]
        
        # Rule 3: Missing pollutant/value
        mask_missing_val = valid_df['pollutant'].isna() | valid_df['value'].isna()
        self._log_rejections(valid_df[mask_missing_val], 'MISSING_VALUE', 'Pollutant name or value is null', 'OpenAQ')
        valid_df = valid_df[~mask_missing_val]
        
        # Rule 4: Negative values
        # Note: some sensors might briefly report small negatives due to calibration drift, but standard DQ drops them.
        mask_negative = valid_df['value'] < 0
        self._log_rejections(valid_df[mask_negative], 'NEGATIVE_VALUE', 'Pollutant value is negative', 'OpenAQ')
        valid_df = valid_df[~mask_negative]
        
        logger.info(f"Pollution Validation: {initial_count} initial -> {len(valid_df)} valid. Rejected {initial_count - len(valid_df)}.")
        return valid_df

    def validate_weather_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validates weather data, logs rejects, and returns valid DataFrame."""
        if df.empty: return df
        
        initial_count = len(df)
        valid_df = df.copy()
        
        # Rule 1: Missing timestamp
        mask_missing_ts = valid_df['timestamp_local'].isna()
        self._log_rejections(valid_df[mask_missing_ts], 'MISSING_TIMESTAMP', 'Timestamp is null', 'Open-Meteo')
        valid_df = valid_df[~mask_missing_ts]
        
        # Rule 2: Missing temperature
        mask_missing_temp = valid_df['temperature_c'].isna()
        self._log_rejections(valid_df[mask_missing_temp], 'MISSING_TEMP', 'Temperature is null', 'Open-Meteo')
        valid_df = valid_df[~mask_missing_temp]
        
        logger.info(f"Weather Validation: {initial_count} initial -> {len(valid_df)} valid. Rejected {initial_count - len(valid_df)}.")
        return valid_df
