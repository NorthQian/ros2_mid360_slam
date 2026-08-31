#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_stl.py —— 修复被前导零填充损坏的二进制 STL 文件

背景
----
标准二进制 STL 的布局是:
    80 字节头 + 4 字节三角形数量(小端) + 50 字节 × 三角形数
读取器会在文件偏移 80 处读取三角形数量。某些导出流程把 STL 内容
写进了预分配(seek/truncate)的零填充缓冲区,导致真实的 STL 数据落在
文件末尾,前面是一大段 0x00。这时偏移 80 处读到的是 0,读取器会认为
模型为空或直接报错。

本脚本会:
  1. 跳过已经是有效格式的文件(标准二进制 STL / ASCII STL)。
  2. 对无效文件,尝试在文件内定位一段完整、自洽的二进制 STL
     (80 字节头 + 数量字段 + 对应长度的三角形数据,且正好占满文件)。
  3. 定位成功后,去掉前导零,把 STL 重写到偏移 0,覆盖原文件
     (默认先把原文件备份到 backup_original/)。

用法
----
  python3 fix_stl.py                    # 修复当前目录下所有 .stl
  python3 fix_stl.py /path/to/dir       # 修复指定目录
  python3 fix_stl.py --recursive        # 递归子目录
  python3 fix_stl.py --dry-run          # 只预览,不写任何文件
  python3 fix_stl.py --no-backup        # 不备份(覆盖前不可恢复)

退出码: 0 全部成功或全部跳过; 1 有文件无法修复。
"""

import argparse
import os
import struct
import sys

HEADER_LEN = 80          # 二进制 STL 头长度
COUNT_LEN = 4            # 三角形数量字段长度
TRIANGLE_STRIDE = 50     # 每个三角形 = 12 个 float + 2 字节属性
FIXED_LEN = HEADER_LEN + COUNT_LEN   # 84,固定部分长度
STL_EXTS = {'.stl'}

def parse_binary_stl_at(data, base):
    """尝试把 data[base:] 解析为二进制 STL(头从 base 开始)。

    返回 (count, stl_end) 表示解析自洽(count>0 且数据长度足够);
    否则返回 None。注意:这里只要求"数据长度足够",不要求占满整个文件。
    """
    if base < 0 or base + FIXED_LEN > len(data):
        return None
    count = struct.unpack_from('<I', data, base + HEADER_LEN)[0]
    if count <= 0:
        return None
    stl_end = base + FIXED_LEN + count * TRIANGLE_STRIDE
    if stl_end > len(data):
        return None
    return count, stl_end

def is_valid_binary_stl(data):
    """标准二进制 STL:头在偏移 0,且 84 + count*50 正好等于文件大小。"""
    res = parse_binary_stl_at(data, 0)
    if res is None:
        return False
    _, stl_end = res
    return stl_end == len(data)

def is_ascii_stl(data):
    """ASCII STL:以 'solid' 开头,且头部含有 'vertex' 关键字。
    (二进制 STL 的头也可能以 'solid' 开头,但不会含有 ASCII 'vertex'。)
    """
    head = data[:8192]
    return head.startswith(b'solid') and b'vertex' in head

def find_embedded_binary_stl(data):
    """在"前面全零、STL 数据在末尾"的文件里定位内嵌的二进制 STL。

    策略:
      - start = 第一个非零字节。STL 的 80 字节头必须在它附近结束,
        因此候选头起点 base ∈ [start-80, start]。
      - base 之前的字节必须全是零(前导填充)。
      - 该 STL 结构(84 + count*50)结束之后,文件剩余部分必须全是零
        (允许有尾部零填充;常见情况下正好占满文件,即无剩余字节)。

    返回 (base, count, stl_end),找不到返回 None。
    """
    n = len(data)

    start = None
    for i, b in enumerate(data):
        if b != 0:
            start = i
            break
    if start is None:
        return None  # 全零文件,无可恢复内容

    for base in range(max(0, start - HEADER_LEN), start + 1):
        # base <= start,且 start 是第一个非零字节,所以 data[:base] 必为全零
        res = parse_binary_stl_at(data, base)
        if res is None:
            continue
        count, stl_end = res
        if stl_end <= n and all(b == 0 for b in data[stl_end:]):
            # STL 结构之后只允许全零(或无剩余字节),否则不认为匹配
            return base, count, stl_end
    return None

def find_stl_files(root, recursive):
    """收集要处理的 STL 文件路径(按名称排序)。"""
    found = []
    if os.path.isfile(root):
        found = [root] if os.path.splitext(root)[1].lower() in STL_EXTS else []
    else:
        for dirpath, dirnames, filenames in os.walk(root):
            if not recursive and dirpath != root:
                # 只处理顶层;跳过 backup 目录避免误处理备份
                dirnames[:] = []
                continue
            if not recursive and dirnames:
                dirnames[:] = []
            if recursive:
                # 不要递归进备份目录
                dirnames[:] = [d for d in dirnames if d != 'backup_original']
            for fn in sorted(filenames):
                if os.path.splitext(fn)[1].lower() in STL_EXTS:
                    found.append(os.path.join(dirpath, fn))
    return found

def fix_file(path, backup, dry_run):
    """修复单个文件,返回 (status, detail)。"""
    try:
        with open(path, 'rb') as f:
            data = f.read()
    except OSError as e:
        return 'error', f'无法读取: {e}'

    if len(data) == 0:
        return 'skip', '空文件'
    if is_valid_binary_stl(data):
        return 'skip', '已是标准二进制 STL'
    if is_ascii_stl(data):
        return 'skip', 'ASCII STL(本来就无需修复)'

    hit = find_embedded_binary_stl(data)
    if hit is None:
        return 'fail', '未找到可恢复的 STL 结构'

    base, count, stl_end = hit
    clean = data[base:stl_end]

    # 写前再次确认:重写后的文件是合法的标准二进制 STL
    res = parse_binary_stl_at(clean, 0)
    assert res is not None and res[1] == len(clean), \
        f'{path}: 重建结果自检失败'

    if dry_run:
        return 'would_fix', \
            f'可修复: {len(data)} -> {len(clean)} 字节, 三角形数={count}, 前导零={base}'

    if backup:
        bak_dir = os.path.join(os.path.dirname(os.path.abspath(path)), 'backup_original')
        os.makedirs(bak_dir, exist_ok=True)
        bak_path = os.path.join(bak_dir, os.path.basename(path))
        if not os.path.exists(bak_path):   # 保留首次备份,不覆盖
            with open(bak_path, 'wb') as f:
                f.write(data)

    # 原子写入:先写临时文件再替换,避免中途断电留下半个文件
    tmp = path + '.fix.tmp'
    with open(tmp, 'wb') as f:
        f.write(clean)
    os.replace(tmp, path)
    return 'fixed', f'{len(data)} -> {len(clean)} 字节, 三角形数={count}'

def main():
    ap = argparse.ArgumentParser(description='修复被前导零填充损坏的 STL 文件')
    ap.add_argument('path', nargs='?', default='.',
                    help='目录(默认当前目录)或单个 STL 文件')
    ap.add_argument('-r', '--recursive', action='store_true',
                    help='递归处理子目录')
    ap.add_argument('--dry-run', action='store_true',
                    help='只预览要做什么,不写任何文件')
    ap.add_argument('--no-backup', action='store_true',
                    help='覆盖前不备份(不可恢复,慎用)')
    args = ap.parse_args()

    files = find_stl_files(args.path, args.recursive)
    if not files:
        print('没有找到 .stl 文件。')
        return 0

    print(f'共 {len(files)} 个 STL 文件:')
    status_count = {}
    any_fail = False
    for path in files:
        status, detail = fix_file(path, not args.no_backup, args.dry_run)
        status_count[status] = status_count.get(status, 0) + 1
        mark = {'fixed': 'FIXED', 'would_fix': 'WOULD-FIX',
                'skip': 'skip  ', 'fail': 'FAIL  ',
                'error': 'ERROR '}[status]
        print(f'  [{mark}] {path}: {detail}')
        if status in ('fail', 'error'):
            any_fail = True

    print()
    print('总结: ' + ', '.join(f'{k}={v}' for k, v in sorted(status_count.items())))
    if any_fail:
        print('有文件无法自动修复,请人工检查。')
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())

