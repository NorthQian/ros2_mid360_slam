# #!/usr/bin/env python3

# import rclpy
# from rclpy.node import Node
# from geometry_msgs.msg import Twist
# import serial
# import struct
# from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
# class SerialTwistPublisher(Node):
#     def __init__(self):
#         super().__init__('serial_twist_publisher')

#         # 参数配置
#         self.declare_parameter('port', '/dev/ttyACM0')
#         self.declare_parameter('baudrate', 115200)
#         self.declare_parameter('linear_scale', 1000.0)  # m/s -> mm/s
#         self.declare_parameter('angular_scale', 1000.0)  # rad/s -> milli rad/s or deg/s ?

#         port = self.get_parameter('port').get_parameter_value().string_value
#         baudrate = self.get_parameter('baudrate').get_parameter_value().integer_value
#         self.linear_scale = self.get_parameter('linear_scale').get_parameter_value().double_value
#         self.angular_scale = self.get_parameter('angular_scale').get_parameter_value().double_value
#          # 添加一个定时器，每秒打印一次日志，确认 spin() 正常工作
#         self.timer = self.create_timer(1.0, self.timer_callback)

#         # 初始化串口
#         try:
#             self.ser = serial.Serial(port, baudrate, timeout=1)
#             self.get_logger().info(f'串口 {port} 已打开，波特率 {baudrate}')
#         except Exception as e:
#             self.get_logger().error(f'无法打开串口: {e}')
#             raise
#         # 使用 best effort 的 QoS 设置
#         # 使用与发布者一致的 QoS 设置
#         qos = QoSProfile(
#             depth=10,
#             reliability=QoSReliabilityPolicy.RELIABLE,
#             durability=QoSDurabilityPolicy.TRANSIENT_LOCAL
#         )

#         self.subscription = self.create_subscription(
#             Twist,
#             'cmd_vel',
#             self.twist_callback,
#             qos
#         )
#         # # 订阅 /cmd_vel
#         # self.subscription = self.create_subscription(
#         #     Twist,
#         #     'cmd_vel',
#         #     self.twist_callback,
#         #     10
#         # )

#     def timer_callback(self):
#         self.get_logger().info("【DEBUG】spin() 正常运行中...")

#     def twist_callback(self, msg):
#         vx = msg.linear.x
#         wz = msg.angular.z

#         # 转换为整数并缩放
#         speed = int(vx * self.linear_scale)
#         angular = int(wz * self.angular_scale)

#         # 限制范围（可选）
#         speed = max(min(speed, 0x7FFF), -0x8000)
#         angular = max(min(angular, 0x7FFF), -0x8000)

#         # 转换为 2 字节（有符号，大端）
#         speed_bytes = struct.pack('>h', speed)
#         angular_bytes = struct.pack('>h', angular)

#         # 构造数据包
#         packet = bytes([
#             0xCC,
#             speed_bytes[0], speed_bytes[1],
#             angular_bytes[0], angular_bytes[1],
#             0xEE
#         ])
        

#     # 模拟发送数据
#         # self.get_logger().info(f'模拟发送数据: {packet.hex()}')
#         try:
#             self.ser.write(packet)
#             self.get_logger().debug(f'发送数据: {packet.hex()}')
#         except Exception as e:
#             self.get_logger().error(f'串口写入失败: {e}')

# def main():
#     rclpy.init()
#     node = SerialTwistPublisher()
#     rclpy.spin(node)
#     node.destroy_node()
#     rclpy.shutdown()

# if __name__ == '__main__':
#     main()

# # ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "
# # linear:
# #   x: 0.3
# #   y: 0.0
# #   z: 0.0
# # angular:
# #   x: 0.0
# #   y: 0.0
# #   z: 0.5"



#!/usr/bin/env python3

import rclpy
import serial
from rclpy.node import Node
from geometry_msgs.msg import Twist



class CmdVelSubscriber(Node):
    def __init__(self):
        super().__init__('cmd_vel_subscriber')

        # 参数配置
        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baudrate', 230400)
        self.declare_parameter('send_rate', 20.0)       # 串口下发频率 (Hz)
        self.declare_parameter('cmd_timeout', 0.3)      # /cmd_vel 超时 (s)，超时后下发零速
        self.declare_parameter('linear_scale', 1000.0)
        self.declare_parameter('angular_scale', 1000.0)
        self.declare_parameter('speed_scale', 1.0)      # 下发给 MCU 的速度幅值比例缩放 (0~1 变慢)

        port = self.get_parameter('port').get_parameter_value().string_value
        baudrate = self.get_parameter('baudrate').get_parameter_value().integer_value
        self.linear_scale = self.get_parameter('linear_scale').get_parameter_value().double_value
        self.angular_scale = self.get_parameter('angular_scale').get_parameter_value().double_value
        self.speed_scale = max(self.get_parameter('speed_scale').get_parameter_value().double_value, 0.0)
        self.send_rate = max(self.get_parameter('send_rate').get_parameter_value().double_value, 1.0)
        self.cmd_timeout = self.get_parameter('cmd_timeout').get_parameter_value().double_value
        
                # 初始化串口
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.get_logger().info(f'串口 {port} 已打开，波特率 {baudrate}')
        except Exception as e:
            self.get_logger().error(f'无法打开串口: {e}')
            raise

        # 订阅 /cmd_vel 话题
        self.subscription = self.create_subscription(
            Twist,           # 消息类型
            '/cmd_vel',      # 话题名称
            self.listener_callback,  # 回调函数
            10               # QoS profile depth
        )
        self.get_logger().info("正在监听 /cmd_vel 话题...")

        # 最近一次收到的速度指令，以及接收时刻（失速保护用）
        self.last_vx = 0
        self.last_vy = 0
        self.last_wz = 0
        self.last_cmd_time = None
        self.stalled = False

        # 固定频率下发：即使 /cmd_vel 停了也持续发，超时则发零速
        self.timer = self.create_timer(1.0 / self.send_rate, self.timer_callback)
        self.get_logger().info(
            f'下发频率 {self.send_rate} Hz，失速超时 {self.cmd_timeout} s')
        self.get_logger().info(
            f'速度幅值缩放 speed_scale={self.speed_scale} '
            f'(线性缩放，满速 255 -> {int(round(0xFF * self.speed_scale))})')
        self.get_logger().info(
            f'角速度：payload 固定 6 字节(length=0x06)，angular_scale={self.angular_scale} '
            f'(满幅 255 -> {round(0xFF / self.angular_scale, 3)} rad/s)，'
            f'正=逆时针(左转)')

    def listener_callback(self, msg):
        # 只记录最新指令，实际发送交给定时器
        # 全向麦轮协议（MCU case 0x07）：Vx/Vy/Vw 三轴下发，payload 固定 6 字节
        self.last_vx = int(round(msg.linear.x * self.linear_scale))
        self.last_vy = int(round(msg.linear.y * self.linear_scale))
        self.last_wz = int(round(msg.angular.z * self.angular_scale))
        self.last_cmd_time = self.get_clock().now()

    def timer_callback(self):
        # 失速保护：超时未收到 /cmd_vel（节点崩溃、话题中断、目标取消）
        # 就下发零速，避免 MCU 保持最后一次速度继续跑
        if self.last_cmd_time is None:
            vx, vy, wz = 0, 0, 0
        else:
            elapsed = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1e9
            if elapsed > self.cmd_timeout:
                vx, vy, wz = 0, 0, 0
                if not self.stalled:
                    self.stalled = True
                    self.get_logger().warn(
                        f'{elapsed:.2f} s 未收到 /cmd_vel，失速保护触发：下发零速')
            else:
                vx, vy, wz = self.last_vx, self.last_vy, self.last_wz
                if self.stalled:
                    self.stalled = False
                    self.get_logger().info('收到新的 /cmd_vel，恢复正常下发')

        self.send_speed(vx, vy, wz)

    def scale_axis(self, value):
        """单轴量：先按协议上限截断，再按 speed_scale 线性缩放。

        顺序很重要：
        1) 先按协议上限截断——linear_scale 换算后常常远超 uint8（launch 里 5000.0
           意味着 0.051 m/s 就打满 255，nav2 的指令基本全程饱和）。
        2) 再比例缩放——必须放在截断之后，否则饱和值乘完又被压回 255，等于没减速。
        """
        value = max(min(value, 0xFF), -0xFF)
        return int(round(value * self.speed_scale))

    def build_frame(self, vx, vy, wz):
        """组帧：12 4C | 07 | 06 | vx_sign vx vy_sign vy wz_sign wz | checksum

        入参是 ROS 系（REP-103）的值：vx 正 = 前进，vy 正 = 左移，
        wz 正 = 逆时针（俯视左转）。

        字节即 ROS 系原值，不做任何符号补偿 —— 底盘的实际轴映射尚未实测，
        凭空假设一个取反只会让后续测量结果无法解读。

        符号位约定：0 = 正，1 = 负。

        payload 固定 6 字节（length = 0x06）：MCU 固件只接受 0x06、不接受 0x04，
        所以没有角速度时也必须下发 wz = 0，不能省略这两个字节。
        """
        vx = self.scale_axis(vx)
        vy = self.scale_axis(vy)
        wz = self.scale_axis(wz)

        payload = bytes([
            0 if vx >= 0 else 1, abs(vx),
            0 if vy >= 0 else 1, abs(vy),
            0 if wz >= 0 else 1, abs(wz),
        ])

        # length = payload 字节数（恒为 6）；checksum = 帧头到 payload 末尾累加和 mod 256
        content = bytes([0x12, 0x4C, 0x07, len(payload)]) + payload
        return content + bytes([sum(content) & 0xFF])

    def send_speed(self, vx, vy, wz=0):
        packet = self.build_frame(vx, vy, wz)

        try:
            self.ser.write(packet)
        except Exception as e:
            self.get_logger().error(f'串口写入失败: {e}', throttle_duration_sec=1.0)
        self.get_logger().debug(f'发送数据包: {packet.hex()}')
        self.get_logger().info(
            f'下发速度(ROS系): vx={vx}, vy={vy}, wz={wz}',
            throttle_duration_sec=1.0)


def main(args=None):
    rclpy.init(args=args)

    cmd_vel_subscriber = CmdVelSubscriber()

    try:
        rclpy.spin(cmd_vel_subscriber)
    except KeyboardInterrupt:
        pass


    cmd_vel_subscriber.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()