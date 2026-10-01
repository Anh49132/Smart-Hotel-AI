def test_all_management_pages_render(client):
    for path in ["/", "/rooms", "/bookings", "/customers", "/services", "/invoices", "/reports", "/ai", "/users"]:
        response = client.get(path)
        assert response.status_code == 200, path
