from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import random
import time
import threading
import urllib.request
import json
from robot_hat import Servo

# --- Sound Effects via Robot HAT Speaker ---
SOUND_AVAILABLE = False
try:
    from robot_hat import Music
    import struct
    import wave
    import math
    import os
    
    _music = Music()
    _sound_dir = os.path.join(os.path.dirname(__file__), 'sounds')
    os.makedirs(_sound_dir, exist_ok=True)
    
    def _generate_tone_wav(filepath, frequencies, duration_each=0.15, sample_rate=22050, volume=1.0):
        """Generate a .wav file with a sequence of tones."""
        samples = []
        for freq in frequencies:
            num_samples = int(sample_rate * duration_each)
            for i in range(num_samples):
                t = i / sample_rate
                val = volume * math.sin(2 * math.pi * freq * t)
                # Fade in/out to avoid clicks
                envelope = min(i / 200, (num_samples - i) / 200, 1.0)
                samples.append(int(val * envelope * 32767))
        with wave.open(filepath, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack('<' + 'h' * len(samples), *samples))
    
    # Generate tone files
    _prime_wav = os.path.join(_sound_dir, 'prime.wav')
    _danger_wav = os.path.join(_sound_dir, 'danger.wav')
    
    # Prime Site: ascending happy chime (C5 → E5 → G5 → C6)
    _generate_tone_wav(_prime_wav, [523, 659, 784, 1047], duration_each=0.12)
    # Danger: descending alarm (G4 → E4 → C4, repeated)
    _generate_tone_wav(_danger_wav, [392, 330, 262, 392, 330, 262], duration_each=0.1)
    
    _music.music_set_volume(100)
    # Also max out system ALSA volume
    import subprocess
    try:
        subprocess.run(['amixer', 'sset', 'Master', '100%'], capture_output=True)
    except: pass
    try:
        subprocess.run(['amixer', 'sset', 'PCM', '100%'], capture_output=True)
    except: pass
    SOUND_AVAILABLE = True
    print("✓ Sound effects initialized (Robot HAT speaker, volume MAX)")
except Exception as e:
    print(f"⚠ Sound init warning (non-fatal): {e}")

# Vilib/Camera availability flag
VILIB_AVAILABLE = False

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
CORS(app)

import logging
# Completely silence Flask/Werkzeug request logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
log.disabled = True

# Also override the internal request logger to be sure
from werkzeug.serving import WSGIRequestHandler
def log_request(self, code='-', size='-'): 
    return
WSGIRequestHandler.log_request = log_request

def start_vilib():
    global VILIB_AVAILABLE
    try:
        from vilib import Vilib
        print("Initializing Vilib Camera...")
        Vilib.camera_start(vflip=False, hflip=False)
        # Disable local display (HDMI) to prevent "no gui" errors in SSH
        Vilib.display(local=False, web=True)
        
        # --- NEW: Image Recognition Overlay ---
        # Check for dependencies first to avoid Vilib thread crash
        try:
            import tflite_runtime
            # If successful, try generic object detection
            try:
                Vilib.object_detect_switch(True)
                print("Vilib Object Detection Enabled")
            except Exception as e:
                print(f"Vilib Object Enable Failed: {e}")
        except ImportError:
            print("Module 'tflite_runtime' not found. Object detection disabled.")
            # Fallback to Face Detection (uses OpenCV usually)
            try:
                Vilib.face_detect_switch(True) 
                print("Vilib Face Detection Enabled (Fallback)")
            except Exception as e:
                print(f"Face Detection Enable Failed: {e}")

        VILIB_AVAILABLE = True
        print("Vilib Camera Started Successfully")
        
    except (ImportError, RuntimeError) as e:
        VILIB_AVAILABLE = False
        print(f"⚠ CAMERA WARNING: Could not initialize Vilib/Camera: {e}")
        print("Video feed will be disabled, but other systems will continue to run.")

# Always start camera thread; it handles its own availability check internally
camera_thread = threading.Thread(target=start_vilib)
camera_thread.daemon = True
camera_thread.start()

# Integrate Rover & Scout
import sys
import os
# Add parent dir to path to find terraquest_base and scout
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from terraquest_base import TerraQuestRover
from terraquest_scout import TerraQuestScout

# Global Instances
rover = None      # Manual Rover
scout = None      # Autonomous Scout
rover_thread = None

def start_rover_thread():
    global rover, rover_thread
    if rover is None:
        rover = TerraQuestRover()
    
    # Check if thread is already running
    if rover_thread is None or not rover_thread.is_alive():
        rover.running = True
        rover_thread = threading.Thread(target=rover.run)
        rover_thread.daemon = True
        rover_thread.start()
        print("Rover Thread Started (Idle)")

def force_cleanup_gpio():
    """Force-release any GPIO pins held by a previous crashed process."""
    try:
        import lgpio
        # Close any stale lgpio chip handles (typically 0-15)
        for handle in range(16):
            try:
                lgpio.gpiochip_close(handle)
            except:
                pass
        print("✓ GPIO cleanup complete (stale handles released)")
    except ImportError:
        print("⚠ lgpio not available, skipping GPIO cleanup")
    except Exception as e:
        print(f"⚠ GPIO cleanup warning (non-fatal): {e}")

# Force-release GPIO before any hardware init
force_cleanup_gpio()

# Initialize rover logic on app start with retry logic
max_retries = 3
retry_delay = 2  # seconds

for attempt in range(max_retries):
    try:
        print(f"Attempting to initialize rover (attempt {attempt + 1}/{max_retries})...")
        start_rover_thread()
        print("✓ Rover initialized successfully!")
        break
    except Exception as e:
        print(f"✗ Failed to start rover thread (attempt {attempt + 1}/{max_retries}): {e}")
        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("⚠ WARNING: Rover initialization failed after all retries. Sensor data will not be available.")
            print(f"Error details: {e}")
            import traceback
            traceback.print_exc()


@app.route('/')
def index():
    return render_template('index.html')

# Sound effect cooldown tracker
_last_sound_time = 0
_SOUND_COOLDOWN = 3  # seconds between sounds

@app.route('/api/sound/prime', methods=['POST'])
def sound_prime():
    global _last_sound_time
    if SOUND_AVAILABLE:
        now = time.time()
        if now - _last_sound_time > _SOUND_COOLDOWN:
            _last_sound_time = now
            _music.sound_play_threading(_prime_wav)
            return jsonify({'status': 'playing prime sound'})
        return jsonify({'status': 'cooldown'})
    return jsonify({'error': 'sound not available'}), 400

@app.route('/api/sound/danger', methods=['POST'])
def sound_danger():
    global _last_sound_time
    if SOUND_AVAILABLE:
        now = time.time()
        if now - _last_sound_time > _SOUND_COOLDOWN:
            _last_sound_time = now
            _music.sound_play_threading(_danger_wav)
            return jsonify({'status': 'playing danger sound'})
        return jsonify({'status': 'cooldown'})
    return jsonify({'error': 'sound not available'}), 400

@app.route('/api/scout/start', methods=['POST'])
def start_scout():
    global scout, rover
    print("API: Received Scout Start Request")
    
    if rover is None:
        return jsonify({'error': 'Rover hardware not initialized'}), 500

    # Only initialize scout once
    if scout is None:
        try:
            print("INITIALIZING SCOUT ENGINE...")
            print("Creating TerraQuestScout with shared hardware...")
            # Share both hardware (px) and sensors to avoid I2C/Port conflicts
            scout = TerraQuestScout(
                px_instance=rover.px, 
                sensors_instance=rover.sensors, 
                sio_client=socketio
            )
            print("Scout instance created successfully")
        except Exception as e:
            print(f"SCOUT INIT FAILED: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Init failed: {e}'}), 500
    
    # Start the scout movement
    if not scout.running:
        try:
            # Ensure base rover isn't doing anything
            rover.stop()
            rover.mission_active = False 
            
            print("LAUNCHING SCOUT THREADS...")
            scout.start()
            
            # Auto-stop after 5 seconds
            def auto_stop():
                time.sleep(5)
                if scout and scout.running:
                    print("AUTO-STOPPING SCOUT AFTER 5 SECONDS")
                    scout.stop()
            
            auto_stop_thread = threading.Thread(target=auto_stop)
            auto_stop_thread.daemon = True
            auto_stop_thread.start()
            
            return jsonify({'status': 'Scout Started (5s auto-stop)'})
        except Exception as e:
            print(f"SCOUT START FAILED: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Start failed: {e}'}), 500
    else:
        return jsonify({'status': 'Scout Already Running'})

@app.route('/api/scout/stop', methods=['POST'])
def stop_scout():
    if scout and scout.running:
        scout.stop()
        return jsonify({'status': 'Scout Stopped'})
    return jsonify({'error': 'Scout not running'})

def read_tof_distance(tof_sensor):
    """
    Read distance from ToF sensor with error handling
    Returns distance in cm, or -1 if error/timeout
    """
    try:
        if tof_sensor is None:
            return -1
            
        # Wait for data to be ready (with timeout)
        timeout = time.time() + 1.0  # 1 second timeout
        while not tof_sensor.data_ready:
            if time.time() > timeout:
                return -1
            time.sleep(0.01)
        
        # Get distance
        dist = tof_sensor.distance
        
        # Clear interrupt for next reading
        tof_sensor.clear_interrupt()
        
        return dist if dist > 0 else -1
    
    except Exception as e:
        return -1


@app.route('/api/demo', methods=['POST'])
def run_demo():
    """Simple choreographed demo movement"""
    global rover
    
    if rover is None:
        return jsonify({'error': 'Rover not initialized'}), 500
    
    def demo_sequence():
        radar_running = {'active': True}  # Flag to control radar thread
        
        def radar_sweep_continuous():
            """Continuously sweep radar servo back and forth during demo"""
            try:
                servo_radar = Servo("P3")
                socketio.emit('radar_status', {'status': 'scanning'})
                print("DEMO: Radar servo started (continuous sweep)")
                
                while radar_running['active']:
                    # Sweep forward: -90° to +90°
                    for angle in range(-90, 91, 10):
                        if not radar_running['active']:
                            break
                        servo_radar.angle(angle)
                        time.sleep(0.15)
                        socketio.emit('radar_update', {'angle': angle, 'distance': 100})
                        print(f"RADAR: {angle}°")
                    
                    # Sweep backward: +90° to -90°
                    for angle in range(90, -91, -10):
                        if not radar_running['active']:
                            break
                        servo_radar.angle(angle)
                        time.sleep(0.15)
                        socketio.emit('radar_update', {'angle': angle, 'distance': 100})
                        print(f"RADAR: {angle}°")
                
                # Return to center when done
                servo_radar.angle(0)
                socketio.emit('radar_status', {'status': 'complete'})
                print("DEMO: Radar servo stopped")
                
            except Exception as e:
                print(f"RADAR ERROR: {e}")
                import traceback
                traceback.print_exc()
                socketio.emit('radar_status', {'status': 'error', 'message': str(e)})
        
        # Start radar sweep in background thread
        radar_thread = threading.Thread(target=radar_sweep_continuous, daemon=True)
        radar_thread.start()
        
        try:
            px = rover.px
            print("DEMO: Starting choreographed sequence...")
            
            # 1. Move forward for 1 second (50% reduced)
            print("DEMO: Moving forward...")
            px.set_dir_servo_angle(0)
            px.forward(30)
            time.sleep(1)  # Reduced from 2 to 1 second
            px.stop()
            time.sleep(0.5)
            
            # 2. Pan camera left and right
            print("DEMO: Panning camera...")
            px.set_cam_pan_angle(-30)  # Pan left
            time.sleep(0.5)
            px.set_cam_pan_angle(30)   # Pan right
            time.sleep(0.5)
            px.set_cam_pan_angle(0)    # Center
            time.sleep(0.5)
            
            # 3. Turn left
            print("DEMO: Turning left...")
            px.set_dir_servo_angle(-40)
            px.forward(30)
            time.sleep(0.8)
            px.stop()
            px.set_dir_servo_angle(0)
            time.sleep(0.5)
            
            # 4. Move forward again after turn
            print("DEMO: Moving forward after turn...")
            px.set_dir_servo_angle(0)
            px.forward(30)
            time.sleep(0.75)  # Reduced from 1.5 to 0.75 seconds (50%)
            px.stop()
            time.sleep(0.5)
            
            # 5. Pan camera again
            print("DEMO: Panning camera again...")
            try:
                px.set_cam_pan_angle(-30)  # Pan left
                time.sleep(0.5)
                px.set_cam_pan_angle(30)   # Pan right
                time.sleep(0.5)
                px.set_cam_pan_angle(0)    # Center
                time.sleep(0.5)
                print("DEMO: Step 5 complete")
            except Exception as e:
                print(f"DEMO: Error in step 5 (pan camera): {e}")
            
            # 6. Tilt down and slowly pan left/right once
            print("DEMO: Tilting down and panning...")
            try:
                px.set_cam_tilt_angle(-15)  # Tilt DOWN less (was -30, hitting ground)
                time.sleep(0.5)
                
                # Very slow pan left and right - once
                px.set_cam_pan_angle(-30)  # Pan left
                time.sleep(2.0)  # Very slow (was 1.2)
                px.set_cam_pan_angle(30)   # Pan right
                time.sleep(2.0)  # Very slow (was 1.2)
                
                # End in left position
                px.set_cam_pan_angle(-30)  # Pan left
                time.sleep(0.5)
                print("DEMO: Step 6 complete")
            except Exception as e:
                print(f"DEMO: Error in step 6 (tilt/pan): {e}")
            
            # Stop radar sweep
            radar_running['active'] = False
            
            # Final stop
            px.stop()
            print("DEMO: Sequence complete!")
            
        except Exception as e:
            print(f"DEMO ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Run demo in background thread
    demo_thread = threading.Thread(target=demo_sequence)
    demo_thread.daemon = True
    demo_thread.start()
    
    return jsonify({'status': 'Demo started'})

@app.route('/api/mission/start', methods=['POST'])
def start_mission():
    """Activated via 'MANUAL CONTROL' button"""
    global scout
    # Stop autonomous scouting if it was running
    if scout and scout.running:
        scout.stop()
        
    if rover:
        rover.mission_active = True
        return jsonify({'status': 'Manual Control Active', 'active': True})
    return jsonify({'error': 'Rover not initialized'}), 500

@app.route('/api/mission/stop', methods=['POST'])
def stop_mission():
    global scout
    if scout and scout.running:
        scout.stop()
    if rover:
        rover.mission_active = False
        rover.stop()
        return jsonify({'status': 'System Stopped', 'active': False})
    return jsonify({'error': 'Rover not initialized'}), 500

@app.route('/api/mission/status')
def mission_status():
    status = {'active': False, 'scouting': False}
    if rover:
        status['active'] = rover.mission_active
    if scout:
        status['scouting'] = scout.running
    return jsonify(status)

@app.route('/api/control/move', methods=['POST'])
def control_move():
    global scout
    if rover:
        # User Manual Takeover (Stop Scout if running)
        if scout and scout.running:
            scout.stop()
            socketio.emit('alert', {'type': 'info', 'msg': 'Manual Takeover: Scout Stopped'})

        data = request.json
        speed = int(data.get('speed', 0))
        angle = int(data.get('angle', 0))
        rover.manual_drive(speed, angle)
        return jsonify({'status': 'ok', 'speed': speed, 'angle': angle})
    return jsonify({'error': 'Rover not initialized'}), 400

@app.route('/api/control/camera', methods=['POST'])
def control_camera():
    if rover:
        data = request.json
        pan = int(data.get('pan', 0))
        tilt = int(data.get('tilt', 0))
        rover.manual_camera(pan, tilt)
        return jsonify({'status': 'ok', 'pan': pan, 'tilt': tilt})
    return jsonify({'error': 'Rover not initialized'}), 400

@app.route('/data')
def get_sensor_data():
    if rover:
        # If rover is initialized, attempt to refresh sensors manually if not running
        # (Optional: calling check_cliff/obstacle updates the values even if not in auto-loop)
        if not rover.mission_active:
             try:
                 rover.check_cliff()
                 rover.check_obstacle()
             except: pass

        data = {
            'lux': rover.light_data['als'], 
            'uv_index': rover.light_data['uvs'],
            'magnetic': rover.mag_data['strength'],
            'mag_anomaly': rover.mag_data['anomaly'],
            'moisture': round(rover.distance, 1) if rover.distance else 0,
            'temp': rover.env_data.get('temp', 0),          
            'co2':  rover.env_data.get('gas', 0),
            'humidity': rover.env_data.get('humidity', 0),
            'altitude': rover.env_data.get('altitude', 0),
            'pressure': rover.env_data.get('pressure', 0)
        }
        # --- SCORING LOGIC (Bimodal Fusion) ---
        # Goal: Baseline ~50-55 (fluctuating), magnet detection → 85+

        # 1. DPS (Discovery Potential Score) - "Is there something cool here?"
        dps = 0
        
        # Magnetometer anomaly is the PRIMARY discovery driver
        mag_anom = data['mag_anomaly']
        if mag_anom > 200:
            dps += 100  # Very strong anomaly = max discovery
        elif mag_anom > 100:
            dps += 80
        elif mag_anom > 50:
            dps += 60   # Moderate anomaly
        elif mag_anom > 20:
            dps += 15   # Faint background noise (keeps baseline low)
        else:
            dps += 5    # Minimal baseline
            
        # Minor environmental bonus (keeps score fluctuating, not static)
        # Temperature in comfortable range adds a small bump
        temp = data['temp']
        if 18 < temp < 35:
            dps += 5
        
        # Gas resistance bonus (small, just for fluctuation)
        if data['co2'] > 50000:
            dps += 5

        dps = min(100, dps)  # Cap at 100

        # 2. TSS (Terrain Safety Score) - "Is it safe to be there?"
        tss = 80  # Start at 80 (not 100) so baseline AWS is lower
        
        # Air Quality: Lower gas resistance = pollution (aggressive for demo)
        if data['co2'] < 10000:
            tss -= 65   # Very bad air → AWS crashes to teens
        elif data['co2'] < 30000:
            tss -= 50   # Bad air → AWS drops to 20s
        elif data['co2'] < 50000:
            tss -= 30   # Moderate → AWS drops to 30s
            
        # Humidity: High humidity (>80%) = soft soil risk
        if data['humidity'] > 80:
            tss -= 15
        elif data['humidity'] > 60:
            tss -= 5   # Mild deduction for moderate humidity
            
        # Pressure: Unstable conditions
        if data['pressure'] < 950 or data['pressure'] > 1050:
            tss -= 15
            
        tss = max(0, min(100, tss))  # Clamp 0-100

        # 3. AWS Fusion (Weighted)
        # With baseline: TSS~70, DPS~10-20 → AWS = (70*0.6)+(15*0.4) = 42+6 = ~48-55
        # With magnet:   TSS~70, DPS~80-100 → AWS = (70*0.6)+(90*0.4) = 42+36 = ~78-85+
        aws = int((tss * 0.6) + (dps * 0.4))
        
        # Add natural fluctuation (±3) so the score looks alive, not static
        aws += random.randint(-3, 3)
        aws = max(0, min(100, aws))  # Clamp 0-100

        data['aws'] = aws
        data['tss'] = tss
        data['dps'] = dps  # Send DPS value for potential UI use

        return jsonify(data)
    
    # Fallback if rover not ready
    data = {
        'lux': 0, 'uv_index': 0, 'magnetic': 0, 'mag_anomaly': 0,
        'moisture': 0, 'temp': 0, 'co2': 0, 'humidity': 0, 'altitude': 0, 'pressure': 0,
        'aws': 0, 'tss': 0
    }
    return jsonify(data)


@app.route('/api/location')
def get_location():
    try:
        # Fetch location based on the server's public IP
        with urllib.request.urlopen('https://ipapi.co/json/', timeout=5) as response:
            data = json.loads(response.read().decode())
            return jsonify({
                'lat': data.get('latitude'),
                'lon': data.get('longitude'),
                'city': data.get('city'),
                'region': data.get('region'),
                'org': data.get('org')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/thermal')
def get_thermal_data():
    if rover and rover.thermal_frame:
        # Return list of 768 dicts or just values
        # Just values is smaller payload 
        return jsonify(rover.thermal_frame)
    return jsonify([])

if __name__ == '__main__':
    # Use socketio.run instead of app.run
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
