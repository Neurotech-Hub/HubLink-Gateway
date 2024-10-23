# config.py

# Hub Link API Endpoint
HUBLINK_ENDPOINT = "https://hublink.cloud"

# Data location (removable drive)
DATA_DIRECTORY = 'data' #f'{BASE_PATH}/data'

# Database file location
DATABASE_FILE = 'instance/hublink.db' #f'{BASE_PATH}/instance/hublink.db'

# Standardized datetime format
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

# DT_RULE options for formatting datetime:
# 'seconds' - Uses format 'YYYYMMDDHHMMSS'
# 'hours'   - Uses format 'YYYYMMDDHH'
# 'days'    - Uses format 'YYYYMMDD'
# 'weeks'   - Uses format 'YYYYWW' (Week of the year)
# 'months'  - Uses format 'YYYYMM'
# 'years'   - Uses format 'YYYY'
# 'never'   - No datetime component, returns an empty string
# Any other value will raise a ValueError.
VALID_DT_RULES = ['seconds', 'hours', 'days', 'weeks', 'months', 'years', 'never']