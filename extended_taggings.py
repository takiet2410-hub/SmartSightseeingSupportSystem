import pandas as pd
import re

# =========================
# CẤU HÌNH CƠ BẢN
# =========================
INPUT_FILE = "temp_crawling_progress.xlsx"   # Đổi thành file của bạn
OUTPUT_FILE = "temp_crawling_progress_tagged.xlsx"

PLACE_COL   = "name"
INFO_COL    = "info_summary"
TIME_COL    = "available_time_needed"
COMP_COL    = "companion_tags"
SEASON_COL  = "season_tags"

TIME_CHOICES      = ["1-2 giờ", "2-4 giờ", "4-8 giờ", "8-24 giờ"]
COMPANION_CHOICES = ["Cặp đôi", "Gia đình", "Một mình", "Nhóm bạn bè"]
SEASON_CHOICES    = ["Xuân", "Hạ", "Thu", "Đông", "Quanh năm"]

# FILL_MODE:
#   "empty_only"     → chỉ điền ô đang TRỐNG, không đụng vào ô đã có giá trị
#   "extend_up_to_3" → nếu đã có sẵn 1 tag, có thể thêm để đủ tối đa 3 tag
FILL_MODE = "extend_up_to_3"   # bạn có thể đổi thành "empty_only" nếu muốn an toàn hơn


# =========================
# HÀM HỖ TRỢ CHUNG
# =========================

def norm_text(name, info):
    return f"{str(name)} {str(info)}".lower()

def parse_existing_tags(value, allowed):
    """Tách chuỗi sẵn có thành list tag hợp lệ (lọc theo allowed)."""
    if pd.isna(value):
        return []
    s = str(value)
    if not s.strip():
        return []
    parts = re.split(r"[;,/|]", s)
    tags = []
    for p in parts:
        t = p.strip()
        if t in allowed and t not in tags:
            tags.append(t)
    return tags

def combine_tags(existing_str, suggested_list, allowed, max_tags=3):
    """
    Gộp tag sẵn có + tag đề xuất.
    - Nếu FILL_MODE = "empty_only" và đã có tag → giữ nguyên.
    - Nếu FILL_MODE = "extend_up_to_3" → thêm tag mới nhưng không vượt quá max_tags.
    """
    existing = parse_existing_tags(existing_str, allowed)

    if FILL_MODE == "empty_only" and existing:
        return ", ".join(existing)

    final = list(existing)
    for t in suggested_list:
        if t in allowed and t not in final and len(final) < max_tags:
            final.append(t)

    if not final and allowed:
        final = [allowed[0]]

    return ", ".join(final[:max_tags])


# =========================
# LOGIC GỢI Ý TAG CHO COMPANION
# =========================

def suggest_companion_tags(name, info):
    text = norm_text(name, info)
    tags = []

    # Công viên, khu vui chơi, resort, safari...
    if any(k in text for k in [
        "công viên nước", "công viên", "khu vui chơi", "vinpearl",
        "safari", "thảo cầm viên", "vườn thú", "khu du lịch sinh thái",
        "khu du lịch", "resort"
    ]):
        tags = ["Gia đình", "Nhóm bạn bè", "Cặp đôi"]

    # Tâm linh, đền chùa, nhà thờ...
    elif any(k in text for k in [
        "chùa", "đền", "nhà thờ", "miếu", "lăng", "mộ",
        "thánh địa", "thánh thất", "tâm linh"
    ]):
        tags = ["Một mình", "Cặp đôi"]

    # Núi, thác, rừng, trekking...
    elif any(k in text for k in [
        "núi", "thác", "đèo", "hang", "động", "rừng",
        "cao nguyên", "vườn quốc gia", "trekking", "leo núi"
    ]):
        tags = ["Nhóm bạn bè", "Cặp đôi"]

    # Phố, chợ, phố cổ, chợ đêm...
    elif any(k in text for k in [
        "chợ", "phố đi bộ", "phố cổ", "phố", "khu phố", "chợ đêm", "night market"
    ]):
        tags = ["Nhóm bạn bè", "Cặp đôi"]

    else:
        tags = ["Cặp đôi"]

    out = []
    for t in tags:
        if t in COMPANION_CHOICES and t not in out:
            out.append(t)
    return out[:3]


# =========================
# LOGIC GỢI Ý TAG CHO SEASON
# =========================

def suggest_season_tags(name, info):
    """
    Gợi ý season_tags chỉ dựa trên TÊN địa điểm (cột name),
    giảm tần suất dùng 'Xuân', ưu tiên:
      - Bảo tàng: Quanh năm
      - Đền/chùa/tâm linh: Quanh năm (chỉ khi tên có 'Lễ hội' mới dùng Xuân)
      - Làng hoa: Xuân
      - Làng cổ / phố cổ / làng nghề: Thu, Quanh năm
      - Biển / đảo / vịnh / bãi: Xuân, Hạ
      - Núi / đèo / cao nguyên / đồi: Thu, Hạ
      - Còn lại: Quanh năm
    """
    t = str(name).lower()  # CHỈ dùng name, bỏ qua info_summary

    # 1. Lễ hội rõ trong tên → Xuân (ưu tiên mùa lễ hội)
    if "lễ hội" in t:
        return ["Xuân", "Thu"]

    # 2. Bảo tàng → đi quanh năm, ít phụ thuộc thời tiết
    if "bảo tàng" in t or "museum" in t:
        return ["Quanh năm"]

    # 3. Đền / chùa / tâm linh → quanh năm
    if any(k in t for k in ["chùa", "đền", "phủ", "miếu", "thánh địa", "thánh thất", "tâm linh"]):
        return ["Quanh năm"]

    # 4. Làng hoa → mùa hoa nở, sát Tết
    if "hoa" in t:
        return ["Xuân"]

    # 5. Làng cổ / phố cổ / làng nghề / phố cổ kiểu di sản
    if any(k in t for k in ["làng cổ", "phố cổ", "làng nghề", "phố hiến"]):
        # ưu tiên Thu & Quanh năm (thời tiết mát, dễ đi dạo)
        return ["Xuân", "Thu", "Quanh năm"]

    # 6. Biển / bãi biển / vịnh / đảo / cồn / cù lao / phá
    if any(k in t for k in ["biển", "bãi biển", "bãi tắm", "vịnh", "đảo", "cù lao", "cồn", "phá"]):
        return ["Xuân", "Hạ", "Thu"]

    # 7. Núi / đèo / cao nguyên / đồi
    if any(k in t for k in ["núi", "đèo", "cao nguyên", "đỉnh", "đồi"]):
        return ["Thu", "Hạ"]

    # 8. Mặc định: đi được quanh năm
    return ["Quanh năm"]

# =========================
# LOGIC GỢI Ý TAG CHO TIME
# =========================

def suggest_time_tags(name, info):
    text = norm_text(name, info)
    tags = []

    # Rất dài / qua đêm / cả ngày
    if any(k in text for k in [
        "cắm trại", "camping", "qua đêm", "ở lại", "homestay",
        "2 ngày", "một ngày", "1 ngày", "trọn ngày"
    ]):
        tags.append("8-24 giờ")

    # Công viên lớn, vườn quốc gia, đảo, khu du lịch...
    if any(k in text for k in [
        "vườn quốc gia", "khu du lịch", "khu du lịch sinh thái",
        "khu vui chơi", "công viên", "resort", "safari",
        "đảo", "cao nguyên", "vịnh", "tour"
    ]):
        if "4-8 giờ" not in tags:
            tags.append("4-8 giờ")

    # Bảo tàng, đền chùa, phố cổ, city tour...
    if any(k in text for k in [
        "bảo tàng", "nhà trưng bày", "chùa", "đền", "phố cổ",
        "phố đi bộ", "city tour", "city_tour", "phố", "quảng trường"
    ]):
        if "2-4 giờ" not in tags:
            tags.append("2-4 giờ")

    # Điểm dừng chân, check-in nhanh
    if any(k in text for k in [
        "điểm dừng", "dừng chân", "ghé", "cổng chào", "cổng", "check-in"
    ]):
        if "1-2 giờ" not in tags:
            tags.append("1-2 giờ")

    # Hang, động, thác, trekking...
    if any(k in text for k in ["hang", "động", "thác", "trekking", "leo núi", "đèo", "rừng"]):
        if "2-4 giờ" not in tags:
            tags.append("2-4 giờ")
        if "4-8 giờ" not in tags and len(tags) < 3:
            tags.append("4-8 giờ")

    if not tags:
        tags = ["2-4 giờ"]

    out = []
    for t in tags:
        if t in TIME_CHOICES and t not in out:
            out.append(t)
    return out[:3]


# =========================
# CHƯƠNG TRÌNH CHÍNH
# =========================

def main():
    print(f"Đang đọc file: {INPUT_FILE}")
    df = pd.read_excel(INPUT_FILE)

    if PLACE_COL not in df.columns or INFO_COL not in df.columns:
        raise ValueError(f"Cần có cột '{PLACE_COL}' và '{INFO_COL}' trong file.")

    names = df[PLACE_COL].astype(str)
    infos = df[INFO_COL].astype(str)

    # Gợi ý tag
    suggested_comp   = [suggest_companion_tags(n, i) for n, i in zip(names, infos)]
    suggested_season = [suggest_season_tags(n, i) for n, i in zip(names, infos)]
    suggested_time   = [suggest_time_tags(n, i) for n, i in zip(names, infos)]

    # Nếu cột chưa tồn tại, tạo mới
    if COMP_COL not in df.columns:
        df[COMP_COL] = ""
    if SEASON_COL not in df.columns:
        df[SEASON_COL] = ""
    if TIME_COL not in df.columns:
        df[TIME_COL] = ""

    # Gộp với dữ liệu sẵn có
    df[COMP_COL] = [
        combine_tags(existing, sugg, COMPANION_CHOICES)
        for existing, sugg in zip(df[COMP_COL], suggested_comp)
    ]

    df[SEASON_COL] = [
        combine_tags(existing, sugg, SEASON_CHOICES)
        for existing, sugg in zip(df[SEASON_COL], suggested_season)
    ]

    df[TIME_COL] = [
        combine_tags(existing, sugg, TIME_CHOICES)
        for existing, sugg in zip(df[TIME_COL], suggested_time)
    ]

    df.to_excel(OUTPUT_FILE, index=False)
    print(f"✅ Xong! Đã lưu file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
