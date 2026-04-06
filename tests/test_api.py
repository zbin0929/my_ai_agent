# -*- coding: utf-8 -*-
"""
API 集成测试
============

测试核心 API 接口的基本功能：健康检查、会话 CRUD、模型列表、技能列表、文件上传。
使用 FastAPI TestClient 进行同步测试，不依赖外部 LLM 服务。
"""

import os
import json
import pytest


class TestHealth:
    """健康检查接口"""

    def test_health_returns_ok(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "llm" in data


class TestSessions:
    """会话管理接口"""

    def test_list_sessions(self, client):
        res = client.get("/api/sessions")
        assert res.status_code == 200
        data = res.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_create_session(self, client):
        res = client.post("/api/sessions", json={"title": "测试会话"})
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert data["title"] == "测试会话"
        assert data["pinned"] is False

    def test_create_session_default_title(self, client):
        res = client.post("/api/sessions", json={})
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "新对话"

    def test_update_session_title(self, client):
        # 创建
        create_res = client.post("/api/sessions", json={"title": "原标题"})
        sid = create_res.json()["id"]
        # 更新
        update_res = client.patch(f"/api/sessions/{sid}", json={"title": "新标题"})
        assert update_res.status_code == 200
        assert update_res.json()["title"] == "新标题"

    def test_update_session_pin(self, client):
        create_res = client.post("/api/sessions", json={"title": "pin测试"})
        sid = create_res.json()["id"]
        update_res = client.patch(f"/api/sessions/{sid}", json={"pinned": True})
        assert update_res.status_code == 200
        assert update_res.json()["pinned"] is True

    def test_delete_session(self, client):
        create_res = client.post("/api/sessions", json={"title": "待删除"})
        sid = create_res.json()["id"]
        del_res = client.delete(f"/api/sessions/{sid}")
        assert del_res.status_code == 200
        assert del_res.json()["ok"] is True

    def test_get_messages_empty(self, client):
        create_res = client.post("/api/sessions", json={"title": "空会话"})
        sid = create_res.json()["id"]
        msg_res = client.get(f"/api/sessions/{sid}/messages")
        assert msg_res.status_code == 200
        data = msg_res.json()
        assert data["messages"] == []

    def test_get_messages_nonexistent(self, client):
        res = client.get("/api/sessions/nonexistent_id_12345/messages")
        assert res.status_code == 200
        assert res.json()["messages"] == []

    def test_invalid_session_id_rejected(self, client):
        # 包含路径遍历字符的 session_id 应被拒绝或安全处理
        res = client.delete("/api/sessions/../../../etc")
        assert res.status_code in (200, 400, 404, 405, 422)

    def test_update_nonexistent_session(self, client):
        res = client.patch("/api/sessions/nonexistent_abc", json={"title": "x"})
        assert res.status_code == 404


class TestModels:
    """模型管理接口"""

    def test_list_models(self, client):
        res = client.get("/api/models")
        assert res.status_code == 200
        data = res.json()
        assert "models" in data
        assert isinstance(data["models"], list)

    def test_model_structure(self, client):
        """验证返回的模型包含必要字段"""
        res = client.get("/api/models")
        models = res.json()["models"]
        for m in models:
            assert "id" in m
            assert "name" in m
            assert "provider" in m
            assert "model_id" in m
            assert "base_url" in m


class TestSkills:
    """技能管理接口"""

    def test_list_skills(self, client):
        res = client.get("/api/skills")
        assert res.status_code == 200
        data = res.json()
        assert "skills" in data
        assert isinstance(data["skills"], list)


class TestAgents:
    """Agent 管理接口"""

    def test_list_agents(self, client):
        res = client.get("/api/agents")
        assert res.status_code == 200
        data = res.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    def test_default_agent_exists(self, client):
        res = client.get("/api/agents")
        agents = res.json()["agents"]
        ids = [a["id"] for a in agents]
        assert "default" in ids


class TestFileUpload:
    """文件上传接口"""

    def test_upload_text_file(self, client):
        content = b"hello world test content"
        res = client.post(
            "/api/files/upload",
            files={"file": ("test.txt", content, "text/plain")},
        )
        assert res.status_code == 200
        data = res.json()
        assert "file_id" in data
        assert "url" in data
        assert data["filename"] == "test.txt"

    def test_upload_no_file(self, client):
        res = client.post("/api/files/upload")
        assert res.status_code == 422  # validation error

    def test_upload_disallowed_extension(self, client):
        content = b"malicious content"
        res = client.post(
            "/api/files/upload",
            files={"file": ("evil.exe", content, "application/octet-stream")},
        )
        assert res.status_code == 400


class TestErrorHandling:
    """错误处理"""

    def test_404_on_unknown_route(self, client):
        res = client.get("/api/nonexistent")
        assert res.status_code == 404

    def test_delete_nonexistent_model(self, client):
        res = client.delete("/api/models/nonexistent_model_xyz")
        assert res.status_code == 404
