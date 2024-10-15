import os
import asyncio
import time
from bleak import BleakScanner, BleakClient, BleakError
from config import DATABASE_FILE, DATA_DIRECTORY  # Import DATA_DIRECTORY for file storage
from S3Manager import needFile

SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
CHARACTERISTIC_UUID_READY = "87654321-4321-4321-4321-abcdefabcdf5"
CHARACTERISTIC_UUID_FILENAME = "87654321-4321-4321-4321-abcdefabcdf3"
CHARACTERISTIC_UUID_FILETRANSFER = "87654321-4321-4321-4321-abcdefabcdf2"
CHARACTERISTIC_UUID_NEEDFILE_RESPONSE = "87654321-4321-4321-4321-abcdefabcdf4"
EOF_MARKER = "EOF"  # Define a special marker for end of file

async def get_data_from_device(device):
    global current_file, path
    arduino_address = device.address.replace(':', '')

    try:
        async with BleakClient(device, timeout=30) as client:
            if client.is_connected:
                print(f"Already connected to {device.name}")
            else:
                await client.connect()
                print(f"Connected to {device.name} at {time.time()}")  # Log timestamp
            
            services = client.services
            print(f"Discovered services: {services}")

            if SERVICE_UUID not in [str(service.uuid) for service in services]:
                print(f"Required service {SERVICE_UUID} not found on {device.name}")
                return

            # Define callback for file transfer data
            async def handle_file_transfer(sender, data):
                file_data = data.decode('utf-8').strip()
                print(f"Receiving file data: {file_data}")

                # Check for EOF marker
                if file_data == EOF_MARKER:
                    print(f"EOF reached for {current_file}")
                    return  # EOF reached, stop handling data for this file

                # Write the data to the current file
                with open(os.path.join(DATA_DIRECTORY, current_file), 'a') as file:
                    file.write(file_data + '\n')

            # Define callback for filename characteristic
            async def handle_filename(sender, data):
                global current_file
                filename = data.decode('utf-8').strip()
                current_file = filename
                print(f"Received filename: {filename} at {time.time()}")  # Log timestamp

                # Check if the file is needed
                file_needed = needFile(filename)

                # Respond with "SEND" or "SKIP"
                response = b'SEND' if file_needed else b'SKIP'
                await client.write_gatt_char(CHARACTERISTIC_UUID_NEEDFILE_RESPONSE, response)
                print(f"Sent response: {response.decode('utf-8')} for {filename} at {time.time()}")  # Log timestamp

                if file_needed:
                    print(f"File {filename} is needed. Ready to receive.")
                else:
                    print(f"File {filename} is not needed. Moving to next file.")

            # Start receiving notifications for both filename and file transfer
            await client.start_notify(CHARACTERISTIC_UUID_FILENAME, handle_filename)
            await client.start_notify(CHARACTERISTIC_UUID_FILETRANSFER, handle_file_transfer)

            # Signal the ESP32 that the Pi is ready for file transfer
            await client.write_gatt_char(CHARACTERISTIC_UUID_READY, b'READY')
            print("Pi signaled readiness for file transfer at", time.time())  # Log timestamp

            # Wait for connection to remain alive
            while client.is_connected:
                await asyncio.sleep(0.1)  # Check the connection every 100ms

            # Stop notifications once the connection is lost
            await client.stop_notify(CHARACTERISTIC_UUID_FILENAME)
            await client.stop_notify(CHARACTERISTIC_UUID_FILETRANSFER)

    except BleakError as e:
        print(f"Failed to interact with {device.name}: {e}")

    finally:
        if client.is_connected:
            await client.disconnect()
            print(f"Disconnected from {device.name}")

# BLE scan and connect process
async def scan_and_connect():
    devices = await BleakScanner.discover(timeout=3)
    arduino_devices = [device for device in devices if "ESP32_BLE_SD" in device.name]

    if not arduino_devices:
        print("No ESP32 devices found.")
        return

    for device in arduino_devices:
        print(f"Found device: {device.name}, {device.address}")
        await get_data_from_device(device)

# Run the BLE process
asyncio.run(scan_and_connect())
