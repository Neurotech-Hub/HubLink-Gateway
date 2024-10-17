from LinkBLE import searchForLinks
from S3Manager import update_local_database
from config import DATA_DIRECTORY  # Import the variables from config
import asyncio

# Now you can call the functions from S3Manager.py
if __name__ == "__main__":
    # Sync so we know what files we need (should not be uploading new though)
    update_local_database()

    # Call searchForLinks() to get new data
    asyncio.run(searchForLinks()) # updates S3 files