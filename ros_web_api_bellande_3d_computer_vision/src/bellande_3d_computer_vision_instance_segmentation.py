# Copyright (C) 2024 Bellande Robotics Sensors Research Innovation Center, Ronaldson Bellande
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import os
import requests
import numpy as np
import base64
from sensor_msgs.msg import PointCloud2
import sensor_msgs.point_cloud2 as pc2


def pointcloud_instance_segmentation(cloud_msg):
    points = np.array(list(pc2.read_points(cloud_msg, skip_nans=True, field_names=("x", "y", "z"))))
    
    points_base64 = base64.b64encode(points.tobytes()).decode('utf-8')

    payload = {
        "pointcloud": points_base64
    }

    headers = {
        "Authorization": f"Bearer {api_access_key}"
    }

    response = requests.post(api_url, json=payload, headers=headers)

    if response.status_code == 200:
        result = response.json()
        instance_labels = np.array(result['instance_labels'])
        
        fields = [
            pc2.PointField(name="x", offset=0, datatype=pc2.PointField.FLOAT32, count=1),
            pc2.PointField(name="y", offset=4, datatype=pc2.PointField.FLOAT32, count=1),
            pc2.PointField(name="z", offset=8, datatype=pc2.PointField.FLOAT32, count=1),
            pc2.PointField(name="instance", offset=12, datatype=pc2.PointField.UINT32, count=1),
        ]
        
        segmented_cloud = pc2.create_cloud(cloud_msg.header, fields, np.hstack((points, instance_labels.reshape(-1, 1))))
        return segmented_cloud
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def pointcloud_callback(msg):
    segmented_cloud = pointcloud_instance_segmentation(msg)
    if segmented_cloud:
        pub.publish(segmented_cloud)


def main():
    global api_url, api_access_key, pub

    config_file_path = os.path.join(os.path.dirname(__file__), '../config/configs.json')
    if not os.path.exists(config_file_path):
        print("Config file not found:", config_file_path)
        return
    with open(config_file_path, 'r') as config_file:
        config = json.load(config_file)
        url = config['url']
        endpoint_path = config['endpoint_path']["instance_segmentation"]
        api_access_key = config["Bellande_Framework_Access_Key"]
    
    if ros_version == "1":
        rospy.init_node('pointcloud_instance_segmentation_node', anonymous=True)
        pub = rospy.Publisher('pointcloud_instance_segmentation_result', PointCloud2, queue_size=10)
        sub = rospy.Subscriber('input_pointcloud', PointCloud2, pointcloud_callback)
    elif ros_version == "2":
        rclpy.init()
        node = rclpy.create_node('pointcloud_instance_segmentation_node')
        pub = node.create_publisher(PointCloud2, 'pointcloud_instance_segmentation_result', 10)
        sub = node.create_subscription(PointCloud2, 'input_pointcloud', pointcloud_callback, 10)

    api_url = f"{url}{endpoint_path}"

    try:
        print("Pointcloud instance segmentation node is running. Ctrl+C to exit.")
        if ros_version == "1":
            rospy.spin()
        elif ros_version == "2":
            rclpy.spin(node)
    except KeyboardInterrupt:
        print("Shutting down pointcloud instance segmentation node.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        if ros_version == "2":
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    ros_version = os.getenv("ROS_VERSION")
    if ros_version == "1":
        import rospy
    elif ros_version == "2":
        import rclpy
    main()
