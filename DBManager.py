import os
import sqlite3
from config import DATABASE_FILE, DATETIME_FORMAT
from datetime import datetime

def ensure_database_exists():
    """Ensures that the necessary tables exist in the database."""
    if not os.path.exists(DATABASE_FILE):
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

if __name__ == "__main__":
    ensure_database_exists()