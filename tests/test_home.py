def test_homepage(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Jottit" in response.data


def test_check_subdomain_available(client):
    response = client.get("/check-subdomain?name=freshname")
    assert response.status_code == 200
    assert response.json == {"available": True}


def test_check_subdomain_taken(client, taken_subdomain):
    response = client.get(f"/check-subdomain?name={taken_subdomain}")
    assert response.status_code == 200
    assert response.json == {"available": False}


def test_check_subdomain_invalid(client):
    response = client.get("/check-subdomain?name=x")
    assert response.status_code == 200
    assert response.json == {"error": "Invalid name"}
