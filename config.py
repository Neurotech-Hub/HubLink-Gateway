# config.py

# examples:
# from config import DATA_DIRECTORY
# from S3Manager import needFile

# Base path for removable drive
BASE_PATH = '/media/gaidica/NULL/NullLink'

# Data location (removable drive)
DATA_DIRECTORY = f'{BASE_PATH}/data'

# Database file location
DATABASE_FILE = f'{BASE_PATH}/s3_files.db'

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
DT_RULE = 'days'

# File size rule
MAX_FILE_SIZE = 5000000 # bytes

# Use/upload to cloud
USE_CLOUD = False

# Scan deletion rules
DELETE_SCANS = True
DELETE_SCANS_DAYS_OLD = -1 # set to -1 to skip
DELETE_SCANS_PERCENT_REMAINING = -1 # set to -1 to skip