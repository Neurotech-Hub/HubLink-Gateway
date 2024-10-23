# HubLink-Pi

## Peripheral Interaction Guidelines

This system is designed for BLE (Bluetooth Low Energy) file transfers between a central client (e.g., a Raspberry Pi or similar device running this script) and peripheral devices, such as an ESP32 acting as a data storage provider. Here's how your peripheral should interact with this system:

### Peripheral Requirements
1. **Device Name Filtering**: The BLE peripheral (e.g., ESP32) should have a device name that includes a specific identifier (e.g., "ESP32_BLE_SD") so that the central client can discover it efficiently. This allows the central client to filter and identify relevant devices during scanning.

2. **Characteristic Configuration**:
   - The peripheral should implement two main characteristics:
     - **Filename Characteristic (UUID: `57617368-5502-0001-8000-00805f9b34fb`)**: This characteristic is used to handle the filenames being requested.
     - **File Transfer Characteristic (UUID: `57617368-5503-0001-8000-00805f9b34fb`)**: This characteristic is used to transfer the actual file data.
   - Ensure the characteristics have the correct properties:
     - **Indications** for `CHARACTERISTIC_UUID_FILETRANSFER` and `CHARACTERISTIC_UUID_FILENAME` to ensure reliable data delivery.

3. **BLE Indications**:
   - Indications require acknowledgment from the client. The ESP32 should be configured to send indications when new data is available.
   - Use the **Client Characteristic Configuration Descriptor (CCCD)** to properly manage the indication subscription from the central device. This ensures that the ESP32 sends indications only when the client subscribes.

4. **File List Handling**:
   - The peripheral should send the list of available filenames to the central device after it establishes a connection. The filenames are divided into chunks if they exceed the Maximum Transmission Unit (MTU) size.
   - After the entire filename is transmitted, an "End of Name" (`EON`) notification is sent, indicating that the complete filename has been sent. After sending all filenames, an "End of Filenames" (`EOF`) notification should be transmitted.

5. **File Transfer Mechanism**:
   - When the central client requests a file by writing to the **Filename Characteristic**, the ESP32 should start sending the file data over the **File Transfer Characteristic** using indications.
   - The file data should be sent byte by byte (or in small chunks) to comply with BLE MTU limitations. An "End of File" (`EOF`) indication is sent after the entire file has been transmitted.

6. **Timeout Handling**:
   - The ESP32 should be robust in handling timeouts, in case the client disconnects or fails to acknowledge the indications.
   - If no acknowledgment is received for an indication, the ESP32 should retry or consider the transfer incomplete after a given number of retries.

7. **MTU Considerations**:
   - Since the MTU negotiation may be limited, the ESP32 should split filenames and file data into smaller chunks (e.g., 20 bytes) to ensure they fit within the MTU.
   - The central client will handle reassembling these chunks to reconstruct the entire filename or file.

8. **Behavior During File Requests**:
   - Upon receiving a filename request, the ESP32 should:
     1. **Open the File**: Open the requested file for reading.
     2. **Send Data**: Use the **File Transfer Characteristic** to send the file data.
     3. **Indicate EOF**: Once the file has been completely sent, indicate an `EOF` to notify the client that the transfer is complete.

9. **Error Handling**:
   - The ESP32 should be designed to handle errors gracefully, such as:
     - **File Not Found**: If a requested file does not exist, the ESP32 should return an appropriate error code or indication.
     - **Connection Drops**: If the connection to the client is lost during transfer, the ESP32 should clean up any open file handles and reset the state.

10. **Testing and Debugging**:
    - Use tools like **nRF Connect** to validate the indications and ensure they are being properly received by a client.
    - Debugging tools (such as Serial Monitor) on the ESP32 can be helpful for confirming that indications are being sent, and errors are properly logged.

By following these guidelines, the BLE peripheral device can efficiently interact with the central client and perform reliable file transfers. This approach ensures minimal data loss and reliable communication, leveraging the robustness of BLE indications.

## Configuration Descriptions (config.py)

1. **BASE_PATH**: 
   - Defines the base path for removable storage. This is where data from connected BLE peripherals will be saved.

2. **DATA_DIRECTORY**:
   - Represents the full path to the directory where data will be stored. This directory is used to store files received from BLE devices. The `searchForLinks()` function creates subdirectories under this path for each scan based on the current date and time.

3. **DATABASE_FILE**:
   - Defines the path to the SQLite database used by the system. This database is essential for keeping track of scanned files, MAC addresses, and updating metadata for tracking file states. Functions like `ensure_database_exists()`, `updateMAC()`, and `needFile()` in `DBManager.py` use this configuration to interact with the database.

4. **BUCKET_NAME**:
   - Specifies the Amazon S3 bucket to which data may be uploaded. This is used in the `S3Manager` module, which handles uploading files from `DATA_DIRECTORY` to cloud storage if `USE_CLOUD` is set to `True`.

5. **DATETIME_FORMAT**:
   - Provides a standardized format for timestamps used throughout the system. It is applied when saving files, updating metadata, and logging timestamps, ensuring consistency across all time-related operations.

6. **DT_RULE**:
   - Defines how datetime strings should be formatted for creating the directory structure and filenames. This is critical for building consistent file paths in the S3 bucket and local storage, as well as determining the depth of timestamp information used in file storage (e.g., down to seconds, hours, or days).

7. **MAX_FILE_SIZE**:
   - Specifies the maximum allowable file size for files to be transferred from BLE peripherals. In `BLEFileTransferClient`, files exceeding this size are skipped, and the system prints a message indicating the exclusion.

8. **USE_CLOUD**:
   - Controls whether files should be uploaded to cloud storage (Amazon S3). If set to `True`, files from `DATA_DIRECTORY` are uploaded to the specified S3 bucket after successful BLE file transfer. This is triggered in the `searchForLinks()` function if any files are received and the `USE_CLOUD` setting is enabled.

9. **DELETE_SCANS, DELETE_SCANS_DAYS_OLD, DELETE_SCANS_PERCENT_REMAINING**:
   - These settings control the deletion of old scan data from `DATA_DIRECTORY`:
     - **DELETE_SCANS**: Enables or disables deletion of old scans entirely.
     - **DELETE_SCANS_DAYS_OLD**: Specifies the age in days after which folders can be deleted. It helps manage space on the removable drive.
     - **DELETE_SCANS_PERCENT_REMAINING**: Ensures that a minimum percentage of the media drive remains available by deleting older scan folders until the threshold is met. The `purgeScans()` function uses these values to determine when and how much to delete.

10. **DEVICE_NAME_INCLUDES**:
    - Filters BLE devices based on their name during the discovery process. In `searchForLinks()`, the list of found BLE devices is filtered by this value to identify relevant peripherals (e.g., those with "ESP32" in the name). This helps target only the intended devices, ignoring others that might be broadcasting nearby.

These configuration options make the system flexible, allowing easy adjustments to the storage path, database management, data retention policies, cloud integration, and device filtering. This allows the system to adapt to various environments and requirements.
 
---

## Dependencies
pip install -r requirements.txt

...

- `pip install bleak`

### Setup

**Virtual Environment**
1. Init: cd to project folder, `python3 -m venv venv` 
2. Start session: `source venv/bin/activate`
3. (Opt) run your script, eg, `python3 S3.py`
4. `deactivate`

**AWS CLI**
1. `sudo apt install awscli`
2. `aws configure`

**Boto3 (AWS)**
1. Init: `pip install boto3` (this will persist in myenv)

**Running myenv in VS Code**
1. Ctrl + Shift + P; Python: Select Interpreter (select venv)

**SQLite Browser**
1. `sudo apt update`
2. `sudo apt install sqlitebrowser`
3. `sqlitebrowser`

Todo:
- [ ] Wakeup/cronjob schedule
- [ ] Smarter timeouts on ESP and Pi (something like a watchdog?)
