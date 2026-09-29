def test_home(client):
    r = client.get("/")
    assert r.status_code == 200

def test_login_page(client):
    assert client.get("/auth/login").status_code == 200

def test_shop(client):
    assert client.get("/shop/").status_code == 200