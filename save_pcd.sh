#!/bin/bash
# 保存 FAST-LIO 累积的 3D 点云地图 (PCD)
# 调用 FAST-LIO 自带的 /map_save 服务，把点云写入 mid360.yaml 里的 map_file_path。
# 需要在建图节点运行期间执行。

cd "$(dirname "$0")"
source install/setup.bash
export ROS_DOMAIN_ID=0

MAP_PATH="/home/nvidia/ros2_MID360_slam/maps/test.pcd"

echo "正在请求 FAST-LIO 保存点云地图..."
ros2 service call /map_save std_srvs/srv/Trigger {}
echo
echo "完成。若成功，点云地图已保存到:"
echo "  $MAP_PATH"
echo "检查: ls -l $MAP_PATH"