import time
import threading
import math
import subprocess
from robot_hat import Music, Grayscale_Module, Ultrasonic
from picarx import Picarx
from terraquest_sensors import TerraQuestSensors
import socketio 

print("SCOUT MODULE LOADED - V2 (NO TTS IMPORT)")

# Tuning Constants("SCOUT MODULE LOADED - V2 (NO TTS IMPORT)")

# Tuning Constants
CLIFF_THRESHOLD = 200     # Darker < 200 means drop-off or black line
OBSTACLE_DIST_CM = 25     # Arc turn if closer than this
MAG_EUREKA_GAUSS = 0.6    # Anomaly threshold
NORMAL_SPEED = 30
TURN_SPEED = 40
REVERSE_SPEED = -40

class TerraQuestScout:
    def __init__(self, sio_client=None):
        self.px = Picarx()
        self.sensors = TerraQuestSensors()
        self.gs = Grayscale_Module("A0", "A1", "A2")
        self.us = Ultrasonic("D2", "D3")
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
        
        # State Flags
        self.cliff_detected = False
        self.obstacle_detected = False
        self.eureka_event = False
        
        # Threads
        self.nav_thread = threading.Thread(target=self.navigation_loop)
        self.sensor_thread = threading.Thread(target=self.sensor_loop)
        self.nav_thread.daemon = True
        self.sensor_thread.daemon = True

    def start(self):
        self.running = True
        self.sensor_thread.start()
        self.nav_thread.start()
        print("SCOUT: Engine Started")
        self.say("Scout Engine Online")

    def stop(self):
        self.running = False
        self.px.stop()
        print("SCOUT: Engine Stopped")
        
    # ... (sensor_loop omitted, no changes needed to logic itself)
    # ... but wait, I can't use replace_file_content to skip chunks. 
    # I should use multi_replace or just match the relevant blocks.
    # Actually, I'll just check where tts.say is used.

    # Re-implementing just the methods that use tts.say 
    # Wait, replace_file_content replaces a contiguous block. 
    # I will replace the start method first.


    def sensor_loop(self):
        """High-frequency sensor polling"""
        while self.running:
            # 1. Edge Detection (Critical - 50Hz)
            cliff_vals = self.gs.get_grayscale_data()
            if any(v < CLIFF_THRESHOLD for v in cliff_vals):
                self.cliff_detected = True
            else:
                self.cliff_detected = False
            
            # 2. UV Sensor (High Value Event)
            if self.sensors.ltr:
                try:
                    als, uvs = self.sensors.get_light_data()
                    if uvs > 8: # High UV Index
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
                self.px.forward(REVERSE_SPEED) # Reverse
                time.sleep(2.0)
                
                print("SCOUT: Pivoting...")
                # Pivot: Left wheels back, Right wheels forward (or turn servo)
                # PicarX turn logic: 
                self.px.set_dir_servo_angle(40)
                self.px.forward(NORMAL_SPEED) # Turn out
                time.sleep(1.0) 
                
                self.px.set_dir_servo_angle(0)
                # Reset Safety flag implicitly by moving away (sensor loop updates)
                continue

            # PRIORITY 2: EUREKA (MAGNET)
            if self.eureka_event:
                self.status = "EUREKA"
                print("SCOUT: EUREKA! Anomaly Detected.")
                self.px.stop()
                
                # Alerts
                if self.sio:
                    self.sio.emit('alert', {'type': 'eureka', 'msg': 'Subsurface Anomaly Detected!'})
                
                self.say("Subsurface Anomaly Detected")
                # self.music.sound_play_threaded('./alert.wav') # Assume file exists or use beep
                
                time.sleep(3.0) # Wait for inspection
                
                self.eureka_event = False # Reset flag
                continue

            # PRIORITY 3: OBSTACLE
            if self.obstacle_detected:
                self.status = "AVOIDING OBSTACLE"
                self.px.set_dir_servo_angle(30) # Shallow arc
                self.px.forward(NORMAL_SPEED)
                # Don't sleep long, check sensors rapidly
                time.sleep(0.1)
                continue

            # DEFAULT: FORWARD SCOUT
            self.status = "SCOUTING"
            self.px.set_dir_servo_angle(0)
            self.px.forward(NORMAL_SPEED)
            time.sleep(0.1)
