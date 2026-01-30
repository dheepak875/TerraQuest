import time
import board
import busio

print("1. Checking I2C Bus...")
try:
    i2c = board.I2C()
    print("   I2C Bus Object Created.")
except Exception as e:
    print(f"   CRITICAL: Failed to create I2C bus: {e}")
    exit()

print("\n2. Scanning for Devices...")
try:
    while not i2c.try_lock():
        pass
    devices = i2c.scan()
    i2c.unlock()
    print(f"   Found devices at: {[hex(d) for d in devices]}")
    
    if 0x53 in devices:
        print("   -> 0x53 (LTR-390 default) FOUND!")
    else:
        print("   -> 0x53 NOT FOUND. Check wiring!")
except Exception as e:
    print(f"   Scan Failed: {e}")

print("\n3. Testing LTR-390 Driver...")
try:
    import adafruit_ltr390
    ltr = adafruit_ltr390.LTR390(i2c)
    print("   Driver Initialized.")
    
    print("\n4. Reading Data (5 seconds)...")
    for i in range(5):
        try:
            lux = ltr.light
            uv = ltr.uvs
            print(f"   Reading {i+1}: Light={lux}, UV={uv}")
        except Exception as e:
            print(f"   Read Error: {e}")
        time.sleep(1)
        
except ImportError:
    print("   ERROR: 'adafruit_ltr390' library not found. Run: pip3 install adafruit-circuitpython-ltr390")
except ValueError as e:
    print(f"   ERROR: Sensor initialization failed: {e}")
except Exception as e:
    print(f"   ERROR: {e}")
