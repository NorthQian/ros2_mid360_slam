#!/bin/bash
# 无头(Headless)启动 FAST-LIO 建图
# Jetson 无屏幕：livox 驱动 + FAST-LIO 在后台运行，日志写入 log/。
# rviz 请在你自己的电脑上运行，跨主机订阅话题查看。

cd "$(dirname "$0")"
source install/setup.bash
export ROS_DOMAIN_ID=0

# ===== 启动前自动清理旧的 ROS 节点，避免重复 =====
echo "清理旧 ROS 进程..."
pkill -9 -f 'ros2 launch' 2>/dev/null
pkill -9 -f 'fastlio_mapping' 2>/dev/null
pkill -9 -f 'livox_ros_driver2_node' 2>/dev/null
pkill -9 -f 'octomap_server' 2>/dev/null
pkill -9 -f 'pointcloud_to_laserscan_node' 2>/dev/null
pkill -9 -f 'pcd2pgm_node' 2>/dev/null
sleep 1
# ==================================================

LOG_DIR="$(pwd)/log"
mkdir -p "$LOG_DIR"

cmds=(  "ros2 launch livox_ros_driver2 msg_MID360_launch.py"
        "ros2 launch fast_lio mapping.launch.py rviz:=true"
        "ros2 launch octomap_server2 octomap_server_launch.py incremental_2D_projection:=true"
     )

PIDS=()
for i in "${!cmds[@]}"
do
	cmd="${cmds[$i]}"
	LOG="$LOG_DIR/node_$((i+1)).log"
	echo "Starting: $cmd  ->  $LOG"
	# nohup + setsid 使其在 SSH 断开后仍继续运行
	setsid bash -c "cd $(pwd); source install/setup.bash; export ROS_DOMAIN_ID=0; $cmd" \
		> "$LOG" 2>&1 &
	PIDS+=($!)
	sleep 0.2
done

echo
echo "已后台启动 ${#PIDS[@]} 个节点，日志在 $LOG_DIR/。"
echo "在本机(远端电脑)上: rviz2 -d fastlio.rviz"
echo "查看日志: tail -f log/node_1.log  (或 node_2.log)"
