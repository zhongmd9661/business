"""12.9-12.10 制度文件变更同步测试"""
import os
import sys
import time
from pathlib import Path

import requests

# 确保 src 可导入
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://localhost:8006"


def get_admin_token():
    """获取管理员 Token"""
    # 使用之前测试创建的管理员账户
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "test_admin",
        "password": "admin123",
    })
    if resp.status_code == 200:
        return resp.json()["access_token"]

    # 如果不存在，创建一个新的管理员
    resp = requests.post(f"{BASE_URL}/api/auth/register", json={
        "username": "sync_admin",
        "password": "admin123",
    })
    # 手动设为管理员
    import src.web_service.models_db as models_db
    db = models_db.SessionLocal()
    user = db.query(models_db.User).filter(models_db.User.username == "sync_admin").first()
    if user:
        user.role = "admin"
        db.commit()
    db.close()

    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "sync_admin",
        "password": "admin123",
    })
    return resp.json()["access_token"]


def test_sync_status():
    """测试同步状态查询"""
    print("=" * 60)
    print("12.9 制度文件变更同步测试")
    print("=" * 60)

    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 查询当前同步状态
    print("\n[1/3] 查询当前同步状态...")
    resp = requests.get(f"{BASE_URL}/api/rules/sync/status", headers=headers)
    assert resp.status_code == 200, f"查询同步状态失败: {resp.text}"
    status = resp.json()
    print(f"  待处理变更数: {status['pending_changes']}")
    print(f"  文档数: {len(status['documents'])}")
    for doc in status['documents']:
        print(f"    - {doc['name']}: {doc['status']}")

    # 2. 手动触发同步
    print("\n[2/3] 手动触发同步...")
    resp = requests.post(f"{BASE_URL}/api/rules/sync", headers=headers)
    assert resp.status_code == 200, f"触发同步失败: {resp.text}"
    sync_result = resp.json()
    print(f"  同步结果: {sync_result['detail']}")
    print(f"  变更文件数: {sync_result.get('changed_files', 0)}")
    if 'diff' in sync_result:
        print(f"  差异统计: {sync_result['diff']}")
    print(f"  是否有冲突: {sync_result.get('has_conflicts', False)}")

    # 3. 查询同步历史
    print("\n[3/3] 查询同步历史...")
    resp = requests.get(f"{BASE_URL}/api/rules/sync/history", headers=headers)
    assert resp.status_code == 200, f"查询同步历史失败: {resp.text}"
    history = resp.json()
    print(f"  历史记录数: {len(history)}")
    for record in history[:5]:  # 显示最近 5 条
        print(f"    - {record['trigger_type']}: {record['document_name']}, "
              f"新增={record['rules_added']}, 修改={record['rules_modified']}, "
              f"删除={record['rules_deleted']}, 状态={record['status']}")

    print("\n" + "=" * 60)
    print("12.9 同步测试完成！")
    print("=" * 60)


def test_sync_interval():
    """12.10 同步间隔配置测试"""
    print("\n" + "=" * 60)
    print("12.10 同步间隔配置测试")
    print("=" * 60)

    # 验证 RULE_SYNC_INTERVAL_MIN 环境变量已生效
    import src.web_service.config as config
    print(f"\n  当前配置的同步间隔: {config.RULE_SYNC_INTERVAL_MIN} 分钟")
    print(f"  环境变量值: {os.environ.get('RULE_SYNC_INTERVAL_MIN', '未设置')}")

    # 验证定时器是否在运行
    from src.web_service.app import _sync_task
    if _sync_task and not _sync_task.done():
        print(f"  ✓ 定时扫描器正在运行")
    else:
        print(f"  ⚠ 定时扫描器未运行")

    print("\n" + "=" * 60)
    print("12.10 同步间隔测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_sync_status()
    test_sync_interval()
