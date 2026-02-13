from smbus2 import SMBus
import time

# SparkFun Soil Moisture Sensor
ADDRESS = 0x28 

# Registers (Attiny85 I2C)
# Based on firmware default
REG_MOISTURE = 0x0F # Most common firmware exposes 2-byte value starting here?
# Actually simpler: Just read 2 bytes from the device

def read_soil(bus):
    try:
        # According to some FW versions, just read 2 bytes directly
        # But let's verify connectivity first by reading a known register like ID or Version
        # Version is usually at 0x02
        try:
            version = bus.read_byte_data(ADDRESS, 0x02) # Version register
            print(f"Connected! Firmware Version: {version}")
        except:
            print("Could not read version.")

        while True:
            # Read 2 bytes for moisture (0-1023)
            # Some versions use registers, some use direct read.
            # Try reading from register 0x00 and 0x01?
            
            # The official library reads 2 bytes starting at register 0x00?
            # Let's try reading 2 bytes from 0x00
            val = bus.read_i2c_block_data(ADDRESS, 0x00, 2)
            moisture = val[0] | (val[1] << 8)
            
            print(f"Moisture: {moisture} (Raw Bytes: {val})")
            time.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print(f"Testing Soil Sensor at {hex(ADDRESS)} using SMBus2...")
    try:
        with SMBus(1) as bus: # Bus 1 for Pi 
            read_soil(bus)
    except Exception as e:
        print(f"Bus Error: {e}")
