"""
登录状态检测与自动恢复。
在采集流程开始前检测是否已登录，未登录时引导用户通过手机号+验证码完成登录。
"""
import logging
from playwright.sync_api import TimeoutError as PwTimeout

from .config import DEFAULT_PHONE

log = logging.getLogger(__name__)


# QCC 登录模态框选择器
PHONE_INPUT_SELECTOR = ".qccd-input.qcc-login-quick-login-phone"
VERIFY_CODE_INPUT_SELECTOR = ".qccd-input.qcc-login-quick-login-verifyCode"
GET_CODE_BTN_SELECTOR = ".qcc-login-quick-login-count-down .qccd-btn-count-down"
LOGIN_SUBMIT_BTN_SELECTOR = ".qccd-btn.qccd-btn-primary.qccd-btn-lg.qccd-btn-block"
AGREE_CHECKBOX_SELECTOR = ".qcc-login-phone-tip .qccd-checkbox-input"



def handle_kicked_off(page) -> bool:
    """处理"账号已下线"弹窗。返回 True 表示检测到了弹窗。"""
    try:
        kicked = page.locator("text=账号已下线").first
        if kicked.count() > 0 and kicked.is_visible(timeout=3000):
            log.info("检测到账号已下线弹窗")
            # 点击弹窗中的"重新登录"按钮
            try:
                btn = page.locator("text=重新登录").first
                if btn.count() > 0 and btn.is_visible(timeout=2000):
                    btn.click()
                    page.wait_for_timeout(2000)
                    log.info("点击了重新登录按钮")
            except Exception:
                log.debug("重新登录按钮点击失败")
            return True
    except Exception as e:
        log.debug("检测账号下线弹窗异常: %s", e)
    return False

def is_logged_in(page) -> bool:
    """检查是否已登录。"""
    # 先处理"账号已下线"弹窗
    if handle_kicked_off(page):
        return False

    try:
        login_btn = page.locator(".qcc-header-login-btn")
        if login_btn.count() > 0:
            return False
    except Exception:
        pass

    try:
        login_modal = page.locator(".qcc-login")
        if login_modal.count() > 0 and login_modal.first.is_visible(timeout=3000):
            return False
    except Exception:
        pass

    return True


def login_with_sms(page, phone=None) -> bool:
    """
    通过手机号+验证码登录。
    返回登录是否成功。
    """
    if phone is None:
        phone = DEFAULT_PHONE

    if not phone:
        phone = input("请输入手机号: ").strip()

    if not phone:
        log.error("手机号不能为空")
        return False

    print()  
    print("  正在打开登录页面...")
    print()  

    # 点击登录按钮 (如果未弹出登录框)
    try:
        login_btn = page.locator(".qcc-header-login-btn")
        if login_btn.count() > 0:
            login_btn.first.click()
            page.wait_for_timeout(2000)
    except Exception:
        pass

    # 切换到短信/密码登录模式
    log.info("切换到短信登录模式")
    # 方法1: 点击左上角切换图标 (.qcc-login-type-change)
    try:
        switch_btn = page.locator(".qcc-login-type-change").first
        if switch_btn.count() > 0 and switch_btn.first.is_visible(timeout=3000):
            switch_btn.first.click()
            page.wait_for_timeout(2000)
            log.info("点击了切换按钮")
    except Exception:
        pass

    # 方法2: 点击右上角"短信/密码登录"标签
    try:
        sms_tab = page.locator("text=é·æ¶/å¯ç ç»å½").first
        if sms_tab.count() > 0 and sms_tab.first.is_visible(timeout=2000):
            sms_tab.first.click()
            page.wait_for_timeout(2000)
            log.info("点击了短信/密码登录标签")
    except Exception:
        pass

    # 方法3: 点击验证码登录Tab
    try:
        tab = page.locator(".qcc-login-phone-tabs-item").first
        if tab.count() > 0:
            tab.click()
            page.wait_for_timeout(1000)
            log.info("点击了验证码登录Tab")
    except Exception:
        pass

    # 输入手机号
    log.info("输入手机号")
    phone_input = page.locator(PHONE_INPUT_SELECTOR).first
    try:
        phone_input.click(timeout=5000)
        phone_input.fill("")
        phone_input.fill(phone)
    except PwTimeout:
        log.warning("手机号输入框点击超时，尝试直接输入")
        phone_input.fill(phone)

    page.wait_for_timeout(1000)

    # 勾选同意协议
    log.info("勾选同意协议")
    try:
        checkbox = page.locator(AGREE_CHECKBOX_SELECTOR).first
        if checkbox.count() > 0 and checkbox.is_visible(timeout=3000):
            checkbox.click()
            page.wait_for_timeout(500)
    except Exception as e:
        log.debug("勾选协议失败: %s", e)

    # 点击获取验证码
    log.info("点击获取验证码")
    code_btn = page.locator(GET_CODE_BTN_SELECTOR).first
    try:
        if code_btn.count() > 0:
            code_btn.click()
    except PwTimeout:
        log.warning("获取验证码按钮点击超时")

    page.wait_for_timeout(2000)

    # 提示用户输入验证码
    print("请在手机短信中查看验证码，然后输入到终端。")
    verify_code = input("请输入验证码: ").strip()
    if not verify_code:
        log.error("验证码不能为空")
        return False

    # 输入验证码
    log.info("输入验证码")
    verify_input = page.locator(VERIFY_CODE_INPUT_SELECTOR).first
    try:
        verify_input.click(timeout=3000)
        verify_input.fill(verify_code)
    except PwTimeout:
        log.warning("验证码输入框点击超时")

    page.wait_for_timeout(1000)

    # 点击登录按钮
    log.info("点击登录按钮")
    submit_btn = page.locator(LOGIN_SUBMIT_BTN_SELECTOR).first
    try:
        if submit_btn.count() > 0:
            submit_btn.click()
    except PwTimeout:
        log.warning("登录按钮点击超时")

    # 等待登录完成
    log.info("等待登录完成...")
    page.wait_for_timeout(5000)

    # 检查是否登录成功
    if is_logged_in(page):
        log.info("登录成功！")
        print()
        print("  登录成功！")
        print()
        return True
    else:
        log.error("登录失败，请检查手机号和验证码是否正确")
        page.screenshot(path="debug_login_failed.png")
        log.info("已保存调试截图: debug_login_failed.png")
        return False


def check_and_login(page, phone=None) -> bool:
    """
    检查登录状态，未登录则执行验证码登录。
    返回登录是否成功。
    """
    # 先处理"账号已下线"弹窗
    if handle_kicked_off(page):
        log.info("账号被挤下线，需要重新登录")
        pass  # 继续走登录流程

    if is_logged_in(page):
        log.info("已登录，跳过登录检查")
        return True

    log.info("检测到未登录状态，开始验证码登录")
    print()
    print("  [!] QCC 登录已过期，需要重新登录")
    print()

    return login_with_sms(page, phone)