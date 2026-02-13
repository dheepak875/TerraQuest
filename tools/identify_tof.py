import board
from smbus2 import SMBus

# VL53 Series Sensors usually at 0x29
ADDRESS = 0x29

def check_id():
    print(f"Probing 0x{ADDRESS:02X}...")
    try:
        with SMBus(1) as bus:
            # Try to read Model ID (Register 0xC0 for L0X, 0x010F for L1X)
            
            # L0X Check
            try:
                val = bus.read_byte_data(ADDRESS, 0xC0)
                print(f"Register 0xC0 (L0X ID): 0x{val:02X}")
                if val == 0xEE:
                    print("--> Confirmed: VL53L0X")
            except Exception as e:
                print(f"Read 0xC0 failed: {e}")

            # L1X / L4X Check (16-bit register address 0x010F)
            # SMBus2 doesn't do 16-bit register addresses easily natively in one command sometimes
            # We have to write the address MSB, LSB first, then read.
            try:
                # Write 0x01, 0x0F
                bus.write_i2c_block_data(ADDRESS, 0x01, [0x0F])
                # Read 1 byte
                val = bus.read_byte(ADDRESS)
                print(f"Register 0x010F (L1X ID): 0x{val:02X}")
                
               # Common IDs
                if val == 0xEA: # L1X
                    print("--> Confirmed: VL53L1X (or L1CB)")
                elif val == 0xEB: # L4
                     print("--> Confirmed: VL53L4 series")
                     
            except Exception as e:
                print(f"Read 0x010F failed: {e}")

    except Exception as e:
        print(f"Bus Error: {e}")

if __name__ == "__main__":
    check_id()
