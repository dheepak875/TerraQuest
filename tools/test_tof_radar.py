#!/usr/bin/env python3
"""
ToF Radar Test Script
Tests the VL53L4CD Time-of-Flight sensor mounted on a servo arm
Sweeps the servo 180 degrees and collects distance readings
"""

import time
import board
from adafruit_vl53l4cd import VL53L4CD
from robot_hat import Servo

# Configuration
SERVO_PIN = "P3"  # PWM 3 port on robot hat
SWEEP_MIN_ANGLE = -90  # Start angle (degrees)
SWEEP_MAX_ANGLE = 90   # End angle (degrees)
SWEEP_STEP = 10        # Angle increment per step
SWEEP_DELAY = 0.2      # Delay at each position (seconds)

def main():
    print("=" * 50)
    print("ToF Radar Test - VL53L4CD + Servo Sweep")
    print("=" * 50)
    
    # Initialize I2C and ToF sensor
    print("\n[1/2] Initializing ToF Sensor...")
    try:
        i2c = board.I2C()
        tof = VL53L4CD(i2c)
        
        # Configure sensor for optimal performance
        tof.inter_measurement = 0  # Continuous measurement
        tof.timing_budget = 200    # 200ms timing budget
        
        # Start ranging
        tof.start_ranging()
        print("✓ ToF Sensor Initialized (VL53L4CD)")
    except Exception as e:
        print(f"✗ Error initializing ToF sensor: {e}")
        return
    
    # Initialize Servo
    print("\n[2/2] Initializing Servo Motor...")
    try:
        servo = Servo(SERVO_PIN)
        servo.angle(0)  # Center position
        time.sleep(0.5)
        print(f"✓ Servo Initialized on {SERVO_PIN}")
    except Exception as e:
        print(f"✗ Error initializing servo: {e}")
        return
    
    print("\n" + "=" * 50)
    print("Starting Radar Sweep...")
    print("=" * 50)
    print(f"Sweep Range: {SWEEP_MIN_ANGLE}° to {SWEEP_MAX_ANGLE}°")
    print(f"Step Size: {SWEEP_STEP}°")
    print(f"Press Ctrl+C to stop\n")
    
    try:
        sweep_count = 0
        while True:
            sweep_count += 1
            print(f"\n--- Sweep #{sweep_count} ---")
            
            # Sweep from min to max
            for angle in range(SWEEP_MIN_ANGLE, SWEEP_MAX_ANGLE + 1, SWEEP_STEP):
                # Move servo to position
                servo.angle(angle)
                time.sleep(SWEEP_DELAY)
                
                # Read distance
                distance = read_distance(tof)
                
                # Display reading
                bar = create_distance_bar(distance, max_distance=400)
                print(f"Angle: {angle:4d}° | Distance: {distance:5.1f} cm | {bar}")
            
            # Sweep back from max to min
            for angle in range(SWEEP_MAX_ANGLE, SWEEP_MIN_ANGLE - 1, -SWEEP_STEP):
                # Move servo to position
                servo.angle(angle)
                time.sleep(SWEEP_DELAY)
                
                # Read distance
                distance = read_distance(tof)
                
                # Display reading
                bar = create_distance_bar(distance, max_distance=400)
                print(f"Angle: {angle:4d}° | Distance: {distance:5.1f} cm | {bar}")
    
    except KeyboardInterrupt:
        print("\n\nStopping radar sweep...")
    
    finally:
        # Return servo to center and cleanup
        print("Returning servo to center position...")
        servo.angle(0)
        time.sleep(0.5)
        print("Test complete!")


def read_distance(tof_sensor):
    """
    Read distance from ToF sensor with error handling
    Returns distance in cm, or -1 if error
    """
    try:
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
        # print(f"Error reading ToF: {e}")
        return -1


def create_distance_bar(distance, max_distance=400):
    """
    Create a visual bar representation of distance
    """
    if distance < 0:
        return "[NO DATA]"
    
    # Clamp distance to max
    distance = min(distance, max_distance)
    
    # Calculate bar length (40 characters max)
    bar_length = int((distance / max_distance) * 40)
    
    # Create bar
    bar = "█" * bar_length
    empty = "░" * (40 - bar_length)
    
    return f"[{bar}{empty}]"


if __name__ == "__main__":
    main()
