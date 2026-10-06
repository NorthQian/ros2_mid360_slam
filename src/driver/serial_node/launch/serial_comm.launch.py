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
                # 这三个是「ROS 速度 -> MCU 整数」的换算，不是物理标定。
                # 下发字节 = clamp(v * scale, ±255) * speed_scale，
                # 所以 v*scale 一旦超过 255 就饱和，低于饱和线的速度全被压成同一个字节，
                # 控制器的小速度指令一律变成「开关式」满速 —— 横向(vy)尤其明显。
                # 取值让导航的最大速度正好落在饱和线附近：
                #   linear:  max_vel_x 0.26 * 980  = 254.8 -> 255 * 0.5 = 127(与改动前一致)
                #   angular: max_vel_theta 0.8 * 320 = 256  -> 255 * 0.5 = 127(与改动前一致)
                # 即：最大速度的字节数和改动前完全相同(物理最高速不变)，只是把饱和点
                # 从「0.051 m/s」抬到了最大速度，让底下的速度恢复成比例控制。
                {'linear_scale': 980.0},
                {'angular_scale': 320.0},
                # 速度太快就调小这个：0.5 = 半速，0.3 = 三成速度
                {'speed_scale': 0.5},
            ],
            output='screen'
        )
    ])