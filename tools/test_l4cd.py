import time
import board
from adafruit_vl53l4cd import VL53L4CD

print("Testing VL53L4CD Time of Flight Sensor...")

i2c = board.I2C()

try:
    vl53 = VL53L4CD(i2c)
    
    # Start ranging
    vl53.start_ranging()
    
    print("Sensor Initialized!")
    print("Reading distance...")

    while True:
        # Wait for data to be ready
        while not vl53.data_ready:
            pass
            
        dist = vl53.distance
        print(f"Distance: {dist} cm")
        
        # Clear interrupt to allow next reading
        vl53.clear_interrupt()
        
        time.sleep(0.1)

except Exception as e:
    print(f"Error: {e}")
