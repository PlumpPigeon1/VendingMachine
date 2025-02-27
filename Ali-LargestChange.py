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
    for i in range(4):  # 4 rows in detection grid
        for j in range(3):  # 3 columns in detection grid
            polygon_points = np.array([grid_points[i][j], grid_points[i][j+1], 
                                     grid_points[i+1][j+1], grid_points[i+1][j]], dtype=np.int32)
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

def update_data_file(chunk):
    """Update data.txt by decreasing the value at the chunk position"""
    try:
        if chunk is not None:
            i, j = chunk
            # Map 4x3 detection grid to data.txt index (assuming it uses row*3 + col)
            index = i * 3 + j  # Matches your data.txt indexing
            
            # Load current data
            with open('data.txt', 'r') as f:
                data = json.load(f)
            
            if str(index) in data:
                # Assuming the value is a dict with a numeric value as the second part
                item_dict = data[str(index)]
                item_key = list(item_dict.keys())[0]  # e.g., "item_name"
                current_value = int(item_dict[item_key])
                
                if current_value > 0:
                    item_dict[item_key] = current_value - 1
                    data[str(index)] = item_dict
                    
                    # Write updated data back
                    with open('data.txt', 'w') as f:
                        json.dump(data, f, indent=4)
                    print(f"Decreased {item_key} at position {index} to {current_value - 1}")
                else:
                    print(f"Value at position {index} is already 0")
            else:
                print(f"No data found for position {index}")
    except Exception as e:
        print(f"Error updating data file: {e}")

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
        
        frame = picam2.capture_array()
        curr_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if prev_frame is not None:
            max_chunk = find_most_changed_chunk(curr_frame, prev_frame, grid_points)
            if max_chunk is not None:
                print(f"Change detected at chunk: {max_chunk}")
                update_data_file(max_chunk)
                
                picam2.stop()
                cv2.imshow("Current Frame", curr_frame)
                cv2.waitKey(1)
                time.sleep(2)
                
            else:
                cv2.imshow("Current Frame", curr_frame)
        
        prev_frame = curr_frame
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    picam2.stop()
    cv2.destroyAllWindows()

main()
