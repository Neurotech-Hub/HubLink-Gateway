import os
import boto3
import sqlite3
from datetime import datetime
from config import DATABASE_FILE, DATETIME_FORMAT
from DBManager import get_settings

# Helper function to format datetime based on DT_RULE
def format_datetime():
    settings = get_settings()
    now = datetime.now()
    if settings['dt_rule'] == 'seconds':
        return now.strftime('%Y%m%d%H%M%S')
    elif settings['dt_rule'] == 'hours':
        return now.strftime('%Y%m%d%H')
    elif settings['dt_rule'] == 'days':
        return now.strftime('%Y%m%d')
    elif settings['dt_rule'] == 'weeks':
        return now.strftime('%Y%U')
    elif settings['dt_rule'] == 'months':
        return now.strftime('%Y%m')
    elif settings['dt_rule'] == 'years':
        return now.strftime('%Y')
    elif settings['dt_rule'] == 'never':
        return ''
    else:
        raise ValueError("Invalid DT_RULE value")

def build_s3_filename(id, filename):
    """Builds the S3 filename string based on DT_RULE."""
    datetime_str = format_datetime()
    if datetime_str:
        return f"{id}/{datetime_str}/{filename}"
    else:
        return f"{id}/{filename}"

# def update_local_database():
#     """Updates the local database to reflect what is in the S3 bucket."""
#     ensure_database_exists()
#     conn = sqlite3.connect(DATABASE_FILE)
#     cursor = conn.cursor()

#     # Get the list of files from S3
#     try:
#         s3_files = s3.list_objects_v2(Bucket=settings['bucket_name']).get('Contents', [])
#     except s3.exceptions.ClientError as e:
#         if e.response['Error']['Code'] == 'AllAccessDisabled':
#             print("Access to the S3 bucket is disabled. Please check permissions.")
#             return
#         else:
#             raise
    
#     # Update the s3_files table to reflect the current state of the S3 bucket
#     existing_files = {row[0]: row[1] for row in cursor.execute('SELECT filename, size FROM s3_files').fetchall()}
#     current_files = {file['Key']: file['Size'] for file in s3_files}

#     # Insert or update entries from S3
#     for filename, size in current_files.items():
#         updated_at = datetime.now().strftime(DATETIME_FORMAT)
#         if filename in existing_files:
#             if existing_files[filename] != size:
#                 cursor.execute('''
#                     UPDATE s3_files SET size = ?, updated_at = ? WHERE filename = ?
#                 ''', (size, updated_at, filename))
#                 print(f"Updated file in database: {filename}")
#         else:
#             cursor.execute('''
#                 INSERT INTO s3_files (filename, size, updated_at)
#                 VALUES (?, ?, ?)
#             ''', (filename, size, updated_at))
#             print(f"Added to database: {filename}")

#     # Delete entries that are no longer in S3
#     for filename in existing_files:
#         if filename not in current_files:
#             cursor.execute('DELETE FROM s3_files WHERE filename = ?', (filename,))
#             print(f"Deleted from database: {filename}")
    
#     conn.commit()
#     conn.close()

# def needFile(id, filename, size):
#     """Checks if a file with the given filename and size is needed in the local cache."""
#     conn = sqlite3.connect(DATABASE_FILE)
#     cursor = conn.cursor()

#     # Build the filename string
#     s3_filename = build_s3_filename(id, filename)

#     # Check if the file exists with the same size
#     cursor.execute('SELECT filename, size FROM s3_files WHERE filename = ? AND size = ?', (s3_filename, size))
#     result = cursor.fetchone()
#     conn.close()

    # If no exact match is found, return True
    return result is None

def upload_files(data_directory):
    """Uploads files from the local directory if they are not already in S3 and updates the database."""
    settings = get_settings()
    # Create a session using the provided access and secret keys
    session = boto3.Session(
        aws_access_key_id=settings['aws_access_key_id'],
        aws_secret_access_key=settings['aws_secret_access_key']
    )

    # Create an S3 client using the session
    s3 = session.client('s3')

    # Iterate through each MAC address folder
    for id in os.listdir(data_directory):
        id_path = os.path.join(data_directory, id)
        if not os.path.isdir(id_path):
            continue

        # Iterate through each file in the MAC address folder
        for filename in os.listdir(id_path):
            file_path = os.path.join(id_path, filename)
            if not os.path.isfile(file_path):
                continue

            s3_key = build_s3_filename(id, filename)

            # Upload file to S3
            s3.upload_file(file_path, settings['bucket_name'], s3_key)
            print(f'Uploaded: {s3_key}')