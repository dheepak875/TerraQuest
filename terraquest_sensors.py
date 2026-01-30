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

# Try to import Adafruit LTR390
try:
    import adafruit_ltr390
    LTR_AVAILABLE = True
except ImportError:
    LTR_AVAILABLE = False
    print("Warning: adafruit-circuitpython-ltr390 not installed.")

class TerraQuestSensors:
    def __init__(self):
        self.bme = None
        self.mlx = None
        self.ltr = None
        self.thermal_frame = [0] * 768
        
        self.init_bme688()
        self.init_mlx90640()
        self.init_ltr390()
    
    def init_ltr390(self):
        if LTR_AVAILABLE:
            try:
                i2c = board.I2C()
                self.ltr = adafruit_ltr390.LTR390(i2c)
                print("LTR390 UV/Light Sensor Initialized.")
            except Exception as e:
                print(f"Error initializing LTR390: {e}")
                self.ltr = None
    
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

    def get_light_data(self):
        """
        Returns (als, uvs)
        als: Ambient Light Sensor (Lux-ish raw)
        uvs: UV Sensor (Raw UV Index)
        """
        if self.ltr:
            try:
                als = self.ltr.light
                uvs = self.ltr.uvs
                return int(als), int(uvs)
            except Exception as e:
                # print(f"LTR Runtime Error: {e}")
                pass
        return 0, 0

# Test execution
if __name__ == "__main__":
    sensors = TerraQuestSensors()
    while True:
        env = sensors.read_environment()
        print(f"Env Data: {env}")
        time.sleep(1)
