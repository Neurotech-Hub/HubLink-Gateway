import os
import boto3
import sqlite3
import socket
from datetime import datetime
from config import DATABASE_FILE, BUCKET_NAME  # Import the variables from config

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
        updated_at TEXT,
        file_size INTEGER
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
        updated_at TEXT,
        file_size INTEGER
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
        print(f"Create or update: {file['Key']} with size: {file['Size']}")
        filename = file['Key']
        created_at = datetime.fromtimestamp(file['LastModified'].timestamp()).isoformat()
        updated_at = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4]

        # Insert or ignore the data in the s3_files table
        cursor.execute('''
            INSERT OR IGNORE INTO s3_files (s3_filename, created_at, updated_at, file_size)
            VALUES (?, ?, ?, ?)
        ''', (filename, created_at, updated_at, file['Size']))

        # Update the updated_at value regardless of whether file_size has changed
        cursor.execute('''
            UPDATE s3_files
            SET updated_at = ?, file_size = ?
            WHERE s3_filename = ?
        ''', (updated_at, file['Size'], filename))
    
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
    def get_s3_file_size(filename):
        try:
            response = s3.head_object(Bucket=BUCKET_NAME, Key=filename)
            return response['ContentLength']
        except s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            else:
                raise
  
    """Uploads files that are in the local directory but missing from S3."""
    local_files = get_local_files(data_directory)
    s3_files = get_s3_filenames()

    files_to_upload = local_files - s3_files
    files_to_check = local_files.intersection(s3_files)
  
    print(f"S3 files: {s3_files}")
    print(f"Files to upload: {files_to_upload}")
    print(f"Files to check for updates: {files_to_check}")

    # Check if the local file size differs from the S3 file size
    for filename in files_to_check:
        local_file_size = os.path.getsize(os.path.join(data_directory, filename))
        s3_file_size = get_s3_file_size(filename)
        if s3_file_size is not None and s3_file_size != local_file_size:
            print(f"Updating file on S3: {filename}")
            s3.upload_file(os.path.join(data_directory, filename), BUCKET_NAME, filename)
            print(f"Uploaded: {filename}")
    for filename in files_to_upload:
        file_path = os.path.join(data_directory, filename)
        if os.path.isfile(file_path):
            s3.upload_file(file_path, BUCKET_NAME, filename)
            print(f'Uploaded: {filename}')
            # Update the database with the newly uploaded file
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            created_at = updated_at = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4]
            file_size = os.path.getsize(file_path)
            cursor.execute('''
                INSERT OR IGNORE INTO s3_files (s3_filename, created_at, updated_at, file_size)
                VALUES (?, ?, ?, ?)
            ''', (filename, created_at, updated_at, file_size))
            conn.commit()
            conn.close()

def needFile(filename, filesize):
    ensure_database_exists()
    """Returns True if the file is not present in the s3_files database or if the filesize is different."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT file_size FROM s3_files WHERE s3_filename = ?', (filename,))
    result = cursor.fetchone()
    
    # If the file doesn't exist in the database, return True
    if result is None:
        conn.close()
        return True
    
    # If the file exists but the filesize is different, return True
    stored_filesize = result[0]
    conn.close()
    return stored_filesize != filesize

def sync_s3_and_local_files(data_directory):
    ensure_database_exists()
    """Master function to sync files between S3 and local directory."""
    # Step 1: Update or create the s3_files database with the current S3 file list
    create_or_update_s3_files_table()

    # Step 2: Upload missing files from local directory to S3 and update the database accordingly
    upload_missing_files(data_directory)