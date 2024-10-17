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

# Folder format rule
DT_RULE = 'days'