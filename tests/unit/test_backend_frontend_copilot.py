from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.app import create_app


def test_frontend_copilot_chat_endpoint_can_be_monkeypatched(monkeypatch):
    monkeypatch.setattr(
        'src.backend.app.process_frontend_copilot_turn',
        lambda **_: {
            'message': '测试回复',
            'followUpPrompts': ['继续问'],
            'recommendedNextActions': ['查看动作'],
            'contextLabel': '当前产品：测试',
            'warning': None,
        },
    )

    with TestClient(create_app()) as client:
        response = client.post(
            '/frontend/copilot/chat',
            json={
                'product_id': 1,
                'page_key': 'workbench',
                'page_title': 'Amazon 运营工作台',
                'user_message': '先看什么？',
                'history': [],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body['message'] == '测试回复'
    assert body['followUpPrompts'] == ['继续问']
