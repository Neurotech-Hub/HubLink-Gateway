import asyncio
from bleak import BleakScanner, BleakClient, BleakError
from S3Manager import needFile
from config import DATA_DIRECTORY
import os

SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
CHARACTERISTIC_UUID_FILENAME = "87654321-4321-4321-4321-abcdefabcdf3"
CHARACTERISTIC_UUID_FILETRANSFER = "87654321-4321-4321-4321-abcdefabcdf2"

class BLEFileTransferClient:
    def __init__(self):
        self.file_list = []
        self.eof_received = False
        self.file_transfer_event = asyncio.Event()  # Event to track file transfer activity
        self.transfer_timeout_task = None  # Task to manage dynamic timeout during file transfer
        self.current_file = None
        self.current_file_path = None

    async def handle_file_transfer(self, sender, data):
        data_str = data.decode('utf-8').strip()
        if data_str == "EOF":
            self.eof_received = True
            if self.current_file is not None:
                self.current_file.close()
                self.current_file = None
                print("File transfer complete.")
            if self.transfer_timeout_task:
                self.transfer_timeout_task.cancel()  # Cancel the timeout task if the file transfer completes
            self.file_transfer_event.set()  # Signal that the file transfer is complete
            return

        if self.current_file is None:
            print("Error: No file currently open for writing.")
            return

        # Write data to the current file
        self.current_file.write(data_str + '\n')
        print(f"Receiving file data: {data_str}")

        # Reset the timeout timer each time data is received
        if self.transfer_timeout_task:
            self.transfer_timeout_task.cancel()
        self.transfer_timeout_task = asyncio.create_task(self.start_dynamic_timeout())

    async def handle_filename(self, sender, data):
        file_info = data.decode('utf-8').strip()
        if file_info == "EOF":
            print("Received all filenames.")
            print(self.file_list)
            self.eof_received = True
            return
        elif '|' in file_info:
            try:
                filename, filesize = file_info.split('|')
                filesize = int(filesize)
            except ValueError:
                print(f"Malformed file_info received: {file_info}")
                return
        else:
            print(f"Malformed file_info received: {file_info}")
            return
        
        print(f"Received filename: {filename}, size: {filesize}")
        self.file_list.append((filename, int(filesize)))

    async def start_dynamic_timeout(self):
        try:
            await asyncio.sleep(3)  # Timeout period for no data received
            print("Timeout during file transfer. Deleting partial file.")
            if self.current_file is not None:
                self.current_file.close()
                self.current_file = None
            if self.current_file_path and os.path.exists(self.current_file_path):
                os.remove(self.current_file_path)
                self.current_file_path = None
            self.eof_received = True  # Set EOF flag to move on to the next file
        except asyncio.CancelledError:
            # Task was canceled because new data was received
            pass

    async def notification_manager(self, client):
        # Reset file list and EOF flag for a new connection
        self.file_list = []
        self.eof_received = False

        try:
            # Start notifications for both FILENAME and FILETRANSFER characteristics
            print("Requesting file list from ESP32...")
            await client.start_notify(CHARACTERISTIC_UUID_FILENAME, self.handle_filename)
            await client.start_notify(CHARACTERISTIC_UUID_FILETRANSFER, self.handle_file_transfer)

            # Wait for all filenames to be received or timeout
            await asyncio.sleep(5)  # Fixed wait time for filenames to arrive

            # After receiving filenames, request only those that are needed
            for filename, filesize in self.file_list:
                if needFile(filename, filesize):
                    print(f"Requesting file: {filename}")
                    self.current_file_path = os.path.join(DATA_DIRECTORY, filename)
                    try:
                        self.current_file = open(self.current_file_path, 'w')
                    except IOError as e:
                        print(f"Failed to open file {filename} for writing: {e}")
                        continue
                    await client.write_gatt_char(CHARACTERISTIC_UUID_FILENAME, filename.encode('utf-8'))

                    # Start the dynamic timeout for file transfer
                    print(f"Starting dynamic timeout for file: {filename}")
                    self.transfer_timeout_task = asyncio.create_task(self.start_dynamic_timeout())

                    # Wait for the file transfer to complete
                    await self.file_transfer_event.wait()
                    self.file_transfer_event.clear()  # Clear event for next transfer
                    
                    # Cancel any ongoing timeout task as EOF has been received
                    if self.transfer_timeout_task:
                        self.transfer_timeout_task.cancel()

                    # Reset EOF flag for the next file
                    self.eof_received = False

        except BleakError as e:
            print(f"Error during BLE interaction: {e}")
        finally:
            # Stop notifications and clean up if necessary
            await client.stop_notify(CHARACTERISTIC_UUID_FILENAME)
            await client.stop_notify(CHARACTERISTIC_UUID_FILETRANSFER)
            print("Notifications stopped and cleanup complete.")

async def searchForLinks():
    ble_client = BLEFileTransferClient()
    try:
        devices = await BleakScanner.discover(timeout=3)
        for device in devices:
            if "ESP32_BLE_SD" in device.name:
                print(f"Found ESP32: {device.name}, {device.address}")
                async with BleakClient(device.address) as client:
                    print(f"Connected to {device.name}")
                    await ble_client.notification_manager(client)
    except BleakError as e:
        print(f"Failed to connect or interact with device: {e}")

if __name__ == "__main__":
    asyncio.run(searchForLinks())