# 小车搭建与配置修改指南

> 记录从 clone 代码到跑通建图/导航过程中，**必须手动修改**的地方。
> 这些问题都是源码仓库里原本就存在的坑，重新 clone 后需要重新改一遍。

---

## 一、环境依赖

- 系统：Ubuntu 22.04
- ROS2：Humble
- Livox SDK：`/usr/local/lib/liblivox_lidar_sdk_shared.so`（`livox_ros_driver2` 需要）
- 其他依赖：PCL、Eigen、tf2（ROS Humble desktop 基本自带）
- 建议禁用系统自带conda 如果使用系统自带conda进行了编译，那么需要删除build文件夹后再编译

```bash
sudo apt install ros-humble-desktop ros-dev-tools
sudo apt install ros-humble-octomap ros-humble-octomap-msgs ros-humble-octomap-rviz-plugins
sudo apt install ros-humble-pcl-ros

```
- 注意需要提前安装https://github.com/Livox-SDK/Livox-SDK2 否则colcon build会报错
---

## 二、编译前必改

### 1. livox 驱动的 `package.xml` 缺失 ⚠️

`livox_ros_driver2` 的 `package.xml` 被 `.gitignore` 忽略了，clone 下来**没有这个文件**，直接编译会报：

```
CMake Error: File .../livox_ros_driver2/package.xml does not exist.
```

**解决**：编译前手动生成（根据 ROS2 版本复制） 或者直接改个名字：

```bash
cd src/driver/livox_ros_driver2
cp package_ROS2.xml package.xml
cp -r launch_ROS2 launch
```

---

## 三、编译

在项目根目录（工作区根目录）执行 注意直接运行colcon build有可能失败：

```bash
./build.sh
# 等价于：
# colcon build --symlink-install --cmake-args -DROS_EDITION=ROS2 -DHUMBLE_ROS=humble
```

### 跳过 octomap_server2（可选，项目用不到）

`octomap_server2` 依赖 `octomap_msgs`，默认没装会编译失败。它是生成 3D 八叉树地图用的，本项目导航用 2D 栅格地图，**不需要它**：

```bash
colcon build --symlink-install \
    --cmake-args -DROS_EDITION=ROS2 -DHUMBLE_ROS=humble \
    --packages-skip octomap_server2
```

或者想保留就装依赖：

```bash
sudo apt install ros-humble-octomap ros-humble-octomap-msgs ros-humble-octomap-ros
```

---

## 四、雷达网络 IP 配置

配置文件位置：

```
src/driver/livox_ros_driver2/config/MID360_config.json
```

里面有两处 IP：

| 项 | 值 | 说明 |
|----|----|------|
| 雷达 IP（`lidar_configs` → `ip`） | `192.168.1.3` | MID-360 雷达自己的 IP |
| 主机 IP（`host_net_info` 四处 `*_ip`） | `192.168.1.5` | 上位机网口 IP |

**需要把上位机连接雷达的那个网口 IP 设成 `192.168.1.5`**：

```bash
# 例如网口是 eth0
sudo ip addr add 192.168.1.5/24 dev eth0
# 或通过 NetworkManager 图形界面设静态 IP 192.168.1.5/24
```

### ⚠️ 雷达实际可能是动态 IP

雷达出厂默认走 DHCP，实际 IP 可能是 `192.168.1.164`（驱动会自动发现并连上，不影响使用）。但**每次上电可能变**。

> 长期建议：用 Livox 官方工具 **LivoxViewer2** 把雷达设成静态 IP `192.168.1.3`，和配置文件一致。

**验证连通**：

```bash
ping 192.168.1.3        # 能通说明网络配对
```

---

## 五、关键 Bug 修复：看不到点云 ⚠️⚠️

现象：`ros2 topic hz /cloud_registered` 无输出，rviz 无点云。

**根本原因**：`fast_lio` 源码里只有当 `lidar_type == AVIA`（=1）时才订阅 Livox 的 `CustomMsg` 格式；但 `mid360.yaml` 里 `lidar_type` 被写成了 `0`，导致 fast_lio 去订阅 `PointCloud2`，和雷达发的 `CustomMsg` 类型对不上，收不到数据。

**解决**：修改 `src/lio/FAST_LIO/config/mid360.yaml`：

```yaml
preprocess:
    lidar_type: 1    # 原来是 0，改成 1（AVIA / Livox 系列）
```

> 这是运行时参数，改完**不用重新编译**，重启 fast_lio 即可。

---

## 六、启动测试

```bash
cd ~/ros2_humble_main
source install/setup.bash
```

**终端 1**（雷达驱动）：

```bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

**终端 2**（fast_lio 建图，自动弹 rviz）：

```bash
ros2 launch fast_lio mapping.launch.py
```

**验证**：

```bash
ros2 topic hz /livox/lidar        # 雷达点云（~10Hz）
ros2 topic hz /livox/imu          # IMU
ros2 topic hz /cloud_registered   # fast_lio 输出的全局地图点云
ros2 topic info /livox/lidar      # Type 应只有 CustomMsg 一种
```

**注意**：

- 启动前确保没有残留进程（重复启动会导致 `/livox/lidar` 出现两种类型、两个重名节点）：
  ```bash
  pkill -9 -f livox_ros_driver2; pkill -9 -f fastlio_mapping; pkill -9 -f laser_mapping; pkill -9 -f rviz2
  ```
- livox 驱动和 fast_lio **各只开一次**，各占一个终端。

---

## 七、后续待办（尚未完成）

### 1. 串口节点需重写（底盘是自定义协议）

当前 `src/driver/serial_node` 里的 `serial_twist_publisher` 是**差速底盘**协议，只发 `linear.x + angular.z`，帧为 `CC 速度 角速度 EE`。

本项目底盘是 **全向麦轮 + 自定义协议 + 电机自闭环**，需要重写成发 `vx / vy / wz` 三个分量，帧格式按 MCU 端协议来。

### 2. odom 话题名不匹配

- `fast_lio` 发布里程计话题：`/Odometry`
- `nav2`（`nav2_params.yaml` 里 `odom_topic`）订阅：`/odom`

两者名字对不上，导航前需要统一（改 `nav2_params.yaml` 的 `odom_topic: /Odometry`，或在 launch 里加 remap）。

### 3. 建图完成后

1. fast_lio 走一圈后 `Ctrl+C`，或运行 `./save_pcd.sh`，地图存到工作空间根目录的 `maps/test.pcd`（路径由 `mapping.launch.py` 自动推导）；
2. 用 `pcd2pgm` 把 `.pcd` 转 2D 栅格地图；
3. 配合 `pointcloud_to_laserscan` + `icp_registration` + `nav2` 做导航。

---

## 附：快速排查清单

| 现象 | 原因 | 解决 |
|------|------|------|
| 编译报 `package.xml does not exist` | livox 缺 package.xml | 见「二」复制生成 |
| 编译报 `octomap_msgs not found` | 缺 octomap 依赖 | 见「三」跳过或装依赖 |
| `/cloud_registered` 无数据 | `lidar_type=0` bug | 见「五」改成 1 |
| `/livox/lidar` 有两种 Type | 残留进程重复启动 | pkill 后干净重启 |
| rviz 黑色 / 打不开 | Wayland 环境 | `export QT_QPA_PLATFORM=xcb` 再启动 |
| 雷达能连但 IP 是 164 | 动态 IP | LivoxViewer2 设静态 192.168.1.3 |
