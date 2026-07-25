import pyautogui
import pygetwindow as gw
import win32gui
import win32con
import win32api
import time

WINDOW_TITLE = "移动办公"

def focus_window(title):
    try:
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            print(f"❌ 未找到窗口: {title}")
            return False
        win = windows[0]
        hwnd = win._hWnd
        win32gui.SetForegroundWindow(hwnd)
        win.maximize()
        return True
    except Exception as e:
        print(f"⚠️ 聚焦失败: {e}")
        return False

def send_wheel_message(hwnd, delta):
    """
    直接向窗口发送 WM_MOUSEWHEEL 消息。
    delta > 0 为向上滚动, delta < 0 为向下滚动。
    """
    # 根据 Windows API，WM_MOUSEWHEEL 的 wParam 包含滚轮量
    # WHEEL_DELTA = 120. 这里我们发送一个标准单位。
    # lParam 必须包含当前鼠标坐标
    cursor_pos = win32api.GetCursorPos()
    lparam = (cursor_pos[0] & 0xFFFF) | ((cursor_pos[1] & 0xFFFF) << 16)
    wparam = (delta // 120) << 16

    win32gui.PostMessage(hwnd, win32con.WM_MOUSEWHEEL, wparam, lparam)

def main():
    if not focus_window(WINDOW_TITLE):
        return

    windows = gw.getWindowsWithTitle(WINDOW_TITLE)
    hwnd = windows[0]._hWnd
    win = windows[0]
    cx = win.left + win.width // 2
    cy = win.top + win.height // 2

    # 将鼠标移至窗口中心，确保发送消息时的坐标在窗内
    pyautogui.moveTo(cx, cy)
    time.sleep(1)

    print("\n--- 🚀 [API MODE] 开始测试底层消息注入 ---")

    # 1. 纵向滚动 (Y-Axis) - 使用 Win32 API 直接发指令
    print("\n[Step 1] 发送 WM_MOUSEWHEEL 消息: 向下 $\rightarrow$ 向上")
    for i in range(5):
        send_wheel_message(hwnd, -120) # 发送一个单位的向下滚动
        print(f"  🔽 API-Scroll Down {i+1}/5")
        time.sleep(0.2)

    time.sleep(1)

    for i in range(5):
        send_wheel_message(hwnd, 120) # 发送一个单位的向上滚动
        print(f"  🔼 API-Scroll Up {i+1}/5")
        time.sleep(0.2)

    # 2. 横向滑动 (X-Axis) - 使用 pydirectinput 或 pyautogui 的慢速拖拽
    # 因为横向滑动通常不是通过单一消息完成，而是需要一个完整的【按下->移动->释放】序列
    print("\n[Step 2] 测试底层拖拽: 右 $\rightarrow$ 左")
    pyautogui.moveTo(cx, cy)
    time.sleep(0.5)

    print("  🖱️ 执行慢速精准拖拽 (模拟真实人类)...")
    pyautogui.mouseDown(button='left')
    # 使用更小的步长，缓慢移动
    for _ in range(30):
        pyautogui.moveRel(-10, 0) # 分多次小幅移动
        time.sleep(0.02)
    pyautogui.mouseUp()
    print("  ✅ 右移完成")

    time.sleep(1)

    print("  🖱️ 执行恢复拖拽...")
    pyautogui.mouseDown(button='left')
    for _ in range(30):
        pyautogui.moveRel(10, 0)
        time.sleep(0.02)
    pyautogui.mouseUp()
    print("  ✅ 回滚完成")

    print("\n✨ 所有 API 层级交互测试完毕！")

if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    main()
