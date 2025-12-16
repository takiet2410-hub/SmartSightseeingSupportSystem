from unittest.mock import MagicMock, patch

def test_add_favorite(client):
    mock_dest_col = MagicMock()
    mock_dest_col.find_one.return_value = {"landmark_id": "lm_1"}
    
    mock_fav_col = MagicMock()
    mock_fav_col.update_one.return_value = MagicMock()

    with patch("favorites.get_favorites_collection", return_value=mock_fav_col), \
         patch("favorites.get_db_collection", return_value=mock_dest_col):
        
        response = client.post("/favorites/lm_1")
        assert response.status_code == 200
        assert response.json() == {"message": "Đã thêm vào mục yêu thích"}

def test_add_favorite_not_found(client):
    # Test case địa điểm không tồn tại
    with patch("favorites.get_db_collection") as mock_dest:
        mock_dest.return_value.find_one.return_value = None
        response = client.post("/favorites/invalid")
        assert response.status_code == 404
