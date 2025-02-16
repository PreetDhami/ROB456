#!/usr/bin/env python3

# Bill Smart, smartw@oregonstate.edu
#
# This example implements the Go then Stop code using a callback based on the scan
#


# Import ROS Python basic API and sys
import rospy
import sys

# We're going to do some math
import numpy as np

# Velocity commands are given with Twist messages, from geometry_msgs
from geometry_msgs.msg import Twist

# Laser scans are given with the LaserScan message, from sensor_msgs
from sensor_msgs.msg import LaserScan


# A callback to deal with the LaserScan messages.
def callback(scan):
	# Every time we get a laser scan, calculate the shortest scan distance in front
	# of the robot, and set the speed accordingly.  We assume that the robot is 38cm
	# wide.  This means that y-values with absolute values greater than 19cm are not
	# in front of the robot.  It also assumes that the LiDAR is at the front of the
	# robot (which it actually isn't) and that it's centered and pointing forwards.
	# We can work around these assumptions, but it's cleaner if we don't

	# Pulling out some useful values from scan
	angle_min = scan.angle_min
	angle_max = scan.angle_max
	num_readings = len(scan.ranges)

	# Doing this for you - get out theta values for each range/distance reading
	thetas = np.linspace(angle_min, angle_max, num_readings)

	# TODO: Determine what the closest obstacle/reading is for scans in front of the robot
	#  Step 1: Determine which of the range readings correspond to being "in front of" the robot (see comment at top)
	#    Remember that robot scans are in the robot's coordinate system - theta = 0 means straight ahead
	#  Step 2: Get the minimum distance to the closest object
	# Suggestion: Do this with a for loop before being fancy with numpy (which is substantially faster)
	# DO NOT hard-wire in the number of readings, or the min/max angle. You CAN hardwire in the size of the robot
	cos_d = np.cos(thetas)
	sin_d = np.sin(thetas)
	distances = np.zeros(thetas.shape)
	for i in range(num_readings):
		x = scan.ranges[i]*cos_d[i] - 0.19  # Assuming x >= 0
		y = np.abs(scan.ranges[i]*sin_d[i])
		distances[i] = x if y <= 0.19 else scan.range_max
	min_distance = min(distances)

	# Doing this for you - create a twist and fill in all the fields.
	#   We'll only mess with t.linear.x - the forward speed
	t = Twist()
	t.linear.x = 0.0
	t.linear.y = 0.0
	t.linear.z = 0.0
	t.angular.x = 0.0
	t.angular.y = 0.0
	t.angular.z = 0.0

	# TODO:
	# Step 1: Use the closest distance from above to decide when to stop (the current solution will stop if
	#   there's anything near the robot)
	# Step 2: Scale how fast you move by the distance to the closet object (tanh is handy here...)
	# Step 3: Make sure to actually stop if close to 1 m
	#
	if min_distance < 1.0:
		t.linear.x = 0   # Stop
	else:
		t.linear.x = np.min([1.5, min_distance - 0.95])  # Capped linear velocity based on distance to wall

	# Send the command to the robot.
	publisher.publish(t)

	# Print out a log message to the INFO channel to let us know it's working.
	rospy.loginfo(f'Shortest: {min_distance} => {t.linear.x}')


if __name__ == '__main__':
	# Initialize the node, and call it "driver".
	rospy.init_node('stopper', argv=sys.argv)

	# Set up a publisher.  The default topic for Twist messages is cmd_vel.
	publisher = rospy.Publisher('cmd_vel', Twist, queue_size=10)

	# Set up a subscriber.  The default topic for LaserScan messages is base_scan.
	subscriber = rospy.Subscriber('base_scan', LaserScan, callback, queue_size=10)

	# Now that everything is wired up, we just spin.
	rospy.spin()
