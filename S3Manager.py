import os
import boto3
import sqlite3
import socket
from datetime import datetime
from config import DATABASE_FILE, BUCKET_NAME  # Import the variables from config
import re

# Set up your S3 client (assumes credentials are configured)
s3 = boto3.client('s3')

def ensure_database_exists():
    """Ensures that the s3_files table exists in the database."""
    if not os.path.exists(DATABASE_FILE):
        print(f"Database file {DATABASE_FILE} does not exist. Creating it now.")
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # Create the s3_files table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS s3_files (
        s3_filename TEXT PRIMARY KEY,
        created_at TEXT,
        updated_at TEXT
      )
    ''')
    conn.commit()
    conn.close()

def create_or_update_s3_files_table():
    # Clear the s3_files table if the connection with S3 is successful
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        s3.list_objects_v2(Bucket=BUCKET_NAME)
        cursor.execute('DELETE FROM s3_files')
        conn.commit()
        print("Cleared existing database entries as connection with S3 was successful.")
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'AllAccessDisabled':
            print("Access to the S3 bucket is disabled. Please check permissions.")
            return
        else:
            raise
    finally:
        conn.close()
    """Creates or updates the s3_files table."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Create the s3_files table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS s3_files (
        s3_filename TEXT PRIMARY KEY,
        created_at TEXT,
        updated_at TEXT
      )
    ''')

    # Get the list of files from S3
    try:
        s3_files = s3.list_objects_v2(Bucket=BUCKET_NAME).get('Contents', [])
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'AllAccessDisabled':
            print("Access to the S3 bucket is disabled. Please check permissions.")
            return
        else:
            raise
    
    for file in s3_files:
        print(f"Create or update: {file['Key']}")
        filename = file['Key']
        created_at = datetime.fromtimestamp(file['LastModified'].timestamp()).isoformat()
        updated_at = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4]

        # Insert or ignore the data in the s3_files table
        cursor.execute('''
            INSERT OR IGNORE INTO s3_files (s3_filename, created_at, updated_at)
            VALUES (?, ?, ?)
        ''', (filename, created_at, updated_at))

        # Update the updated_at value
        cursor.execute('''
            UPDATE s3_files
            SET updated_at = ?
            WHERE s3_filename = ?
        ''', (updated_at, filename))
    
    conn.commit()
    conn.close()
    
def get_local_files(data_directory):
    """Returns a set of local files in the specified directory."""
    return {f for f in os.listdir(data_directory) if os.path.isfile(os.path.join(data_directory, f))}

def get_s3_filenames():
    ensure_database_exists()
    """Returns a set of filenames currently in S3."""
    if not os.path.exists(DATABASE_FILE):
        print(f"Database file {DATABASE_FILE} does not exist.")
        return set()

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT s3_filename FROM s3_files')
        s3_filenames = {row[0] for row in cursor.fetchall()}
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return set()
    finally:
        conn.close()

    return s3_filenames

def upload_missing_files(data_directory):
    ensure_database_exists()
    """Uploads files that are in the local directory but missing from S3."""
    local_files = get_local_files(data_directory)
    s3_files = get_s3_filenames()

    files_to_upload = local_files - s3_files
    files_to_check = local_files.intersection(s3_files)
  
    # Print counts instead of full structures
    print(f"Number of S3 files: {len(s3_files)}")
    print(f"Number of files to upload: {len(files_to_upload)}")
    print(f"Number of files to check for updates: {len(files_to_check)}")

    # Upload new files to S3
    for filename in files_to_upload:
        file_path = os.path.join(data_directory, filename)
        if os.path.isfile(file_path):
            s3.upload_file(file_path, BUCKET_NAME, filename)
            print(f'Uploaded: {filename}')
            # Update the database with the newly uploaded file
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            created_at = updated_at = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4]
            cursor.execute('''
                INSERT OR IGNORE INTO s3_files (s3_filename, created_at, updated_at)
                VALUES (?, ?, ?)
            ''', (filename, created_at, updated_at))
            conn.commit()
            conn.close()

def needFile(filename):
    ensure_database_exists()
    """Returns True if the file is not present in the s3_files database."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT s3_filename FROM s3_files WHERE s3_filename = ?', (filename,))
    result = cursor.fetchone()
    
    # If the file doesn't exist in the database, return True
    if result is None:
        #print(f"File '{filename}' does not exist in the database. Needs to be updated.")
        conn.close()
        return True
    
    conn.close()
    return False

def cleanup_old_versions():
    """Cleans up old versions of files on S3 if they have the same MAC and filename but different filesize."""
    ensure_database_exists()
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Get all files from the database
    cursor.execute('SELECT s3_filename, updated_at FROM s3_files')
    s3_files = cursor.fetchall()

    # Group files by MAC and rest of the filename
    file_groups = {}
    for filename, updated_at in s3_files:
        match = re.match(r'^(?P<mac>[A-Fa-f0-9]+)_(?P<filesize>\d+)__(?P<rest>.+)$', filename)
        if not match:
            # If the filename doesn't match the expected pattern, skip it
            print(f"Skipping file '{filename}' due to unexpected format.")
            continue
        
        mac = match.group('mac')
        rest = match.group('rest')
        key = (mac, rest)
        
        if key not in file_groups:
            file_groups[key] = []
        file_groups[key].append((filename, updated_at))

    # Iterate through each group and delete old versions
    for (mac, rest), files in file_groups.items():
        # Sort files by updated_at in descending order (most recent first)
        files.sort(key=lambda x: x[1], reverse=True)
        # Keep the most recent file, delete the others
        for filename, _ in files[1:]:
            try:
                # Attempt to delete the duplicate file from S3
                s3.delete_object(Bucket=BUCKET_NAME, Key=filename)
                print(f"Deleted duplicate file from S3: {filename}")

                # If successful, delete the entry from the database
                cursor.execute('DELETE FROM s3_files WHERE s3_filename = ?', (filename,))
                conn.commit()
                print(f"Deleted duplicate entry from the database: {filename}")
            except s3.exceptions.ClientError as e:
                print(f"Failed to delete file from S3: {filename}. Error: {e}")

    conn.close()

def sync_s3_and_local_files(data_directory):
    ensure_database_exists()
    """Master function to sync files between S3 and local directory."""
    # Step 1: Update or create the s3_files database with the current S3 file list
    create_or_update_s3_files_table()

    # Step 2: Upload missing files from local directory to S3 and update the database accordingly
    upload_missing_files(data_directory)

    # Step 3: Clean up old versions of files in S3
    cleanup_old_versions()
