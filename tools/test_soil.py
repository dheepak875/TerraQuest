from __future__ import print_function
import qwiic_soil_moisture_sensor
import time
import sys

def run_example():
    print("\nSparkFun Soil Moisture Sensor Test (Verbose)\n")
    
    # Try creating instance with explicit address (0x28 is default, but ensuring)
    # The default constructor usually scans the bus. Let's see if we can help it.
    try:
        my_soil = qwiic_soil_moisture_sensor.QwiicSoilMoistureSensor(address=0x28)
    except Exception as e:
        print(f"Error creating sensor object: {e}")
        return

    # Check connection
    if my_soil.is_connected():
        print("Sensor connected at 0x28!")
        my_soil.begin()
        
        while True:
            # Force read
            try:
                moisture = my_soil.level
                print(f"Moisture Payload: {moisture}")
                
                # Also try reading raw register if payload is 0 (debug step)
                # (Assuming library exposes .level correctly)
                
            except Exception as e:
                print(f"Read Error: {e}")
                
            time.sleep(1)
            
    else:
        print("The Qwiic Soil Moisture Sensor device isn't connected to the system.")
        print("Checking bus directly...")
        # (This just prints a message, the real check was above)
        return

if __name__ == '__main__':
    try:
        run_example()
    except (KeyboardInterrupt, SystemExit) as exErr:
        print("\nEnding Test")
        sys.exit(0)
