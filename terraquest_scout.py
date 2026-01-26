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
CLIFF_THRESHOLD = 200     # Darker < 200 means drop-off or black line
OBSTACLE_DIST_CM = 25     # Arc turn if closer than this
MAG_EUREKA_GAUSS = 0.6    # Anomaly threshold
NORMAL_SPEED = 30
TURN_SPEED = 40
REVERSE_SPEED = -40

class TerraQuestScout:
    def __init__(self, px_instance, sensors_instance, sio_client=None):
        self.px = px_instance
        self.sensors = sensors_instance
        
        # Fixed: robot_hat.Grayscale_Module requires ADC objects
        try:
            self.gs = Grayscale_Module(ADC("A0"), ADC("A1"), ADC("A2"))
        except Exception as e:
            print(f"Grayscale Init Error: {e}")
            self.gs = None
            
        # Fixed: robot_hat.Ultrasonic requires Pin objects
        try:
            self.us = Ultrasonic(Pin("D2"), Pin("D3"))
        except Exception as e:
            print(f"Ultrasonic Init Error: {e}")
            self.us = None

        # TTS not in robot_hat, using espeak fallback
        self.music = Music()
        self.sio = sio_client
        
        self.running = False
        self.status = "IDLE"
        
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
            # 1. Edge Detection (Critical - 50Hz)
            cliff_vals = self.gs.get_grayscale_data()
            if any(v < CLIFF_THRESHOLD for v in cliff_vals):
                self.cliff_detected = True
            else:
                self.cliff_detected = False
            
            # 2. Magnetometer (Eureka - 20Hz)
            if self.sensors.mag:
                try:
                    s_ut, anomaly = self.sensors.get_magnetic_data()
                    if anomaly > 2000: 
                         if not self.eureka_event: 
                             self.eureka_event = True
                except:
                    pass

            # 3. Ultrasonic (Obstacle - 10Hz)
            dist = self.us.read()
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
                print("SCOUT: CLIFF! Reversing...")
                self.px.set_dir_servo_angle(0)
                self.px.forward(REVERSE_SPEED)
                time.sleep(2.0)
                
                print("SCOUT: Pivoting...")
                self.px.set_dir_servo_angle(40)
                self.px.forward(NORMAL_SPEED)
                time.sleep(1.0) 
                
                self.px.set_dir_servo_angle(0)
                continue

            # PRIORITY 2: EUREKA (MAGNET) - PERSISTENT STOP
            if self.eureka_event:
                self.status = "EUREKA DETECTED"
                print("SCOUT: EUREKA! Stopping Engine.")
                self.px.stop()
                
                if self.sio:
                    self.sio.emit('alert', {'type': 'eureka', 'msg': 'Subsurface Anomaly Detected!'})
                
                self.say("Subsurface Anomaly Detected. Scouting Suspended.")
                self.running = False
                break 

            # PRIORITY 3: OBSTACLE
            if self.obstacle_detected:
                self.status = "AVOIDING OBSTACLE"
                self.px.set_dir_servo_angle(30)
                self.px.forward(NORMAL_SPEED)
                time.sleep(0.1)
                continue

            # DEFAULT: FORWARD SCOUT
            self.status = "SCOUTING"
            self.px.set_dir_servo_angle(0)
            self.px.forward(NORMAL_SPEED)
            time.sleep(0.1)

