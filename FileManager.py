import os
import shutil
import psutil
from datetime import datetime, timedelta
from config import DATA_DIRECTORY, DELETE_SCANS, DELETE_SCANS_DAYS_OLD, DELETE_SCANS_PERCENT_REMAINING

def purgeScans():
    """Purges old scan folders from DATA_DIRECTORY based on defined rules."""
    if not DELETE_SCANS:
        print("Scan deletion is disabled.")
        return
    
    # Get list of all folders in DATA_DIRECTORY
    scan_folders = [os.path.join(DATA_DIRECTORY, folder) for folder in os.listdir(DATA_DIRECTORY) if os.path.isdir(os.path.join(DATA_DIRECTORY, folder))]
    print(f"Found {len(scan_folders)} scan folders.")
    
    # Delete folders older than DELETE_SCANS_DAYS_OLD
    if DELETE_SCANS_DAYS_OLD > 0:
        cutoff_date = datetime.now() - timedelta(days=DELETE_SCANS_DAYS_OLD)
        print(f"Deleting folders older than {DELETE_SCANS_DAYS_OLD} days (cutoff: {cutoff_date})")
        for folder in scan_folders:
            folder_mod_time = datetime.fromtimestamp(os.path.getmtime(folder))
            if folder_mod_time <= cutoff_date:
                print(f"Deleting folder {folder} - older than {DELETE_SCANS_DAYS_OLD} days.")
                shutil.rmtree(folder)
        # Refresh the list of scan folders after deletion
        scan_folders = [os.path.join(DATA_DIRECTORY, folder) for folder in os.listdir(DATA_DIRECTORY) if os.path.isdir(os.path.join(DATA_DIRECTORY, folder))]
        print(f"Refreshed list of scan folders. {len(scan_folders)} folders remaining.")
    else:
        print("DELETE_SCANS_DAYS_OLD is set to 0 or less, skipping age-based deletion.")
    
    # Delete folders if disk space is below DELETE_SCANS_PERCENT_REMAINING
    if DELETE_SCANS_PERCENT_REMAINING > 0:
        disk_usage = psutil.disk_usage(DATA_DIRECTORY)
        percent_remaining = 100 - (disk_usage.percent)
        print(f"Disk space check: {percent_remaining}% remaining. Threshold: {DELETE_SCANS_PERCENT_REMAINING}%.")
        if percent_remaining < DELETE_SCANS_PERCENT_REMAINING:
            print(f"Disk space remaining ({percent_remaining}%) is below the threshold ({DELETE_SCANS_PERCENT_REMAINING}%). Deleting older folders.")
            # Sort folders by modification time, oldest first
            scan_folders.sort(key=lambda folder: os.path.getmtime(folder))
            for folder in scan_folders:
                if percent_remaining >= DELETE_SCANS_PERCENT_REMAINING:
                    print(f"Disk space is now above threshold ({percent_remaining}%). Stopping deletion.")
                    break
                print(f"Deleting folder {folder} to free up space.")
                shutil.rmtree(folder)
                # Update disk usage after each deletion
                disk_usage = psutil.disk_usage(DATA_DIRECTORY)
                percent_remaining = 100 - (disk_usage.percent)
                print(f"Folder {folder} deleted. Updated disk space: {percent_remaining}% remaining.")
    else:
        print("DELETE_SCANS_PERCENT_REMAINING is set to 0 or less, skipping disk space-based deletion.")

if __name__ == "__main__":
    purgeScans()
