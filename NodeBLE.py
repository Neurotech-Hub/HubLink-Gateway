import asyncio
from bleak import BleakScanner, BleakClient, BleakError
from S3Manager import needFile
from config import DATA_DIRECTORY

SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
CHARACTERISTIC_UUID_FILENAME = "87654321-4321-4321-4321-abcdefabcdf3"
CHARACTERISTIC_UUID_FILETRANSFER = "87654321-4321-4321-4321-abcdefabcdf2"

class BLEFileTransferClient:
    def __init__(self):
        self.file_list = []
        self.eof_received = False

    async def handle_file_transfer(self, sender, data):
        data_str = data.decode('utf-8').strip()
        if data_str == "EOF":
            if hasattr(self, 'current_file') and self.current_file is not None:
                self.current_file.close()
                self.current_file = None
            print("File transfer complete.")
            return

        if not hasattr(self, 'current_file') or self.current_file is None:
            print("Error: No file currently open for writing.")
            return

        # Write data to the current file
        self.current_file.write(data_str + '')
        print(f"Receiving file data: {data_str}")

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

    async def wait_for_event(self, condition_fn, timeout):
        try:
            await asyncio.wait_for(self._wait_until(condition_fn), timeout=timeout)
        except asyncio.TimeoutError:
            print("Timeout waiting for event.")

    async def _wait_until(self, condition_fn):
        while not condition_fn():
            await asyncio.sleep(1)

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
            await self.wait_for_event(lambda: self.eof_received, timeout=5)

            # After receiving filenames, request only those that are needed
            for filename, filesize in self.file_list:
                if needFile(filename, filesize):
                    print(f"Requesting file: {filename}")
                    await client.write_gatt_char(CHARACTERISTIC_UUID_FILENAME, filename.encode('utf-8'))

                    # Wait for the file transfer to complete or timeout
                    await self.wait_for_event(lambda: False, timeout=3)  # Adjust the condition for actual completion logic

        except BleakError as e:
            print(f"Error during BLE interaction: {e}")
        finally:
            # Stop notifications and clean up if necessary
            await client.stop_notify(CHARACTERISTIC_UUID_FILENAME)
            await client.stop_notify(CHARACTERISTIC_UUID_FILETRANSFER)
            print("Notifications stopped and cleanup complete.")

async def main():
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

asyncio.run(main())