# Farmer Climate Data Management Commands

This directory contains Django management commands for managing farmer climate data.

## Overview

The climate data system provides farmers with up-to-date satellite and weather data to help them make informed decisions and access climate-adaptive financial services. The system consists of three primary components:

1. **Coordinates Update**: Geocodes farmer locations to obtain precise geographic coordinates
2. **Climate Data Update**: Fetches satellite and weather data for farmers based on their coordinates
3. **Climate History**: Maintains historical climate data for trend analysis and visualization

## Available Commands

### `update_farmer_coordinates`

Converts farmer location names into geographic coordinates (latitude/longitude) using geocoding services.

#### Usage

```bash
# Update coordinates for all farmers without coordinates
python manage.py update_farmer_coordinates --all

# Update a specific farmer by ID
python manage.py update_farmer_coordinates --farmer_id=123
```

#### Arguments

- `--all`: Update all farmers without coordinates
- `--farmer_id`: Update a specific farmer by ID

### `update_climate_data`

Fetches and updates climate data (NDVI values and rainfall anomalies) for farmers with coordinates.

#### Usage

```bash
# Update climate data for all farmers that need updates
python manage.py update_climate_data

# Update a specific farmer by ID 
python manage.py update_climate_data --farmer_id=123

# Force update regardless of last update time
python manage.py update_climate_data --force

# Show detailed progress information
python manage.py update_climate_data --verbose
```

#### Arguments

- `--farmer_id`: ID of a specific farmer to update
- `--force`: Force update even if data is recent
- `--verbose`: Show detailed progress information

### `generate_climate_history`

Generates sample climate history data for farmers with coordinates. This is useful for testing and demonstration purposes.

#### Usage

```bash
# Generate 90 days of climate history for all farmers with coordinates
python manage.py generate_climate_history

# Generate history for a specific farmer
python manage.py generate_climate_history --farmer_id=123

# Generate 180 days of history
python manage.py generate_climate_history --days=180

# Clear existing history before generating new data
python manage.py generate_climate_history --clear
```

#### Arguments

- `--farmer_id`: ID of a specific farmer to generate history for
- `--days`: Number of days of history to generate (default: 90)
- `--clear`: Clear existing history before generating new data

## Workflow

The typical workflow is:

1. First run `update_farmer_coordinates` to ensure farmers have valid coordinates
2. Then run `update_climate_data` to fetch current climate metrics for those coordinates
3. Optionally run `generate_climate_history` to create historical data for testing

When the `update_climate_data` command is run, it will:
1. Update the farmer's current climate data (NDVI and rainfall anomaly)
2. Automatically add a record to the climate history database

## Data Models

The system uses the following data models:

1. **Farmer**: Contains the current climate data and coordinates
2. **ClimateHistory**: Stores historical climate data records for trend analysis

## Data Metrics

The system collects and maintains two primary climate metrics:

1. **NDVI (Normalized Difference Vegetation Index)**: A measure of vegetation health from -0.1 to 0.9
2. **Rainfall Anomaly**: Deviation in millimeters from historical rainfall averages

## Environment Requirements

For proper operation, the following environment variables should be set:

```
OPENWEATHER_API_KEY=your_openweather_api_key
SENTINEL_INSTANCE_ID=your_sentinel_instance_id
SENTINEL_API_KEY=your_sentinel_api_key
SENTINEL_OAUTH_CLIENT_ID=your_sentinel_oauth_client_id
SENTINEL_OAUTH_CLIENT_SECRET=your_sentinel_oauth_client_secret
```

If these variables are not set, the system will fall back to using mock data for development and testing purposes.

## Scheduling Updates

For production use, it is recommended to schedule these commands to run automatically:

```python
# Example in settings.py to configure Celery beat schedule
CELERY_BEAT_SCHEDULE = {
    'update-climate-data': {
        'task': 'backend.farmers.tasks.update_all_farmer_climate_data',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
}
``` 