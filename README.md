# ros2-humble-mid360

#### 介绍
本程序完成了mid360进行建图和导航的基础功能框架

#### 环境说明
ros2 版本：  **humble**
 

#### 使用说明
 **1、功能包说明**  
driver:  设备资源处理

    livox_ros_driver2 --- 获取mid360雷达点云

    serial_node --- 底盘串口通信



lio：    建图算法

    FAST_LIO --- fast_lio建图

    point_lio --- point_lio建图(无法使用)




mapper:  二维、三维栅格建图以及点云处理

    octomap_server2 --- 在/octomap_full、/octomap_binary上发布三维栅格图，同时在/project_map上发布二维栅格图

    pcd2pgm --- 用于读取点云的pcd文件，并在/map上发布二维的栅格图

    pointcloud_to_laserscan --- 将mid360的点云数据转换成的激光雷达数据，用于导航




navigation：导航包以及导航相关算法

    robot_navigation2 --- 使用navigation2进行导航




registration:    定位算法

    amcl_registration --- 使用amcl进行定位

    icp_registration  --- 使用icp进行定位




 **2、编译** 

`colcon build --symlink-install --cmake-args   -DROS_EDITION=ROS2   -DHUMBLE_ROS=humble `


或者


`./build.sh`


编译 octomap_server2时会报警告，不理就行


**3、运行** 

3.1 -- 建图

命令：

`./mapping.sh`

在建图前，先配置将mid360的ip配置一下，网上有教程，目录在driver/livox_ros_driver2/config/MID360_config.json,

然后再前往lio/FAST_LIO/config/mid360.yaml中，检查是否满足以下情况


```
pcd_save_en: true
dense_publish_en: false
map_file_path: "maps/test.pcd"
建图产物统一保存在工作空间根目录的 maps/ 下，路径由 mapping.launch.py 按工作空间位置
自动推导，搬到别的目录也不用改；上面这行只是直接用 ros2 run 启动时的兜底值。
想换文件名，改 mapping.launch.py 里拼路径那行的 test.pcd。
```


3.2 -- 保存地图

命令:

`./save_pcd.sh`

保存pcd文件，执行的是fast_lio自带的保存方法，路径也是fast_lio的保存路径


命令:

`./save_2dmap.sh`

保存pgm文件，保存路径以及保存topic均要在该文件中修改


命令：

`./save_3dmap.sh`

保存bt或者ot文件，该命令只能保存octomap生成的三维栅格图，同样需要在命令文件中修改保存路径




3.3 -- 导航

命令：

`./nav1.sh`

执行完3.1建图后，会在工作空间的 maps/ 目录下生成 test.pcd，可以通过在当前目录打开终端

执行:

`pcl_viewer maps/test.pcd`

查看点云情况,确认点云无误后

打开 mapper/pcd2pgm/config/pcd.yaml

设置：

```
file_directory: maps/        #兜底值，pcd2pgm.launch.py 会自动填成 <工作空间>/maps/，末尾斜杠不可少
file_name: test              #文件名
thre_z_max: 0.35             #机器人最大高度
thre_z_min: -0.04            #需求点云最低高度
```


打开 mapper/pointcloud_to_laserscan/launch/pointcloud_to_laserscan_launch.py

设置：

```
'min_height': -0.09,     # 与thre_z_min 一致
'max_height': 0.35,      # 与thre_z_max 一致
```


打开 driver/serial_node/launch/serial_comm.launch.py

自行设置串口和波特率,由于学艺不精，无法做到精准定位，因此这两个可以看成倍率

```
{'linear_scale': 5000.0},     # 前后速度倍率
{'angular_scale': 500.0},   # 转向速度倍率
```


打开 registration/icp_registration/config/icp.yaml

设置:

```
pcd_path: "maps/test.pcd"    #兜底值，icp.launch.py 会自动填成 <工作空间>/maps/test.pcd
map_frame_id: "map"
odom_frame_id: "odom"
laser_frame_id: "base_link"
pointcloud_topic: "/livox/lidar"
```

 **其他** 

ros2有很多topic，刚开始学时被弄的头晕了，网上找来找去，始终不知道/map,/odom,/base_link

他们之间谁能继承谁，谁链接谁一点都不懂，也不知道该如何链接mid360的livox_frame以及其他的，

最后经历了大量的寻找以及实验，才知道导航topic链接是这样的

/map -> /odom -> base_link -> livox_frame(或者其他雷达的link)

其中/map -> /odom 的tf关系是由 各种 SLAM算法发布的，例如icp、amcl

/odom -> /base_link 的tf关系是由各种lio算法发布的，例如fast_lio,point_lio

对于mid360的点云数据来说，还需要进行

/base_link -> livox_frame 的tf变换，是由 pointcloud_to_laserscan 算法发布的


如果需要用octomap进行点云处理，则需要将octomap_server_launch.py中的

```
DeclareLaunchArgument('pointcloud_min_height', default_value='-0.12'),    #机器人高低度 单位m
DeclareLaunchArgument('pointcloud_max_height', default_value='0.35'),    #机器人低高度 单位m
```

这两句按照实际情况更改，与上述的与thre_z_max、与thre_z_min保持一致

