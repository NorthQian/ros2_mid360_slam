#!/bin/bash
# 保存 3D 栅格地图 (OctoMap, .bt)
# 用 octomap_server 的 octomap_saver_node，订阅 /octomap_full(由 octomap_server2 生成，
# 需在建图时运行 octomap_server2)并写出 .bt 三维栅格文件。

cd "$(dirname "$0")"
source install/setup.bash
export ROS_DOMAIN_ID=0

# ===== 可修改项 =====
# 脚本开头已 cd 到仓库根目录，地图统一放根目录下的 maps/
SAVE_DIR="$(pwd)/maps"
FILE="octomap.bt"          # 三维栅格文件名
# ====================

mkdir -p "$SAVE_DIR"

# octomap_saver_node 来自 ros-humble-octomap-server 包
if ! ros2 pkg list 2>/dev/null | grep -q "^octomap_server$"; then
	echo "错误: 未安装 octomap_server 包。请执行: sudo apt install -y ros-humble-octomap-server"
	exit 1
fi

echo "正在把 /octomap_full 保存为 $SAVE_DIR/$FILE ..."
ros2 run octomap_server octomap_saver_node --ros-args \
	-r /octomap_full:=/octomap_full \
	-p octomap_path:="$SAVE_DIR/$FILE"
echo
echo "完成。产物:"
echo "  $SAVE_DIR/$FILE"