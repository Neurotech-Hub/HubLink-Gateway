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

    # Drop the existing table and recreate it for simplicity
    cursor.execute('DROP TABLE IF EXISTS s3_files')
    cursor.execute('''
        CREATE TABLE s3_files (
            s3_filename TEXT PRIMARY KEY,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    # Get the list of files from S3
    s3_files = s3.list_objects_v2(Bucket=BUCKET_NAME).get('Contents', [])
    
    for file in s3_files:
        filename = file['Key']
        created_at = datetime.fromtimestamp(file['LastModified'].timestamp()).isoformat()
        updated_at = created_at

        # Insert or replace the data in the s3_files table
        cursor.execute('''
            INSERT INTO s3_files (s3_filename, created_at, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(s3_filename) DO UPDATE SET updated_at=excluded.updated_at
        ''', (filename, created_at, updated_at))
    
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
    """Uploads files that are in the local directory but missing from S3."""
    local_files = get_local_files(data_directory)
    s3_files = get_s3_filenames()

    files_to_upload = local_files - s3_files
    for filename in files_to_upload:
        file_path = os.path.join(data_directory, filename)
        if os.path.isfile(file_path):
            s3.upload_file(file_path, BUCKET_NAME, filename)
            print(f'Uploaded: {filename}')

    # Re-create the database with the updated file list from S3
    create_or_update_s3_files_table()

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
    # Step 1: Update or create the s3_files database with the current S3 file list
    create_or_update_s3_files_table()
    
    # Step 2: Upload missing files from local directory to S3
    upload_missing_files(data_directory)