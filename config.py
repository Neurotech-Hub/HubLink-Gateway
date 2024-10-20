# config.py

# examples:
# from config import DATA_DIRECTORY
# from S3Manager import needFile

SECRET_URL = "9612xJxgwx8q8at2NDIhqv4y"
SECRET_DOMAIN = "https://hub-link.onrender.com/dashboard"

# Base path for removable drive
# BASE_PATH = '/media/gaidica/NULL/NullLink'

# Data location (removable drive)
DATA_DIRECTORY = 'data' #f'{BASE_PATH}/data'

# Database file location
DATABASE_FILE = 'instance/hublink.db' #f'{BASE_PATH}/instance/hublink.db'

# S3 bucket name
BUCKET_NAME = 'neurotechhub-000'

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
DT_RULE = 'days'

# File size rule
MAX_FILE_SIZE = 5000000 # bytes

# Use/upload to cloud
USE_CLOUD = False

# Scan deletion rules
DELETE_SCANS = True
DELETE_SCANS_DAYS_OLD = -1 # set to -1 to skip
DELETE_SCANS_PERCENT_REMAINING = -1 # set to -1 to skip

# Device filter by name
DEVICE_NAME_INCLUDES = "ESP32"

# Override MAC with ID file
ID_FILE_STARTS_WITH = "id_"