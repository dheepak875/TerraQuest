import time
import board
import busio
import math

try:
    import adafruit_mlx90640
    MLX_AVAILABLE = True
except ImportError:
    print("Error: adafruit-circuitpython-mlx90640 not installed.")
    MLX_AVAILABLE = False

def test_thermal():
    if not MLX_AVAILABLE:
        return

    i2c = board.I2C()
    try:
        mlx = adafruit_mlx90640.MLX90640(i2c)
        print("MLX90640 Initialized at 0x33")
        
        # Setup refresh rate
        mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
        
        frame = [0] * 768
        
        print("Starting Thermal Stream (Ctrl+C to stop)...")
        while True:
            try:
                mlx.getFrame(frame)
                
                # Stats
                min_t = min(frame)
                max_t = max(frame)
                avg_t = sum(frame) / len(frame)
                
                # Find hotspot
                max_index = frame.index(max_t)
                x = max_index % 32
                y = max_index // 32
                
                print(f"Min: {min_t:.1f}°C | Max: {max_t:.1f}°C (at {x},{y}) | Avg: {avg_t:.1f}°C")
                
                # Simple ASCII Visualizer (Downsampled 32x24 -> 32x12 for terminal aspect ratio)
                # print_ascii_art(frame) 
                
                time.sleep(0.5)
                
            except ValueError:
                # Often happens if I2C is too slow or packet dropped
                continue
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)

    except Exception as e:
        print(f"Failed to init MLX90640: {e}")

chars = " .:-=+*#%@"

def print_ascii_art(frame):
    # Downsample or just print every other row for terminal fit
    # 32 columns, 24 rows
    print("\033[H\033[J") # Clear screen code
    min_t = min(frame)
    max_t = max(frame)
    range_t = max_t - min_t
    
    if range_t == 0: range_t = 1
    
    for y in range(0, 24, 2): # Skip every other row
        row_str = ""
        for x in range(32):
            val = frame[y * 32 + x]
            norm = (val - min_t) / range_t
            char_idx = int(norm * (len(chars) - 1))
            row_str += chars[char_idx]
        print(row_str)

if __name__ == "__main__":
    test_thermal()
