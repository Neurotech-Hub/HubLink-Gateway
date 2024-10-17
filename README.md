# NullLink-Pi

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
 
---

## Dependencies
- `sudo apt-get install curl`
- `pip install bleak`

### Setup

**Virtual Environment**
1. Init: cd to project folder, `python3 -m venv myenv` 
2. Start session: `source myenv/bin/activate`
3. (Opt) run your script, eg, `python3 S3.py`
4. `deactivate`

**AWS CLI**
1. `sudo apt install awscli`
2. `aws configure`

**Boto3 (AWS)**
1. Init: `pip install boto3` (this will persist in myenv)

**Running myenv in VS Code**
1. Ctrl + Shift + P; Python: Select Interpreter (select myenv)

**SQLite Browser**
1. `sudo apt update`
2. `sudo apt install sqlitebrowser`
3. `sqlitebrowser`

Todo:
- [ ] Wakeup schedule
- [ ] Prune local files (based on remaining storage and/or age)
- [ ] Optimize BLE timing delays on ESP
- [ ] Smarter timeouts on ESP and Pi (something like a watchdog?)