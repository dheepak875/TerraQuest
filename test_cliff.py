
import time
from robot_hat import ADC, Grayscale_Module

print("Initializing Grayscale Module...")
try:
    # Initialize exactly like the main code
    gs = Grayscale_Module(ADC("A0"), ADC("A1"), ADC("A2"))
except Exception as e:
    print(f"Error initializing: {e}")
    exit()

print("\n--- CLIFF SENSOR TEST V2 ---")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        # Try multiple known methods for SunFounder libs
        try:
            # Method 1: Standard for some versions
            readings = gs.get_grayscale_data()
        except AttributeError:
             try:
                 # Method 2: Another common variation
                 readings = gs.read()
             except AttributeError:
                 # Method 3: Manual manual read
                 readings = [gs.chn_0.read(), gs.chn_1.read(), gs.chn_2.read()]

        # Calculate status based on current threshold (200)
        status = "SAFE"
        if isinstance(readings, list) and any(r < 200 for r in readings):
            status = "CLIFF!"
            
        print(f"Readings: {readings} | Status: {status}")
        time.sleep(0.5)
        
except KeyboardInterrupt:
    print("\nTest Stopped.")
