import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def maps_dir(pkg_name):
    # install/<pkg>/share/<pkg> 往上 4 层即工作空间根目录，地图统一放在 <ws>/maps/
    share = get_package_share_directory(pkg_name)
    ws_root = os.path.abspath(os.path.join(share, '..', '..', '..', '..'))
    return os.path.join(ws_root, 'maps')


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('pcd2pgm'), 'config', 'pcd.yaml')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    pcd2pgm_node = Node(
        package='pcd2pgm',
        executable='pcd2pgm_node',
        output='screen',
        parameters=[
            config,
            # pcd2pgm 内部是 file_directory + file_name + ".pcd" 直接拼接，
            # 末尾分隔符不能少。
            {'file_directory': maps_dir('pcd2pgm') + os.sep},
            {'use_sim_time': use_sim_time }
        ]
    )

    return LaunchDescription([pcd2pgm_node])
