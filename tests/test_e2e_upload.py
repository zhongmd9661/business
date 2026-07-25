"""端到端测试 — 使用真实测试案例材料验证文件上传 → OCR → 审核 → 报告下载全流程"""
import os
import sys
import time
from pathlib import Path

import requests

# 确保 src 可导入
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://localhost:8006"


def test_e2e_flow():
    """完整的端到端测试流程"""
    print("=" * 60)
    print("端到端测试：文件上传 → OCR → 审核 → 报告下载")
    print("=" * 60)

    # 1. 注册新用户（使用时间戳确保用户名唯一）
    print("\n[1/6] 注册新用户...")
    import time
    unique_suffix = int(time.time() * 1000) % 100000
    test_username = f"e2e_test_{unique_suffix}"
    resp = requests.post(f"{BASE_URL}/api/auth/register", json={
        "username": test_username,
        "password": "test123456",
    })
    assert resp.status_code == 200, f"注册失败: {resp.text}"
    print(f"  ✓ 注册成功，用户角色: {resp.json()['role']}")

    # 2. 登录获取 Token
    print("\n[2/6] 登录获取 Token...")
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": test_username,
        "password": "test123456",
    })
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  ✓ 登录成功，Token 前缀: {token[:20]}...")

    # 3. 上传测试案例文件
    print("\n[3/6] 上传测试案例文件...")
    test_case_dir = project_root / "01业务招待费材料案例" / "案例3"
    files_to_upload = []
    for fpath in sorted(test_case_dir.glob("*")):
        if fpath.is_file():
            files_to_upload.append(fpath)
    print(f"  共上传 {len(files_to_upload)} 个文件: {[f.name for f in files_to_upload]}")

    # 读取所有文件内容，避免文件句柄关闭问题
    file_data = []
    for fpath in files_to_upload:
        content = fpath.read_bytes()
        file_data.append(("files", (fpath.name, content, "application/octet-stream")))

    resp = requests.post(f"{BASE_URL}/api/tasks/upload", files=file_data, headers=headers)
    assert resp.status_code == 200, f"上传失败: {resp.text}"
    task_id = resp.json()["task_id"]
    print(f"  ✓ 上传成功，任务 ID: {task_id}")

    # 4. 等待任务完成（轮询状态）
    print("\n[4/6] 等待 OCR 识别与审核完成...")
    max_wait = 600  # 最多等待 10 分钟
    start_time = time.time()
    status_history = []

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            print(f"  ⚠ 超时 {max_wait} 秒，任务未完成")
            break

        resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
        assert resp.status_code == 200, f"查询任务失败: {resp.text}"
        task = resp.json()
        current_status = task["status"]
        status_history.append((time.strftime("%H:%M:%S"), current_status))
        print(f"  [{time.strftime('%H:%M:%S')}] 状态: {current_status} (已等待 {int(elapsed)}s)")

        if current_status in ("completed", "failed"):
            break

        time.sleep(10)  # 每 10 秒轮询一次

    # 打印状态变更历史
    print("\n  状态变更历史:")
    for ts, status in status_history:
        print(f"    {ts}: {status}")

    assert task["status"] == "completed", f"任务失败: {task.get('error_message', '未知错误')}"
    print(f"  ✓ 任务完成！")

    # 5. 下载审核报告
    print("\n[5/6] 下载审核报告...")
    resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}/report", headers=headers)
    assert resp.status_code == 200, f"下载报告失败: {resp.text}"
    report = resp.text
    print(f"  ✓ 报告长度: {len(report)} 字符")
    print(f"  报告预览 (前 500 字符):")
    print(f"  {'-' * 40}")
    print(f"  {report[:500]}")
    print(f"  {'-' * 40}")

    # 6. 查看字段提取结果
    print("\n[6/6] 查看字段提取结果...")
    resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}/fields", headers=headers)
    assert resp.status_code == 200, f"获取字段失败: {resp.text}"
    fields = resp.json()
    print(f"  ✓ 提取到 {len(fields)} 个文件的字段数据")
    for field in fields:
        print(f"    - {field['filename']}: {len(field['content'])} 字符")

    print("\n" + "=" * 60)
    print("端到端测试完成！")
    print("=" * 60)

    return task_id


if __name__ == "__main__":
    test_e2e_flow()
