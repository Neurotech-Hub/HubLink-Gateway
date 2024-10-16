import asyncio
from bleak import BleakScanner, BleakClient, BleakError

SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
CHARACTERISTIC_UUID_FILENAME = "87654321-4321-4321-4321-abcdefabcdf3"
CHARACTERISTIC_UUID_FILETRANSFER = "87654321-4321-4321-4321-abcdefabcdf2"

file_list = []  # List to store filenames received from the ESP32
EOF_received = False  # Flag to track when "EOF" is received for filenames

# Timeout settings
FILENAME_TIMEOUT = 5  # seconds to wait for filenames
FILE_TRANSFER_TIMEOUT = 10  # seconds to wait for file transfer

# Callback to handle incoming file data during file transfer
async def handle_file_transfer(sender, data):
    data_str = data.decode('utf-8').strip()
    if data_str == "EOF":
        print("File transfer complete.")
        return
    print(f"Receiving file data: {data_str}")

# Callback to handle incoming filenames
async def handle_filename(sender, data):
    global file_list, EOF_received
    filename = data.decode('utf-8').strip()
    
    if filename == "EOF":
        print("Received all filenames.")
        EOF_received = True
        return
    
    print(f"Received filename: {filename}")
    file_list.append(filename)

# Function to manage notifications and file requests
async def notification_manager(client):
    global EOF_received, file_list

    # Reset file list and EOF flag for a new connection
    file_list = []
    EOF_received = False

    try:
        # Start notifications for both FILENAME and FILETRANSFER characteristics
        print("Requesting file list from ESP32...")
        await client.start_notify(CHARACTERISTIC_UUID_FILENAME, handle_filename)
        await client.start_notify(CHARACTERISTIC_UUID_FILETRANSFER, handle_file_transfer)

        # Wait for all filenames to be received or timeout
        try:
            await asyncio.wait_for(wait_for_filenames(), timeout=FILENAME_TIMEOUT)
        except asyncio.TimeoutError:
            print("Timeout waiting for filenames.")
            return

        # After receiving filenames, request one file as an example
        if file_list:
            print(f"Requesting file: {file_list[0]}")
            await client.write_gatt_char(CHARACTERISTIC_UUID_FILENAME, file_list[0].encode('utf-8'))

            # Wait for the file transfer to complete or timeout
            try:
                await asyncio.wait_for(wait_for_file_transfer(), timeout=FILE_TRANSFER_TIMEOUT)
            except asyncio.TimeoutError:
                print("Timeout during file transfer.")

    except BleakError as e:
        print(f"Error during BLE interaction: {e}")
    finally:
        # Stop notifications and clean up if necessary
        await client.stop_notify(CHARACTERISTIC_UUID_FILENAME)
        await client.stop_notify(CHARACTERISTIC_UUID_FILETRANSFER)
        print("Notifications stopped and cleanup complete.")

# Wait function for receiving filenames
async def wait_for_filenames():
    global EOF_received
    while not EOF_received:
        await asyncio.sleep(1)

# Wait function for receiving file transfer data
async def wait_for_file_transfer():
    # This function waits for the file transfer to complete, i.e., receiving EOF
    while True:
        await asyncio.sleep(1)

# Main function to scan, connect, and handle BLE interaction
async def main():
    try:
        devices = await BleakScanner.discover()
        for device in devices:
            if "ESP32_BLE_SD" in device.name:
                print(f"Found ESP32: {device.name}, {device.address}")
                async with BleakClient(device.address) as client:
                    print(f"Connected to {device.name}")
                    await notification_manager(client)
    except BleakError as e:
        print(f"Failed to connect or interact with device: {e}")

asyncio.run(main())
