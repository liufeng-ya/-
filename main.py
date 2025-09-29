# windows_sendinput_auto_fish.py
# Windows-only: 使用 SendInput 注入鼠标事件

import ctypes
import time
import sys
import random
import pygetwindow as gw


# 一些可能需要安装的东西
try:
    import pyautogui
except Exception:
    print("请安装: pip install pyautogui")
    raise

USE_KEYBOARD = True
try:
    import keyboard
except Exception:
    USE_KEYBOARD = False
    print("请安装: pip install keyboard")
    raise

try:
    import win32gui
except Exception:
    print("请安装: pip install win32gui")
    raise

# -------------------------
# 读取窗口大小/分辨率的相关定义
# -------------------------

# 查找窗口
window = gw.getWindowsWithTitle("猛兽派对")[0]
hwnd = win32gui.FindWindow(None, "猛兽派对")

# 获取客户区大小
rect = win32gui.GetClientRect(hwnd)
window_width = (rect[2] - rect[0])
window_height = (rect[3] - rect[1])
window_left = window.left
window_top = window.top

# -------------------------
# SendInput 相关定义
# -------------------------
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

# SendInput 装饰器
SendInput = ctypes.windll.user32.SendInput

# -------------------------
# 封装低级鼠标函数
# -------------------------
def _send_mouse_event(flags, dx=0, dy=0, data=0):
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
    left_down()
    time.sleep(0.05)  # 极短的按下间隔
    left_up()

# 可选：移动鼠标到屏幕坐标（使用绝对坐标需要归一化到 0..65535）
def move_mouse_abs(x, y):
    # 获取屏幕尺寸
    sx = ctypes.windll.user32.GetSystemMetrics(0)
    sy = ctypes.windll.user32.GetSystemMetrics(1)
    # 归一化到 0..65535
    nx = int(x * 65535 / (sx - 1))
    ny = int(y * 65535 / (sy - 1))
    _send_mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, nx, ny)

# -------------------------
# 钓鱼逻辑（集成像素检测）
# -------------------------

# 一些检查坐标
CHECK_X, CHECK_Y = (0.5874 * window_width) + window_left, (0.9278 * window_height) + window_top # 橙色区域，用于检测张力表盘是否存在
CHECK_X2, CHECK_Y2 = (0.5444 * window_width) + window_left, (0.9067 * window_height) + window_top  # 绿色区域，用于检测是否快到张力上限
CHECK_X3, CHECK_Y3 = (0.5083 * window_width) + window_left, (0.2811 * window_height) + window_top  # 感叹号的坐标，用于检测是否有鱼咬钩

CHECK_X, CHECK_Y = int(CHECK_X), int(CHECK_Y)
CHECK_X2, CHECK_Y2 = int(CHECK_X2), int(CHECK_Y2)
CHECK_X3, CHECK_Y3 = int(CHECK_X3), int(CHECK_Y3)

def get_pointer_color(x, y):
    return pyautogui.pixel(x, y)

def color_changed(base_color, new_color, tolerance=12):
    br, bg, bb = base_color
    nr, ng, nb = new_color
    return (abs(br - nr) > tolerance) or (abs(bg - ng) > tolerance) or (abs(bb - nb) > tolerance)

def color_in_range(base_color, new_color, tolerance=12):
    br, bg, bb = base_color
    nr, ng, nb = new_color
    return (abs(br - nr) <= tolerance) and (abs(bg - ng) <= tolerance) and (abs(bb - nb) <= tolerance)

def bite_check():
    base_color_yellow = (255, 226, 100) #感叹号的颜色
    t = 0
    while True:
        sleep_time = random.randint(1,5) / 100
        time.sleep(sleep_time)
        t += 1
        for h in range (-10, 11, 10):
            for i in range(0, 421, 20): #范围检测，因为感叹号位置会随着视角变化而变化
                color_mark = get_pointer_color(CHECK_X3 + h, i + 200)
                if color_in_range(base_color_yellow, color_mark, tolerance=20):
                    print("有鱼咬钩！")
                    return True
        if t >= 45:
            return False

def reel():
    # 改用底层注入的 left_down/left_up

    start_time = time.time()
    base_color_green = (127, 181, 77) #这是张力表盘绿色区的颜色
    base_color_orange = (255, 195, 83) #这是张力表盘橙色区的颜色
    times = 0

    while True:
        # 支持按 q 退出
        if USE_KEYBOARD and keyboard.is_pressed('q'):
            left_up()
            print("检测到 q，退出并终止脚本")
            sys.exit(0)

        try:
            color_exist = get_pointer_color(CHECK_X, CHECK_Y)
            color_bound = get_pointer_color(CHECK_X2, CHECK_Y2)
        except Exception as e:
            print("读取像素失败:", e)
            time.sleep(0.05)
            continue

        times += 1
        time.sleep(0.1)  # 等待回落

         # 超时 30s / 完成钓鱼 强制结束
        if time.time() - start_time > 30 or (color_changed(base_color_orange, color_exist, tolerance=100) and times>=30):
            print("结束本次钓鱼")
            left_up()
            break

        left_down()

        if times % 15 == 0:
            print("持续收杆中")
            
        if color_changed(base_color_green, color_bound, tolerance=40) and times>=30:
            print("即将到达张力上限，暂时松手")
            left_up()
            sleep_time = random.randint(20,30) / 10 # random.randint(50,60) / 10
            time.sleep(sleep_time)
            

        

def auto_fish_once():

    # 抛竿（长按）
    left_down()
    sleep_time = random.randint(30,40) / 10
    time.sleep(sleep_time)
    left_up()
    print("抛竿完成")

    # 等待鱼咬钩
    status = bite_check()
    if not status:
        print("长时间未检测到感叹号，默认为空军，强制结束这一轮")
        return

    # 收杆
    reel()

    # 收鱼
    sleep_time = random.randint(15,25) / 10
    time.sleep(sleep_time)
    left_down()
    time.sleep(0.2)
    left_up()
    print("收鱼完成")
    time.sleep(1)

# -------------------------
# 主循环
# -------------------------
if __name__ == "__main__":
    print("请将窗口切回至猛兽派对，运行此脚本后不要移动猛兽派对窗口，不然需要重新运行此脚本")
    time.sleep(2)
    try:
        while True:
            auto_fish_once()
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("KeyboardInterrupt，退出。")
