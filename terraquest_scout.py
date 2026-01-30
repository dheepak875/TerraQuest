import time
import threading
import math
import subprocess
from robot_hat import Music, Grayscale_Module, Ultrasonic, ADC, Pin
from picarx import Picarx
from terraquest_sensors import TerraQuestSensors
import socketio 

print("SCOUT MODULE LOADED - V2 (FIXED PINS/SENSORS)")

# Tuning Constants("SCOUT MODULE LOADED - V2 (NO TTS IMPORT)")

# Tuning Constants
CLIFF_THRESHOLD = 200     # LOW Values (< 200) = Cliff/Void. Table is lighter (~300+).
OBSTACLE_DIST_CM = 25     # Arc turn if closer than this
MAG_EUREKA_GAUSS = 0.6    # Anomaly threshold
NORMAL_SPEED = 15         # Reduced for table safety
TURN_SPEED = 30
REVERSE_SPEED = -30       # Slower reverse too

class TerraQuestScout:
    def __init__(self, px_instance, sensors_instance, sio_client=None):
        self.px = px_instance
        self.sensors = sensors_instance
        
        # We will use manual comparison logic instead of px.get_cliff_status
        # because the internal calibration logic is opaque.
        # self.px.set_cliff_reference([600, 600, 600]) 

        self.music = Music()
        self.sio = sio_client
        
        self.running = False
        self.status = "IDLE"

    # ... (say/start/stop methods remain same) ...
    # Cleaning up accidental duplicate block

        
    def say(self, text):
        """Fallback TTS using espeak"""
        try:
            # -a 200 (amplitude/volume), -s 140 (speed)
            subprocess.Popen(['espeak-ng', '-a', '200', '-s', '140', text])
        except Exception:
            try:
                subprocess.Popen(['espeak', text]) 
            except:
                print(f"TTS Failed: {text}")
        
    def start(self):
        if self.running:
            return
        
        self.running = True
        self.status = "SCOUTING"
        
        # State Flags
        self.cliff_detected = False
        self.obstacle_detected = False
        self.eureka_event = False

        # Re-initialize threads each time we start so they can be restarted
        self.nav_thread = threading.Thread(target=self.navigation_loop)
        self.sensor_thread = threading.Thread(target=self.sensor_loop)
        self.nav_thread.daemon = True
        self.sensor_thread.daemon = True

        self.sensor_thread.start()
        self.nav_thread.start()
        print("SCOUT: Engine Started")
        self.say("Scout Engine Online")

    def stop(self):
        self.running = False
        self.px.stop()
        self.status = "STOPPED"
        print("SCOUT: Engine Stopped")

    def sensor_loop(self):
        """High-frequency sensor polling"""
        while self.running:
            # 1. Edge Detection
            # Manual Check is safer than black-box library logic
            cliff_vals = self.px.get_grayscale_data()
            if any(v < CLIFF_THRESHOLD for v in cliff_vals):
                self.cliff_detected = True
            else:
                self.cliff_detected = False

            # 2. UV Sensor (High Value Event)
            # Replaces Magnetometer Eureka
            if self.sensors.ltr:
                try:
                    als, uvs = self.sensors.get_light_data()
                    if uvs > 8: # High UV Index
                        if not self.eureka_event:
                            self.eureka_event = True
                except:
                    pass

            # 3. Ultrasonic (Obstacle - 10Hz)
            # Use px native helper
            dist = self.px.get_distance()
            if dist > 0 and dist < OBSTACLE_DIST_CM:
                self.obstacle_detected = True
            else:
                self.obstacle_detected = False
                
            time.sleep(0.02) # ~50Hz loop

    def navigation_loop(self):
        """State Machine for movement"""
        while self.running:
            # PRIORITY 1: CLIFF / EDGE
            if self.cliff_detected:
                self.status = "CLIFF DETECTED"
                print("SCOUT: CLIFF! Stopping & Reversing...")
                self.px.stop()
                time.sleep(0.1)
                
                self.px.set_dir_servo_angle(0)
                self.px.forward(REVERSE_SPEED)
                time.sleep(1.0) # Reduced from 2.0s to prevent backing off the other side
                self.px.stop()
                
                print("SCOUT: Pivoting...")
                self.px.set_dir_servo_angle(40)
                # Turn carefully
                self.px.forward(NORMAL_SPEED)
                time.sleep(0.8) 
                
                self.px.set_dir_servo_angle(0)
                continue

            # PRIORITY 2: EUREKA (MAGNET) - ALERT ONLY
            if self.eureka_event:
                # We used to stop here, now we just alert and continue
                if self.sio:
                    self.sio.emit('alert', {'type': 'eureka', 'msg': 'Subsurface Anomaly Detected!'})
                
                # Reset event so we don't spam alerts forever (or handle debounce elsewhere)
                self.eureka_event = False 
                
                # self.status = "EUREKA DETECTED"
                # print("SCOUT: EUREKA! Stopping Engine.")
                # self.px.stop()
                # self.say("Subsurface Anomaly Detected. Scouting Suspended.")
                # self.running = False
                # break 

            # PRIORITY 3: OBSTACLE
            if self.obstacle_detected:
                self.status = "AVOIDING OBSTACLE"
                print("SCOUT: Obstacle! Taking evasive action.")
                self.px.stop()
                time.sleep(0.2)
                
                # Back up slightly first
                self.px.set_dir_servo_angle(0)
                self.px.forward(REVERSE_SPEED)
                time.sleep(0.5)
                
                # Then turn
                self.px.set_dir_servo_angle(35)
                self.px.forward(NORMAL_SPEED)
                time.sleep(0.8)
                continue

            # DEFAULT: FORWARD SCOUT
            self.status = "SCOUTING"
            self.px.set_dir_servo_angle(0)
            self.px.forward(NORMAL_SPEED)
            time.sleep(0.1)

