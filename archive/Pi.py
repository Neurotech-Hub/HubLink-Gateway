import os
import asyncio
from bleak import BleakScanner, BleakClient

SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
CHARACTERISTIC_UUID_FILELIST = "87654321-4321-4321-4321-abcdefabcdf1"  # Send list to Arduino
CHARACTERISTIC_UUID_FILETRANSFER = "87654321-4321-4321-4321-abcdefabcdf2"  # Receive file data

async def get_known_files(arduino_address):
    # Read known files from local storage
    path = f"{arduino_address.replace(':', '')}_files"
    if os.path.exists(path):
        return [f for f in os.listdir(path)]
    else:
        os.mkdir(path)
        return []

# Callback function to handle notifications from Arduino
def handle_notification(sender: int, data: bytearray):
    decoded_data = data.decode('utf-8').strip()
    
    # Check if this is a filename or file content
    if decoded_data.endswith(".txt"):  # Assuming all files are .txt
        global current_file
        current_file = decoded_data
        print(f"Receiving new file: {current_file}")
    else:
        # Write data to file
        with open(f"{path}{current_file}", 'a') as f:
            f.write(decoded_data + '\n')
        print(f"Data from {current_file}: {decoded_data}")

async def get_data_from_device(device):
    global current_file, path  # Make these variables accessible to the callback
    arduino_address = device.address.replace(':', '')
    known_files = await get_known_files(arduino_address)

    file_list = ','.join(known_files)
    print(f"Sending known file list to {device.name}: {file_list}")

    async with BleakClient(device, timeout=30) as client:
        try:
            # Check if the client is already connected
            if client.is_connected:
                print(f"Already connected to {device.name}")
            else:
                # Try to connect if not already connected
                await client.connect()
                print(f"Connected to {device.name}")
            
            # Discover services
            services = client.services
            print(f"Discovered services: {services}")

            # Check if the required service exists
            if SERVICE_UUID not in [str(service.uuid) for service in services]:
                print(f"Required service {SERVICE_UUID} not found on {device.name}")
                return

            print(f"Required service {SERVICE_UUID} found!")

            # Send the known file list to the ESP32 (Arduino)
            await client.write_gatt_char(CHARACTERISTIC_UUID_FILELIST, file_list.encode('utf-8'))
            
            # Define path to save files
            path = f"{arduino_address}_files/"
            
            # Start receiving notifications from the ESP32 for file data
            await client.start_notify(CHARACTERISTIC_UUID_FILETRANSFER, handle_notification)
            
            # Wait for disconnection or manual stop (keep connection alive)
            while client.is_connected:
                await asyncio.sleep(1)  # Sleep to prevent busy waiting
            
            # Stop receiving notifications once disconnected or stopped
            await client.stop_notify(CHARACTERISTIC_UUID_FILETRANSFER)
            print("Stopped receiving notifications")

        except Exception as e:
            print(f"Failed to read from {device.name}: {e}")

        finally:
            # Ensure that the client is disconnected when done
            if client.is_connected:
                await client.disconnect()
                print(f"Disconnected from {device.name}")

async def scan_and_connect():
    max_retries = 3  # Set the number of retries
    devices = []

    for attempt in range(max_retries):
        devices = await BleakScanner.discover(timeout=10)
        arduino_devices = [device for device in devices if "ESP32_BLE_SD" in device.name]

        if arduino_devices:
            break  # Exit if devices are found
        else:
            print(f"Retrying scan {attempt + 1}/{max_retries}...")

    if not arduino_devices:
        print("No Arduino devices found after retrying.")
        return

    for device in arduino_devices:
        print(f"Found Arduino device: {device.name}, {device.address}")
        await get_data_from_device(device)

    print("Finished reading from all devices.")

# Run the BLE scan and connect process
asyncio.run(scan_and_connect())
