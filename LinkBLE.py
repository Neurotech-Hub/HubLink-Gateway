import asyncio
from bleak import BleakScanner, BleakClient, BleakError
from S3Manager import needFile, upload_files
from config import DATA_DIRECTORY
import os
from datetime import datetime
from DBManager import sortRecentMAC, updateMAC, get_settings
import time

SERVICE_UUID = "57617368-5501-0001-8000-00805f9b34fb"
CHARACTERISTIC_UUID_FILENAME = "57617368-5502-0001-8000-00805f9b34fb"
CHARACTERISTIC_UUID_FILETRANSFER = "57617368-5503-0001-8000-00805f9b34fb"

settings = get_settings()

class BLEFileTransferClient:
    def __init__(self, mac_address, base_directory):
        self.file_list = []
        self.mac_address = mac_address.replace(':', '')
        self.base_directory = base_directory
        self.eof_received = False
        self.file_transfer_event = asyncio.Event()  # Event to track file transfer activity
        self.all_filenames_received = asyncio.Event()  # Event to track completion of filename reception
        self.current_file = None
        self.current_file_path = None
        self.current_filename_buffer = ""  # Buffer to piece together filename chunks
        self.file_transfer_timeout_task = None  # Task to manage dynamic timeout during file transfer

    async def handle_file_transfer(self, sender, data):
        if data == b"EOF":
            self.eof_received = True
            if self.current_file is not None:
                self.current_file.close()
                self.current_file = None
                #print("File transfer complete.")
            self.file_transfer_event.set()  # Signal that the file transfer is complete

            # Cancel the timeout task if the transfer is complete
            if self.file_transfer_timeout_task:
                self.file_transfer_timeout_task.cancel()

            return

        if self.current_file is None:
            print("Error: No file currently open for writing.")
            return

        # Write data to the current file
        try:
            self.current_file.write(data)
        except Exception as e:
            print(f"Failed to write data to file: {e}")

        # Reset the timeout timer each time data is received
        if self.file_transfer_timeout_task:
            self.file_transfer_timeout_task.cancel()
        self.file_transfer_timeout_task = asyncio.create_task(self.start_dynamic_filetransfer_timeout())

    async def start_dynamic_filetransfer_timeout(self):
        try:
            await asyncio.sleep(10)  # Timeout period for no data received
            if not self.eof_received:
                print("Timeout during file transfer. Deleting partial file.")
                if self.current_file is not None:
                    self.current_file.close()
                    self.current_file = None
                if self.current_file_path and os.path.exists(self.current_file_path):
                    os.remove(self.current_file_path)
                    self.current_file_path = None
                self.file_transfer_event.set()  # Signal that file transfer should be considered complete
        except asyncio.CancelledError:
            # Task was canceled because new data was received
            pass

    async def handle_filename(self, sender, data):
        file_info = data.decode('utf-8').strip()
        if file_info == "EOF":
            print("Received all filenames.")
            self.all_filenames_received.set()  # Signal that all filenames have been received
            return
        elif file_info == "EON":
            # End of current filename notification, process the complete filename
            if '|' in self.current_filename_buffer:
                try:
                    filename, filesize = self.current_filename_buffer.split('|')
                    filesize = int(filesize)
                except ValueError:
                    print(f"Malformed file_info received: {self.current_filename_buffer}")
                    self.current_filename_buffer = ""
                    return
                
                print(f"Received filename: {filename}, size: {filesize}")
                self.file_list.append((filename, filesize))
            else:
                print(f"Malformed file_info received: {self.current_filename_buffer}")
            
            # Clear the buffer after processing
            self.current_filename_buffer = ""
        else:
            # Append data to filename buffer until 'EON' is received
            self.current_filename_buffer += file_info

    async def notification_manager(self, client):
        # Reset file list and EOF flag for a new connection
        self.file_list = []
        self.eof_received = False
        self.current_filename_buffer = ""
        self.all_filenames_received.clear()

        try:
            # Start notifications for both FILENAME and FILETRANSFER characteristics
            print("Requesting file list from ESP32...")
            await client.start_notify(CHARACTERISTIC_UUID_FILETRANSFER, self.handle_file_transfer)
            await client.start_notify(CHARACTERISTIC_UUID_FILENAME, self.handle_filename)

            # Wait for all filenames to be received
            await self.all_filenames_received.wait()  # Wait until all filenames have been received

            # Determine the ID to use (either from ID file or MAC address)
            id = self.mac_address
            if settings['id_file_starts_with']:
                for filename, filesize in self.file_list:
                    if filename.startswith(settings['id_file_starts_with']):
                        id = filename[len(settings['id_file_starts_with']):].split('.')[0]
                        break

            # After receiving filenames, request only those that are needed
            for filename, filesize in self.file_list:
                if filesize > settings['max_file_size']:
                    print(f"{filename} exceeds settings['max_file_size']");
                    continue
                if needFile(id, filename, filesize):
                    print(f"Requesting {filename}")
                    id_directory = os.path.join(self.base_directory, id)
                    os.makedirs(id_directory, exist_ok=True)
                    self.current_file_path = os.path.join(id_directory, filename)
                    try:
                        self.current_file = open(self.current_file_path, 'wb')
                    except IOError as e:
                        print(f"Failed to open file {filename} for writing: {e}")
                        continue

                    try:
                        await client.write_gatt_char(CHARACTERISTIC_UUID_FILENAME, filename.encode('utf-8'))  # Send filename without MAC address
                    except BleakError as e:
                        print(f"Error during GATT write operation: {e}")
                        await self.disconnect_client(client)
                        return

                    # Start measuring time for the file transfer
                    start_time = time.time()

                    # Start the dynamic timeout for file transfer
                    self.file_transfer_timeout_task = asyncio.create_task(self.start_dynamic_filetransfer_timeout())

                    # Wait for the file transfer to complete
                    await self.file_transfer_event.wait()
                    self.file_transfer_event.clear()  # Clear event for next transfer

                    # Calculate and print the elapsed time for the file transfer
                    elapsed_time = time.time() - start_time
                    print(f"{filename} ({filesize} bytes) took {elapsed_time:.2f} seconds.")

                    # Cancel any ongoing timeout task as EOF has been received
                    if self.file_transfer_timeout_task:
                        self.file_transfer_timeout_task.cancel()

                    # Reset EOF flag for the next file
                    self.eof_received = False

        except BleakError as e:
            print(f"Error during BLE interaction: {e}")
            await self.disconnect_client(client)
        except asyncio.TimeoutError:
            print("File transfer timed out.")
        except Exception as e:
            print(f"Unexpected error: {e}")
            await self.disconnect_client(client)
        finally:
            # Stop notifications and clean up if necessary
            try:
                await client.stop_notify(CHARACTERISTIC_UUID_FILENAME)
                await client.stop_notify(CHARACTERISTIC_UUID_FILETRANSFER)
            except BleakError as e:
                print(f"Error stopping notifications: {e}")
            print("Notifications stopped and cleanup complete.")

    async def disconnect_client(self, client):
        try:
            await client.disconnect()
            print("Disconnected gracefully.")
        except BleakError as e:
            print(f"Error during disconnection: {e}")

async def searchForLinks():
    mac_address = None
    ble_client = None
    base_directory = os.path.join(DATA_DIRECTORY, datetime.now().strftime('%Y%m%d%H%M%S'))
    os.makedirs(base_directory, exist_ok=True)
    devices_found = False
    try:
        devices = await BleakScanner.discover(timeout=5)
        if not devices:
            print("No devices found.")
            return
        
        # Extract MAC addresses of ESP32 devices
        mac_addresses = [device.address for device in devices if settings['device_name_includes'] in device.name]
        # Sort MAC addresses by least recently updated
        sorted_mac_addresses = sortRecentMAC(mac_addresses)
        
        for mac_address in sorted_mac_addresses:
            print(f"Attempting to connect to ESP32: {mac_address}")
            ble_client = BLEFileTransferClient(mac_address, base_directory)
            try:
                async with BleakClient(mac_address) as client:
                    print(f"Connected to {mac_address}")
                    await ble_client.notification_manager(client)
                    updateMAC(mac_address)  # Update MAC address after successful connection
                    devices_found = True
            except BleakError as e:
                print(f"Error during connection or BLE interaction: {e}")
            except Exception as e:
                print(f"Unexpected error during connection: {e}")
    except BleakError as e:
        print(f"Failed to connect or interact with device: {e}")
    except Exception as e:
        print(f"Unexpected error during device discovery: {e}")
    finally:
        # Cleanup base directory if no files were transferred and no devices connected
        if os.path.exists(base_directory) and not devices_found:
            if not os.listdir(base_directory):
                os.rmdir(base_directory)
        # Call upload_files if devices connected and files were transferred
        if devices_found and os.path.exists(base_directory):
            if settings['use_cloud']:
                upload_files(base_directory)
            else:
                print("Cloud storage is turned off.")

if __name__ == "__main__":
    asyncio.run(searchForLinks())
