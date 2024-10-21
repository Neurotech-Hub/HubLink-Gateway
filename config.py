# config.py

###############################################################
# USER CONFIGURATION SECTION                                  #
# Only edit the following values:                             #
###############################################################

SECRET_URL = "9612xJxgwx8q8at2NDIhqv4y"
SECRET_DOMAIN = "https://hub-link.onrender.com/dashboard"

###############################################################

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
