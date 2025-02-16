#!/usr/bin/env python3

# This assignment implements Dijkstra's shortest path on a graph, finding an unvisited node in a graph,
#   picking which one to visit, and taking a path in the map and generating waypoints along that path
#
# Given to you:
#   Priority queue
#   Image handling
#   Eight connected neighbors
#
# Slides https://docs.google.com/presentation/d/1XBPw2B2Bac-LcXH5kYN4hQLLLl_AMIgoowlrmPpTinA/edit?usp=sharing

# The ever-present numpy
import numpy as np

# Our priority queue
import heapq

# Using imageio to read in the image
import imageio


# -------------- Showing start and end and path ---------------
def plot_with_path(im, im_threshhold, robot_loc=None, goal_loc=None, path=None):
    """Show the map plus, optionally, the robot location and goal location and proposed path
    @param im - the image of the SLAM map
    @param im_threshhold - the image of the SLAM map
    @param robot_loc - the location of the robot in pixel coordinates
    @param goal_loc - the location of the goal in pixel coordinates
    @param path - the proposed path in pixel coordinates"""

    # Putting this in here to avoid messing up ROS
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 2)
    axs[0].imshow(im, origin='lower')
    axs[0].set_title("original image")
    axs[1].imshow(im_threshhold, origin='lower', cmap="gist_gray")
    axs[1].set_title("threshold image")
    """
    # Used to double check that the is_xxx routines work correctly
    for i in range(0, im_threshhold.shape[1]-1, 10):
        for j in range(0, im_threshhold.shape[0]-1, 10):
            if is_wall(im_thresh, (i, j)):
                axs[1].plot(i, j, '.b')
    """

    # Show original and thresholded image
    for i in range(0, 2):
        if robot_loc is not None:
            axs[i].plot(robot_loc[0], robot_loc[1], '+r', markersize=10)
        if goal_loc is not None:
            axs[i].plot(goal_loc[0], goal_loc[1], '*g', markersize=10)
        if path is not None:
            for p, q in zip(path[0:-1], path[1:]):
                axs[i].plot([p[0], q[0]], [p[1], q[1]], '-y', markersize=2)
                axs[i].plot(p[0], p[1], '.y', markersize=2)
    # Double checking lower left corner
    axs[1].plot(10, 5, 'xy', markersize=5)
    # Depending on if your mac, windows, linux, and if interactive is true, you may need to call this to get the plt
    # windows to show
    plt.show()


# -------------- Thresholded image True/False ---------------
def is_wall(im, pix):
    """ Is the pixel a wall pixel?
    @param im - the image
    @param pix - the pixel i,j"""
    if im[pix[1], pix[0]] == 255:
        return True
    return False


def is_unseen(im, pix):
    """ Is the pixel one we've seen?
    @param im - the image
    @param pix - the pixel i,j"""
    if im[pix[1], pix[0]] == 128:
        return True
    return False


def is_free(im, pix):
    """ Is the pixel empty?
    @param im - the image
    @param pix - the pixel i,j"""
    if im[pix[1], pix[0]] == 0:
        return True
    return False


def convert_image(im):
    """ Convert the image to a thresholded image with not seen pixels marked
    @param im - WXHX ?? image (depends on input)
    @return an image of the same WXH but with 0 (free) 255 (wall) 128 (unseen)"""
    im_ret = np.zeros((im.shape[0], im.shape[1]), dtype='uint8') + 128

    im_avg = im
    if len(im.shape) == 3:
        # RGB image - convert to gray scale
        im_avg = np.mean(im, axis=2)
    # Force into 0,1
    im_avg = im_avg / np.max(im_avg)
    # threshold
    #   in our example image, black is walls
    im_ret[im_avg < 0.7] = 255
    im_ret[im_avg > 0.9] = 0
    return im_ret


# -------------- Getting 4 or 8 neighbors ---------------
def four_connected(pix):
    """ Generator function for 4 neighbors
    @param im - the image
    @param pix - the i, j location to iterate around"""
    for i in [-1, 1]:
        ret = pix[0] + i, pix[1]
        yield ret
    for i in [-1, 1]:
        ret = pix[0], pix[1] + i
        yield ret


def eight_connected(pix):
    """ Generator function for 8 neighbors
    @param im - the image
    @param pix - the i, j location to iterate around"""
    for i in range(-1, 2):
        for j in range(-1, 2):
            if i == 0 and j == 0:
                pass
            ret = pix[0] + i, pix[1] + j
            yield ret


def dijkstra(im, robot_loc, goal_loc):
    """ Occupancy grid image, with robot and goal loc as pixels
    @param im - the thresholded image - use is_free(i, j) to determine if in reachable node
    @param robot_loc - where the robot is (tuple, i,j)
    @param goal_loc - where to go to (tuple, i,j)
    @returns a list of tuples"""

    # Sanity check
    if not is_free(im, robot_loc):
        raise ValueError(f"Start location {robot_loc} is not in the free space of the map")

    if not is_free(im, goal_loc):
        raise ValueError(f"Goal location {goal_loc} is not in the free space of the map")

    # The priority queue itself is just a list, with elements of the form (weight, (i,j))
    #    - i.e., a tuple with the first element the weight/score, the second element a tuple with the pixel location
    priority_queue = []
    # Push the start node onto the queue
    #   push takes the queue itself, then a tuple with the first element the priority value and the second
    #   being whatever data you want to keep - in this case, the robot location, which is a tuple
    heapq.heappush(priority_queue, (0, robot_loc))

    # The power of dictionaries - we're going to use a dictionary to store every node we've visited, along
    #   with the node we came from and the current distance
    # This is easier than trying to get the distance from the heap
    visited = {}
    # Use the (i,j) tuple to index the dictionary
    #   Store the best distance, the parent, and if closed y/n
    visited[robot_loc] = (0, None, False)   # For every other node this will be the current_node, distance

    # While the list is not empty - use a break for if the node is the end node
    while priority_queue:
        # Get the current best node off of the list
        current_node = heapq.heappop(priority_queue)
        # Pop returns the value and the i, j
        node_score = current_node[0]
        node_ij = current_node[1]

        # Showing how to get this data back out of visited
        visited_triplet = visited[node_ij]
        visited_distance = visited_triplet[0]
        visited_parent = visited_triplet[1]
        visited_closed_yn = visited_triplet[2]

        # TODO
        #  Step 1: Break out of the loop if node_ij is the goal node
        #  Step 2: If this node is closed, skip it
        #  Step 3: Set the node to closed
        #    Now do the instructions from the slide (the actual algorithm)
        #  Lec 8_1: Planning, at the end
        #  https://docs.google.com/presentation/d/1pt8AcSKS2TbKpTAVV190pRHgS_M38ldtHQHIltcYH6Y/edit#slide=id.g18d0c3a1e7d_0_0
# YOUR CODE HERE
        if node_ij == goal_loc:  # if current node is goal node exit loop
            break
        elif not visited_closed_yn:
            visited[node_ij] = (visited[node_ij][0], visited[node_ij][1], True)  # closes current node
            for adj_node in four_connected(node_ij):
                if adj_node not in visited:
                    visited[adj_node] = (20000000, None, False)
                if visited[adj_node][2] is False and is_free(im, adj_node):  # if free space and unvisited
                    if visited[adj_node][0] > visited_distance + 1:
                        visited[adj_node] = (visited_distance + 1, current_node[1], False)
                    heapq.heappush(priority_queue, (visited[adj_node][0], adj_node))

    # Now check that we actually found the goal node
    if not goal_loc in visited:
        return []

    path = []
    path.append(goal_loc)
    # TODO: Build the path by starting at the goal node and working backwards
# YOUR CODE HERE
    current_node = visited[goal_loc][1]
    for i in range(visited[goal_loc][0]):
        path.append(current_node)
        current_node = visited[current_node][1]
    
    return path


if __name__ == '__main__':
    im = imageio.imread("Data/SLAM_map.png")
    im_thresh = convert_image(im)

    robot_start_loc = (200, 150)
    # Closer one to try
    # robot_goal_loc = (315, 250)
    robot_goal_loc = (615, 850)

    """
    print(f"Image shape {im_thresh.shape}")
    for i in range(0, im_thresh.shape[1]-1):
        for j in range(0, im_thresh.shape[0]-1):
            if is_free(im_thresh, (i, j)):
                print(f"Free {j} {i}")
    """
    path = dijkstra(im_thresh, robot_start_loc, robot_goal_loc)
    plot_with_path(im, im_thresh, robot_start_loc, robot_goal_loc, path)

    print("Done")
