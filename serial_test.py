#!/usr/bin/env python3
"""
直接串口测试脚本 —— 不启动 ROS 节点，直接按 MCU case 0x07 协议向 /dev/ttyACM0 发帧。

帧格式（11 字节）:
    12 4C | 07 | 06 | <vx_sign> <vx> <vy_sign> <vy> <wz_sign> <wz> | <checksum>
    - 帧头:  0x12 0x4C
    - cmd:   0x07 (下发速度)
    - length: 0x06 (content 字节数)
    - content: vx_sign vx_mag vy_sign vy_mag wz_sign wz_mag
               (sign: 0=正, 1=负; mag: uint8 0~255)
    - checksum: 前 10 字节累加和 mod 256

    固件只接受 6 字节 payload，不接受 0x04。没有角速度时 wz 也必须下发 0，
    不能省掉这两个字节。

符号约定（参数与 ROS / REP-103 一致，字节即原值，不做符号补偿）:
    vx 正 = 前进        vy 正 = 左移        wz 正 = 逆时针（俯视左转）

    底盘的实际轴映射尚未实测，脚本不做任何取反 —— 打印出的 hex 就是串口上
    的真实字节。
    与 src/driver/serial_node/.../serial_twist_publisher.py 的 build_frame() 一致。

用法:
    python3 serial_test.py                          # vx=100, vy=0, wz=0, 发 20 帧
    python3 serial_test.py -x 100 -y -50            # 前进 + 右移
    python3 serial_test.py -w 150                   # 只测左转
    python3 serial_test.py -w -150 -n 50 -i 30      # 只测右转, 50 帧, 间隔 30ms

参数:
    -x/--vx        前进速度   (默认 100)
    -y/--vy        左移速度   (默认 0)
    -w/--wz        角速度     (默认 0)
    -n/--frames    帧数       (默认 20)
    -i/--interval  帧间隔 ms  (默认 30)
    -p/--port      串口设备   (默认 /dev/ttyACM0)

结束时会连发 5 帧零速度再关串口；运行中按 Ctrl-C 也会先下发零速度再退出。
"""
import argparse
import sys
import time

import serial

PORT = '/dev/ttyACM0'
BAUD = 230400
STOP_FRAMES = 5   # 结尾连发几帧零速度


def build_frame(vx: int, vy: int, wz: int) -> bytes:
    """构造 case 0x07 速度帧（payload 固定 6 字节）。入参为 ROS 系方向。"""
    vx = max(min(vx, 0xFF), -0xFF)
    vy = max(min(vy, 0xFF), -0xFF)
    wz = max(min(wz, 0xFF), -0xFF)

    vx_sign = 0 if vx >= 0 else 1
    vy_sign = 0 if vy >= 0 else 1
    wz_sign = 0 if wz >= 0 else 1

    content = bytes([
        0x12, 0x4C,   # 帧头
        0x07,         # cmd_id
        0x06,         # length = content 字节数
        vx_sign, abs(vx),
        vy_sign, abs(vy),
        wz_sign, abs(wz),
    ])
    checksum = sum(content) % 256
    return content + bytes([checksum])


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('-x', '--vx', type=int, default=100, help='前进速度 (默认 100)')
    ap.add_argument('-y', '--vy', type=int, default=0, help='左移速度 (默认 0)')
    ap.add_argument('-w', '--wz', type=int, default=0, help='角速度, 正=左转 (默认 0)')
    ap.add_argument('-n', '--frames', type=int, default=20, help='帧数 (默认 20)')
    ap.add_argument('-i', '--interval', type=int, default=30, help='帧间隔 ms (默认 30)')
    ap.add_argument('-p', '--port', default=PORT, help=f'串口设备 (默认 {PORT})')
    args = ap.parse_args()

    try:
        ser = serial.Serial(args.port, BAUD, timeout=1)
    except Exception as e:
        print(f"[错误] 打开串口 {args.port} 失败: {e}")
        sys.exit(1)

    print(f"串口 {args.port} 已打开 @ {BAUD}")
    print(f"下发 vx={args.vx}, vy={args.vy}, wz={args.wz}, "
          f"共 {args.frames} 帧, 间隔 {args.interval}ms")

    frame = build_frame(args.vx, args.vy, args.wz)
    print(f"帧内容: {frame.hex()} ({len(frame)} 字节)")

    stop_frame = build_frame(0, 0, 0)
    try:
        for i in range(args.frames):
            ser.write(frame)
            ser.flush()
            print(f"[{i+1}/{args.frames}] 发送: {frame.hex()}")
            time.sleep(args.interval / 1000.0)
    except KeyboardInterrupt:
        print("\n[中断] 收到 Ctrl-C，立即下发零速度")
    finally:
        # ===== 收尾：连发若干帧零速度，确保车停下来 =====
        # 最后发出的速度帧必须为 0，否则 MCU 会一直按上一次速度行驶。
        # 多发几帧更保险：即使中间丢帧，也还有后续零速度帧兜底。
        for i in range(STOP_FRAMES):
            ser.write(stop_frame)
            ser.flush()
            print(f"[停止 {i+1}/{STOP_FRAMES}] 发送: {stop_frame.hex()}")
            time.sleep(args.interval / 1000.0)

        ser.close()
        print("发送完毕，最后一帧为零速度(停车)，串口已关闭")


if __name__ == '__main__':
    main()
