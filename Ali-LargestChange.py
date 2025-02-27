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
            polygon_points = np.array([grid_points[i][j], grid_points[i][j+1], 
                                     grid_points[i+1][j], grid_points[i+1][j+1]], dtype=np.int32)
            mask = np.zeros_like(diff, dtype=np.uint8)
            cv2.fillPoly(mask, [polygon_points], (255, 255, 255))
            all = np.sum(mask)
            
            masked_img = cv2.bitwise_and(diff, mask)
            change_value = np.sum(masked_img > 50)/all
            
            if change_value > 1.0e-6 and change_value > max_change:
                max_change = change_value
                max_chunk = (i, j)
                
    return max_chunk

def load_points_from_config():
    with open('calibration.conf', 'r') as f:
        points_as_lists = json.load(f)
    points = [[tuple(point) for point in sublist] for sublist in points_as_lists]
    return points

def update_items_file(chunk):
    """Update items.txt by decreasing the value at the chunk position"""
    try:
        # Convert chunk coordinates to a single index (i*3 + j)
        if chunk is not None:
            i, j = chunk
            index = i * 3 + j
            
            # Read current values from file
            with open('items.txt', 'r') as f:
                values = [int(x.strip()) for x in f.read().split(',')]
            
            #Decrease the value at the detected chunk position if > 0
            if 0 <= index < len(values) and values[index] > 0:
                values[index] -= 1
                
                # Write updated values back to file
                with open('items.txt', 'w') as f:
                    f.write(','.join(map(str, values)))
                print(f"Decreased item count at position {index}. New values: {values}")
            else:
                print(f"No update at position {index}. Value is already 0 or invalid position.")
    except Exception as e:
        print(f"Error updating items file: {e}")

def main():
    grid_points = load_points_from_config()
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
    
    camera_controls = {
        "AeEnable": False,
        "AwbEnable": False,
        "AnalogueGain": 15.0,
        "ExposureTime": 20000,
        "ColourGains": (1.5, 1.5),
    }
    
    print("Press 'q' to quit the loop.")
    prev_frame = None
    
    while True:
        picam2.start()
        picam2.set_controls(camera_controls)
        
        # Capture frame
        frame = picam2.capture_array()
        curr_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if prev_frame is not None:
            max_chunk = find_most_changed_chunk(curr_frame, prev_frame, grid_points)
            if max_chunk is not None:
                print(f"Change detected at chunk: {max_chunk}")
                update_items_file(max_chunk)
                
                # Turn off camera for 2 seconds
                picam2.stop()
                cv2.imshow("Current Frame", curr_frame)  # Show frame before sleeping
                cv2.waitKey(1)  # Update display
                time.sleep(2)  # Sleep for 2 seconds
                
            else:
                cv2.imshow("Current Frame", curr_frame)
        
        prev_frame = curr_frame
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    picam2.stop()
    cv2.destroyAllWindows()

main()
