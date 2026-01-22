import time
from picarx import Picarx

def main():
    px = Picarx()
    print("TerraQuest Sensor Calibration")
    print("----------------------------")
    print("Press Ctrl+C to stop")
    print("Move the robot over different surfaces (Table vs Air/Cliff)")
    print("")

    try:
        while True:
            # Get grayscale values [Left, Center, Right]
            # Higher value usually means lighter surface (reflection)
            # Lower value usually means darker surface or empty void (no reflection)
            # BUT it depends on the surface! Test it.
            readings = px.get_grayscale_data()
            
            # Format output comfortably
            print(f"Readings: {readings} | Left: {readings[0]:4} | Center: {readings[1]:4} | Right: {readings[2]:4}", end='\r')
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print("\nCalibration Stopped.")
    finally:
        px.stop()

if __name__ == "__main__":
    main()
