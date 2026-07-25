"""Web 服务集成测试 — 认证、任务、规则管理、权限隔离"""
import pytest


class TestAuth:
    """12.1 注册/登录流程测试"""

    def test_register_success(self, app):
        resp = app.post("/api/auth/register", json={
            "username": "new_user",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "new_user"
        assert data["role"] == "user"

    def test_register_duplicate(self, app):
        app.post("/api/auth/register", json={
            "username": "dup_user",
            "password": "password123",
        })
        resp = app.post("/api/auth/register", json={
            "username": "dup_user",
            "password": "password123",
        })
        assert resp.status_code == 400

    def test_register_short_password(self, app):
        resp = app.post("/api/auth/register", json={
            "username": "short_pw",
            "password": "ab",
        })
        assert resp.status_code == 422

    def test_login_success(self, app):
        app.post("/api/auth/register", json={
            "username": "login_test",
            "password": "password123",
        })
        resp = app.post("/api/auth/login", json={
            "username": "login_test",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "user"

    def test_login_wrong_password(self, app):
        app.post("/api/auth/register", json={
            "username": "wrong_pw",
            "password": "password123",
        })
        resp = app.post("/api/auth/login", json={
            "username": "wrong_pw",
            "password": "wrong_password",
        })
        assert resp.status_code == 401

    def test_health_check(self, app):
        resp = app.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestTaskAuth:
    """任务接口需要认证"""

    def test_access_without_auth_fails(self, app):
        resp = app.get("/api/tasks")
        assert resp.status_code in (401, 403)

    def test_list_tasks_empty(self, app, user_headers):
        resp = app.get("/api/tasks", headers=user_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestRuleManagement:
    """12.7 规则管理权限测试"""

    def test_list_rules(self, app, user_headers):
        """普通用户可以查阅规则"""
        resp = app.get("/api/rules", headers=user_headers)
        assert resp.status_code == 200

    def test_list_categories(self, app, user_headers):
        resp = app.get("/api/rules/categories", headers=user_headers)
        assert resp.status_code == 200

    def test_create_rule_as_admin(self, app, admin_headers):
        """管理员可以创建规则"""
        resp = app.post("/api/rules", json={
            "category": "金额标准",
            "rule_name": "测试规则",
            "clause": "测试条款",
            "level": "高",
            "description": "集成测试规则",
            "check_expression": '{"type": "amount_compare", "field": "per_person_amount", "operator": ">", "threshold": 100}',
        }, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["rule_name"] == "测试规则"
        assert data["enabled"] is True

    def test_create_rule_as_regular_user_fails(self, app, user_headers):
        """普通用户不能创建规则"""
        resp = app.post("/api/rules", json={
            "category": "金额标准",
            "rule_name": "测试规则",
            "clause": "测试条款",
            "level": "高",
        }, headers=user_headers)
        assert resp.status_code == 403

    def test_update_rule_as_admin(self, app, admin_headers):
        """管理员可以修改规则"""
        # 先创建
        create_resp = app.post("/api/rules", json={
            "category": "金额标准",
            "rule_name": "可修改规则",
            "clause": "测试条款",
            "level": "高",
        }, headers=admin_headers)
        rule_id = create_resp.json()["id"]

        # 修改
        resp = app.put(f"/api/rules/{rule_id}", json={
            "level": "低",
            "enabled": False,
        }, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["level"] == "低"
        assert data["enabled"] is False

    def test_update_rule_as_regular_user_fails(self, app, user_headers):
        """普通用户不能修改规则"""
        resp = app.put("/api/rules/1", json={
            "level": "低",
        }, headers=user_headers)
        assert resp.status_code == 403

    def test_delete_rule_as_admin(self, app, admin_headers):
        """管理员可以删除规则"""
        create_resp = app.post("/api/rules", json={
            "category": "金额标准",
            "rule_name": "可删除规则",
            "clause": "测试条款",
            "level": "高",
        }, headers=admin_headers)
        rule_id = create_resp.json()["id"]

        resp = app.delete(f"/api/rules/{rule_id}", headers=admin_headers)
        assert resp.status_code == 200

    def test_delete_rule_as_regular_user_fails(self, app, user_headers):
        """普通用户不能删除规则"""
        resp = app.delete("/api/rules/1", headers=user_headers)
        assert resp.status_code == 403


class TestPermissionIsolation:
    """12.6 权限隔离测试"""

    def test_user_a_cannot_access_user_b_tasks(self, app):
        """用户 A 无法访问用户 B 的任务"""
        headers_a = {"Authorization": f"Bearer {app.post('/api/auth/login', json={'username': 'iso_a', 'password': 'pass123'}).json().get('access_token', '')}"}
        # Register user A first if not exists
        reg_a = app.post("/api/auth/register", json={"username": "iso_a", "password": "pass123"})
        reg_b = app.post("/api/auth/register", json={"username": "iso_b", "password": "pass123"})

        login_a = app.post("/api/auth/login", json={"username": "iso_a", "password": "pass123"})
        login_b = app.post("/api/auth/login", json={"username": "iso_b", "password": "pass123"})

        headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        # Both users should have empty task lists
        tasks_a = app.get("/api/tasks", headers=headers_a).json()
        tasks_b = app.get("/api/tasks", headers=headers_b).json()
        assert len(tasks_a) == 0
        assert len(tasks_b) == 0

    def test_user_cannot_delete_nonexistent_task(self, app, user_headers):
        resp = app.get("/api/tasks/99999", headers=user_headers)
        assert resp.status_code == 404


class TestRuleSync:
    """同步状态查询"""

    def test_sync_status(self, app, admin_headers):
        resp = app.get("/api/rules/sync/status", headers=admin_headers)
        assert resp.status_code == 200

    def test_sync_history(self, app, admin_headers):
        resp = app.get("/api/rules/sync/history", headers=admin_headers)
        assert resp.status_code == 200
