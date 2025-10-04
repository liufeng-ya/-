# windows_sendinput_auto_fish.py
# Windows-only: 使用 SendInput 注入鼠标事件

import ctypes
import time
import sys
import random
import pygetwindow as gw
import json
import os
from datetime import datetime



# --- 依赖库导入 ---
try:
    import pyautogui
except ImportError:
    print("错误: 缺少 pyautogui 库，请运行: pip install pyautogui")
    raise

import cv2
import numpy as np

USE_KEYBOARD = True
try:
    import keyboard
    import threading
except ImportError:
    USE_KEYBOARD = False
    print("错误: 缺少 keyboard 库，请运行: pip install keyboard")
    raise

# --- 彩色打印与全局控制 ---
# Windows控制台颜色代码
STD_OUTPUT_HANDLE = -11
FOREGROUND_BLUE = 0x09
FOREGROUND_GREEN = 0x0a
FOREGROUND_CYAN = 0x0b
FOREGROUND_RED = 0x0c
FOREGROUND_MAGENTA = 0x0d
FOREGROUND_YELLOW = 0x0e
FOREGROUND_WHITE = 0x0f

# 背景颜色常量
BACKGROUND_BLUE = 0x10
BACKGROUND_GREEN = 0x20
BACKGROUND_CYAN = 0x30
BACKGROUND_RED = 0x40
BACKGROUND_MAGENTA = 0x50
BACKGROUND_YELLOW = 0x60
BACKGROUND_WHITE = 0x70

# 获取标准输出句柄
std_out_handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

def set_color(color):
    """设置控制台文本颜色"""
    ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, color)

def print_with_bg(message, fg_color=FOREGROUND_WHITE, bg_color=0, end='\n'):
    """带背景色的打印函数，文字前景色固定为白色"""
    combined_color = fg_color | bg_color
    set_color(combined_color)
    print(message, end=end)
    set_color(FOREGROUND_WHITE)  # 恢复默认白色

def cprint(message, color, end='\n'):
    """带颜色的打印函数"""
    set_color(color)
    print(message, end=end)
    set_color(FOREGROUND_WHITE) # 恢复默认白色

# 定义颜色类别
C_INFO = FOREGROUND_CYAN      # 浅蓝色: 普通信息
C_STATUS = FOREGROUND_YELLOW  # 浅黄色: 状态变化
C_SUCCESS = FOREGROUND_GREEN  # 浅绿色: 成功事件
C_WARN = FOREGROUND_MAGENTA   # 浅粉色: 警告信息
C_ERROR = FOREGROUND_RED      # 红色: 错误信息
C_DEBUG = FOREGROUND_WHITE    # 白色: 调试信息
C_CONTROL = FOREGROUND_BLUE   # 蓝色: 用户控制
C_GRAY = FOREGROUND_WHITE     # 灰色: 用于未知和空军统计

is_running = True  # 控制主循环是否运行

# 统计文件路径
STATISTICS_FILE = "statistics-content.json"

# 检查统计文件是否存在，如果不存在则禁用统计功能
STATISTICS_ENABLED = os.path.exists(STATISTICS_FILE)
if STATISTICS_ENABLED:
    cprint(f"发现统计文件 {STATISTICS_FILE}，将记录钓鱼数据", C_SUCCESS)
else:
    cprint(f"未发现统计文件 {STATISTICS_FILE}，本次运行将不记录数据", C_WARN)

# 鱼计数器
legendary_count = 0
epic_count = 0
rare_count = 0
extraordinary_count = 0
standard_count = 0
unknown_count = 0  # 新增：未知稀有度
airforce_count = 0

# 稀有度前景颜色映射 (最接近 RGB 的 16 色)
rarity_fg_colors = {
    'legendary': FOREGROUND_YELLOW,      # 接近 (255,201,53)
    'epic': FOREGROUND_MAGENTA,          # 接近 (171,99,255)
    'rare': FOREGROUND_CYAN,             # 接近 (106,175,246)，使用青色
    'extraordinary': FOREGROUND_GREEN,   # 接近 (142,201,85)
    'standard': FOREGROUND_WHITE,        # 接近 (183,186,193)，使用白色
    'unknown': FOREGROUND_MAGENTA        # 未知稀有度
}

# --- 统计功能 ---
def load_statistics():
    """从JSON文件加载统计数据"""
    if not os.path.exists(STATISTICS_FILE):
        return {"records": []}
    
    try:
        with open(STATISTICS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        cprint(f"加载统计文件失败: {e}", C_WARN)
        return {"records": []}

def save_statistics(data):
    """保存统计数据到JSON文件"""
    try:
        with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        cprint(f"保存统计文件失败: {e}", C_ERROR)

def record_fishing_result(rarity):
    """记录单次钓鱼结果"""
    # 检查统计功能是否启用
    if not STATISTICS_ENABLED:
        cprint("统计功能已禁用，跳过记录", C_DEBUG)
        return
        
    stats = load_statistics()
    
    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rarity": rarity,
        "is_airforce": rarity == 'airforce'
    }
    
    stats["records"].append(record)
    save_statistics(stats)
    cprint(f"已记录钓鱼结果到 {STATISTICS_FILE}", C_DEBUG)

def display_statistics():
    """显示统计信息"""
    stats = load_statistics()
    records = stats.get("records", [])
    
    if not records:
        cprint("暂无钓鱼统计数据", C_INFO)
        return
    
    # 统计各稀有度数量
    rarity_counts = {
        'legendary': 0,
        'epic': 0,
        'rare': 0,
        'extraordinary': 0,
        'standard': 0,
        'unknown': 0,
        'airforce': 0
    }
    
    for record in records:
        rarity = record.get('rarity', 'airforce')
        if rarity in rarity_counts:
            rarity_counts[rarity] += 1
    
    total_attempts = len(records)
    total_fish = sum(rarity_counts[r] for r in rarity_counts if r != 'airforce')
    airforce_count_total = rarity_counts['airforce']
    airforce_rate = (airforce_count_total / total_attempts * 100) if total_attempts > 0 else 0
    
    # 打印统计信息
    cprint("\n" + "="*50, C_INFO)
    cprint("📊 历史钓鱼统计", C_INFO)
    cprint("="*50, C_INFO)
    
    chinese_rarity_names = {
        'legendary': '传奇鱼',
        'epic': '史诗鱼',
        'rare': '稀有鱼',
        'extraordinary': '非凡鱼',
        'standard': '标准鱼',
        'unknown': '未知鱼'
    }
    
    # 逐行显示各稀有度统计
    for rarity in ['legendary', 'epic', 'rare', 'extraordinary', 'standard', 'unknown']:
        count = rarity_counts[rarity]
        rate = (count / total_attempts * 100) if total_attempts > 0 else 0
        zh_name = chinese_rarity_names[rarity]
        # 未知稀有度使用灰色显示
        if rarity == 'unknown':
            color = C_GRAY
        else:
            color = rarity_fg_colors[rarity]
        cprint(f"{zh_name}: {count}条 ({rate:.2f}%)", color)
    
    # 显示空军统计
    cprint(f"空军: {airforce_count_total}次 ({airforce_rate:.2f}%)", C_GRAY)
    
    # 显示总计
    cprint(f"\n总钓鱼次数: {total_attempts}次", C_INFO)
    cprint("="*50 + "\n", C_INFO)

def toggle_run():
    """切换脚本的运行/暂停状态"""
    global is_running
    is_running = not is_running
    status = '停止' if not is_running else '恢复运行'
    cprint(f"\n程序已 {status} (快捷键: Ctrl+L)\n", C_CONTROL)

def keyboard_listener():
    """监听键盘事件，用于暂停/恢复脚本"""
    while True:
        if USE_KEYBOARD and keyboard.is_pressed('ctrl+l'):
            toggle_run()
            time.sleep(0.5)  # 防止按键重复检测
        time.sleep(0.1)

# 在后台启动键盘监听线程
listener_thread = threading.Thread(target=keyboard_listener, daemon=True)
listener_thread.start()

try:
    import win32gui
    import win32con
except ImportError:
    cprint("错误: 缺少 pywin32 库，请运行: pip install pywin32", C_ERROR)
    raise



# --- 窗口与坐标设置 ---
# 查找游戏窗口
try:
    window = gw.getWindowsWithTitle("猛兽派对")[0]
    hwnd = win32gui.FindWindow(None, "猛兽派对")
except IndexError:
    cprint("错误: 未找到 '猛兽派对' 游戏窗口，请确保游戏正在运行。", C_ERROR)
    sys.exit(1)

# 获取窗口客户区的大小和位置
rect = win32gui.GetClientRect(hwnd)
window_width = rect[2] - rect[0]
window_height = rect[3] - rect[1]
window_left = window.left
window_top = window.top

cprint(f"成功获取窗口: '猛兽派对'", C_INFO)
cprint(f"窗口大小: {window_width}x{window_height}  位置: ({window_left}, {window_top})", C_INFO)

# 分辨率检测和配置提示
if window_width == 1920 and window_height == 1080:
    cprint("检测到 1920*1080 分辨率，已应用优化坐标设置", C_SUCCESS)
elif window_width == 3840 and window_height == 2160:
    cprint("检测到 3840*2160 分辨率，已应用优化坐标设置", C_SUCCESS)
    cprint("green_zone 固定坐标: (2140, 1870)", C_DEBUG)
    cprint("orange_zone 固定坐标: (2155, 1850)", C_DEBUG)
else:
    cprint(f"未识别的分辨率 {window_width}*{window_height}，使用默认坐标设置", C_WARN)

# 定义像素检测的相对坐标比例
# 格式: (x_ratio, y_ratio, description)
COORDS_CONFIG = {
    "orange_zone": (0.5874, 0.9278, "张力表盘橙色区域"),
    "green_zone": (0.5444, 0.9067, "张力表盘绿色边界"),
    "bite_mark": (0.5083, 0.2811, "咬钩感叹号"),
}

# 计算绝对坐标
def get_abs_coord(ratio_x, ratio_y, is_orange_zone=False):
    # 针对3840*2160分辨率的特殊处理
    if window_width == 3840 and window_height == 2160:
        if is_orange_zone:
            return 2155, 1850  # orange_zone固定坐标
        else:
            return 2113, 1910  # green_zone固定坐标
    else:
        # 其他分辨率使用比例计算
        return int(ratio_x * window_width + window_left), int(ratio_y * window_height + window_top)

CHECK_X, CHECK_Y = get_abs_coord(COORDS_CONFIG["orange_zone"][0], COORDS_CONFIG["orange_zone"][1], is_orange_zone=True)
CHECK_X2, CHECK_Y2 = get_abs_coord(COORDS_CONFIG["green_zone"][0], COORDS_CONFIG["green_zone"][1])
CHECK_X3, CHECK_Y3 = get_abs_coord(COORDS_CONFIG["bite_mark"][0], COORDS_CONFIG["bite_mark"][1])

cprint(f"计算坐标: 橙色区({CHECK_X}, {CHECK_Y}), 绿色边界({CHECK_X2}, {CHECK_Y2}), 感叹号({CHECK_X3}, {CHECK_Y3})", C_DEBUG)

# 窗口位置检测计数器
window_check_counter = 0
window_check_frequency = 10  # 每10次操作检测一次窗口位置

def update_window_position():
    """更新窗口位置信息"""
    global window, hwnd, window_width, window_height, window_left, window_top, window_check_counter
    
    try:
        # 获取最新的窗口信息
        new_window = gw.getWindowsWithTitle("猛兽派对")[0]
        new_hwnd = win32gui.FindWindow(None, "猛兽派对")
        
        # 获取新的窗口位置和大小
        new_rect = win32gui.GetClientRect(new_hwnd)
        new_window_width = new_rect[2] - new_rect[0]
        new_window_height = new_rect[3] - new_rect[1]
        new_window_left = new_window.left
        new_window_top = new_window.top
        
        # 检查窗口位置是否发生变化
        if (new_window_left != window_left or new_window_top != window_top or 
            new_window_width != window_width or new_window_height != window_height):
            cprint(f"检测到窗口位置变化: 从 ({window_left}, {window_top}) {window_width}x{window_height} "
                   f"变为 ({new_window_left}, {new_window_top}) {new_window_width}x{new_window_height}", C_WARN)
            
            # 更新全局变量
            window = new_window
            hwnd = new_hwnd
            window_width = new_window_width
            window_height = new_window_height
            window_left = new_window_left
            window_top = new_window_top
            
            # 重新计算检测坐标
            global CHECK_X, CHECK_Y, CHECK_X2, CHECK_Y2, CHECK_X3, CHECK_Y3
            CHECK_X, CHECK_Y = get_abs_coord(COORDS_CONFIG["orange_zone"][0], COORDS_CONFIG["orange_zone"][1], is_orange_zone=True)
            CHECK_X2, CHECK_Y2 = get_abs_coord(COORDS_CONFIG["green_zone"][0], COORDS_CONFIG["green_zone"][1])
            CHECK_X3, CHECK_Y3 = get_abs_coord(COORDS_CONFIG["bite_mark"][0], COORDS_CONFIG["bite_mark"][1])
            
            cprint(f"已更新坐标 (优化版): 橙色区({CHECK_X}, {CHECK_Y}), 绿色边界({CHECK_X2}, {CHECK_Y2}), 感叹号({CHECK_X3}, {CHECK_Y3})", C_DEBUG)
        
        window_check_counter = 0  # 重置计数器
        return True
    except Exception as e:
        cprint(f"更新窗口位置失败: {e}", C_ERROR)
        return False

def check_window_position():
    """检查窗口位置，每一定次数检测一次"""
    global window_check_counter
    window_check_counter += 1
    
    # 每window_check_frequency次操作检测一次窗口位置
    if window_check_counter >= window_check_frequency:
        update_window_position()


# --- Win32 SendInput 底层鼠标注入定义 ---
# 这部分代码用于模拟更真实的鼠标点击，绕过某些游戏的检测
PUL = ctypes.POINTER(ctypes.c_ulong)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort)
    ]

class INPUT_I(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", INPUT_I)
    ]

# 常量
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_WHEEL = 0x0800

# 获取 SendInput 函数
SendInput = ctypes.windll.user32.SendInput

# --- 鼠标事件封装 ---
def _send_mouse_event(flags, dx=0, dy=0, data=0):
    """构建并发送一个鼠标INPUT事件"""
    extra = ctypes.c_ulong(0)
    mi = MOUSEINPUT(dx, dy, data, flags, 0, ctypes.pointer(extra))
    ii = INPUT_I()
    ii.mi = mi
    command = INPUT(INPUT_MOUSE, ii)
    # 1 表示发送一个 INPUT
    SendInput(1, ctypes.byref(command), ctypes.sizeof(command))

def left_down():
    _send_mouse_event(MOUSEEVENTF_LEFTDOWN)

def left_up():
    _send_mouse_event(MOUSEEVENTF_LEFTUP)

def left_click():
    """执行一次完整的左键单击"""
    left_down()
    time.sleep(0.05)  # 模拟按下的短暂时间
    left_up()

# 移动鼠标到绝对坐标 (0..65535 范围)
def move_mouse_abs(x, y):
    # 获取屏幕尺寸
    sx = ctypes.windll.user32.GetSystemMetrics(0)
    sy = ctypes.windll.user32.GetSystemMetrics(1)
    # 归一化到 0..65535
    nx = int(x * 65535 / (sx - 1))
    ny = int(y * 65535 / (sy - 1))
    _send_mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, nx, ny)

# --- 像素与颜色检测 ---

def get_pointer_color(x, y):
    """获取指定屏幕坐标的像素颜色"""
    return pyautogui.pixel(x, y)

def color_changed(base_color, new_color, tolerance=12):
    """检查两种颜色之间的差异是否超过容差"""
    br, bg, bb = base_color
    nr, ng, nb = new_color
    return (abs(br - nr) > tolerance) or (abs(bg - ng) > tolerance) or (abs(bb - nb) > tolerance)

def color_in_range(base_color, new_color, tolerance=12):
    """检查一种颜色是否在另一种颜色的容差范围内"""
    br, bg, bb = base_color
    nr, ng, nb = new_color
    return (abs(br - nr) <= tolerance) and (abs(bg - ng) <= tolerance) and (abs(bb - nb) <= tolerance)
def detect_fish_unified(region, rarity_threshold=0.1, indicator_threshold=0.05, tolerance=5):
    """统一检测鱼稀有度和指示颜色，合并两种检测逻辑
    Args:
        region: (top, left, bottom, right) 区域坐标
        rarity_threshold: 稀有度匹配像素占比阈值
        indicator_threshold: 指示颜色匹配像素占比阈值
        tolerance: 颜色容差 (±5)
    Returns:
        str: 'legendary', 'epic', 'rare', 'extraordinary', 'standard', 'unknown', 或 'airforce'
    """
    # 定义稀有度颜色基准 (R, G, B)
    rarity_colors = {
        'legendary': (255, 201, 53),    # 传奇鱼
        'epic': (171, 99, 255),         # 史诗鱼
        'rare': (106, 175, 246),        # 稀有鱼
        'extraordinary': (142, 201, 85),# 非凡鱼
        'standard': (183, 186, 193)     # 标准鱼
    }
    
    # 定义指示颜色
    light_brown = (199, 118, 38)   # 浅棕色，容差±5
    bright_yellow = (255, 232, 79)  # 明黄色，容差±10
    
    top, left, bottom, right = region
    total_pixels = (bottom - top) * (right - left)
    if total_pixels <= 0:
        return 'airforce'
    
    # 记录每个稀有度的匹配像素数
    match_counts = {rarity: 0 for rarity in rarity_colors}
    brown_count = 0
    yellow_count = 0
    sample_count = 0
    step = 10  # 步长为10的顺序采样
    
    # 计算预计采样点数
    num_y_steps = ((bottom - top - 1) // step) + 1
    num_x_steps = ((right - left - 1) // step) + 1
    expected_samples = num_y_steps * num_x_steps
    
    cprint(f"开始在区域 {region} 内步长{step}顺序采样 (预计 {expected_samples} 个点) 统一检测鱼稀有度和指示颜色...", C_DEBUG)
    
    for y in range(top, bottom, step):
        for x in range(left, right, step):
            try:
                color = get_pointer_color(x, y)
                
                # 首先检查稀有度颜色
                rarity_matched = False
                for rarity, target_color in rarity_colors.items():
                    if color_in_range(target_color, color, tolerance):
                        match_counts[rarity] += 1
                        rarity_matched = True
                        break  # 一个像素只匹配一个稀有度（优先第一个匹配）
                
                # 如果没有匹配稀有度，检查指示颜色
                if not rarity_matched:
                    # 检查浅棕色（容差±5）
                    if color_in_range(light_brown, color, tolerance=5):
                        brown_count += 1
                    # 检查明黄色（容差±10）
                    elif color_in_range(bright_yellow, color, tolerance=10):
                        yellow_count += 1
                
                sample_count += 1
            except Exception as e:
                cprint(f"采样点 ({x}, {y}) 颜色获取失败: {e}", C_DEBUG)
                sample_count += 1  # 仍计入采样
    
    if sample_count == 0:
        cprint("采样失败，无有效点", C_DEBUG)
        return 'airforce'
    
    # 计算每个稀有度的匹配比例
    max_ratio = 0
    best_rarity = 'airforce'
    for rarity, count in match_counts.items():
        ratio = count / sample_count
        cprint(f"{rarity}: {count}/{sample_count} ({ratio:.2%})", C_DEBUG)
        if ratio > max_ratio and ratio >= rarity_threshold:
            max_ratio = ratio
            best_rarity = rarity
    
    # 计算指示颜色的匹配比例
    brown_ratio = brown_count / sample_count
    yellow_ratio = yellow_count / sample_count
    cprint(f"标志色1: {brown_count}/{sample_count} ({brown_ratio:.2%})", C_DEBUG)
    cprint(f"标志色2: {yellow_count}/{sample_count} ({yellow_ratio:.2%})", C_DEBUG)
    
    # 优先返回稀有度检测结果
    if best_rarity != 'airforce':
        cprint(f"检测到 {best_rarity} 鱼 (比例 {max_ratio:.2%})", C_DEBUG)
        return best_rarity
    
    # 如果稀有度检测失败，检查指示颜色
    if brown_ratio >= indicator_threshold or yellow_ratio >= indicator_threshold:
        cprint(f"检测到鱼指示颜色 ({brown_ratio:.2%} 或 {yellow_ratio:.2%} ≥ {indicator_threshold:.2%})", C_DEBUG)
        cprint("钓到了鱼！但检测稀有度失败。", C_WARN)
        return 'unknown'  # 返回未知稀有度
    
    # 都未检测到
    cprint(f"未检测到足够匹配像素，判定为空军 (稀有度阈值 {rarity_threshold}, 指示颜色阈值 {indicator_threshold})", C_DEBUG)
    return 'airforce'
# --- 混合匹配咬钩检测 ---
cprint("初始化混合匹配检测...", C_INFO)

# 1. 定义精确的搜索区域 (ROI)
center_x, center_y = window_left + window_width // 2, window_top + window_height // 2
roi_width = int(window_width * 0.08 * 2)
roi_height = int(window_height * 0.40)
roi_x = center_x - roi_width // 2
roi_y = center_y - roi_height
roi_search_area = (roi_x, roi_y, roi_width, roi_height)
cprint(f"颜色定位搜索区域 (ROI): x={roi_x}, y={roi_y}, w={roi_width}, h={roi_height}", C_DEBUG)

# 2. 定义黄色HSV范围
LOWER_YELLOW = np.array([22, 120, 200])
UPPER_YELLOW = np.array([28, 255, 255])

# 3. 读取OpenCV模板（保持透明通道）
template = cv2.imread("exclamation_mark.png", cv2.IMREAD_UNCHANGED)
template_bgr = template[:, :, :3]        # RGB部分
template_alpha = template[:, :, 3]       # alpha通道作为mask
w, h = template_bgr.shape[1], template_bgr.shape[0]
cprint(f"已加载模板 'exclamation_mark.png' (大小: {w}x{h})", C_DEBUG)

def find_yellow_blob(img_bgr):
    """在图中寻找最大的黄色像素簇，返回其中心点"""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_YELLOW, UPPER_YELLOW)
    
    # 寻找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None

    # 找到最大的轮廓
    largest_contour = max(contours, key=cv2.contourArea)
    
    # 如果最大的轮廓太小，也忽略
    if cv2.contourArea(largest_contour) < 50:
        return None
        
    # 计算中心点
    M = cv2.moments(largest_contour)
    if M["m00"] == 0:
        return None
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    
    return (cx, cy)

def verify_with_opencv(img_bgr, center_point, threshold=0.5):
    """在候选中心点周围的小区域内进行OpenCV模板匹配验证"""
    # 定义一个紧密包裹感叹号的小ROI
    verify_roi_w, verify_roi_h = 100, 200
    vx = center_point[0] - verify_roi_w // 2
    vy = center_point[1] - verify_roi_h // 2
    
    # 确保ROI在图像范围内
    vx = max(0, vx)
    vy = max(0, vy)
    
    # 从原始大图中截取小ROI
    img_roi = img_bgr[vy:vy+verify_roi_h, vx:vx+verify_roi_w]
    
    if img_roi.shape[0] < 1 or img_roi.shape[1] < 1:
        return False

    # 在小ROI上进行模板匹配
    res = cv2.matchTemplate(img_roi, template_bgr, cv2.TM_CCOEFF_NORMED, mask=template_alpha)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    
    
    return max_val >= threshold

# --- 核心钓鱼逻辑 ---
def bite_check():
    """混合模式检测鱼是否咬钩（先黄色定位，再OpenCV验证）"""
    cprint(f"等待鱼咬钩 (混合模式: 黄色定位 + OpenCV验证)...", C_STATUS)
    timeout = 40
    start_time = time.time()
    
    check_interval = 0.1  # 每0.1秒检测一次
    
    while is_running:
        # 使用可中断的等待
        elapsed = 0
        while elapsed < check_interval and is_running:
            time.sleep(0.01)  # 小段睡眠，便于快速响应中断
            elapsed += 0.01
        
        if not is_running:
            break
            
        # 1. 快速颜色定位
        try:
            screenshot = pyautogui.screenshot(region=roi_search_area)
            img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception as e:
            cprint(f"截图失败: {e}", C_WARN)
            continue
            
        blob_center = find_yellow_blob(img_bgr)
        
        if blob_center:
            # 2. 精确OpenCV模板验证
            if verify_with_opencv(img_bgr, blob_center, threshold=0.5):
                cprint("有鱼咬钩！ (混合匹配成功)", C_SUCCESS)
                # 使用可中断的随机等待
                wait_time = random.uniform(0.1, 0.5)
                elapsed = 0
                while elapsed < wait_time and is_running:
                    time.sleep(0.01)
                    elapsed += 0.01
                if not is_running:
                    return False
                return True

        # 判断是否超时
        if time.time() - start_time >= timeout:
            cprint("咬钩检测超时，未检测到鱼", C_WARN)
            return False
            
    cprint("咬钩检测被中断", C_CONTROL)
    return False

def reel():
    """控制收杆过程，处理张力"""
    start_time = time.time()
    base_color_green = (127, 181, 77)   # 张力表盘绿色区
    base_color_orange = (255, 195, 83)  # 张力表盘橙色区
    success_popup_delay = 0.6           # 钓鱼成功弹窗的延迟时间（秒）
    
    cprint(f"开始收杆...", C_STATUS)
    cprint(f"目标颜色: 绿色区={base_color_green}, 橙色区={base_color_orange}", C_DEBUG)
    
    times = 0
    try:
        initial_orange = get_pointer_color(CHECK_X, CHECK_Y)
        cprint(f"初始橙色区颜色: {initial_orange}", C_DEBUG)
    except Exception as e:
        cprint(f"读取初始像素失败: {e}", C_WARN)

    while is_running:
        # 检查窗口位置
        check_window_position()
        
        if not is_running:
            cprint("收杆被中断", C_CONTROL)
            break
            
        # 紧急退出
        if USE_KEYBOARD and keyboard.is_pressed('q'):
            left_up()
            cprint("检测到 'q'，紧急终止脚本", C_CONTROL)
            sys.exit(0)

        try:
            color_exist = get_pointer_color(CHECK_X, CHECK_Y)
            color_bound = get_pointer_color(CHECK_X2, CHECK_Y2)
        except Exception as e:
            cprint(f"读取像素失败: {e}", C_WARN)
            time.sleep(0.05)
            continue

        # 条件1：钓鱼成功 (张力表盘消失)
        if times >= 10 and color_changed(base_color_orange, color_exist, tolerance=100):
            cprint(f"检测到张力表盘消失，准备验证钓鱼结果...", C_STATUS)
            left_up()
            
            # 等待0.4秒后进入第一轮检测
            time.sleep(0.4)

            center_x = window_left + window_width // 2
            # 根据不同分辨率设置不同的检测区域
            if window_width == 1920 and window_height == 1080:
                region_top = window_top + 115
                region_bottom = window_top + 160
                region_left = center_x - 100
                region_right = center_x + 10
            elif window_width == 3840 and window_height == 2160:
                region_top = window_top + 230
                region_bottom = window_top + 320
                region_left = center_x - 130
                region_right = center_x + 20
            else:
                # 默认设置（保持原有逻辑）
                region_top = window_top + 190
                region_bottom = window_top + 250
                region_left = center_x - 130
                region_right = center_x + 20
            
            # 确保区域在窗口范围内
            region_top = max(window_top, region_top)
            region_bottom = min(window_top + window_height, region_bottom)
            region_left = max(window_left, region_left)
            region_right = min(window_left + window_width, region_right)
            
            region = (region_top, region_left, region_bottom, region_right)
            
            # 多轮检测逻辑（最多5秒）
            max_wait_time = 5
            elapsed_time = 0
            check_interval = 1  # 每次检测间隔1秒
            
            while elapsed_time < max_wait_time and is_running:
                cprint(f"第{elapsed_time // check_interval + 1}轮统一检测鱼稀有度和指示颜色，区域: {region}", C_DEBUG)
                rarity = detect_fish_unified(region, rarity_threshold=0.1, indicator_threshold=0.05, tolerance=5)
                
                if not is_running:
                    return 'airforce'
                
                if rarity != 'airforce':
                    cprint(f"钓鱼成功！稀有度: {rarity}", C_SUCCESS)
                    return rarity
                
                # 都未检测到，等待1秒后重试（使用可中断等待）
                if elapsed_time + check_interval < max_wait_time:
                    cprint(f"未检测到鱼，{check_interval}秒后重试...", C_DEBUG)
                    # 使用可中断的等待
                    wait_elapsed = 0
                    while wait_elapsed < check_interval and is_running:
                        time.sleep(0.01)
                        wait_elapsed += 0.01
                    elapsed_time += check_interval
                else:
                    break
            
            # 超时仍未检测到
            cprint(f"检测超时（{max_wait_time}秒），判定为空军", C_WARN)
            return 'airforce'

        # 条件2：超时
        if time.time() - start_time > 30:
            cprint("收杆超时 (30秒)", C_WARN)
            left_up()
            return 'airforce'  # 超时视为空军

        times += 1
        time.sleep(0.1)

        if times % 10 == 0:
            cprint(f"收杆中 (第 {times} 次): 橙色区={color_exist}, 绿色边界={color_bound}", C_DEBUG)

        left_down()

        if times % 15 == 0:
            cprint("持续收杆...", C_STATUS)
            
        # 条件3：张力过高，需要松手
        if times >= 30 and color_changed(base_color_green, color_bound, tolerance=40):
            try:
                # 松手前再次确认张力表盘是否存在
                color_exist_before = get_pointer_color(CHECK_X, CHECK_Y)
                if color_changed(base_color_orange, color_exist_before, tolerance=100):
                    cprint(f"松手前检测到张力表盘消失，准备验证钓鱼结果...", C_STATUS)
                    left_up()
                    
                    # 等待0.4秒后进入第一轮检测
                    time.sleep(0.4)

                    center_x = window_left + window_width // 2
                    # 根据不同分辨率设置不同的检测区域
                    if window_width == 1920 and window_height == 1080:
                        region_top = window_top + 115
                        region_bottom = window_top + 160
                        region_left = center_x - 100
                        region_right = center_x + 10
                    elif window_width == 3840 and window_height == 2160:
                        region_top = window_top + 230
                        region_bottom = window_top + 320
                        region_left = center_x - 130
                        region_right = center_x + 20
                    else:
                        # 默认设置（保持原有逻辑）
                        region_top = window_top + 190
                        region_bottom = window_top + 250
                        region_left = center_x - 130
                        region_right = center_x + 20
            
                    
                    # 确保区域在窗口范围内
                    region_top = max(window_top, region_top)
                    region_bottom = min(window_top + window_height, region_bottom)
                    region_left = max(window_left, region_left)
                    region_right = min(window_left + window_width, region_right)
                    
                    region = (region_top, region_left, region_bottom, region_right)
                    
                    # 多轮检测逻辑（最多5秒）
                    max_wait_time = 5
                    elapsed_time = 0
                    check_interval = 1  # 每次检测间隔1秒
                    
                    while elapsed_time < max_wait_time and is_running:
                        cprint(f"第{elapsed_time // check_interval + 1}轮统一检测鱼稀有度和指示颜色 (松手后)，区域: {region}", C_DEBUG)
                        rarity = detect_fish_unified(region, rarity_threshold=0.1, indicator_threshold=0.05, tolerance=5)
                        
                        if not is_running:
                            return 'airforce'
                        
                        if rarity != 'airforce':
                            cprint(f"钓鱼成功！稀有度: {rarity}", C_SUCCESS)
                            return rarity
                        
                        # 都未检测到，等待1秒后重试（使用可中断等待）
                        if elapsed_time + check_interval < max_wait_time:
                            cprint(f"未检测到鱼，{check_interval}秒后重试...", C_DEBUG)
                            # 使用可中断的等待
                            wait_elapsed = 0
                            while wait_elapsed < check_interval and is_running:
                                time.sleep(0.01)
                                wait_elapsed += 0.01
                            elapsed_time += check_interval
                        else:
                            break
                    
                    # 超时仍未检测到
                    cprint(f"检测超时（{max_wait_time}秒），判定为空军", C_WARN)
                    return 'airforce'
            except Exception as e:
                cprint(f"松手前检查像素失败: {e}", C_WARN)
            
            cprint(f"张力过高，暂时松手。边界颜色: {color_bound}", C_STATUS)
            left_up()
            sleep_time = random.uniform(2.0, 3.0)
            # 使用可中断的等待
            elapsed = 0
            while elapsed < sleep_time and is_running:
                time.sleep(0.01)
                elapsed += 0.01
            if not is_running:
                return 'airforce'
            cprint("继续收杆", C_STATUS)
def auto_fish_once():
    """执行一轮完整的自动钓鱼流程"""
    global legendary_count, epic_count, rare_count, extraordinary_count, standard_count, unknown_count, airforce_count
    
    # 显示统计信息
    display_statistics()
    
    cprint("\n" + "="*20 + " 开始新一轮钓鱼 " + "="*20, C_INFO)
    
    # 1. 抛竿
    cprint("抛竿中...", C_STATUS)
    left_down()

    #1.5 纠正身位
    def async_press_a():
        sleep_time1 = random.uniform(0.6, 2.1)
        # 使用可中断的等待
        elapsed = 0
        while elapsed < sleep_time1 and is_running:
            time.sleep(0.01)
            elapsed += 0.01
        if not is_running:
            return
            
        keyboard.press('a')
        sleep_time2 = random.uniform(0.25, 0.38)
        # 使用可中断的等待
        elapsed = 0
        while elapsed < sleep_time2 and is_running:
            time.sleep(0.01)
            elapsed += 0.01
        if not is_running:
            keyboard.release('a')
            return
            
        keyboard.release('a')
    
    async_thread = threading.Thread(target=async_press_a)
    async_thread.start()

    sleep_time = random.uniform(3.0, 4.0)
    # 使用可中断的等待
    elapsed = 0
    while elapsed < sleep_time and is_running:
        time.sleep(0.01)
        elapsed += 0.01
    if not is_running:
        left_up()
        return
    left_up()
    cprint("抛竿完成", C_SUCCESS)

    # 2. 等待鱼咬钩
    if not bite_check():
        cprint("本轮未钓到鱼或被中断", C_WARN)
        return

    # 3. 咬钩后初始点击
    click_duration = random.uniform(0.1, 0.3)
    cprint(f"咬钩后初始点击，持续 {click_duration:.2f} 秒", C_STATUS)
    left_down()
    time.sleep(click_duration)
    left_up()
    
    # 4. 等待浮漂稳定
    wait_time = 1.6 + 2 * click_duration
    cprint(f"等待浮漂上浮，持续 {wait_time:.2f} 秒", C_STATUS)
    # 使用可中断的等待
    elapsed = 0
    while elapsed < wait_time and is_running:
        time.sleep(0.01)
        elapsed += 0.01
    if not is_running:
        return

    # 5. 收杆与张力控制
    reel_result = reel()
    
    # 处理结果
    if reel_result == 'airforce':
        airforce_count += 1
    else:
        # 6. 收鱼
        cprint("收鱼中...", C_STATUS)
        sleep_time = random.uniform(1.5, 2.5)
        # 使用可中断的等待
        elapsed = 0
        while elapsed < sleep_time and is_running:
            time.sleep(0.01)
            elapsed += 0.01
        if not is_running:
            return
            
        # 使用可中断的等待
        elapsed = 0
        while elapsed < 0.5 and is_running:
            time.sleep(0.01)
            elapsed += 0.01
        if not is_running:
            return
            
        left_down()
        
        # 使用可中断的等待
        elapsed = 0
        while elapsed < 0.2 and is_running:
            time.sleep(0.01)
            elapsed += 0.01
        if not is_running:
            left_up()
            return
            
        left_up()
        # 更新计数器
        if reel_result == 'legendary':
            legendary_count += 1
        elif reel_result == 'epic':
            epic_count += 1
        elif reel_result == 'rare':
            rare_count += 1
        elif reel_result == 'extraordinary':
            extraordinary_count += 1
        elif reel_result == 'standard':
            standard_count += 1
        elif reel_result == 'unknown':
            unknown_count += 1
    
    # 记录钓鱼结果到JSON
    record_fishing_result(reel_result)
    
    # 打印本次结果
    if reel_result == 'airforce':
        cprint("这次钓鱼空军", C_WARN)
    elif reel_result == 'unknown':
        cprint("这次钓到了鱼，但稀有度未知", C_WARN)
    else:
        chinese_rarity = {
            'legendary': '传奇',
            'epic': '史诗',
            'rare': '稀有',
            'extraordinary': '非凡',
            'standard': '标准'
        }
        zh_name = chinese_rarity[reel_result]
        fg_color = rarity_fg_colors[reel_result]
        cprint("这次钓到了", C_DEBUG, end='')
        cprint(zh_name, fg_color, end='')
        cprint("鱼", C_DEBUG)
    
    # 打印本次统计（基于内存计数器）
    total_fish = legendary_count + epic_count + rare_count + extraordinary_count + standard_count + unknown_count
    total_attempts = total_fish + airforce_count
    airforce_rate = (airforce_count / total_attempts * 100) if total_attempts > 0 else 0
    cprint("本次运行统计: ", C_DEBUG, end='')
    cprint(f"传奇{legendary_count}条", rarity_fg_colors['legendary'], end=', ')
    cprint(f"史诗{epic_count}条", rarity_fg_colors['epic'], end=', ')
    cprint(f"稀有{rare_count}条", rarity_fg_colors['rare'], end=', ')
    cprint(f"非凡{extraordinary_count}条", rarity_fg_colors['extraordinary'], end=', ')
    cprint(f"标准{standard_count}条", rarity_fg_colors['standard'], end=', ')
    cprint(f"未知{unknown_count}条", C_GRAY, end=', ')
    cprint(f"空军{airforce_count}次, 空军率{airforce_rate:.1f}%", C_GRAY)
    
    cprint("="*20 + " 本轮钓鱼结束 " + "="*20, C_INFO)
    # 使用可中断的等待
    elapsed = 0
    while elapsed < 2 and is_running:
        time.sleep(0.01)
        elapsed += 0.01

# --- 主程序入口 ---
if __name__ == "__main__":
    cprint("="*50, C_INFO)
    cprint("猛兽派对 - 自动钓鱼脚本", C_INFO)
    cprint("作者: Fox, 由SammFang改版", C_INFO)
    cprint("="*50, C_INFO)
    cprint("\n请将游戏窗口置于前台，脚本开始后不要移动窗口。", C_WARN)
    cprint(f"按 Ctrl+L 可以暂停或恢复脚本。", C_WARN)
    cprint(f"按 'q' 可以紧急终止脚本。", C_WARN)
    
    for i in range(3, 0, -1):
        cprint(f"{i} 秒后开始...", C_INFO)
        time.sleep(1)

    try:
        while True:
            if not is_running:
                cprint("程序已停止，等待恢复...", C_CONTROL)
                while not is_running:
                    time.sleep(0.5)
                cprint("程序恢复，开始新一轮", C_CONTROL)
            
            auto_fish_once()
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        cprint("\n检测到 Ctrl+C，程序退出。", C_CONTROL)
    except Exception as e:
        cprint(f"\n发生未处理的异常: {e}", C_ERROR)
    finally:
        cprint("脚本已停止。", C_INFO)

