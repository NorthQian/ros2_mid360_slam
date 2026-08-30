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
cd ~/ros2_MID360_slam
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
scp nvidia@192.168.5.27:~/ros2_MID360_slam/src/lio/FAST_LIO/rviz/fastlio.rviz ~/ros2_mid360/
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

**注意**：
- `save_2dmap.sh` 依赖 `nav2_map_server`（已装）；`save_3dmap.sh` 依赖 `octomap_server` 包，
  需先执行：`sudo apt install -y ros-humble-octomap-server`。
- 各脚本需在建图节点运行期间执行。
- 查看 2D 图：直接 `eog maps/map.pgm`，或在 rviz / Nav2 里加载 `maps/map.yaml`。

---

## 环境速查

| 项 | 值 |
|----|----|
| Jetson IP | 192.168.5.27 |
| 工作目录（Jetson） | `~/ros2_MID360_slam` |
| rviz 配置 | `src/lio/FAST_LIO/rviz/fastlio.rviz` |
| MID360 配置 | `src/lio/FAST_LIO/config/mid360.yaml` |
| ROS_DOMAIN_ID | 0 |
