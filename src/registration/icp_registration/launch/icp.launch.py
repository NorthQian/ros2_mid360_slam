import os
import sys
import yaml
from ament_index_python.packages import get_package_share_directory
from launch.substitutions import Command
sys.path.append(os.path.join(get_package_share_directory('icp_registration'), 'launch'))


def maps_dir(pkg_name):
  # install/<pkg>/share/<pkg> 往上 4 层即工作空间根目录，地图统一放在 <ws>/maps/
  share = get_package_share_directory(pkg_name)
  ws_root = os.path.abspath(os.path.join(share, '..', '..', '..', '..'))
  return os.path.join(ws_root, 'maps')


def generate_launch_description():
  from launch_ros.actions import Node
  from launch import LaunchDescription

  params = os.path.join(get_package_share_directory('icp_registration'), 'config', 'icp.yaml')
  node = Node(
    package='icp_registration',
    executable='icp_registration_node',
    output='screen',
    parameters=[
      params,
      {'pcd_path': os.path.join(maps_dir('icp_registration'), 'test.pcd')}
    ]
  )
  
  return LaunchDescription([node])
    