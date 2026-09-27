#!/bin/bash
# 独立脚本：杀死所有 ROS / ROS2 相关进程
# 用法:
#   ./kill_ros.sh          先 SIGTERM 优雅退出，等待 2s 后对残留进程 SIGKILL
#   ./kill_ros.sh -9       直接 SIGKILL，不等
#   ./kill_ros.sh --list   只列出会杀掉的进程，不执行

cd "$(dirname "$0")" 2>/dev/null

SELF=$$
MODE=term

case "$1" in
	-9|--force) MODE=kill ;;
	--list)     MODE=list ;;
	-h|--help)
		grep '^#' "$0" | cut -c3-
		exit 0
		;;
esac

# 需要匹配的进程名/命令行关键字
PATTERNS=(
	# ---- 本项目节点 ----
	livox_ros_driver2_node
	fastlio_mapping
	point_lio
	octomap_server
	pointcloud_to_laserscan_node
	pcd2pgm_node
	icp_registration
	amcl_registration
	serial_twist
	serial_node
	# ---- launch / 工具 ----
	'ros2 launch'
	'ros2 run'
	'ros2 topic'
	'ros2 bag'
	'ros2 param'
	ros2_control_node
	robot_state_publisher
	# ---- nav2 全家桶 ----
	nav2_
	nav2_amcl
	nav2_bringup
	nav2_costmap
	nav2_controller_server
	nav2_planner_server
	nav2_bt_navigator
	nav2_behaviors
	nav2_map_server
	nav2_lifecycle_manager
	# ---- 可视化 / 其它 ----
	rviz2
	rviz
	robot_navigation2
	# ---- ros2 daemon ----
	_ros2_daemon
	ros2_daemon
)

# 收集目标 PID（排除自己、父进程和本脚本名）
declare -A TARGETS
add_pids() {
	local pid
	for pid in $(pgrep -f "$1" 2>/dev/null); do
		[ "$pid" = "$SELF" ] && continue
		[ "$pid" = "$PPID" ] && continue
		TARGETS[$pid]=1
	done
}

for p in "${PATTERNS[@]}"; do
	add_pids "$p"
done

# 兜底：所有可执行文件位于 ROS 安装目录下的进程
for pid in $(ls -l /proc/*/exe 2>/dev/null | grep -o '^/proc/[0-9]*' | cut -d/ -f3); do
	exe=$(readlink -f "/proc/$pid/exe" 2>/dev/null) || continue
	case "$exe" in
		*/opt/ros/*|*/ros2/*) TARGETS[$pid]=1 ;;
	esac
done

if [ ${#TARGETS[@]} -eq 0 ]; then
	echo "没有找到运行中的 ROS 进程。"
	exit 0
fi

echo "找到 ${#TARGETS[@]} 个进程:"
for pid in "${!TARGETS[@]}"; do
	cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null)
	printf '  %-8s %s\n' "$pid" "${cmd:0:110}"
done

[ "$MODE" = list ] && exit 0

kill_one() {
	for pid in "${!TARGETS[@]}"; do
		kill -"$1" "$pid" 2>/dev/null
	done
}

if [ "$MODE" = kill ]; then
	kill_one 9
else
	kill_one 15
	sleep 2
	# 对仍在运行的残留进程补刀
	for pid in $(pgrep -f "$(IFS='|'; echo "${PATTERNS[*]}")" 2>/dev/null); do
		[ "$pid" = "$SELF" ] && continue
		kill -9 "$pid" 2>/dev/null
	done
fi

sleep 0.5

# 停止 ros2 daemon（daemon 不响应信号时用 ros2 daemon stop）
ros2 daemon stop >/dev/null 2>&1

LEFT=0
for pid in "${!TARGETS[@]}"; do
	[ -d "/proc/$pid" ] && LEFT=$((LEFT+1))
done

if [ "$LEFT" -eq 0 ]; then
	echo "已清理完毕，所有 ROS 进程已退出。"
else
	echo "仍有 $LEFT 个进程未退出，可用 sudo 重试或稍后再运行本脚本。"
fi
