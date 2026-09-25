#!/bin/bash
# 无头(Headless)启动导航链路
# Jetson 无屏幕：所有节点后台运行，日志写入 log/。rviz 请在你自己的电脑上开。
# 链路(作者原设计): 驱动 -> FAST-LIO(odom->base_link) -> 串口底盘 -> 点云转2D扫描
#       -> pcd2pgm(读 maps/test.pcd 发静态 /map, transient_local)
#       -> ICP 配准(定位, 发 map->odom) -> Nav2(use_map_topic:true 订阅 /map)

cd "$(dirname "$0")"
source install/setup.bash
export ROS_DOMAIN_ID=0

# ===== 启动前自动清理旧的 ROS 节点，避免重复 =====
echo "清理旧 ROS 进程..."
pkill -9 -f 'ros2 launch' 2>/dev/null
pkill -9 -f 'fastlio_mapping' 2>/dev/null
pkill -9 -f 'livox_ros_driver2_node' 2>/dev/null
pkill -9 -f 'octomap_server' 2>/dev/null
pkill -9 -f 'serial_twist' 2>/dev/null
pkill -9 -f 'pointcloud_to_laserscan_node' 2>/dev/null
pkill -9 -f 'pcd2pgm_node' 2>/dev/null
pkill -9 -f 'icp_registration' 2>/dev/null
pkill -9 -f 'nav2' 2>/dev/null
sleep 1
# ==================================================

LOG_DIR="$(pwd)/log"
mkdir -p "$LOG_DIR"

cmds=(
	"ros2 launch livox_ros_driver2 msg_MID360_launch.py"
	"ros2 launch fast_lio mapping.launch.py rviz:=true"
	"ros2 launch serial_node serial_comm.launch.py"
	"ros2 launch pointcloud_to_laserscan pointcloud_to_laserscan_launch.py"
	"ros2 launch octomap_server2 octomap_server_launch.py incremental_2D_projection:=true"
	"ros2 launch pcd2pgm pcd2pgm.launch.py use_sim_time:=false"
	"ros2 launch icp_registration icp.launch.py"
	"ros2 launch robot_navigation2 navigation2.launch.py rviz:=true"
)

PIDS=()
for i in "${!cmds[@]}"
do
	cmd="${cmds[$i]}"
	LOG="$LOG_DIR/nav_$((i+1)).log"
	echo "Starting: $cmd  ->  $LOG"
	# nohup + setsid 使其在 SSH 断开后仍继续运行
	setsid bash -c "cd $(pwd); source install/setup.bash; export ROS_DOMAIN_ID=0; $cmd" \
		> "$LOG" 2>&1 &
	PIDS+=($!)
	sleep 0.3
done

echo
echo "已后台启动 ${#PIDS[@]} 个节点，日志在 $LOG_DIR/nav_*.log"
echo "查看某个节点: tail -f log/nav_5.log  (数字对应上面的启动顺序)"
echo "在本机(远端电脑)上: rviz2 -d fastlio.rviz"
