# MID360 + FAST-LIO 建图

基于 Jetson（无屏幕）的 MID360 激光雷达实时建图，远程端（你的电脑）用 rviz 查看。

## 架构

```
Jetson (192.168.5.27, 无屏幕)            你的电脑 (192.168.5.14, 有屏幕)
┌──────────────────────────┐            ┌──────────────────────────────┐
│ livox_ros_driver2 读取MID360 │  DDS/组播   │  rviz2 订阅话题并显示          │
│ fastlio_mapping (建图)      │ ─────────► │  /cloud_registered /path     │
│ 后台运行, 日志写 log/       │   ROS2多主机 │  /map /tf                    │
└──────────────────────────┘            └──────────────────────────────┘
```

- 两端必须 **同网段**、**ROS_DOMAIN_ID 一致**（默认都是 `0`）。
- livox 驱动与 FAST-LIO 是纯计算节点，**不需要屏幕**，故在 Jetson 后台运行即可。
- 只有 rviz 需要屏幕，所以把它放在你的电脑上。

---

## 一、启动建图（Jetson 上）

```bash
cd ~/ros2_mid360_slam
./mapping.sh
```

脚本会**后台启动**两个节点并写入日志：

| 节点 | 日志 |
|------|------|
| livox 驱动（读 MID360） | `log/node_1.log` |
| FAST-LIO 建图（rviz 已关闭 `rviz:=false`） | `log/node_2.log` |

后台运行使用 `setsid nohup`，**SSH 断开也不停止**。

### 查看状态 / 日志

```bash
tail -f log/node_1.log   # 驱动是否收到点云
tail -f log/node_2.log   # FAST-LIO 是否在算图
ros2 node list           # 应看到 fastlio_mapping 等节点
ros2 topic list          # 应看到 /cloud_registered /path /map /tf
```

### 停止建图

```bash
pkill -f 'ros2 launch'
```

---

## 二、远程端查看（你的电脑上）

**1. 拷贝 rviz 配置文件**（只需拷一次）：

```bash
scp nvidia@192.168.5.27:~/ros2_mid360_slam/src/lio/FAST_LIO/rviz/fastlio.rviz ~/ros2_mid360/
```

**2. 启动 rviz：**

```bash
source /opt/ros/<你的发行版>/setup.bash   # 如 humble
export ROS_DOMAIN_ID=0                     # 与 Jetson 一致
rviz2 -d ~/ros2_mid360/fastlio.rviz
```

**3. 验证连通：**

```bash
ros2 topic list    # 能看到 Jetson 的话题即已连通
```

rviz 中应看到：
- `/cloud_registered` —— 注册后的点云（即地图在实时增长）
- `/path` —— 传感器运动轨迹
- `/tf`、Fixed Frame 通常为 `map`

**判据**：移动 LiDAR，新区域被填充、已建区域不漂移散开，即为健康建图。

---

## 三、常见问题

### `ros2 topic list` 看不到对方的话题
- 确认两端**同网段**、`ROS_DOMAIN_ID` 一致。
- 确认防火墙放行 DDS 组播/端口：`7400-7500/udp`（或改用 Discovery Server 方式）。
- Fast DDS 默认靠组播发现节点，跨子网或组播被挡时无法发现。

### rviz 打开了但没数据
- 先 `ros2 topic list` 确认话题存在；确认 Fixed Frame 与 TF 正常。

## 三、保存地图

`mapping.sh` 已同时启动 livox 驱动 + FAST-LIO + octomap_server2（生成 `/projected_map` 2D 栅格与 `/octomap_full` 3D 栅格）。

| 脚本 | 产物 | 说明 |
|------|------|------|
| `./save_pcd.sh` | `maps/test.pcd`（3D 点云） | 调 FAST-LIO 自带 `/map_save`，路径见 `mid360.yaml` 的 `map_file_path` |
| `./save_2dmap.sh` | `maps/map.pgm + map.yaml`（2D 栅格） | 用 `nav2_map_server map_saver_cli` 订阅 `/projected_map`；话题/路径在脚本顶部可改 |
| `./save_3dmap.sh` | `maps/octomap.bt`（3D 栅格） | 用 `octomap_server octomap_saver_node` 订阅 `/octomap_full`；路径在脚本顶部可改 |

**三个脚本都要跑一遍，缺一不可** —— 三种格式各有用途，互相不能替代，
建议按 **pcd → 2dmap → 3dmap** 的顺序依次执行。

**注意**：
- 各脚本**必须在建图节点（`./mapping.sh`）运行期间执行**：`save_pcd.sh` 是向
  FAST-LIO 发 `/map_save` 服务调用，另外两个是订阅 octomap 实时发布的话题，
  建图停掉后就取不到数据了。
- `save_2dmap.sh` 依赖 `nav2_map_server`（已装）；`save_3dmap.sh` 依赖 `octomap_server` 包，
  需先执行：`sudo apt install -y ros-humble-octomap-server`。
- 查看 2D 图：直接 `eog maps/map.pgm`，或在 rviz / Nav2 里加载 `maps/map.yaml`。

---

## 四、导航（Jetson 上，headless）

先确认 `maps/test.pcd` 存在（建图后 `./save_pcd.sh` 生成），然后：

```bash
cd ~/ros2_mid360_slam
./nav.sh
```

`nav.sh` 会**自动清理旧节点**并后台启动 8 个节点（日志 `log/nav_*.log`）。链路（作者原设计）：

```
livox驱动 → FAST-LIO(odom→base_link) → 串口底盘 → pointcloud_to_laserscan(2D扫描+base_link→livox_frame)
         → pcd2pgm(读 maps/test.pcd 发静态 /map)   ← 静态已存地图, 不会重建
         → icp_registration(定位, 发 map→odom)      ← 解决黑屏
         → Nav2(use_map_topic:true 订阅 /map)
```

| 序号 | 节点 | 日志 |
|------|------|------|
| 1 | livox 驱动 | `log/nav_1.log` |
| 2 | FAST-LIO | `log/nav_2.log` |
| 3 | 串口底盘 | `log/nav_3.log` |
| 4 | pointcloud_to_laserscan | `log/nav_4.log` |
| 5 | octomap_server2（/projected_map） | `log/nav_5.log` |
| 6 | **pcd2pgm（静态 /map）** | `log/nav_6.log` |
| 7 | **icp_registration（定位 map→odom）** | `log/nav_7.log` |
| 8 | Nav2 | `log/nav_8.log` |

### 关键改动（相对作者原始配置，本 Jetson 上必需）

**icp 定位的点云话题**：`src/registration/icp_registration/config/icp.yaml`
```yaml
pointcloud_topic: "/cloud_registered_body"   # 原为 /livox/lidar
```
原因：livox 驱动在 `/livox/lidar` 上虽然声明了 `sensor_msgs/PointCloud2`，但**实际订阅不到数据**（实测收 0 条），
导致 icp 永远收不到点云、不配准、不发布 map→odom（rviz 黑屏）。改用 FAST-LIO 输出的
`/cloud_registered_body`（base_link 帧的 PointCloud2，实测 ~5000 点/帧）。

**Nav2 使用静态地图**：`src/navigation/robot_navigation2/launch/navigation2.launch.py`
```python
'map': '',
'use_map_topic': 'true'     # 订阅 pcd2pgm 的 /map, 而非从文件加载
```
这样加载的是 `maps/test.pcd` 生成的静态 /map，**不会实时重建地图**。

### 远程端 rviz 查看（你的电脑上）

```bash
source /opt/ros/<你的发行版>/setup.bash
export ROS_DOMAIN_ID=0
rviz2
```
在 rviz 中：
- **Fixed Frame 设为 `map`**（已由 icp_registration 提供 map→odom TF）
- 添加 **Map** 显示，话题 `/map` → 显示静态已存地图
- 添加 **PointCloud2** 显示，话题 `/cloud_registered` → 实时点云（定位后的机器人）
- 添加 **TF** 显示 → 看到 map→odom→base_link→livox_frame 链路

若地图位置 / 朝向不对：编辑 `icp.yaml` 的 `initial_pose`（`[x,y,z,roll,pitch,yaw]`，相对地图原点）。

---

## 环境速查

| 项 | 值 |
|----|----|
| Jetson IP | 192.168.5.27 |
| 工作目录（Jetson） | `~/ros2_mid360_slam` |
| rviz 配置 | `src/lio/FAST_LIO/rviz/fastlio.rviz` |
| MID360 配置 | `src/lio/FAST_LIO/config/mid360.yaml` |
| ROS_DOMAIN_ID | 0 |
