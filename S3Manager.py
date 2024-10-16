import os
import boto3
import sqlite3
import socket
from datetime import datetime
from config import DATABASE_FILE, BUCKET_NAME  # Import the variables from config

# Set up your S3 client (assumes credentials are configured)
s3 = boto3.client('s3')

def create_or_update_s3_files_table():
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
        print(f"Operating on S3 file: {file['Key']} with size: {file['Size']}")
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
    """Returns a set of filenames currently in S3."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT s3_filename FROM s3_files')
    s3_filenames = {row[0] for row in cursor.fetchall()}
    conn.close()
    return s3_filenames

def upload_missing_files(data_directory):
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

def needFile(filename):
    """Returns True if the file is not present in the s3_files database."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM s3_files WHERE s3_filename = ?', (filename,))
    result = cursor.fetchone()[0]
    conn.close()
    return result == 0

def sync_s3_and_local_files(data_directory):
    """Master function to sync files between S3 and local directory."""
    # Step 1: Upload missing files from local directory to S3
    upload_missing_files(data_directory)

    # Step 2: Update or create the s3_files database with the current S3 file list
    create_or_update_s3_files_table()