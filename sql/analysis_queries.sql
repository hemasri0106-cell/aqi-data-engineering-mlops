-- Station daily AQI trend
SELECT 
    s.station_name, d.date, d.aqi, d.aqi_category
FROM 
    daily_aqi d
JOIN 
    stations s ON d.station_id = s.station_id
ORDER BY 
    s.station_name, d.date;

-- City daily AQI trend
SELECT 
    city, date, aqi, aqi_category
FROM 
    daily_city_aqi
ORDER BY 
    city, date;

-- Compare AQI between stations
SELECT 
    s.city, s.station_name, AVG(d.aqi) as avg_aqi
FROM 
    daily_aqi d
JOIN 
    stations s ON d.station_id = s.station_id
GROUP BY 
    s.city, s.station_name
ORDER BY 
    avg_aqi DESC;

-- AQI category distribution
SELECT 
    city, aqi_category, COUNT(*) as days_in_category
FROM 
    daily_city_aqi
GROUP BY 
    city, aqi_category
ORDER BY 
    city, days_in_category DESC;

-- Highest AQI days
SELECT 
    city, date, aqi, aqi_category
FROM 
    daily_city_aqi
WHERE 
    aqi IS NOT NULL
ORDER BY 
    aqi DESC
LIMIT 10;
