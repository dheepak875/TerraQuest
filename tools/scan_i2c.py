import smbus2
import time

def scan_i2c(bus_num=1):
    print(f"Scanning I2C Bus {bus_num}...")
    try:
        bus = smbus2.SMBus(bus_num)
    except Exception as e:
        print(f"Error opening bus {bus_num}: {e}")
        return

    devices = []
    for address in range(0x03, 0x78):
        try:
            bus.write_quick(address)
            devices.append(hex(address))
        except OSError:
            pass
    
    if devices:
        print(f"Found devices at: {', '.join(devices)}")
        if '0x76' in devices or '0x77' in devices:
            print("  -> Possible BME680/BME688 detected (0x76 or 0x77)")
    else:
        print("No devices found.")
    
    bus.close()

if __name__ == "__main__":
    scan_i2c()
