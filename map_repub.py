#!/usr/bin/env python3
# 转发 /map -> /saved_map，用 volatile QoS，让 rviz 的 Map 显示能稳定收到静态地图。
# map_server 的 /map 是 transient_local 且只发一次；本节点缓存最近地图，每 1s 重发，
# 保证 /saved_map 始终有数据。
import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid


class MapRepub(Node):
    def __init__(self):
        super().__init__('map_repub')
        # 订阅 map_server 的 /map (transient_local)
        sub_qos = rclpy.qos.QoSProfile(
            depth=1,
            reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
            durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL)
        # 发布 /saved_map，用 TRANSIENT_LOCAL(与 rviz Map 显示匹配)并每秒重发
        pub_qos = rclpy.qos.QoSProfile(
            depth=1,
            reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
            durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub = self.create_publisher(OccupancyGrid, '/saved_map', pub_qos)
        self.sub = self.create_subscription(
            OccupancyGrid, '/map', self.cb, sub_qos)
        self.latest = None
        self.create_timer(1.0, self.timer_cb)
        self.get_logger().info('map_repub: /map -> /saved_map (volatile, 1s repub)')

    def cb(self, msg):
        self.latest = msg

    def timer_cb(self):
        if self.latest is not None:
            self.pub.publish(self.latest)


def main():
    rclpy.init()
    rclpy.spin(MapRepub())


if __name__ == '__main__':
    main()
