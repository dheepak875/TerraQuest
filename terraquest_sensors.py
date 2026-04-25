import time
import board
import busio
import math


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

# Try to import MMC5983MA (Sparkfun)
try:
    import qwiic_mmc5983ma
    MAG_AVAILABLE = True
except ImportError:
    MAG_AVAILABLE = False
    print("Warning: sparkfun-qwiic-mmc5983ma not installed.")

# Try to import VL53L4CD ToF Sensor
try:
    from adafruit_vl53l4cd import VL53L4CD
    TOF_AVAILABLE = True
except ImportError:
    TOF_AVAILABLE = False
    print("Warning: adafruit-circuitpython-vl53l4cd not installed.")

class TerraQuestSensors:
    def __init__(self):
        self.bme = None
        self.mlx = None
        self.ltr = None
        self.mag = None
        self.tof = None
        self.thermal_frame = [0] * 768

        # Mag Baseline
        self.mag_baseline = 0
        self.mag_alpha = 0.4  # Fast-tracking so anomaly drops quickly when magnet removed
        
        self.init_bme688()
        self.init_mlx90640()
        self.init_ltr390()
        self.init_magnetometer()
        self.init_tof_sensor()
    
    def init_ltr390(self):
        if LTR_AVAILABLE:
            try:
                i2c = board.I2C()
                self.ltr = adafruit_ltr390.LTR390(i2c)
                print("LTR390 UV/Light Sensor Initialized.")
            except Exception as e:
                print(f"Error initializing LTR390: {e}")
                self.ltr = None

    def init_magnetometer(self):
        if MAG_AVAILABLE:
            try:
                self.mag = qwiic_mmc5983ma.QwiicMMC5983MA()
                if self.mag.is_connected():
                    self.mag.begin()
                    print("SparkFun MMC5983MA Magnetometer Initialized.")
                else:
                    print("MMC5983MA detected but connection failed.")
                    self.mag = None
            except Exception as e:
                print(f"Error initializing MMC5983MA: {e}")
                self.mag = None

    def init_tof_sensor(self):
        if TOF_AVAILABLE:
            try:
                i2c = board.I2C()
                self.tof = VL53L4CD(i2c)
                self.tof.inter_measurement = 0
                self.tof.timing_budget = 200
                self.tof.start_ranging()
                print("VL53L4CD Time-of-Flight Sensor Initialized.")
            except Exception as e:
                print(f"Error initializing ToF Sensor: {e}")
                self.tof = None
    
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
        Note: LTR390 must switch modes between ALS and UVS reads.
        A small delay is needed for the sensor to settle after mode switch.
        """
        if self.ltr:
            try:
                als = self.ltr.light
                time.sleep(0.05)  # Allow mode switch to UVS
                uvs = self.ltr.uvs
                return int(als), int(uvs)
            except Exception as e:
                # print(f"LTR Runtime Error: {e}")
                pass
        return 0, 0

    def get_magnetic_data(self):
        """
        Returns (strength, anomaly)
        Uses a freeze-on-anomaly baseline: baseline only updates during calm periods
        so it doesn't chase magnet readings.
        """
        if self.mag:
            try:
                # Sparkfun Lib returns (x, y, z) in Gauss
                x, y, z = self.mag.get_measurement_xyz_gauss()
                
                # Convert to uTesla (1 Gauss = 100 uT)
                x *= 100
                y *= 100
                z *= 100
                
                # Calculate total strength
                strength = math.sqrt(x*x + y*y + z*z)

                # Baseline tracking
                if self.mag_baseline == 0:
                    self.mag_baseline = strength
                
                # Calculate anomaly BEFORE updating baseline
                anomaly = abs(strength - self.mag_baseline)
                
                # Only update baseline during CALM periods (no anomaly)
                # This prevents baseline from chasing the magnet
                if anomaly < 30:
                    self.mag_baseline = (self.mag_baseline * (1 - self.mag_alpha)) + (strength * self.mag_alpha)
                
                return int(strength), int(anomaly)
            except Exception:
                pass
        return 0, 0

    def get_distance(self):
        """
        Returns distance in cm (or -1 if error/not ready)
        """
        if self.tof:
            try:
                if self.tof.data_ready:
                    dist = self.tof.distance
                    self.tof.clear_interrupt()
                    return dist
            except Exception:
                pass
        return -1

# Test execution
if __name__ == "__main__":
    sensors = TerraQuestSensors()
    while True:
        env = sensors.read_environment()
        dist = sensors.get_distance()
        print(f"Env: {env} | Dist: {dist} cm")
        time.sleep(0.5)
