from main import get_vietnamese_sort_key, normalize_key
from ingest_data import process_tags_to_array, standardize_text

def test_vietnamese_sort_key():
    """Đảm bảo sắp xếp tiếng Việt đúng: An < Đà Lạt < Đà Nẵng"""
    item_da_lat = {"name": "Đà Lạt"}
    item_an_giang = {"name": "An Giang"}
    
    key_da = get_vietnamese_sort_key(item_da_lat)
    key_an = get_vietnamese_sort_key(item_an_giang)
    
    assert key_an < key_da

def test_process_tags_to_array():
    """Test tách chuỗi tag"""
    raw = "Leo núi, Cắm trại , Biển" # Test trim space
    result = process_tags_to_array(raw)
    assert len(result) == 3
    assert "cắm trại" in result
    assert process_tags_to_array(None) == []

def test_normalize_key():
    assert normalize_key("  Quanh Năm  ") == "quanh năm"