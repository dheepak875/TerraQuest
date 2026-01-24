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

class TerraQuestSensors:
    def __init__(self):
        self.bme = None
        self.init_bme688()
        
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

# Test execution
if __name__ == "__main__":
    sensors = TerraQuestSensors()
    while True:
        env = sensors.read_environment()
        print(f"Env Data: {env}")
        time.sleep(1)
