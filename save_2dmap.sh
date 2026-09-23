#!/bin/bash
# 保存 2D 栅格地图 (PGM + YAML)
# 用 nav2_map_server 的 map_saver_cli，订阅 2D 栅格话题(默认为 /projected_map，
# 由 octomap_server2 生成，需在建图时运行 octomap_server2)并保存为 pgm/yaml。

cd "$(dirname "$0")"
source install/setup.bash
export ROS_DOMAIN_ID=0

# ===== 可修改项 =====
TOPIC="/projected_map"                              # 2D 栅格话题(octomap 的 projected_map)
# 脚本开头已 cd 到仓库根目录，地图统一放根目录下的 maps/
OUT="$(pwd)/maps/map"                               # 保存前缀(自动生成 map.pgm / map.yaml)
# ====================

mkdir -p "$(dirname "$OUT")"

if ! ros2 pkg list 2>/dev/null | grep -q nav2_map_server; then
	echo "错误: 未安装 nav2_map_server。请执行: sudo apt install -y ros-humble-nav2-map-server"
	exit 1
fi

echo "正在把话题 $TOPIC 保存为 $OUT ..."
ros2 run nav2_map_server map_saver_cli -t "$TOPIC" -f "$OUT"
echo
echo "完成。产物:"
echo "  $OUT.pgm"
echo "  $OUT.yaml"