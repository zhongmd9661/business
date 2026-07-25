import pydirectinput
import pyautogui
import pygetwindow as gw
import win32gui
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

def main():
    if not focus_window(WINDOW_TITLE):
        return

    # 获取窗口中心点
    win = gw.getWindowsWithTitle(WINDOW_TITLE)[0]
    cx = win.left + win.width // 2
    cy = win.top + win.height // 2

    # pydirectinput 使用绝对坐标，无需 moveTo 如果我们直接在中心点操作
    # 但为了保险，先将鼠标移至中心
    pyautogui.moveTo(cx, cy)
    time.sleep(1)

    print("\n--- 🚀 [HARDWARE MODE] 开始测试底层交互 ---")

    # 1. 纵向滚动 (Y-Axis) - 使用 pydirectinput 发送扫描码
    print("\n[Step 1] 测试底层滚轮: 向下 $\rightarrow$ 向上")
    for i in range(5):
        pydirectinput.scroll(-300) # 直接发送硬件级滚动指令
        print(f"  🔽 Hardware-Scroll Down {i+1}/5")
        time.sleep(0.3)

    time.sleep(1)

    for i in range(5):
        pydirectinput.scroll(300)
        print(f"  🔼 Hardware-Scroll Up {i+1}/5")
        time.sleep(0.3)

    # 2. 横向滑动 (X-Axis) - 使用 pydirectinput 的按下/移动/释放
    print("\n[Step 2] 测试底层拖拽: 右 $\rightarrow$ 左")
    pyautogui.moveTo(cx, cy) # 回到中心点
    time.sleep(0.5)

    print("  🖱️ 执行硬件级 [MouseDown $\rightarrow$ MoveRel $\rightarrow$ MouseUp]...")
    pydirectinput.mouseDown(button='left')
    # 缓慢向左拖拽以模拟真实人类操作，防止被过滤
    pydirectinput.moveRel(-300, 0, relative=True)
    pydirectinput.mouseUp()
    print("  ✅ 硬件级右移完成")

    time.sleep(1)

    print("  🖱️ 执行硬件级 [MouseDown $\rightarrow$ MoveRel $\rightarrow$ MouseUp] (恢复)...")
    pydirectinput.mouseDown(button='left')
    pydirectinput.moveRel(300, 0, relative=True)
    pydirectinput.mouseUp()
    print("  ✅ 硬件级回滚完成")

    print("\n✨ 所有底层硬件交互测试完毕！")

if __name__ == "__main__":
    # pydirectinput 不使用 pyautogui 的 FAILSAFE，但我们可以手动添加
    main()
