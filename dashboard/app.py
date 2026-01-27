from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import random
import time
import threading

# Try importing vilib, if not available (e.g. on dev machine), mock it or skip
try:
    from vilib import Vilib
    VILIB_AVAILABLE = True
except ImportError:
    VILIB_AVAILABLE = False
    print("Warning: Vilib not found. Video feed integration will be skipped/mocked.")

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
    if VILIB_AVAILABLE:
        Vilib.camera_start(vflip=False, hflip=False)
        # Disable local display (HDMI) to prevent "no gui" errors in SSH
        Vilib.display(local=False, web=True)
        print("Vilib Camera Started")

# Start camera in a separate thread to not block Flask
if VILIB_AVAILABLE:
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

# Initialize rover logic on app start
try:
    start_rover_thread()
except Exception as e:
    print(f"Failed to start rover thread: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scout/start', methods=['POST'])
def start_scout():
    global scout, rover
    print("API: Received Scout Start Request")
    
    if rover is None:
        return jsonify({'error': 'Rover hardware not initialized'}), 500

    if scout is None:
        try:
            print("INITIALIZING SCOUT ENGINE...")
            # Share both hardware (px) and sensors to avoid I2C/Port conflicts
            scout = TerraQuestScout(
                px_instance=rover.px, 
                sensors_instance=rover.sensors, 
                sio_client=socketio
            )
        except Exception as e:
            print(f"SCOUT INIT FAILED: {e}")
            return jsonify({'error': f'Init failed: {e}'}), 500
    
    if not scout.running:
        try:
            # Ensure base rover isn't doing anything
            rover.stop()
            rover.mission_active = False 
            
            print("LAUNCHING SCOUT THREADS...")
            scout.start()
            return jsonify({'status': 'Scout Started'})
        except Exception as e:
            print(f"SCOUT START FAILED: {e}")
            return jsonify({'error': f'Start failed: {e}'}), 500
            
    return jsonify({'status': 'Scout Already Running'})

@app.route('/api/scout/stop', methods=['POST'])
def stop_scout():
    if scout and scout.running:
        scout.stop()
        return jsonify({'status': 'Scout Stopped'})
    return jsonify({'error': 'Scout not running'})

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
        'magnetic': rover.mag_data['strength'], 
        'mag_anomaly': rover.mag_data['anomaly'],
        'moisture': round(rover.distance, 1) if rover.distance else 0,
        'temp': rover.env_data.get('temp', 0),          
        'co2':  rover.env_data.get('gas', 0),
        'humidity': rover.env_data.get('humidity', 0),
        'altitude': rover.env_data.get('altitude', 0),
        # Pass pressure separately if needed, previously mapped to 'magnetic'
        'pressure': rover.env_data.get('pressure', 0)
    }
    return jsonify(data)
    
    # Fallback if rover not ready
    data = {
        'magnetic': 0, 'mag_anomaly': 0, 'moisture': 0, 'temp': 0, 'co2': 0, 'humidity': 0, 'altitude': 0, 'pressure': 0
    }
    return jsonify(data)

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
