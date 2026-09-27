from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='serial_node',
            executable='serial_twist_publisher',
            name='serial_twist_publisher',
            parameters=[
                {'port': '/dev/ttyACM0'},
                {'baudrate': 230400},
                {'linear_scale': 5000.0},
                {'angular_scale': 500.0},
                # 速度太快就调小这个：0.5 = 半速，0.3 = 三成速度
                {'speed_scale': 0.5},
            ],
            output='screen'
        )
    ])