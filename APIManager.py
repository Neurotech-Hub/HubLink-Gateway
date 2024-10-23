import requests
import logging
import os
from dotenv import load_dotenv
from S3Manager import build_s3_filename
from config import HUBLINK_ENDPOINT

# Load environment variables from the .env file if it exists
load_dotenv()

# Configuration
SECRET_URL = os.getenv('SECRET_URL')

def filter_needed_files(id, file_list, max_file_size):
    """
    Filters out files that are not needed by checking against the Hublink API.

    Parameters:
        id (str): The account ID or identifier.
        file_list (list): A list of tuples, each containing (filename, size).
        max_file_size (int): Maximum file size allowed.

    Returns:
        list: A filtered list containing only files that are needed.
    """
    # Debugging: Log input data
    print(f"filter_needed_files called with id: {id}, file_list: {file_list}, max_file_size: {max_file_size}")
    
    # Prepare the list of filenames for the API request, passing through build_s3_filename
    filenames_and_sizes = [
        {"filename": build_s3_filename(id, file[0]), "size": file[1]}
        for file in file_list if file[1] <= max_file_size
    ]

    if not filenames_and_sizes:
        print("No files left after filtering by size.")
        return []

    try:
        # Send request to the Hublink API to check which files are needed
        response = requests.post(
            f"{HUBLINK_ENDPOINT}/{SECRET_URL}/files",
            json={"files": filenames_and_sizes},
            headers={"Authorization": f"Bearer {SECRET_URL}", "Content-Type": "application/json"},
            timeout=5  # Short timeout to handle network issues
        )
        
        # Debugging: Check response status
        print(f"API response status: {response.status_code}")
        response.raise_for_status()

        # Extract the result from the API response
        data = response.json()

        # Debugging: Check response content
        print(f"API response data: {data}")

        # Extract the 'exists' field
        needed_files = data.get("exists")

        if needed_files is None:
            print("Warning: 'exists' key missing in response data.")
            return file_list

        # Debugging: Log filtered files based on API response
        print(f"Files needed according to API: {needed_files}")

        # Filter the file list based on the response
        filtered_file_list = [file_list[i] for i in range(len(filenames_and_sizes)) if not needed_files[i]]

        # Debugging: Final filtered file list
        print(f"Filtered file list: {filtered_file_list}")

        return filtered_file_list

    except (requests.exceptions.RequestException, ValueError) as e:
        # Debugging: Log error
        print(f"Error contacting Hublink API: {e}")
        logging.error(f"Error contacting Hublink API: {e}")
        # If there's an error, assume all files are needed
        return file_list

