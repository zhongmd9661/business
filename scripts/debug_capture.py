import pyautogui
import pygetwindow as gw
import time

WINDOW_TITLE = "移动办公"

def test():
    print("🔍 [DIAGNOSTIC] 正在检查窗口...")
    try:
        windows = gw.getWindowsWithTitle(WINDOW_TITLE)
        if not windows:
            print(f"❌ 错误：未找到标题包含 '{WINDOW_TITLE}' 的窗口")
            return

        win = windows[0]
        print(f"✅ 找到窗口: {win.title}")
        print(f"📍 窗口位置: ({win.left}, {win.top}) | 尺寸: {win.width}x{win.height}")

        # 测试：将鼠标移动到窗口中心
        cx = win.left + win.width // 2
        cy = win.top + win.height // 2
        print(f"🖱️ 尝试将鼠标移动到窗口中心: ({cx}, {cy})")
        pyautogui.moveTo(cx, cy, duration=1)
        print("✨ 成功！基础自动化链路 (PyAutoGUI + PyGetWindow) 正常工作。")

    except Exception as e:
        print(f"⚠️ 发生异常: {e}")

if __name__ == "__main__":
    # 安全开关：鼠标移至左上角停止
    pyautogui.FAILSAFE = True
    test()
