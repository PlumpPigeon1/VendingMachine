import cv2
import numpy as np
import json
import PySimpleGUIQt as sg
# import paramiko

global click_coordinates, grid_points, highlightCell, input, mask
mask = [[None] * 3, [None] * 3, [None] * 3, [None] * 3]
grid_points = []
click_coordinates = None
highlightCell = None
# Function to calculate the perpendicular distance from a point to a line
def distance_to_line(p1, p2, p):
    # Line equation Ax + By + C = 0
    A = p2[1] - p1[1]
    B = p1[0] - p2[0]
    C = p2[0] * p1[1] - p2[1] * p1[0]
    return abs(A * p[0] + B * p[1] + C) / np.sqrt(A**2 + B**2)


def line_intersection(p1, p2, p3, p4):
    """
    Find the intersection point of two lines (p1, p2) and (p3, p4).
    Each point is represented as a tuple (x, y).
    """
    # Line 1 represented by p1(x1, y1) and p2(x2, y2)
    x1, y1 = p1
    x2, y2 = p2
    
    # Line 2 represented by p3(x3, y3) and p4(x4, y4)
    x3, y3 = p3
    x4, y4 = p4
    
    # Denominator of the system of equations
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    
    # If denom is zero, lines are parallel or coincident
    if denom == 0:
        return None
    
    # Calculate the intersection point
    x = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
    y = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
    
    return (int(x), int(y))

def ssh_execute_command(host, username, password, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=password)

    results = []

    for c in command:
        stdin, stdout, stderr = ssh.exec_command(c)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        results.append({"command": c, "output": output, "error": error})
    
    ssh.close()
    return results 

def find_intersections(lines1, lines2):
    """
    Find intersection points between each line in lines1 and each line in lines2.
    Each line is a tuple of two points (x1, y1), (x2, y2).
    Returns a list of intersection points.
    """
    intersections = []
    
    # Iterate over each pair of lines
    for line1 in lines1:
        for line2 in lines2:
            p1, p2 = line1
            p3, p4 = line2
            intersection = line_intersection(p1, p2, p3, p4)
            if intersection:
                intersections.append(intersection)
    
    return intersections

# Function to get the closest point on the top or bottom line
def snap_to_top_bottom(p, top_left, top_right, bottom_right, bottom_left):
    # Calculate distance to the top and bottom lines
    dist_top = distance_to_line(top_left, top_right, p)
    dist_bottom = distance_to_line(bottom_left, bottom_right, p)
    dist_left = distance_to_line(top_left, bottom_left, p)
    dist_right = distance_to_line(top_right, bottom_right, p)
    lst = [dist_bottom, dist_top, dist_left, dist_right]
    min_index = min(enumerate(lst), key=lambda x: x[1])[0]
    if min_index == 0:
            return False, get_closest_point_on_line(bottom_left, bottom_right, p)
    elif min_index == 1:
            return False, get_closest_point_on_line(top_left, top_right, p)
    elif min_index == 2:
            return True, get_closest_point_on_line(top_left, bottom_left, p)
    elif min_index == 3:
            return True, get_closest_point_on_line(top_right, bottom_right, p)

def get_user_input():
    layout = [[sg.Text("Enter Item and Quantity of this Cell (ex: Cheetos 10):")], [sg.InputText()], [sg.OK()]]
    window = sg.Window("Input", layout)
    event, values = window.read()
    window.close()
    return values[0] if event == "OK" else None

# Function to get the closest point on a line segment
def get_closest_point_on_line(p1, p2, p):
    # Vector from p1 to p2
    line_vec = np.array(p2) - np.array(p1)
    # Vector from p1 to the point p
    point_vec = np.array(p) - np.array(p1)
    # Project point_vec onto line_vec and get the projection ratio
    line_len = np.linalg.norm(line_vec)
    line_vec_unit = line_vec / line_len
    projection = np.dot(point_vec, line_vec_unit)
    # Clamp the projection to the segment length
    projection = max(0, min(line_len, projection))
    # Get the closest point on the line
    closest_point = np.array(p1) + projection * line_vec_unit
    return tuple(closest_point.astype(int))

# Callback function for mouse events
def mark_points(event, x, y, flags, param):
    global points, rows_defined, current_row_points, current_col_points
    if event == cv2.EVENT_LBUTTONDOWN:
        if not rows_defined:
            points.append((x, y))
            print(len(points))
            if len(points) == 4:
                ysorted = sorted(points, key=lambda x: x[1])
                tops = sorted(ysorted[0:2], key=lambda x: x[0])
                print(tops)
                bottoms = sorted(ysorted[2:4], key=lambda x: x[0], reverse=True)
                print(bottoms)
                points = tops + bottoms
                print(points)
        else:
            # Snap the clicked point to the closest top or bottom line
            if len(points) == 4:
                is_row, snapped_point = snap_to_top_bottom((x, y), points[0], points[1], points[2], points[3])
                if is_row:
                    current_row_points.append(snapped_point)
                else:
                    current_col_points.append(snapped_point)


# Function to draw the trapezoidal grid dynamically
def draw_grid(image, points, row_points, col_points, highlightedCell):
    global grid_points
    temp_img = image.copy()

    # Draw corner points and lines between them
    for i, point in enumerate(points):
        cv2.circle(temp_img, point, 5, (0, 0, 255), -1)  # Red for corner points
        if i > 0:
            cv2.line(temp_img, points[i - 1], point, (255, 0, 0), 2)  # Blue lines for corner points

    # Draw the closing line to complete the trapezoid
    if len(points) == 4:
        cv2.line(temp_img, points[-1], points[0], (255, 0, 0), 2)

    # Draw the row points with blue dots and connect them only to the previous point (pair)
    if len(points) == 4:
        for i, row_point in enumerate(row_points):
            cv2.circle(temp_img, row_point, 5, (255, 0, 0), -1)  # Blue for row points
            if i % 2 == 1:  # Connect only to the previous row point when the index is even (2nd, 4th, etc.)
                cv2.line(temp_img, row_points[i - 1], row_point, (255, 0, 0), 2)
        for i, col_point in enumerate(col_points):
            cv2.circle(temp_img, col_point, 5, (0, 255, 0), -1)  # Blue for row points
            if i % 2 == 1:  # Connect only to the previous row point when the index is even (2nd, 4th, etc.)
                cv2.line(temp_img, col_points[i - 1], col_point, (0, 255, 0), 2)
    if highlightedCell:
        i = highlightedCell[0]
        j = highlightedCell[1]
        point =  np.array([grid_points[i][j], grid_points[i+1][j], grid_points[i+1][j+1], grid_points[i][j+1]])
        points = point.reshape((-1, 1, 2))
        # Draw the polygon on the image (True to close the polygon)
        cv2.polylines(image, [points], isClosed=True, color=(0, 0, 255), thickness=3)
    


    return temp_img

def numpy_encoder(obj):
    if isinstance(obj, np.int64):
        return int(obj)  # Convert numpy.int64 to regular int
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def isPointInCell(cellBoundies, point):
    """
    Determines if a point is inside a polygon using the ray-casting algorithm.

    polygon_points: List of tuples representing the coordinates of the polygon vertices (x, y).
    point: A tuple representing the coordinates of the point (x, y) to check.

    Returns True if the point is inside the polygon, otherwise False.
    """
    x, y = point
    n = len(cellBoundies)
    inside = False

    # Loop through all edges of the polygon
    for i in range(n):
        x1, y1 = cellBoundies[i]
        x2, y2 = cellBoundies[(i + 1) % n]  # Next vertex, wrap around at the end
        
        # Check if the point is within the vertical bounds of the edge
        if y > min(y1, y2) and y <= max(y1, y2):
            # Compute the x-coordinate of the intersection of the ray with the edge
            if x <= max(x1, x2):
                if y1 != y2:  # Avoid division by zero
                    x_intersect = (y - y1) * (x2 - x1) / (y2 - y1) + x1
                if x1 == x2 or x <= x_intersect:
                    inside = not inside  # Flip inside/outside

    return inside

def get_click_coordinates(event, x, y, flags, param):
    global click_coordinates, grid_points, highlightCell, input
    hieght, width = mask[0][0].shape
    print (f"{mask[0][0].shape}")
    if event == cv2.EVENT_LBUTTONDOWN:  # Left mouse button click
        if x > 0 and y > 0 and x < width and y <hieght:
            print(f"x: {x} y: {y} mask: {mask[0][0][y, x]}" )
        for i in range(4):
            for j in range(3):
                if x > 0 and y > 0 and x < width and y < hieght and  mask[i][j][y, x] == 255:
                    highlightCell = (i, j)    

# Main program
def main():
    global points, rows_defined, current_row_points, current_col_points, click_coordinates, highlightCell, grid_points, input, mask

    points = []  # Corner points
    current_row_points = []  # Row points
    current_col_points = [] # Col points
    rows_defined = False
    data = {}

    # Load the image
    image_path = "test.png"  # Replace with your image path
    origimage = cv2.imread(image_path)
    image = cv2.copyMakeBorder(origimage, 0, 200, 200, 200, cv2.BORDER_CONSTANT, value=(255, 255, 255))

    if image is None:
        print("Error: Could not load image.")
        return

    cv2.namedWindow("Mark Points")
    cv2.setMouseCallback("Mark Points", mark_points)

    while True:
        grid_image = draw_grid(image, points, current_row_points, current_col_points, None)
        cv2.imshow("Mark Points", grid_image)

        key = cv2.waitKey(1) & 0xFF
        if len(points) == 4 and not rows_defined:  # When 4 corners are marked, switch to row marking
            rows_defined = True
            print("Corners marked. Now define row points.")
        elif key == ord('s') and rows_defined:  # 's' to save
            lines1 = []
            lines2 = []
            for i, point in enumerate(current_row_points):
                if i > 0 and i%2 == 1:
                    lines1.append((current_row_points[i-1], current_row_points[i]))
            for i, point in enumerate(current_col_points):
                if i > 0 and i%2 == 1:
                    lines2.append((current_col_points[i-1], current_col_points[i]))
            middle_points = find_intersections(lines1, lines2)

            all_points = current_row_points + current_col_points + points + middle_points
            ysorted = sorted(all_points, key=lambda x: x[1])
            grid_points = []
            grid_points.append(sorted(ysorted[0:4], key=lambda x: x[0]))
            grid_points.append(sorted(ysorted[4:8], key=lambda x: x[0]))
            grid_points.append(sorted(ysorted[8:12], key=lambda x: x[0]))
            grid_points.append(sorted(ysorted[12:16], key=lambda x: x[0]))
            grid_points.append(sorted(ysorted[16:20], key=lambda x: x[0]))
            for i in range(4):
                for j in range(3):
                    polygon_points = np.array([grid_points[i][j], grid_points[i][j+1], grid_points[i+1][j+1], grid_points[i+1][j]], dtype=np.int32)
                    # Create a mask with the same size as the image, filled with zeros (black)
                    mask[i][j] = np.zeros_like(grid_image[:, :, 0])
                    print(np.shape(mask[i][j]))
                    # Fill the polygon area with white color (255)
                    cv2.fillPoly(mask[i][j], [polygon_points], 255)
                    print(np.shape(mask[i][j]))
            print(np.shape(grid_points))
            points_as_lists = [[list((point[0] - 200, point[1])) for point in sublist] for sublist in grid_points]
            with open('calibration.conf', 'w') as f:
                json.dump(points_as_lists, f, indent=4, default=numpy_encoder)
            break
    cv2.setMouseCallback("Mark Points", get_click_coordinates)
    while True:
        grid_image = draw_grid(image, points, current_row_points, current_col_points, highlightCell)
        cv2.imshow("Mark Points", grid_image)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC 
            with open("data.txt", "w") as f:
                json.dump(data, f, default=numpy_encoder)
            break
        elif key == ord('a'):
            if highlightCell:
                input = get_user_input()
                temp_value = {input.split(" ")[0]: input.split(" ")[1]}
                data[highlightCell[0] * 3 + highlightCell[1]] = temp_value
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
