import board
import busio
import time

print("Scanning I2C Bus...")

try:
    i2c = board.I2C()
    while not i2c.try_lock():
        pass
    
    try:
        devices = i2c.scan()
        print("Found I2C devices:", [hex(device_address) for device_address in devices])
        
        # Identification Hints
        known = {
            0x77: "BME688 (Env)",
            0x76: "BME688 (Env - Alt)",
            0x33: "MLX90640 (Thermal)",
            0x53: "LTR390 (UV/Light)",
            0x30: "MMC5603/MMC5983 (Magentomeer)",
            0x1E: "HMC5883L (Magnetometer)",
            0x0C: "MLX90393 (Magnetometer)",
            0x10: "VEML7700 (Light)"
        }
        
        for addr in devices:
            if addr in known:
                print(f"  - {hex(addr)}: Likely {known[addr]}")
            else:
                print(f"  - {hex(addr)}: Unknown")
                
    finally:
        i2c.unlock()

except Exception as e:
    print(f"I2C Scan Failed: {e}")
