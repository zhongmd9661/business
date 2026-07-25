"""Web 服务集成测试脚本"""
import os
import sys
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))

BASE = "http://localhost:8000/api"
PASS = "Test1234!"


def step(label: str):
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")


def safe_json(r: requests.Response) -> dict:
    try:
        return r.json()
    except Exception:
        return {"raw": r.text[:200]}


def main():
    # 0. 健康检查
    step("0. 健康检查")
    r = requests.get(f"{BASE}/health")
    print(f"  Status: {r.status_code}  Body: {safe_json(r)}")

    # 1. 注册普通用户
    step("1. 注册普通用户 testuser")
    r = requests.post(f"{BASE}/auth/register", json={"username": "testuser", "password": PASS})
    print(f"  Status: {r.status_code}  Body: {safe_json(r)}")

    # 2. 注册管理员
    step("2. 注册管理员 admin")
    r = requests.post(f"{BASE}/auth/register", json={"username": "admin", "password": PASS})
    print(f"  Status: {r.status_code}  Body: {safe_json(r)}")
    # 升级为管理员
    from src.web_service.models_db import SessionLocal, User
    db = SessionLocal()
    admin = db.query(User).filter(User.username == "admin").first()
    if admin:
        admin.role = "admin"
        db.commit()
        print("  Admin role upgraded to 'admin'")
    db.close()

    # 3. 登录
    step("3. 登录 testuser")
    r = requests.post(f"{BASE}/auth/login", json={"username": "testuser", "password": PASS})
    user_token = r.json().get("access_token")
    print(f"  Status: {r.status_code}  Token: {user_token[:30] if user_token else 'NONE'}...")
    user_headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}

    step("3b. 登录 admin")
    r = requests.post(f"{BASE}/auth/login", json={"username": "admin", "password": PASS})
    admin_token = r.json().get("access_token")
    print(f"  Status: {r.status_code}  Token: {admin_token[:30] if admin_token else 'NONE'}...")
    admin_headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}

    # 4. 查阅规则
    step("4. 查阅审核规则（普通用户）")
    r = requests.get(f"{BASE}/rules", headers=user_headers)
    rules = safe_json(r)
    if isinstance(rules, list):
        print(f"  Status: {r.status_code}  Rules count: {len(rules)}")
        if rules:
            print(f"  First: {rules[0]['rule_name'][:50]}")
    else:
        print(f"  Status: {r.status_code}  Body: {rules}")

    # 5. 规则分类
    step("5. 规则分类")
    r = requests.get(f"{BASE}/rules/categories", headers=user_headers)
    print(f"  Status: {r.status_code}  Body: {safe_json(r)}")

    # 6. 管理员新增规则
    step("6. 管理员新增规则")
    new_rule = {
        "category": "金额标准",
        "rule_name": "测试规则-人均上限",
        "clause": "测试条款 第一条",
        "level": "高",
        "description": "测试用规则",
        "source_document": "测试文档",
    }
    r = requests.post(f"{BASE}/rules", json=new_rule, headers=admin_headers)
    print(f"  Status: {r.status_code}  Body: {safe_json(r)}")
    rule_id = None
    if r.status_code == 201:
        rule_id = r.json().get("id")

    # 7. 普通用户修改规则 → 403
    step("7. 普通用户修改规则 → 应返回 403")
    if rule_id:
        r = requests.put(f"{BASE}/rules/{rule_id}", json={"level": "低"}, headers=user_headers)
        print(f"  Status: {r.status_code}  Body: {safe_json(r)}")

    # 8. 管理员修改规则
    step("8. 管理员修改规则")
    if rule_id:
        r = requests.put(f"{BASE}/rules/{rule_id}", json={"level": "中"}, headers=admin_headers)
        print(f"  Status: {r.status_code}  Body: {safe_json(r)}")

    # 9. 管理员删除规则
    step("9. 管理员删除规则")
    if rule_id:
        r = requests.delete(f"{BASE}/rules/{rule_id}", headers=admin_headers)
        print(f"  Status: {r.status_code}  Body: {safe_json(r)}")

    # 10. 文件上传
    step("10. 文件上传测试")
    test_file = os.path.join(os.path.dirname(__file__),
                             "00规则制度", "00综合部业务招待费",
                             "业务招待费审查风险点.docx")
    if os.path.exists(test_file):
        with open(test_file, "rb") as f:
            r = requests.post(
                f"{BASE}/tasks/upload",
                files={"files": ("test.docx", f, "application/octet-stream")},
                headers=user_headers,
            )
            print(f"  Upload Status: {r.status_code}  Body: {safe_json(r)}")
            task_id = safe_json(r).get("task_id")

            if task_id:
                print(f"  Waiting for task {task_id} to complete (max 120s)...")
                for i in range(120):
                    time.sleep(2)
                    r = requests.get(f"{BASE}/tasks/{task_id}", headers=user_headers)
                    status = safe_json(r).get("status")
                    print(f"    [{i*2}s] status={status}")
                    if status in ("completed", "failed"):
                        if status == "completed":
                            r2 = requests.get(f"{BASE}/tasks/{task_id}/report", headers=user_headers)
                            report = safe_json(r2)
                            if isinstance(report, str):
                                print(f"  Report: {report[:300]}...")
                            else:
                                print(f"  Report response: {report}")
                        elif status == "failed":
                            print(f"  Error: {safe_json(r).get('error_message', 'unknown')}")
                        break
                else:
                    print("  Task timeout after 120s")
    else:
        print(f"  Test file not found: {test_file}")

    # 11. 同步状态
    step("11. 同步状态查询")
    r = requests.get(f"{BASE}/rules/sync/status", headers=admin_headers)
    print(f"  Status: {r.status_code}  Body: {safe_json(r)}")

    # 12. 同步历史
    step("12. 同步历史")
    r = requests.get(f"{BASE}/rules/sync/history", headers=admin_headers)
    data = safe_json(r)
    if isinstance(data, list):
        print(f"  Status: {r.status_code}  Count: {len(data)}")
    else:
        print(f"  Status: {r.status_code}  Body: {data}")

    # 13. 任务列表
    step("13. 任务列表")
    r = requests.get(f"{BASE}/tasks", headers=user_headers)
    data = safe_json(r)
    if isinstance(data, list):
        print(f"  Tasks count: {len(data)}")
        for t in data[:5]:
            print(f"    {t}")
    else:
        print(f"  Body: {data}")

    step("全部测试完成!")


if __name__ == "__main__":
    main()
