#!/usr/bin/env python3
"""
直接串口测试脚本 —— 不启动 ROS 节点，直接按 MCU case 0x07 协议向 /dev/ttyACM0 发帧。

帧格式（9 字节）:
    12 4C | 07 | 04 | <vx_sign> <vx> <vy_sign> <vy> | <checksum>
    - 帧头:  0x12 0x4C
    - cmd:   0x07 (下发速度)
    - length: 0x04 (content 字节数)
    - content: vx_sign vx_mag vy_sign vy_mag   (sign: 0=正, 1=负; mag: uint8 0~255)
    - checksum: 前 8 字节累加和 mod 256

用法:
    python3 serial_test.py                      # 默认 vx=100, vy=0, 发 20 帧后停止
    python3 serial_test.py 100 -50 50 30        # vx=100, vy=-50, 共 50 帧, 每帧间隔 30ms
"""
import serial
import sys
import time

PORT = '/dev/ttyACM0'
BAUD = 230400

def build_frame(vx: int, vy: int) -> bytes:
    """构造 case 0x07 速度帧。"""
    vx = max(min(vx, 0xFF), -0xFF)
    vy = max(min(vy, 0xFF), -0xFF)

    vx_sign = 0 if vx >= 0 else 1
    vy_sign = 0 if vy >= 0 else 1

    content = bytes([
        0x12, 0x4C,   # 帧头
        0x07,         # cmd_id
        0x04,         # length = content 字节数
        vx_sign, abs(vx), vy_sign, abs(vy),
    ])
    checksum = sum(content) % 256
    return content + bytes([checksum])


def main():
    # 解析参数: vx, vy, 帧数, 间隔ms
    vx = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    vy = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    n_frames = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    interval_ms = int(sys.argv[4]) if len(sys.argv) > 4 else 30

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[错误] 打开串口 {PORT} 失败: {e}")
        sys.exit(1)

    print(f"串口 {PORT} 已打开 @ {BAUD}")
    print(f"下发 vx={vx}, vy={vy}, 共 {n_frames} 帧, 间隔 {interval_ms}ms")

    frame = build_frame(vx, vy)
    print(f"帧内容: {frame.hex()}")

    for i in range(n_frames):
        ser.write(frame)
        print(f"[{i+1}/{n_frames}] 发送: {frame.hex()}")
        time.sleep(interval_ms / 1000.0)

    ser.close()
    print("发送完毕，串口已关闭")


if __name__ == '__main__':
    main()
