
import cv2
import numpy as np
from picamera2 import Picamera2
import json
import time

def find_most_changed_chunk(gray1, gray2, grid_points):
    """Find the chunk with the most change between two images."""
    diff = cv2.absdiff(gray1, gray2)

    max_change = 0
    max_chunk = None
    for i in range(4):
        for j in range(3):
            polygon_points = np.array([grid_points[i][j], grid_points[i][j+1], grid_points[i+1][j], grid_points[i+1][j+1]], dtype=np.int32)
            mask = np.zeros_like(diff, dtype=np.uint8)
            cv2.fillPoly(mask, [polygon_points], (255, 255, 255))
            all_pixels = np.sum(mask)

            masked_img = cv2.bitwise_and(diff, mask)
            change_value = np.sum(masked_img > 50) / all_pixels  

            if change_value > 1.0e-6 and change_value > max_change:
                max_change = change_value
                max_chunk = (i, j)  

    return max_chunk

def load_points_from_config():
    """Load the grid points from a JSON configuration file."""
    with open('calibration.conf', 'r') as f:
        points_as_lists = json.load(f)
    points = [[tuple(point) for point in sublist] for sublist in points_as_lists]    
    return points

def update_item_in_file(chunk):
    """Decrease the corresponding item in items.txt based on chunk."""
    if chunk is None:
        return

    filename = "items.txt"
    item_key = f"item_{chunk[0]}_{chunk[1]}"
    updated_lines = []

    with open(filename, "r") as f:
        lines = f.readlines()

    for line in lines:
        item, quantity = line.strip().split()
        quantity = int(quantity)
        
        if item == item_key:
            quantity = max(0, quantity - 1)  # Prevent negative values
            print(f"Updated {item}: {quantity}")

        updated_lines.append(f"{item} {quantity}\n")

    with open(filename, "w") as f:
        f.writelines(updated_lines)

def main():
    grid_points = load_points_from_config()
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))

    # Set fixed white balance, exposure, and gain
    camera_controls = {
        "AeEnable": False,
        "AwbEnable": False,
        "AnalogueGain": 15.0,
        "ExposureTime": 20000,
        "ColourGains": (1.5, 1.5),
    }
    picam2.set_controls(camera_controls)
    picam2.start()

    print("Press 'q' to quit the loop.")
    prev_frame = None

    while True:
        frame = picam2.capture_array()
        curr_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_frame is not None:
            max_chunk = find_most_changed_chunk(curr_frame, prev_frame, grid_points)
            
            if max_chunk is not None:
                print(f"Detected change at: {max_chunk}")
                update_item_in_file(max_chunk)
                
                print("Pausing detection for 3 seconds...")
                time.sleep(3)  # Pause execution for 3 seconds

        prev_frame = curr_frame

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    picam2.stop()
    cv2.destroyAllWindows()

main()
