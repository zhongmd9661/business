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

    # 获取窗口中心点作为操作起点
    win = gw.getWindowsWithTitle(WINDOW_TITLE)[0]
    cx = win.left + win.width // 2
    cy = win.top + win.height // 2
    pyautogui.moveTo(cx, cy)
    time.sleep(1)

    print("\n--- 🚀 开始测试物理交互 ---")

    # 1. 测试纵向滚动 (Y轴)
    print("\n[Step 1] 测试纵向滚轮: 向下 $\rightarrow$ 向上")
    for i in range(5):
        pyautogui.scroll(-300) # 负数向下滚动
        print(f"  🔽 滚动下 {i+1}/5")
        time.sleep(0.2)

    time.sleep(1)

    for i in range(5):
        pyautogui.scroll(300) # 正数向上滚动
        print(f"  🔼 滚回上 {i+1}/5")
        time.sleep(0.2)

    # 2. 测试横向拖拽 (X轴)
    print("\n[Step 2] 测试横向滑动: 右 $\rightarrow$ 左")
    # 将鼠标移至中心点准备拖拽
    pyautogui.moveTo(cx, cy)
    time.sleep(0.5)

    print("  🖱️ 正在执行 [按下左键 $\rightarrow$ 向左拖动] (使页面右移)...")
    pyautogui.mouseDown(button='left')
    # 模拟向左拖拽一段距离 (例如 300 像素)
    pyautogui.moveRel(-300, 0, duration=1.5)
    pyautogui.mouseUp()
    print("  ✅ 右移完成")

    time.sleep(1)

    print("  🖱️ 正在执行 [按下左键 $\rightarrow$ 向右拖动] (恢复原位)...")
    pyautogui.mouseDown(button='left')
    pyautogui.moveRel(300, 0, duration=1.5)
    pyautogui.mouseUp()
    print("  ✅ 回滚完成")

    print("\n✨ 所有物理交互测试完毕！")

if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    main()
