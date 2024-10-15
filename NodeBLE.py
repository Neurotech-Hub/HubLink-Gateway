import os
import asyncio
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
                print(f"Connected to {device.name}")
            
            # Use the services property instead of get_services()
            services = client.services
            print(f"Discovered services: {services}")

            if SERVICE_UUID not in [str(service.uuid) for service in services]:
                print(f"Required service {SERVICE_UUID} not found on {device.name}")
                return

            # Define callback for file transfer characteristic
            async def handle_filename(sender, data):
                filename = data.decode('utf-8').strip()
                print(f"Received filename: {filename}")

                # Check if the file is needed
                file_needed = needFile(filename)

                # Respond with "SEND" or "SKIP"
                response = b'SEND' if file_needed else b'SKIP'
                await client.write_gatt_char(CHARACTERISTIC_UUID_NEEDFILE_RESPONSE, response)

                if file_needed:
                    print(f"File {filename} is needed. Ready to receive.")
                    
                    # Set the path to save the file in DATA_DIRECTORY
                    file_path = os.path.join(DATA_DIRECTORY, filename)
                    
                    # Open the file in write mode
                    with open(file_path, 'w') as file:

                        # Define callback for file data
                        async def handle_file_transfer(sender, data):
                            file_data = data.decode('utf-8').strip()
                            print(f"Receiving file data: {file_data}")
                            
                            # Check for EOF marker
                            if file_data == EOF_MARKER:
                                print(f"EOF reached for {filename}")
                                await client.stop_notify(CHARACTERISTIC_UUID_FILETRANSFER)
                                print(f"File transfer for {filename} completed and saved to {file_path}")
                                return
                            
                            # Write the data to the file
                            file.write(file_data + '\n')

                        # Start monitoring the file transfer characteristic before notifying the ESP32
                        try:
                            await client.start_notify(CHARACTERISTIC_UUID_FILETRANSFER, handle_file_transfer)
                        except BleakError as e:
                            print(f"Failed to start file transfer notifications: {e}")
                            return

                        print(f"Started receiving file data for {filename}")

                        # Wait until the file transfer is complete (EOF marker detected)
                        while client.is_connected:
                            await asyncio.sleep(1)

                else:
                    print(f"File {filename} is not needed.")

            # Start receiving notifications from ESP32 (filename characteristic)
            await client.start_notify(CHARACTERISTIC_UUID_FILENAME, handle_filename)

            # Signal the ESP32 that the Pi is ready for file transfer
            await client.write_gatt_char(CHARACTERISTIC_UUID_READY, b'READY')
            print("Pi signaled readiness for file transfer.")

            # Wait for connection to remain alive
            while client.is_connected:
                await asyncio.sleep(1)

            # Stop receiving notifications from filename characteristic (only if still connected)
            if client.is_connected:
                await client.stop_notify(CHARACTERISTIC_UUID_FILENAME)

    except BleakError as e:
        print(f"Failed to interact with {device.name}: {e}")

    finally:
        if client.is_connected:
            await client.disconnect()
            print(f"Disconnected from {device.name}")

# BLE scan and connect process
async def scan_and_connect():
    devices = await BleakScanner.discover(timeout=10)
    arduino_devices = [device for device in devices if "ESP32_BLE_SD" in device.name]

    if not arduino_devices:
        print("No ESP32 devices found.")
        return

    for device in arduino_devices:
        print(f"Found device: {device.name}, {device.address}")
        await get_data_from_device(device)

# Run the BLE process
asyncio.run(scan_and_connect())
