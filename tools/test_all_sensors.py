#!/usr/bin/env python3
"""
Diagnostic script to test sensor initialization
Run this to see which sensors are working and which are failing
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from terraquest_sensors import TerraQuestSensors
import time

print("=" * 60)
print("TerraQuest Sensor Diagnostic")
print("=" * 60)

print("\nInitializing sensors...")
sensors = TerraQuestSensors()

print("\n" + "=" * 60)
print("Testing Sensor Readings")
print("=" * 60)

for i in range(5):
    print(f"\n--- Reading #{i+1} ---")
    
    # Environment
    env = sensors.read_environment()
    print(f"Environment: Temp={env['temp']}°C, Humidity={env['humidity']}%, Pressure={env['pressure']}hPa, Gas={env['gas']}Ω")
    
    # Light/UV
    als, uvs = sensors.get_light_data()
    print(f"Light/UV: ALS={als} Lux, UV Index={uvs}")
    
    # Magnetometer
    strength, anomaly = sensors.get_magnetic_data()
    print(f"Magnetometer: Strength={strength}µT, Anomaly={anomaly}µT")
    
    # ToF Distance
    dist = sensors.get_distance()
    print(f"ToF Distance: {dist} cm")
    
    # Thermal (just check if we get data)
    thermal = sensors.get_thermal_frame()
    print(f"Thermal: {'OK' if len(thermal) == 768 else 'FAIL'} ({len(thermal)} values)")
    
    time.sleep(1)

print("\n" + "=" * 60)
print("Diagnostic Complete!")
print("=" * 60)
