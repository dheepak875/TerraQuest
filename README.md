# TerraQuest Pilot 🚜💨

TerraQuest is an autonomous and manual control system for the **PiCar-X** rover platform. It features a web-based "Mission Control" dashboard that provides live video, sensor telemetry, and joystick controls.

## Features
*   **Autonomous Mission Mode**: Obstacle avoidance and cliff detection logic.
*   **Manual Control**: Virtual joystick for driving and sliders for camera pan/tilt.
*   **Live Dashboard**: 
    *   Real-time video feed.
    *   Ultrasonic distance sensor display.
    *   Cliff sensor (floor brightness) monitoring.
    *   Start/Stop controls for autonomous mode.

## Hardware Requirements
*   SunFounder PiCar-X (Robot Hat, Servo Motors, Ultrasonic Sensor, Grayscale Module)
*   Raspberry Pi (3B+ or 4 recommended) with Camera Module

## Installation

1.  **Clone the repository** to your Raspberry Pi:
    ```bash
    git clone https://github.com/dheepak875/TerraQuest.git
    cd TerraQuest
    ```

2.  **Install Dependencies**:
    ```bash
    sudo pip3 install flask flask-cors vilib --break-system-packages
    ```
    *(Note: `vilib` is required for the camera feed. If it fails, the app will run without video)*

## Usage

### 1. Calibrate Sensors (Recommended)
Before running, calibrate the cliff sensors for your specific table surface.
```bash
sudo python3 calibrate_sensors.py
```
*   Note down values for "Table" (Safe) and "Air" (Cliff).
*   Update `cliff_threshold` in `terraquest_base.py` if needed (Default: 100).

### 2. Run Mission Control
Start the web dashboard (this also loads the rover logic in the background).

```bash
cd dashboard
sudo python3 app.py
```

### 3. Access Dashboard
Open a browser on your computer/phone and navigate to:
`http://<your-pi-ip>:5000` 
(e.g., `http://terraquest-2.local:5000`)

*   **Start Mission**: Activates autonomous roaming.
*   **Manual Control**: Use the joystick to drive when the mission is STOPPED.

## Project Structure
*   `terraquest_base.py`: Core rover logic (threading, sensors, movement).
*   `dashboard/`: Flask web application and UI templates.
*   `calibrate_sensors.py`: Tool for sensor debugging.
