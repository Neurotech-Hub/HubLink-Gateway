import os
import sqlite3
import requests
from config import DATABASE_FILE, DATETIME_FORMAT, HUBLINK_ENDPOINT, VALID_DT_RULES
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from the .env file if it exists
load_dotenv()

SECRET_URL = os.getenv('SECRET_URL')

def ensure_database_exists():
    """Ensures that the necessary tables exist in the database."""
    db_directory = os.path.dirname(DATABASE_FILE)
    if db_directory and not os.path.exists(db_directory):
        os.makedirs(db_directory)
    
    # Create the database file if it does not exist
    if not os.path.exists(DATABASE_FILE):
        open(DATABASE_FILE, 'w').close()
        print(f"Database file {DATABASE_FILE} does not exist. Creating it now.")
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # Create the s3_files table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS s3_files (
        filename TEXT PRIMARY KEY,
        size INTEGER,
        updated_at TEXT
      )
    ''')
    # Create the mac_addresses table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mac_addresses (
        mac_address TEXT PRIMARY KEY,
        updated_at TEXT
      )
    ''')
    # Create the settings table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
        aws_access_key_id TEXT,
        aws_secret_access_key TEXT,
        bucket_name TEXT,
        dt_rule TEXT NOT NULL,
        max_file_size INTEGER NOT NULL,
        use_cloud BOOLEAN NOT NULL,
        delete_scans BOOLEAN NOT NULL,
        delete_scans_days_old INTEGER,
        delete_scans_percent_remaining INTEGER,
        device_name_includes TEXT,
        id_file_starts_with TEXT,
        alert_email TEXT,
        updated_at TEXT
      )
    ''')
    conn.commit()
    conn.close()

def updateMAC(macAddresses):
    """Finds or creates mac_address entries, updating the updated_at column."""
    if not isinstance(macAddresses, list):
        macAddresses = [macAddresses]
    
    ensure_database_exists()
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    updated_at = datetime.now().strftime(DATETIME_FORMAT)
    for macAddress in macAddresses:
        cursor.execute('''
            INSERT INTO mac_addresses (mac_address, updated_at)
            VALUES (?, ?)
            ON CONFLICT(mac_address) DO UPDATE SET updated_at = ?
        ''', (macAddress, updated_at, updated_at))
    conn.commit()
    conn.close()

def sortRecentMAC(macAddressList):
    """Sorts the given list of MAC addresses such that:
    1. MAC addresses not in the database are added to the front of the list.
    2. MAC addresses already in the database are sorted from least recently updated to most recently updated.
    """
    ensure_database_exists()
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # Find all MAC addresses and sort accordingly
    cursor.execute('''
        SELECT mac_address, updated_at FROM mac_addresses
        WHERE mac_address IN ({})
    '''.format(','.join('?' * len(macAddressList))), macAddressList)
    existing_mac_info = {row[0]: row[1] for row in cursor.fetchall()}
    
    not_in_db = [mac for mac in macAddressList if mac not in existing_mac_info]
    sorted_existing_mac_addresses = sorted(existing_mac_info.keys(), key=lambda mac: existing_mac_info[mac])
    
    conn.close()
    
    # Combine the lists: MAC addresses not in the database first, then sorted existing MAC addresses
    return not_in_db + sorted_existing_mac_addresses

def fetch_and_store_settings():
    """Fetches JSON data and stores it in the settings table."""
    ensure_database_exists()
    url = f"{HUBLINK_ENDPOINT}/{SECRET_URL}.json"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        print("API fetch successful.")
    except requests.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    updated_at = datetime.now().strftime(DATETIME_FORMAT)
    cursor.execute('''
        INSERT OR REPLACE INTO settings (
            aws_access_key_id, aws_secret_access_key, bucket_name, dt_rule, max_file_size,
            use_cloud, delete_scans, delete_scans_days_old, delete_scans_percent_remaining,
            device_name_includes, id_file_starts_with, alert_email, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('aws_access_key_id'),
        data.get('aws_secret_access_key'),
        data.get('bucket_name'),
        data.get('dt_rule') if data.get('dt_rule') in VALID_DT_RULES else 'default_rule',
        data.get('max_file_size'),
        data.get('use_cloud'),
        data.get('delete_scans'),
        data.get('delete_scans_days_old'),
        data.get('delete_scans_percent_remaining'),
        data.get('device_name_includes'),
        data.get('id_file_starts_with'),
        data.get('alert_email'),
        updated_at
    ))
    conn.commit()
    conn.close()

def get_settings(option_key=None):
    """Retrieves settings from the database and returns them as a dictionary or a specific value if option_key is provided."""
    ensure_database_exists()
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM settings LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    if row:
        settings = {
            'aws_access_key_id': row[0],
            'aws_secret_access_key': row[1],
            'bucket_name': row[2],
            'dt_rule': row[3],
            'max_file_size': int(row[4]) if row[4] is not None else None,
            'use_cloud': bool(row[5]),
            'delete_scans': bool(row[6]),
            'delete_scans_days_old': int(row[7]) if row[7] is not None else None,
            'delete_scans_percent_remaining': int(row[8]) if row[8] is not None else None,
            'device_name_includes': row[9],
            'id_file_starts_with': row[10],
            'alert_email': row[11]
        }

        # Apply defaults and overrides
        settings = apply_defaults_and_overrides(settings)
        
        # Return specific setting if option_key is provided
        if option_key:
            return settings.get(option_key)
        
        return settings
    return None if option_key else {}

def apply_defaults_and_overrides(settings):
    """Applies default values and overrides to the given settings dictionary."""
    defaults = {
        'aws_access_key_id': '',
        'aws_secret_access_key': '',
        'bucket_name': '',
        'dt_rule': 'hours',
        'max_file_size': 10485760,  # 10 MB
        'use_cloud': False,
        'delete_scans': False,
        'delete_scans_days_old': -1,
        'delete_scans_percent_remaining': -1,
        'device_name_includes': '',
        'id_file_starts_with': '',
        'alert_email': ''
    }
    
    # Apply defaults for missing settings
    for key, default_value in defaults.items():
        settings.setdefault(key, default_value)
    
    # Ensure dt_rule is valid
    if settings['dt_rule'] not in VALID_DT_RULES:
        settings['dt_rule'] = 'hours'

    # implement business/sanitation
    
    return settings

if __name__ == "__main__":
    ensure_database_exists()