def test_all_management_pages_render(client):
    for path in ["/", "/rooms", "/bookings", "/customers", "/services", "/invoices", "/reports", "/ai", "/users"]:
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.text.count('id="chatLauncher"') == 1
        assert response.text.count('id="chatWindow"') == 1
    assert client.get("/static/js/chat-widget.js").status_code == 200


def test_ai_page_discloses_cloud_provider(client):
    response = client.get("/ai")
    assert "POWERED BY GEMINI" in response.text
    assert "Google Gemini" in response.text
    assert "Dữ liệu local" not in response.text
    assert "POWERED BY OLLAMA" not in response.text
