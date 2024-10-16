from NodeBLE import searchForLinks
from S3Manager import sync_s3_and_local_files, needFile
from config import DATA_DIRECTORY  # Import the variables from config
import asyncio

# Now you can call the functions from S3Manager.py
if __name__ == "__main__":
    # Sync so we know what files we need (should not be uploading new though)
    sync_s3_and_local_files(DATA_DIRECTORY)

    # Call searchForLinks() to get new data
    asyncio.run(searchForLinks())

    # Sync so all new files are on S3 (also updates local sqlite DB)
    sync_s3_and_local_files(DATA_DIRECTORY)