# windows_sendinput_auto_fish.py
# Windows-only: 使用 SendInput 注入鼠标事件

import ctypes
import time
import sys
import random
import pygetwindow as gw



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

is_running = True  # 控制主循环是否运行

# 鱼计数器
legendary_count = 0
epic_count = 0
rare_count = 0
extraordinary_count = 0
standard_count = 0
airforce_count = 0

# 稀有度前景颜色映射 (最接近 RGB 的 16 色)
rarity_fg_colors = {
    'legendary': FOREGROUND_YELLOW,      # 接近 (255,201,53)
    'epic': FOREGROUND_MAGENTA,          # 接近 (171,99,255)
    'rare': FOREGROUND_CYAN,             # 接近 (106,175,246)，使用青色
    'extraordinary': FOREGROUND_GREEN,   # 接近 (142,201,85)
    'standard': FOREGROUND_WHITE         # 接近 (183,186,193)，使用白色
}

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

# 定义像素检测的相对坐标比例
# 格式: (x_ratio, y_ratio, description)
COORDS_CONFIG = {
    "orange_zone": (0.5874, 0.9278, "张力表盘橙色区域"),
    "green_zone": (0.5444, 0.9067, "张力表盘绿色边界"),
    "bite_mark": (0.5083, 0.2811, "咬钩感叹号"),
}

# 计算绝对坐标
def get_abs_coord(ratio_x, ratio_y):
    return int(ratio_x * window_width + window_left), int(ratio_y * window_height + window_top)

CHECK_X, CHECK_Y = get_abs_coord(COORDS_CONFIG["orange_zone"][0], COORDS_CONFIG["orange_zone"][1])
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
            CHECK_X, CHECK_Y = get_abs_coord(COORDS_CONFIG["orange_zone"][0], COORDS_CONFIG["orange_zone"][1])
            CHECK_X2, CHECK_Y2 = get_abs_coord(COORDS_CONFIG["green_zone"][0], COORDS_CONFIG["green_zone"][1])
            CHECK_X3, CHECK_Y3 = get_abs_coord(COORDS_CONFIG["bite_mark"][0], COORDS_CONFIG["bite_mark"][1])
            
            cprint(f"已更新坐标: 橙色区({CHECK_X}, {CHECK_Y}), 绿色边界({CHECK_X2}, {CHECK_Y2}), 感叹号({CHECK_X3}, {CHECK_Y3})", C_DEBUG)
        
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
def detect_fish_rarity(region, threshold=0.1, tolerance=5):
    """检测指定区域内的鱼稀有度，通过像素颜色匹配
    Args:
        region: (top, left, bottom, right) 区域坐标
        threshold: 匹配像素占比阈值
        tolerance: 颜色容差 (±5)
    Returns:
        str: 'legendary', 'epic', 'rare', 'extraordinary', 'standard', 或 'airforce'
    """
    # 定义稀有度颜色基准 (R, G, B)
    rarity_colors = {
        'legendary': (255, 201, 53),    # 传奇鱼
        'epic': (171, 99, 255),         # 史诗鱼
        'rare': (106, 175, 246),        # 稀有鱼
        'extraordinary': (142, 201, 85),# 非凡鱼
        'standard': (183, 186, 193)     # 标准鱼
    }
    
    top, left, bottom, right = region
    total_pixels = (bottom - top) * (right - left)
    if total_pixels <= 0:
        return 'airforce'
    
    # 记录每个稀有度的匹配像素数
    match_counts = {rarity: 0 for rarity in rarity_colors}
    sample_count = 0
    step = 10  # 步长为10的顺序采样
    
    # 计算预计采样点数
    num_y_steps = ((bottom - top - 1) // step) + 1
    num_x_steps = ((right - left - 1) // step) + 1
    expected_samples = num_y_steps * num_x_steps
    
    cprint(f"开始在区域 {region} 内步长{step}顺序采样 (预计 {expected_samples} 个点) 检测鱼稀有度...", C_DEBUG)
    
    for y in range(top, bottom, step):
        for x in range(left, right, step):
            try:
                color = get_pointer_color(x, y)
                # 检查每个稀有度
                for rarity, target_color in rarity_colors.items():
                    if color_in_range(target_color, color, tolerance):
                        match_counts[rarity] += 1
                        break  # 一个像素只匹配一个稀有度（优先第一个匹配）
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
        if ratio > max_ratio and ratio >= threshold:
            max_ratio = ratio
            best_rarity = rarity
    
    if best_rarity == 'airforce':
        cprint(f"未检测到足够匹配像素，判定为空军 (阈值 {threshold})", C_DEBUG)
    else:
        cprint(f"检测到 {best_rarity} 鱼 (比例 {max_ratio:.2%})", C_DEBUG)
    
    return best_rarity

# 读取模板（保持透明通道）
template = cv2.imread("exclamation_mark.png", cv2.IMREAD_UNCHANGED)
template_bgr = template[:, :, :3]        # RGB部分
template_alpha = template[:, :, 3]       # alpha通道作为mask
w, h = template_bgr.shape[1], template_bgr.shape[0]

def exclamation_check(screenshot_region=None):
    """
    执行模板匹配并返回最大匹配度值。
    """
    # 截屏
    if screenshot_region:
        left, top, width, height = screenshot_region
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
    else:
        screenshot = pyautogui.screenshot()
    
    # 转为BGR
    img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # 模板匹配（使用alpha通道作为mask）
    res = cv2.matchTemplate(img_bgr, template_bgr, cv2.TM_CCOEFF_NORMED, mask=template_alpha)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val

# --- 核心钓鱼逻辑 ---
def bite_check():
    """检测鱼是否咬钩（寻找黄色感叹号）"""
    cprint(f"等待鱼咬钩...", C_STATUS)
    
    match_count = 0
    threshold = 0.6  # 匹配阈值
    timeout = 40
    start_time = time.time()

    while is_running:
        # 检查窗口位置
        check_window_position()
        
        if not is_running:
            cprint("咬钩检测被中断", C_CONTROL)
            return False
        
        # 降低检查频率 (原 sleep_time * 4)
        sleep_time = random.randint(4, 20) / 100
        time.sleep(sleep_time)
        
        match_count += 1
        
        # 执行模板匹配
        match_val = exclamation_check(screenshot_region=(CHECK_X3-100, CHECK_Y3-50, 200, 300))
        
        is_success = match_val >= threshold
        
        # 每10次打印一次，或者成功时立即打印
        if is_success or match_count % 10 == 0:
            cprint(f"匹配次数: {match_count}, 匹配度: {match_val:.4f}, 阈值: {threshold}", C_DEBUG)

        if is_success:
            cprint("有鱼咬钩！", C_SUCCESS)
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
            
            # 等待0.4秒后进行单次检测
            time.sleep(0.4)

            center_x = window_left + window_width // 2
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
            
            cprint(f"检测鱼稀有度，区域: {region}", C_DEBUG)
            rarity = detect_fish_rarity(region)
            
            if rarity != 'airforce':
                cprint(f"钓鱼成功！稀有度: {rarity}", C_SUCCESS)
                return rarity
            else:
                cprint("似乎空军了……", C_WARN)
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
        # 条件3：张力过高，需要松手
        if times >= 30 and color_changed(base_color_green, color_bound, tolerance=40):
            try:
                # 松手前再次确认张力表盘是否存在
                color_exist_before = get_pointer_color(CHECK_X, CHECK_Y)
                if color_changed(base_color_orange, color_exist_before, tolerance=100):
                    cprint(f"松手前检测到张力表盘消失，准备验证钓鱼结果...", C_STATUS)
                    left_up()
                    
                    # 等待0.4秒后进行单次检测
                    time.sleep(0.4)

                    center_x = window_left + window_width // 2
                    region_top = window_top + 75
                    region_bottom = window_top + 215
                    region_left = center_x - 350
                    region_right = center_x + 350
                    
                    # 确保区域在窗口范围内
                    region_top = max(window_top, region_top)
                    region_bottom = min(window_top + window_height, region_bottom)
                    region_left = max(window_left, region_left)
                    region_right = min(window_left + window_width, region_right)
                    
                    region = (region_top, region_left, region_bottom, region_right)
                    
                    cprint(f"检测鱼稀有度 (松手后)，区域: {region}", C_DEBUG)
                    rarity = detect_fish_rarity(region)

                    if rarity != 'airforce':
                        cprint(f"钓鱼成功！稀有度: {rarity}", C_SUCCESS)
                        return rarity
                    else:
                        cprint("似乎空军了……", C_WARN)
                        return 'airforce'
            except Exception as e:
                cprint(f"松手前检查像素失败: {e}", C_WARN)
            
            cprint(f"张力过高，暂时松手。边界颜色: {color_bound}", C_STATUS)
            left_up()
            sleep_time = random.uniform(2.0, 3.0)
            time.sleep(sleep_time)
            cprint("继续收杆", C_STATUS)
def auto_fish_once():
    """执行一轮完整的自动钓鱼流程"""
    global legendary_count, epic_count, rare_count, extraordinary_count, standard_count, airforce_count
    cprint("\n" + "="*20 + " 开始新一轮钓鱼 " + "="*20, C_INFO)
    
    # 1. 抛竿
    cprint("抛竿中...", C_STATUS)
    left_down()
    sleep_time = random.uniform(3.0, 4.0)
    time.sleep(sleep_time)
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
    time.sleep(wait_time)

    # 5. 收杆与张力控制
    reel_result = reel()
    
    # 处理结果
    if reel_result == 'airforce':
        airforce_count += 1
    else:
        # 6. 收鱼
        cprint("收鱼中...", C_STATUS)
        sleep_time = random.uniform(1.5, 2.5)
        time.sleep(sleep_time)
        time.sleep(0.5)
        left_down()
        time.sleep(0.2)
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
    
    # 打印本次结果
    if reel_result == 'airforce':
        cprint("这次钓鱼空军", C_WARN)
    else:
        chinese_rarity = {
            'legendary': '传奇鱼',
            'epic': '史诗鱼',
            'rare': '稀有鱼',
            'extraordinary': '非凡鱼',
            'standard': '标准鱼'
        }
        zh_name = chinese_rarity[reel_result]
        fg_color = rarity_fg_colors[reel_result]
        cprint("这次钓到了", C_DEBUG, end='')
        cprint(zh_name, fg_color, end='')
        cprint("鱼", C_DEBUG)
    
    # 打印累计统计
    total_fish = legendary_count + epic_count + rare_count + extraordinary_count + standard_count
    total_attempts = total_fish + airforce_count
    airforce_rate = (airforce_count / total_attempts * 100) if total_attempts > 0 else 0
    cprint("累计统计: ", C_DEBUG, end='')
    cprint(f"传奇{legendary_count}条", rarity_fg_colors['legendary'], end=', ')
    cprint(f"史诗{epic_count}条", rarity_fg_colors['epic'], end=', ')
    cprint(f"稀有{rare_count}条", rarity_fg_colors['rare'], end=', ')
    cprint(f"非凡{extraordinary_count}条", rarity_fg_colors['extraordinary'], end=', ')
    cprint(f"标准{standard_count}条", rarity_fg_colors['standard'], end=', ')
    cprint(f"空军{airforce_count}次, 空军率{airforce_rate:.1f}%", C_DEBUG)
    
    cprint("="*20 + " 本轮钓鱼结束 " + "="*20, C_INFO)
    time.sleep(2)  # 每轮结束后固定等待

# --- 主程序入口 ---
if __name__ == "__main__":
    cprint("="*50, C_INFO)
    cprint("猛兽派对 - 自动钓鱼脚本", C_INFO)
    cprint("作者: Fox, 该版本有SammFang的改动", C_INFO)
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

