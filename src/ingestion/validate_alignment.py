import os
import json
from datetime import datetime
import glob
from dateutil.parser import parse

def get_latest_file(directory, prefix):
    files = glob.glob(os.path.join(directory, f"{prefix}*.json"))
    if not files:
        return None
    return max(files, key=os.path.getctime)

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    poll_dir = os.path.join(base_dir, 'data', 'raw', 'pollution')
    weat_dir = os.path.join(base_dir, 'data', 'raw', 'weather')
    
    poll_file = get_latest_file(poll_dir, "openaq_")
    weat_file = get_latest_file(weat_dir, "openmeteo_")
    
    if not poll_file or not weat_file:
        print("Missing raw data files.")
        return
        
    print(f"Validating latest files:\nPollution: {os.path.basename(poll_file)}\nWeather: {os.path.basename(weat_file)}")
    
    # Analyze pollution
    with open(poll_file, 'r') as f:
        poll_data = json.load(f)
        
    poll_timestamps = []
    for r in poll_data.get('results', []):
        dt_str = r.get('period', {}).get('datetimeFrom', {}).get('utc')
        if dt_str:
            poll_timestamps.append(parse(dt_str))
            
    if not poll_timestamps:
        print("No valid timestamps found in pollution data.")
        return
        
    poll_min = min(poll_timestamps)
    poll_max = max(poll_timestamps)
    
    # Analyze weather
    with open(weat_file, 'r') as f:
        weat_data = json.load(f)
        
    weat_timestamps = []
    hourly = weat_data.get('raw_response', {}).get('hourly', {})
    times = hourly.get('time', [])
    offset = weat_data.get('raw_response', {}).get('utc_offset_seconds', 0)
    
    # The weather times are local. We need to convert them to UTC for comparison.
    # But for a simple overlap check, we can just parse them. They don't have TZ info in the string.
    from datetime import timedelta, timezone
    
    for t_str in times:
        dt = parse(t_str)
        # Apply offset to get UTC
        dt_utc = dt - timedelta(seconds=offset)
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        weat_timestamps.append(dt_utc)
        
    if not weat_timestamps:
        print("No valid timestamps found in weather data.")
        return
        
    weat_min = min(weat_timestamps)
    weat_max = max(weat_timestamps)
    
    print("-" * 40)
    print(f"Pollution: {poll_min} to {poll_max} (Count: {len(poll_timestamps)})")
    print(f"Weather  : {weat_min} to {weat_max} (Count: {len(weat_timestamps)})")
    
    # Check overlap
    overlap_start = max(poll_min, weat_min)
    overlap_end = min(poll_max, weat_max)
    
    if overlap_start <= overlap_end:
        print(f"OVERLAP VALID: {overlap_start} to {overlap_end}")
    else:
        print("ERROR: NO OVERLAPPING DATES FOUND!")
        raise RuntimeError("No overlapping dates between pollution and weather data.")

if __name__ == "__main__":
    main()
