import requests
import logging
import os
from dotenv import load_dotenv

# Load environment variables from the .env file if it exists
load_dotenv()

# Configuration
SECRET_URL = os.getenv('SECRET_URL')


# !! needs to build file using build_s3_filename
# !! needs to send file size to API to check for change
# !! create force_update endpoint for pre/post processing
def filter_needed_files(id, file_list, max_file_size):
    """
    Filters out files that are not needed by checking against the Hublink API.

    Parameters:
        id (str): The account ID or identifier.
        file_list (list): A list of tuples, each containing a filename and size.
        max_file_size (int): Maximum file size allowed.

    Returns:
        list: A filtered list containing only files that are needed.
    """
    # Prepare the list of filenames for the API request
    filenames = [filename for filename, filesize in file_list if filesize <= max_file_size]

    if not filenames:
        return []

    try:
        # Send request to the Hublink API to check which files are needed
        response = requests.post(
            f"{HUBLINK_ENDPOINT}/{id}/files",
            json={"filenames": filenames},
            headers={"Authorization": f"Bearer {SECRET_URL}"},
            timeout=3  # Short timeout to handle network issues
        )
        response.raise_for_status()

        # Extract the result from the API response
        data = response.json()
        needed_files = data.get("exists", [True] * len(filenames))

        # Filter the file list based on the response
        return [file_list[i] for i in range(len(filenames)) if needed_files[i]]

    except (requests.exceptions.RequestException, ValueError) as e:
        logging.error(f"Error contacting Hublink API: {e}")
        # If there's an error, assume all files are needed
        return file_list

if __name__ == "__main__":
    filter_needed_files("0000", ["test1.txt"], 1000)