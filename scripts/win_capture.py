"""Win11 自动化报表截取工具 v3.0 - 诊断增强版
功能：增加预检流程，确保在启动采集前鼠标能准确、可见地定位到目标窗口。
"""

import os
import time
import pathlib
from typing import Tuple, List
import pyautogui
import pygetwindow as gw
from PIL import Image, ImageChops

# ================= 配置区域 =================
CONFIG = {
    "WINDOW_TITLE": "移动办公",
    "OVERLAP_RATIO": 0.3,
    "SETTLE_TIME": 0.6,
    "MAX_Y_PAGES": 50,
    "MAX_X_STEPS": 20,
    "INPUT_DIR": "data/input/capture_batch",
}

def get_target_window():
    """定位、还原并激活目标窗口，并进行可视化验证"""
    try:
        wins = gw.getWindowsWithTitle(CONFIG["WINDOW_TITLE"])
        if not wins:
            print(f"❌ [错误] 未找到标题包含 '{CONFIG['WINDOW_TITLE']}' 的窗口。")
            return None

        win = wins[0]
        if win.isMinimized:
            win.restore()

        try:
            win.activate()
        except Exception as e:
            print(f"⚠️ [警告] 无法激活窗口 ({e})。这通常意味着您需要【以管理员身份运行终端】！")

        time.sleep(1.0)
        return win
    except Exception as e:
        print(f"❌ [错误] 定位窗口过程中发生异常: {e}")
        return None

def visual_preflight_check(win):
    """【可视化预检】将鼠标移动到窗口四个角，让用户确认定位准确"""
    print("\n--- 🚀 开始可视化预检 (Pre-flight Check) ---")
    coords = [
        ("左上角", win.left, win.top),
        ("右上角", win.right, win.top),
        ("右下角", win.right, win.bottom),
        ("左下角", win.left, win.bottom)
    ]
    for name, x, y in coords:
        print(f"正在验证 {name}... 坐标 ({x}, {y})")
        pyautogui.moveTo(x, y, duration=0.5) # 可见移动
        time.sleep(0.2)

    print("✅ 可视化预检完成。如果上述鼠标移动正确，现在将开始正式采集。")
    print("--------------------------------------------\n")

def capture_screen(roi):
    return pyautogui.screenshot(region=(roi['x'], roi['y'], roi['width'], roi['height']))

def is_at_end(img1: Image.Image, img2: Image.Image) -> bool:
    if img1.size != img2.size: return False
    diff = ImageChops.difference(img1, img2)
    return diff.getbbox() is None

def capture_vision_matrix(win):
    # ROI 定义：尽量覆盖全窗，预留极小边距
    roi = {
        "x": win.left + 5,
        "y": win.top + 40,
        "width": win.width - 10,
        "height": win.height - 80
    }
    output_path = pathlib.Path(CONFIG["INPUT_DIR"])
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"🎯 目标 ROI: x={roi['x']}, y={roi['y']}, w={roi['width']}, h={roi['height']}")

    curr_y_idx = 0
    last_img_y = None

    while curr_y_idx < CONFIG["MAX_Y_PAGES"]:
        print(f"Scanning Row {curr_y_idx}...", end="\r")
        curr_x_idx = 0
        last_img_x = None

        while curr_x_idx < CONFIG["MAX_X_STEPS"]:
            if curr_x_idx > 0:
                start_x = roi['x'] + roi['width'] // 2
                start_y = roi['y'] + roi['height'] // 2
                end_x = start_x + int(roi['width'] * (1 - CONFIG["OVERLAP_RATIO"]))

                pyautogui.moveTo(start_x, start_y)
                pyautogui.mouseDown()
                pyautogui.moveTo(end_x, start_y, duration=0.3)
                pyautogui.mouseUp()
                time.sleep(CONFIG["SETTLE_TIME"])

            img = capture_screen(roi)
            img.save(output_path / f"frag_y{curr_y_idx}_x{curr_x_idx}.jpg")

            if last_img_x is not None and is_at_end(last_img_x, img):
                print(f"\n  [Y:{curr_y_idx}] 触及右边界")
                break

            last_img_x = img
            curr_x_idx += 1

        pyautogui.press('pagedown')
        time.sleep(CONFIG["SETTLE_TIME"])

        current_img = capture_screen(roi)
        if last_img_y is not None and is_at_end(last_img_y, current_img):
            print(f"\n\n✨ 检测到底部边界，采集全部结束。")
            break

        last_img_y = current_img
        curr_y_idx += 1

if __name__ == "__main__":
    target_win = get_target_window()
    if target_win:
        # 在正式采集前，先做可视化验证
        visual_preflight_check(target_win)

        # 用户可以根据预检结果决定是否继续 (这里直接执行)
        capture_vision_matrix(target_win)
    else:
        print("错误: 请启动程序并确保窗口标题正确。")
