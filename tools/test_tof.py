import time
import board
import busio

print("Scanning for ToF Sensor (VL53L0X or VL53L1X)...")

i2c = board.I2C()

try:
    print("Trying VL53L0X...")
    import adafruit_vl53l0x
    vl53 = adafruit_vl53l0x.VL53L0X(i2c)
    print("Success! Found VL53L0X")
    MODEL = "L0X"
except Exception as e:
    print(f"L0X Failed: {e}")
    try:
        print("Trying VL53L1X...")
        import adafruit_vl53l1x
        vl53 = adafruit_vl53l1x.VL53L1X(i2c)
        vl53.start_ranging()
        print("Success! Found VL53L1X")
        MODEL = "L1X"
    except Exception as e2:
        print(f"L1X Failed: {e2}")
        print("Could not initialize either sensor. Check wiring!")
        exit(1)

print(f"Reading distances from {MODEL}...")

while True:
    try:
        if MODEL == "L0X":
             dist = vl53.range
        else:
             if vl53.data_ready:
                 dist = vl53.distance
                 vl53.clear_interrupt()
             else:
                 continue
                 
        print(f"Distance: {dist} mm")
        time.sleep(0.1)
    except Exception as e:
        print(f"Read Error: {e}")
