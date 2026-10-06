# Auto-generated ROS2 launch file — created by SolidWorks URDF Exporter
# Used for visualizing the exported robot model in RViz2

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # ============================================================
    # Locate the package share directory and build default paths
    # ============================================================
    pkg_share = get_package_share_directory('robot')

    default_urdf_path = os.path.join(pkg_share, 'urdf', 'robot.urdf')
    default_rviz_config = os.path.join(pkg_share, 'rviz', 'urdf.rviz')

    # ============================================================
    # Declare launch arguments
    # ============================================================
    urdf_path_arg = DeclareLaunchArgument(
        name='urdf_path',
        default_value=default_urdf_path,
        description='Absolute path to the URDF model file'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    )

    use_gui_arg = DeclareLaunchArgument(
        name='use_gui',
        default_value='false',
        description='Enable the joint_state_publisher GUI panel'
    )

    rviz_config_arg = DeclareLaunchArgument(
        name='rviz_config',
        default_value=default_rviz_config,
        description='Path to the RViz2 configuration file'
    )

    use_rviz_arg = DeclareLaunchArgument(
        name='use_rviz',
        default_value='false',
        description='Launch RViz2 for visualization'
    )

    # ============================================================
    # robot_state_publisher node: publishes the robot TF tree
    # and joint states.
    #
    # Uses Command + xacro to load the URDF file:
    #   - Works with plain URDF files (xacro passes them through)
    #   - Also supports .xacro macro files
    #   - The urdf_path argument lets users override the default
    #   - Fixes a bug where urdf_path was declared but never used
    # ============================================================
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': ParameterValue(
                Command([
                    'xacro ', LaunchConfiguration('urdf_path')
                ]),
                value_type=str,
            ),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }],
    )

    # ============================================================
    # joint_state_publisher node: publishes default joint angles
    # for non-fixed joints.
    # Switches between GUI and headless mode based on use_gui.
    # ============================================================
    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_gui')),
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }],
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
        condition=UnlessCondition(LaunchConfiguration('use_gui')),
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }],
    )

    # ============================================================
    # rviz2 node: 3D visualization
    # Only launched when use_rviz:=true (default false, so the
    # headless nav.sh chain can include this file without rviz).
    # ============================================================
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_rviz')),
        arguments=['-d', LaunchConfiguration('rviz_config')],
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }],
    )

    # ============================================================
    # Return LaunchDescription with all nodes in order
    # ============================================================
    return LaunchDescription([
        urdf_path_arg,
        use_sim_time_arg,
        use_gui_arg,
        rviz_config_arg,
        use_rviz_arg,
        robot_state_publisher,
        joint_state_publisher,
        joint_state_publisher_gui,
        rviz_node,
    ])
