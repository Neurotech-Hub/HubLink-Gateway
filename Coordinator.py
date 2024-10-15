from S3Manager import sync_s3_and_local_files, needFile
from config import DATA_DIRECTORY  # Import the variables from config

# Now you can call the functions from S3Manager.py
if __name__ == "__main__":
    
    # Run the sync process
    sync_s3_and_local_files(DATA_DIRECTORY)
