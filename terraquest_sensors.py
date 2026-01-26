import time
import board
import busio

# Try to import the Adafruit BME680 library
try:
    import adafruit_bme680
    BME68X_AVAILABLE = True
except ImportError:
    BME68X_AVAILABLE = False
    print("Warning: adafruit-circuitpython-bme680 not installed. BME688 data will be mocked.")

# Try to import MLX90640
try:
    import adafruit_mlx90640
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    print("Warning: adafruit-circuitpython-mlx90640 not installed.")

# Try to import Qwiic MMC5983MA
try:
    import qwiic_mmc5983ma
    import math
    MAG_AVAILABLE = True
except ImportError:
    MAG_AVAILABLE = False
    print("Warning: sparkfun-qwiic-mmc5983ma not installed.")

class TerraQuestSensors:
    def __init__(self):
        self.bme = None
        self.mlx = None
        self.mag = None
        self.thermal_frame = [0] * 768
        
        # Mag Baseline
        self.mag_baseline = 0
        self.mag_alpha = 0.05 # Low pass filter factor for baseline
        
        self.init_bme688()
        self.init_mlx90640()
        self.init_mmc5983ma()
    
    def init_mmc5983ma(self):
        if MAG_AVAILABLE:
            try:
                self.mag = qwiic_mmc5983ma.QwiicMMC5983MA()
                if self.mag.connected == False:
                    self.mag = None
                    print("MMC5983MA not detected.")
                else:
                    self.mag.begin()
                    print("MMC5983MA Magnetometer Initialized.")
            except Exception as e:
                print(f"Error initializing MMC5983MA: {e}")
                self.mag = None
    
    def init_mlx90640(self):
        if MLX_AVAILABLE:
            try:
                i2c = board.I2C()
                self.mlx = adafruit_mlx90640.MLX90640(i2c)
                self.mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
                print("MLX90640 Thermal Camera Initialized.")
            except Exception as e:
                print(f"Error initializing MLX90640: {e}")
                self.mlx = None
        
    def init_bme688(self):
        if BME68X_AVAILABLE:
            try:
                # Create library object using our Bus I2C port
                i2c = board.I2C()   # uses board.SCL and board.SDA
                # BME688 address is usually 0x77, but sometimes 0x76
                try:
                    self.bme = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x77)
                except:
                    self.bme = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x76)
                
                # Set sea level pressure for altitude calculation (optional)
                self.bme.sea_level_pressure = 1013.25
                print("BME688 Sensor Initialized (Adafruit).")
            except Exception as e:
                print(f"Error initializing BME688: {e}")
                self.bme = None
    
    def read_environment(self):
        """
        Returns a dict with temp, humidity, pressure, gas_resistance
        """
        data = {
            'temp': 0,
            'humidity': 0,
            'pressure': 0,
            'gas': 0
        }
        
        if self.bme:
            try:
                data['temp'] = round(self.bme.temperature, 1) # C
                data['humidity'] = round(self.bme.relative_humidity, 1) # %
                data['pressure'] = round(self.bme.pressure, 2) # hPa
                data['gas'] = round(self.bme.gas, 0) # Ohms
            except Exception as e:
                # print(f"Error reading BME688: {e}")
                pass
        
        return data

    def get_thermal_frame(self):
        if self.mlx:
            try:
                self.mlx.getFrame(self.thermal_frame)
                return self.thermal_frame
            except Exception:
                pass
        return []

    def get_magnetic_data(self):
        """
        Returns (total_strength, anomaly_score)
        """
        if self.mag:
            try:
                # Driver get_measurement_xyz may return False if read fails
                reading = self.mag.get_measurement_xyz()
                if not isinstance(reading, (list, tuple)) or len(reading) < 3:
                     # print("Mag Read Failed: Not a tuple")
                     return 0, 0
                
                x, y, z = reading
                
                # Calculate Total Field Magnitude
                strength = math.sqrt(x*x + y*y + z*z)
                
                # Initialize baseline if first run
                if self.mag_baseline == 0:
                    self.mag_baseline = strength
                
                # Update baseline slowly (approx background field)
                self.mag_alpha = 0.02
                self.mag_baseline = (self.mag_baseline * (1 - self.mag_alpha)) + (strength * self.mag_alpha)
                
                # Anomaly is the deviation from baseline
                anomaly = abs(strength - self.mag_baseline)
                
                return int(strength), int(anomaly)
            except Exception as e:
                # print(f"Mag Runtime Error: {e}")
                pass
        return 0, 0

# Test execution
if __name__ == "__main__":
    sensors = TerraQuestSensors()
    while True:
        env = sensors.read_environment()
        print(f"Env Data: {env}")
        time.sleep(1)
