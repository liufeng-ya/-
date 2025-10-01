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

# 获取标准输出句柄
std_out_handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

def set_color(color):
    """设置控制台文本颜色"""
    ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, color)

def cprint(message, color):
    """带颜色的打印函数"""
    set_color(color)
    print(message)
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

# --- 核心钓鱼逻辑 ---
def bite_check():
    """检测鱼是否咬钩（寻找黄色感叹号）"""
    base_color_yellow = (255, 226, 100)  # 感叹号基准颜色
    
    # 基于窗口高度动态计算扫描范围
    scan_height = int(0.4 * window_height)
    start_y = max(window_top, CHECK_Y3 - scan_height // 2)
    end_y = min(window_top + window_height, CHECK_Y3 + scan_height // 2)
    step_y = 20
    scan_ys = list(range(start_y, end_y + 1, step_y))
    
    cprint(f"等待鱼咬钩...", C_STATUS)
    cprint(f"咬钩检测范围: Y={start_y}-{end_y} (步长{step_y}), X=中心±20 (步长5)", C_DEBUG)

    t = 0
    while is_running:
        if not is_running:
            cprint("咬钩检测被中断", C_CONTROL)
            return False
        
        sleep_time = random.uniform(0.01, 0.05)
        time.sleep(sleep_time)
        t += 1
        
        if t % 15 == 0:
            cprint(f"咬钩检测进行中 (检查第{t}次)...", C_DEBUG)
            
        for h in range(-20, 21, 5):  # 扩大X偏移范围
            for y_pos in scan_ys:
                if not is_running:
                    cprint("咬钩检测被中断", C_CONTROL)
                    return False
                
                x_pos = CHECK_X3 + h
                color_mark = get_pointer_color(x_pos, y_pos)
                
                if color_in_range(base_color_yellow, color_mark, tolerance=25):
                    cprint(f"检测到鱼咬钩！位置:({x_pos}, {y_pos}), 颜色:{color_mark}", C_SUCCESS)
                    return True

        if t >= 60:  # 超时设置
            cprint("咬钩检测超时，未检测到鱼", C_WARN)
            return False
            
    cprint("咬钩检测被中断", C_CONTROL)
    return False

def reel():
    """控制收杆过程，处理张力"""
    start_time = time.time()
    base_color_green = (127, 181, 77)   # 张力表盘绿色区
    base_color_orange = (255, 195, 83)  # 张力表盘橙色区
    
    cprint(f"开始收杆...", C_STATUS)
    cprint(f"目标颜色: 绿色区={base_color_green}, 橙色区={base_color_orange}", C_DEBUG)
    
    times = 0
    try:
        initial_orange = get_pointer_color(CHECK_X, CHECK_Y)
        cprint(f"初始橙色区颜色: {initial_orange}", C_DEBUG)
    except Exception as e:
        cprint(f"读取初始像素失败: {e}", C_WARN)

    while is_running:
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
            cprint(f"检测到张力表盘消失，钓鱼成功！当前颜色: {color_exist}", C_SUCCESS)
            left_up()
            break

        # 条件2：超时
        if time.time() - start_time > 30:
            cprint("收杆超时 (30秒)", C_WARN)
            left_up()
            break

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
                    cprint(f"松手前检测到张力表盘消失，钓鱼成功！颜色: {color_exist_before}", C_SUCCESS)
                    left_up()
                    break
            except Exception as e:
                cprint(f"松手前检查像素失败: {e}", C_WARN)
            
            cprint(f"张力过高，暂时松手。边界颜色: {color_bound}", C_STATUS)
            left_up()
            sleep_time = random.uniform(2.0, 3.0)
            time.sleep(sleep_time)
            cprint("继续收杆", C_STATUS)
            

        

def auto_fish_once():
    """执行一轮完整的自动钓鱼流程"""
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
    reel()

    # 6. 收鱼
    cprint("收鱼中...", C_STATUS)
    sleep_time = random.uniform(1.5, 2.5)
    time.sleep(sleep_time)
    time.sleep(0.5)
    left_down()
    time.sleep(0.2)
    left_up()
    cprint("收鱼完成", C_SUCCESS)
    
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

