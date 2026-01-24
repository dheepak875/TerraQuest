import time
import sys
import math

try:
    import qwiic_mmc5983ma
    MAG_AVAILABLE = True
except ImportError:
    print("Error: sparkfun-qwiic-mmc5983ma not installed.")
    MAG_AVAILABLE = False

def test_mag():
    if not MAG_AVAILABLE:
        return

    try:
        mag = qwiic_mmc5983ma.QwiicMMC5983MA()
        if mag.connected == False:
            print("MMC5983MA sensor not detected on I2C bus.")
            return
        
        mag.begin()
        print("MMC5983MA Magnetometer Initialized at 0x30")
        
        print("Reading Magnetic Field (Ctrl+C to stop)...")
        while True:
            # MMC5983MA driver returns tuple (x, y, z)
            x, y, z = mag.get_measurement_xyz()
            
            # Simple Heading Calculation (assuming flat surface)
            heading = math.atan2(y, x) * 180 / math.pi
            if heading < 0: heading += 360
            
            print(f"X: {x:.2f} | Y: {y:.2f} | Z: {z:.2f} | Heading: {heading:.1f}°")
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Failed to run mag test: {e}")

if __name__ == "__main__":
    test_mag()
