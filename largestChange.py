import cv2
import numpy as np
from picamera2 import Picamera2
import json


def find_most_changed_chunk(gray1, gray2, grid_points):
    """Find the chunk with the most change between two images."""
    # Compute absolute difference between the two images
    diff = cv2.absdiff(gray1, gray2)

    max_change = 0
    max_chunk = None
    for i in range(4):
        for j in range(3):
            polygon_points = np.array([grid_points[i][j], grid_points[i][j+1], grid_points[i+1][j], grid_points[i+1][j+1]], dtype=np.int32)
            # Create a mask with the same size as the image, filled with zeros (black)
            mask = np.zeros_like(diff, dtype=np.uint8)
            
            # Fill the polygon area with white color (255)
            cv2.fillPoly(mask, [polygon_points], (255, 255, 255))
            all = np.sum(mask)

            # Bitwise AND to keep only the pixels inside the polygon
            masked_img = cv2.bitwise_and(diff, mask)

            # Calculate the sum of pixel values inside the polygon with threshold
            change_value = np.sum(masked_img > 50)/all  # Change threshold for pixel intensity difference
            if change_value > 1.0e-6 and change_value > max_change:
                max_change = change_value
                max_chunk = (i, j)  # Store the grid chunk coordinates

    return max_chunk

def load_points_from_config():
    # Load the points from the JSON file
    with open('calibration.conf', 'r') as f:
        points_as_lists = json.load(f)
    
    # Convert lists back to tuples
    points = [[tuple(point) for point in sublist] for sublist in points_as_lists]    
    return points

def main():
    grid_points = load_points_from_config()
    # Initialize Picamera2
    picam2 = Picamera2()

    # Configure the camera and start it
    picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))

    # Set fixed white balance, exposure, and gain
    camera_controls = {
        "AeEnable": False,  # Disable Auto Exposure
        "AwbEnable": False,  # Disable Auto White Balance
        "AnalogueGain": 15.0,  # Fixed gain (optional, adjust as needed)
        "ExposureTime": 20000,  # Fixed exposure time in microseconds
        "ColourGains": (1.5, 1.5),  # Adjust red and blue gains for white balance
    }
    picam2.set_controls(camera_controls)
    picam2.start()

    print("Press 'q' to quit the loop.")

    # Initialize variables for storing consecutive frames
    prev_frame = None

    while True:
        # Capture the current frame
        frame = picam2.capture_array()
        curr_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # If there's a previous frame, calculate the difference
        if prev_frame is not None:
            # Compute the absolute difference between frames
            max_chunk = find_most_changed_chunk(curr_frame, prev_frame, grid_points)
            if (max_chunk != None):
                print(max_chunk)
            # Display the current frame and the difference
            cv2.imshow("Current Frame", curr_frame)

        # Update the previous frame to the current frame
        prev_frame = curr_frame

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    picam2.stop()
    cv2.destroyAllWindows()


main()
