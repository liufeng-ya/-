# windows_sendinput_auto_fish.py
# Windows-only: 使用 SendInput 注入鼠标事件

import ctypes
import time
import sys
import random
import traceback
import pygetwindow as gw

import cv2
import numpy as np

# 一些可能需要安装的东西
try:
    import pyautogui
except Exception:
    print("请安装: pip install pyautogui")
    input("\n-----------------")
    sys.exit(1)

USE_KEYBOARD = True
try:
    import keyboard
except Exception:
    USE_KEYBOARD = False
    print("请安装: pip install keyboard")
    input("\n-----------------")
    sys.exit(1)

try:
    import win32gui
except Exception:
    print("请安装: pip install win32gui")
    input("\n-----------------")
    sys.exit(1)

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
CHECK_X, CHECK_Y = (0.5 * window_width) + window_left + 100 + 50 * (window_width // 1800), (0.9478 * window_height) + window_top # 橙色区域，用于检测张力表盘是否存在
CHECK_X2, CHECK_Y2 = (0.5444 * window_width) + window_left, (0.9067 * window_height) + window_top  # 绿色区域，用于检测是否快到张力上限
CHECK_X3, CHECK_Y3 = (0.5083 * window_width) + window_left, (0.2811 * window_height) + window_top  # 感叹号的坐标，用于检测是否有鱼咬钩
CHECK_X4, CHECK_Y4 = (0.4601 * window_width) + window_left, (0.1722 * window_height) +window_top  # 品质检测的左上坐标

CHECK_X, CHECK_Y = int(CHECK_X), int(CHECK_Y)
CHECK_X2, CHECK_Y2 = int(CHECK_X2), int(CHECK_Y2)
CHECK_X3, CHECK_Y3 = int(CHECK_X3), int(CHECK_Y3)
CHECK_X4, CHECK_Y4 = int(CHECK_X4), int(CHECK_Y4)

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

# 读取模板（保持透明通道）
templates = {
    "exclamation": {
        "bgr": cv2.imread("exclamation_mark.png", cv2.IMREAD_UNCHANGED)[:, :, :3],
        "mask": cv2.imread("exclamation_mark.png", cv2.IMREAD_UNCHANGED)[:, :, 3]
    }
}

def template_check(template_name, screenshot_region=None, threshold=0.65):
    if template_name not in templates:
        raise ValueError(f"模板 {template_name} 未定义")

    template_bgr = templates[template_name]["bgr"]
    template_mask = templates[template_name]["mask"]

    # 截屏
    if screenshot_region:
        left, top, width, height = screenshot_region
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
    else:
        screenshot = pyautogui.screenshot()

    img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # 模板匹配
    res = cv2.matchTemplate(img_bgr, template_bgr, cv2.TM_CCOEFF_NORMED, mask=template_mask)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    #print(f"[{template_name}] 匹配阈值：{max_val}")
    return max_val >= threshold

def bite_check(timeout = 40):
    #base_color_yellow = (250, 226, 100)  # 感叹号的颜色
    start_time = time.time() 
    
    while True:
        sleep_time = random.randint(1, 5) / 100
        time.sleep(sleep_time)
        
        #新版通过OpenCV进行相似度比对
        if template_check("exclamation", screenshot_region=(CHECK_X3-100, CHECK_Y3-200, 200, 400)): 
            print("有鱼咬钩！")
            return True
        '''
        #旧版感叹号检测-颜色比对
        for h in range(-10, 11, 10):
            for i in range(0, 200, 20):  # 范围检测
                color_mark = get_pointer_color(CHECK_X3 + h, CHECK_Y3 + i)
                if color_in_range(base_color_yellow, color_mark, tolerance=10):
                    print("有鱼咬钩！")
                    return True
        '''
        # 判断是否超时
        if time.time() - start_time >= timeout:
            return False

def show_check_region(region):
    """
    region: (left, top, width, height)
    """
    left, top, width, height = region
    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)  # 转BGR显示
    cv2.imshow("Check Region", img)
    cv2.waitKey(0)  # 按任意键关闭窗口
    cv2.destroyAllWindows()
    
def reel():
    # 改用底层注入的 left_down/left_up
    base_color_green = (127, 181, 77) #这是张力表盘绿色区的颜色
    base_color_orange = (255, 195, 83) #这是张力表盘橙色区的颜色
    times = 0

    while True:
        try:
            color_exist = get_pointer_color(CHECK_X, CHECK_Y)
            color_bound = get_pointer_color(CHECK_X2, CHECK_Y2)
        except Exception as e:
            print("读取像素失败:", e)
            time.sleep(0.05)
            continue

        times += 1
        time.sleep(random.randint(1,2)/10)  # 等待回落

        #if times == 28:
        #    show_check_point(CHECK_X, CHECK_Y)
         # 完成钓鱼
        if (color_changed(base_color_orange, color_exist, tolerance=100) and times>=30):
            print("结束本次钓鱼")
            left_up()
            break
        
        if times % 10 <=7:
            left_down()
        else:
            left_up()

        if times % 10 == 0:
            print("持续收杆中")
            
        if color_changed(base_color_green, color_bound, tolerance=40) and times>=30:
            print("即将到达张力上限，暂时松手")
            left_up()
            sleep_time = random.randint(20,30) / 10 # random.randint(50,60) / 10
            time.sleep(sleep_time)
            
def quality_check():
    check_color = get_pointer_color(CHECK_X4, CHECK_Y4)
    #region = (CHECK_X4, CHECK_Y4, 50, 50)
    #show_check_region(region)
    quality_color_map = {
        "basic" : (191, 195, 202),
        "uncommon" : (150, 204, 102),
        "rare" : (128, 183, 247),
        "epic" : (180, 122, 255),
        "legancy" : (253, 203, 84)
    }
    if color_in_range(quality_color_map['basic'], check_color, tolerance=28): 
        return "basic"
    elif color_in_range(quality_color_map['uncommon'], check_color, tolerance=28): 
        return "uncommon"
    elif color_in_range(quality_color_map['rare'], check_color, tolerance=28): 
        return "rare"
    elif color_in_range(quality_color_map['epic'], check_color, tolerance=28): 
        return "epic"
    elif color_in_range(quality_color_map['legancy'], check_color, tolerance=28):  
        return "legancy"
    else:
        return "null"
        
def update_record(file_path):
    quality = quality_check()
    # 映射品质对应行
    quality_map = {
        "basic": "标准",
        "uncommon": "非凡",
        "rare": "稀有",
        "epic": "史诗",
        "legancy": "传奇",
        "null": "未知"
    }
    print(f"本次品质: {quality_map[quality]}")
    if quality == 'null':
        return
    # 读取文件
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 遍历每一行，找到对应品质并更新数量
    for i, line in enumerate(lines):
        if line.startswith(quality_map[quality]):
            name, count = line.strip().split(":")
            count = int(count.strip()) + 1
            lines[i] = f"{name}: {count}\n"
            break

    # 写回文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

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

    time.sleep(1)
    # 侦测品质
    update_record(f"Log/{formatted_time}.txt")


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
    print("请将窗口切回至猛兽派对，运行此脚本后不要移动猛兽派对窗口，不然需要重新运行此脚本\n推荐分辨率1440*900")
    time.sleep(2)
    start_fish_time = time.time() 
    # 转为本地时间 struct_time
    local_time = time.localtime(start_fish_time)
    # 格式化为指定格式
    formatted_time = time.strftime("%Y年%m月%d日 %H-%M-%S", local_time)
    prepare_string = ("标准: 0",
                      "非凡: 0",
                      "稀有: 0",
                      "史诗: 0",
                      "传奇: 0")

    try:
        if (window_width > 1920 or window_height > 1080):
            raise ValueError("请将游戏窗口分辨率调整至1920*1080及以下，即长不高于1920且宽不高于1080")

        with open(f"Log/{formatted_time}.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(prepare_string) + "\n")
        while True:
            auto_fish_once()
            time.sleep(0.5)
    except Exception:
        print("似乎出了点问题，报错信息如下：\n")
        traceback.print_exc()
        input("\n请把报错信息截图并回车关闭程序...")
