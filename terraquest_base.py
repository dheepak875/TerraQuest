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
        self.cliff_threshold = 100 # Calibration: Table ~300-400, Cliff ~5
        
        # Thread control flags
        self.running = False  # Main loop active?
        self.mission_active = False # Should we move?
        
        # Sensor Memory
        self.distance = 0
        self.cliff_sensors = [0, 0, 0]
        self.env_data = {'temp': 0, 'humidity': 0, 'pressure': 0, 'gas': 0, 'altitude': 0}
        
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
        
        # NOTE: User should calibrate. For now, if any reading is < threshold, we treat as cliff.
        if any(r < self.cliff_threshold for r in readings): 
            # DEBUG: Print why we triggered
            print(f"Cliff Detected! Readings: {readings} < Threshold: {self.cliff_threshold}")
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
        # Safety: Do not allow manual control if mission is active
        if self.mission_active:
            print("Ignoring manual command: Mission Active")
            return
            
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
        """Execute one iteration of the rover logic"""
        # Priority 1: Cliff
        if self.check_cliff():
            self.avoid_cliff()
            return
        
        # Priority 2: Obstacle
        if self.check_obstacle():
            self.avoid_obstacle()
            return
        
        # Default: Scouting
        self.move_forward()

    def run(self):
        print("TerraQuest Explorer: Mission Start")
        self.running = True
        try:
            while self.running:
                if self.mission_active:
                    self.run_step()
                    # Update environmental sensors occasionally
                    if time.time() % 1.0 < 0.1: # simple rate limit approx 1hz
                        self.env_data = self.sensors.read_environment()
                    time.sleep(0.05) # Loop delay
                else:
                    self.stop()
                    # Keep updating sensors even when stopped
                    self.env_data = self.sensors.read_environment()
                    time.sleep(1.0) # Idling
                
        except KeyboardInterrupt:
            print("Mission Aborted.")
            self.stop()
        finally:
            self.stop()

if __name__ == "__main__":
    rover = TerraQuestRover()
    rover.mission_active = True # Auto-start if running standalone
    rover.run()
