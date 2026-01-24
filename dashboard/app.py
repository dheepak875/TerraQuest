from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
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
CORS(app)

def start_vilib():
    if VILIB_AVAILABLE:
        Vilib.camera_start(vflip=False, hflip=False)
        Vilib.display(local=True, web=True)
        print("Vilib Camera Started")

# Start camera in a separate thread to not block Flask
if VILIB_AVAILABLE:
    camera_thread = threading.Thread(target=start_vilib)
    camera_thread.daemon = True
    camera_thread.start()

# Integrate Rover
import sys
import os
# Add parent dir to path to find terraquest_base
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from terraquest_base import TerraQuestRover

# Global Rover Instance
rover = None
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

@app.route('/api/mission/start', methods=['POST'])
def start_mission():
    if rover:
        rover.mission_active = True
        return jsonify({'status': 'Mission Started', 'active': True})
    return jsonify({'error': 'Rover not initialized'}), 500

@app.route('/api/mission/stop', methods=['POST'])
def stop_mission():
    if rover:
        rover.mission_active = False
        rover.stop() # Force stop immediately
        return jsonify({'status': 'Mission Stopped', 'active': False})
    return jsonify({'error': 'Rover not initialized'}), 500

@app.route('/api/mission/status')
def mission_status():
    if rover:
        return jsonify({'active': rover.mission_active})
    return jsonify({'active': False})

@app.route('/api/control/move', methods=['POST'])
def control_move():
    if rover and not rover.mission_active:
        data = request.json
        speed = int(data.get('speed', 0))
        angle = int(data.get('angle', 0))
        rover.manual_drive(speed, angle)
        return jsonify({'status': 'ok', 'speed': speed, 'angle': angle})
    return jsonify({'error': 'Rover busy or not initialized'}), 400

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
            'magnetic': int(rover.env_data.get('pressure', 0)), # Mapping Pressure to Magnetic slot for now
            'moisture': round(rover.distance, 1) if rover.distance else 0,
            'temp': rover.env_data.get('temp', 0),          
            'co2':  rover.env_data.get('gas', 0),
            'humidity': rover.env_data.get('humidity', 0)
        }
        return jsonify(data)
        
    # Fallback if rover not ready
    data = {
        'magnetic': 0, 'moisture': 0, 'temp': 0, 'co2': 0
    }
    return jsonify(data)

if __name__ == '__main__':
    # Run on 0.0.0.0 to be accessible externally
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
