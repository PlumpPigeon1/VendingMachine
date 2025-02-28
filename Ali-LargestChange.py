import cv2
import numpy as np
from picamera2 import Picamera2
import json
import time

def find_most_changed_chunk(gray1, gray2, grid_points):
    """Find the chunk with the most change between two images."""
    diff = cv2.absdiff(gray1, gray2)
    
    rows = len(grid_points) - 1  # Number of rows is len(grid_points) - 1
    cols = len(grid_points[0]) - 1  # Number of columns is len(grid_points[0]) - 1
    
    max_change = 0
    max_chunk = None
    for i in range(rows):
        for j in range(cols):
            polygon_points = np.array([grid_points[i][j], grid_points[i][j+1], 
                                     grid_points[i+1][j+1], grid_points[i+1][j]], dtype=np.int32)
            mask = np.zeros_like(diff, dtype=np.uint8)
            cv2.fillPoly(mask, [polygon_points], (255, 255, 255))
            all = np.sum(mask)
            
            masked_img = cv2.bitwise_and(diff, mask)
            change_value = np.sum(masked_img > 50)/all
            
            if change_value > 1.0e-4 and change_value > max_change:
                max_change = change_value
                max_chunk = (i, j)
                
    return max_chunk

def load_points_from_config():
    with open('calibration.conf', 'r') as f:
        points_as_lists = json.load(f)
    points = [[tuple(point) for point in sublist] for sublist in points_as_lists]
    return points

def update_data_file(chunk, cols):
    """Update data.txt by decreasing the quantity at the chunk position"""
    try:
        if chunk is not None:
            i, j = chunk
            # Map (i,j) to linear index: index = i * cols + j
            index = i * (cols-1) + j
            
            # Load current data
            with open('data.txt', 'r') as f:
                data = json.load(f)
            
            if str(index) in data:
                item_dict = data[str(index)]
                item_name = list(item_dict.keys())[0]  # e.g., "Layz"
                current_quantity = int(item_dict[item_name])  # e.g., "9" as int
                
                if current_quantity > 0:
                    item_dict[item_name] = str(current_quantity - 1)  # Update as string
                    data[str(index)] = item_dict
                    
                    # Write updated data back
                    with open('data.txt', 'w') as f:
                        json.dump(data, f, indent=4)
                    print(f"Decreased {item_name} at position {index} to {current_quantity - 1}")
                else:
                    print(f"Quantity at position {index} is already 0")
            else:
                print(f"No data found for position {index}")
    except Exception as e:
        print(f"Error updating data file: {e}")

def main():
    grid_points = load_points_from_config()
    rows = len(grid_points) - 1  # Dynamic rows
    cols = len(grid_points[0]) - 1  # Dynamic columns
    
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
    
    camera_controls = {
        "AeEnable": False,
        "AwbEnable": False,
        "AnalogueGain": 15.0,
        "ExposureTime": 20000,
        "ColourGains": (1.5, 1.5),
    }
    
    print(f"Grid size: {rows} rows x {cols} columns")
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
                update_data_file(max_chunk, cols)
                
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
