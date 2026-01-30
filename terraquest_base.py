import time
from picarx import Picarx
# from robot_hat import Ultrasonic, Grayscale_Module, Pin # Unused after refactor

from terraquest_sensors import TerraQuestSensors

class TerraQuestRover:
    def __init__(self):
        self.px = Picarx()
        # Initialize sensors
        self.sensors = TerraQuestSensors()
        
        # Configuration
        self.cruise_speed = 20  # forward speed
        self.cliff_threshold = 200 # Low Value (<200) is Cliff. Table is > 300.
        
        # Thread control flags
        self.running = False  # Main loop active?
        self.mission_active = False # Should we move?
        
        # Sensor Memory
        self.distance = 0
        self.cliff_sensors = [0, 0, 0]
        self.env_data = {'temp': 0, 'humidity': 0, 'pressure': 0, 'gas': 0, 'altitude': 0}
        self.light_data = {'als': 0, 'uvs': 0}
        self.mag_data = {'strength': 0, 'anomaly': 0}
        self.thermal_frame = []
        
        # Timing trackers
        self.last_env_time = 0
        self.last_light_time = 0
        self.last_mag_time = 0
        self.last_thermal_time = 0
        
    def stop(self):
        self.px.stop()
        
    def move_forward(self):
        self.px.forward(self.cruise_speed)
        
    def check_cliff(self):
        # returns True if cliff detected
        # Get 3 channel values
        # Get 3 channel values using Picarx helper
        self.cliff_sensors = self.px.get_grayscale_data()
        readings = self.cliff_sensors
        # If any sensor reads extremely low (air/white table edge vs black tape) or extremely high depending on surface
        # Assuming table is reflective/light and drop is dark or vice versa. 
        # Standard logic: Table = Light/Reflective (~high/low val?), Drop = Dark/Void
        # Often with these sensors: Black line = low value, White = high value OR vice versa.
        # Let's assume standard "Cliff Detection" means detecting the edge of a table (drop to floor).
        # We'll use a safe threshold. If it drops drastically, it's a cliff.
        
        # NOTE: User should calibrate.
        # Based on calibration: Table ~380-580 or ~300+. Cliff ~60-80.
        # So if any reading is < threshold, we treat as cliff.
        if any(r < self.cliff_threshold for r in readings): 
            # DEBUG: Print why we triggered (Silenced for autonomous operation)
            # print(f"Cliff Detected! Readings: {readings} < Threshold: {self.cliff_threshold}")
            return True
        return False

    def check_obstacle(self):
        self.distance = self.px.get_distance()
        if self.distance > 0 and self.distance < 25:
            return True
        return False

    def avoid_cliff(self):
        print("CLIFF DETECTED! ACTING IMMEDIATELY.")
        self.px.stop()
        time.sleep(0.1)
        self.px.backward(20)
        time.sleep(1.5) # Backup ~1 foot (approx)
        self.px.stop()
        time.sleep(0.5)
        self.px.set_dir_servo_angle(45) # Turn wheels
        self.px.forward(20) 
        # Actually turning 90 degrees requires some duration logic or magnetometer
        # For simple loop, we turn for a set time
        time.sleep(1.0) 
        self.px.set_dir_servo_angle(0)
        self.px.stop()
        
    def avoid_obstacle(self):
        print("Obstacle Detected.")
        self.px.stop()
        time.sleep(0.1)
        self.px.backward(20)
        time.sleep(0.5) # Backup slightly
        self.px.set_dir_servo_angle(-35) # Turn 45 degrees
        self.px.forward(20)
        time.sleep(0.8)
        self.px.set_dir_servo_angle(0)
        self.px.stop()

    def manual_drive(self, speed, angle):
        """
        Direct control for manual mode.
        speed: -100 to 100
        angle: -30 (left) to 30 (right)
        """
        self.px.set_dir_servo_angle(angle)
        
        if speed == 0:
            self.stop()
        elif speed > 0:
            self.px.forward(speed)
        else:
            self.px.backward(abs(speed))

    def manual_camera(self, pan, tilt):
        """
        Direct control for camera.
        pan: -90 to 90
        tilt: -35 to 65
        """
        self.px.set_cam_pan_angle(pan)
        self.px.set_cam_tilt_angle(tilt)

    def run_step(self):
        """Execute one iteration of the rover logic - Now purely for telemetry/checks"""
        # We still want to check for cliffs/obstacles for telemetry alerts
        self.check_cliff()
        self.check_obstacle()
        # move_forward() is REMOVED to prevent autonomous movement in manual mode
        pass

    def run(self):
        print("TerraQuest Explorer: Thread Running")
        self.running = True
        
        try:
            while self.running:
                current_time = time.time()
                
                # 1. Telemetry / Sensors (Always active)
                if current_time - self.last_env_time > 2.0:
                    self.env_data = self.sensors.read_environment()
                    self.last_env_time = current_time
                
                if current_time - self.last_light_time > 0.1:
                    als, uvs = self.sensors.get_light_data()
                    self.light_data['als'] = als
                    self.light_data['uvs'] = uvs
                    
                    # Also read mag
                    s, a = self.sensors.get_magnetic_data()
                    self.mag_data['strength'] = s
                    self.mag_data['anomaly'] = a
                    
                    self.last_light_time = current_time
                
                if current_time - self.last_thermal_time > 0.5:
                    self.thermal_frame = self.sensors.get_thermal_frame()
                    self.last_thermal_time = current_time

                # 2. Control Logic
                # This was the old "Mission" mode. 
                # We'll leave it as a placeholder or remove it.
                # For now, it just means "telemetry is active and rover is 'deployed'"
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("Mission Aborted.")
            self.stop()
        finally:
            self.stop()

if __name__ == "__main__":
    rover = TerraQuestRover()
    rover.mission_active = True # Auto-start if running standalone
    rover.run()
