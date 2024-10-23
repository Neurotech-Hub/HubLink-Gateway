import os

# Hub Link API Endpoint
HUBLINK_ENDPOINT = "https://hublink.cloud"

# Data location (removable drive)
DATA_DIRECTORY = '/media/gaidica/HUBLINK/data'

# Get the directory where this script is located
base_directory = os.path.abspath(os.path.dirname(__file__))

# Set the database file path relative to this directory
DATABASE_FILE = os.path.join(base_directory, 'instance', 'hublink.db')

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