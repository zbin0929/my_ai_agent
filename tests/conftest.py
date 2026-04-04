# -*- coding: utf-8 -*-
"""
pytest 配置和共享 fixtures
"""

import os
import sys
import pytest

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@pytest.fixture
def client():
    """创建 FastAPI 测试客户端"""
    from fastapi.testclient import TestClient
    from api.main import app
    with TestClient(app) as c:
        yield c
