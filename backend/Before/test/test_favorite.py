from fastapi.testclient import TestClient

def test_add_favorite(client: TestClient, sample_data):
    # 1. Thêm L001 vào yêu thích
    response = client.post("/favorites/L001")
    assert response.status_code == 200
    assert response.json()["message"] == "Đã thêm vào mục yêu thích"

    # 2. Kiểm tra trạng thái
    check_response = client.get("/favorites/check/L001")
    assert check_response.json()["is_favorite"] is True

def test_remove_favorite(client: TestClient, sample_data):
    # Setup: Thêm trước
    client.post("/favorites/L001")

    # 1. Xóa
    response = client.delete("/favorites/L001")
    assert response.status_code == 200
    assert response.json()["message"] == "Đã xóa khỏi mục yêu thích"

    # 2. Check lại
    check_response = client.get("/favorites/check/L001")
    assert check_response.json()["is_favorite"] is False

def test_get_my_favorites_list(client: TestClient, sample_data):
    # Setup: Thêm L001 và L002
    client.post("/favorites/L001")
    client.post("/favorites/L002")

    response = client.get("/favorites/")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 2
    ids = [item["id"] for item in data["data"]]
    assert "L001" in ids
    assert "L002" in ids

def test_add_non_existent_favorite(client: TestClient):
    response = client.post("/favorites/INVALID_ID")
    assert response.status_code == 404