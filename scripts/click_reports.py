import pyautogui
import pygetwindow as gw
import win32gui
import win32con
from paddleocr import PaddleOCR
import time

# --- 配置区 ---
WINDOW_TITLE = "移动办公"
# 您想要点击的报表标题关键字列表（可根据实际情况增加）
TARGET_REPORTS = [
    "当月累计折后",
    "月度累计折后",
    "收入结构",
    "累计折扣项明细",
    "计费收入分产品"
]

# 初始化 PaddleOCR (使用本地轻量级模型)
ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)

def focus_window(title):
    """将目标窗口置顶并聚焦"""
    try:
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            print(f"❌ 未找到标题包含 '{title}' 的窗口")
            return False

        window = windows[0]
        # 使用 win32gui 强制置顶，防止被其他窗口遮挡
        hwnd = window._hWnd
        win32gui.SetForegroundWindow(hwnd)
        window.maximize() # 最大化以确保坐标一致性
        print(f"✅ 已聚焦并最大化窗口: {title}")
        return True
    except Exception as e:
        print(f"⚠️ 聚焦窗口失败: {e}")
        return False

def get_text_coordinates(target_text):
    """通过 OCR 获取指定文字在屏幕上的中心坐标"""
    # 截取当前全屏
    screenshot = pyautogui.screenshot()
    img_path = "temp_capture.png"
    screenshot.save(img_path)

    result = ocr.ocr(img_path, cls=True)
    if not result or not result[0]:
        return None

    for line in result[0]:
        text = line[1][0]
        coords = line[0] # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]

        if target_text in text:
            # 计算中心点
            center_x = (coords[0][0] + coords[2][0]) / 2
            center_y = (coords[0][1] + coords[2][1]) / 2
            print(f"📍 找到 '{text}' -> 坐标: ({int(center_x)}, {int(center_y)})")
            return (center_x, center_y)

    return None

def main():
    if not focus_window(WINDOW_TITLE):
        return

    time.sleep(1) # 等待窗口响应

    print("\n🚀 开始尝试点击报表标题...")
    for report_name in TARGET_REPORTS:
        print(f"\n🔍 正在搜索: {report_name}...", end=" ")
        coords = get_text_coordinates(report_name)

        if coords:
            # 移动鼠标并点击
            pyautogui.moveTo(coords[0], coords[1], duration=0.5)
            pyautogui.click()
            print("👉 [CLICKED]")
            time.sleep(0.5) # 点击间隔，防止过快
        else:
            print("❌ 未找到")

    print("\n✅ 所有指定报表点击尝试完成。")

if __name__ == "__main__":
    # 安全开关：将鼠标移动到屏幕左上角可立即停止 pyautogui 脚本
    pyautogui.FAILSAFE = True
    main()
