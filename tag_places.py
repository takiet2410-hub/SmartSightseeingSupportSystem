import pandas as pd
import random

# =========================
# CẤU HÌNH CƠ BẢN
# =========================
# Đổi tên file INPUT_FILE cho đúng với file của bạn
INPUT_FILE = "landmarks.xlsx"          # ví dụ: "landmarks.xlsx"
PLACE_COL  = "name"                    # tên cột chứa tên địa điểm

COMPANION_COL = "companion_tags"
SEASON_COL    = "season_tags"
ACTIVITY_COL  = "activity_tags & vibe_tags (Combined_tags)"

OUTPUT_FILE = "landmarks_tagged.xlsx"  # file output

# Các tag được phép dùng
COMPANION_CHOICES = ["Cặp đôi", "Gia đình", "Một mình", "Nhóm bạn bè"]
SEASON_CHOICES = ["Xuân", "Hạ", "Thu", "Đông", "Quanh năm"]
ACTIVITY_CHOICES = [
    "leo núi", "ngắm cảnh", "biểu tượng", "hồ", "thiên nhiên",
    "chèo thuyền", "kỳ thú", "check-in", "phiêu lưu", "yên tĩnh", "thân thiện"
]

# =========================
# HÀM GẮN companion_tags
# =========================

def choose_companion(name: str) -> str:
    n = name.lower()

    # Tâm linh, lịch sử
    if any(k in n for k in ["chùa", "đền", "nhà thờ", "miếu", "lăng", "mộ", "nghĩa trang", "thánh", "thánh địa"]):
        return random.choice(["Cặp đôi", "Một mình"])

    # Công viên, khu vui chơi, khu du lịch, vườn, safari
    if any(k in n for k in ["công viên", "khu du lịch", "khu sinh thái", "vui chơi", "safari", "vinpearl", "thảo cầm viên", "vườn thú"]):
        return random.choice(["Gia đình", "Nhóm bạn bè"])

    # Núi, thác, hang, rừng, cao nguyên, vườn quốc gia
    if any(k in n for k in ["núi", "thác", "đèo", "hang", "động", "rừng", "cao nguyên", "vườn quốc gia"]):
        return random.choice(["Nhóm bạn bè", "Gia đình"])

    # Chợ, phố đi bộ, phố cổ, khu phố
    if any(k in n for k in ["chợ", "phố đi bộ", "phố cổ", "khu phố"]):
        return random.choice(["Nhóm bạn bè", "Cặp đôi"])

    # Mặc định
    return random.choice(COMPANION_CHOICES)

# =========================
# HÀM GẮN season_tags
# =========================

def choose_season(name: str) -> str:
    n = name.lower()

    # Lễ hội: KHÔNG chọn "Quanh năm" – ưu tiên Xuân, một phần Thu
    if "lễ hội" in n:
        return random.choices(
            ["Xuân", "Thu"],
            weights=[0.7, 0.3]
        )[0]

    # Có chữ "hoa": KHÔNG chọn "Quanh năm" – Xuân nhiều nhất
    if "hoa" in n:
        return random.choices(
            ["Xuân", "Hạ", "Thu"],
            weights=[0.6, 0.2, 0.2]
        )[0]

    # Biển, đảo, vịnh, bãi, cồn, phá → Hạ
    if any(k in n for k in ["biển", "bãi", "vịnh", "đảo", "cồn", "phá"]):
        return "Hạ"

    # Núi, đèo, cao nguyên, thác, rừng, vườn quốc gia
    if any(k in n for k in ["núi", "đèo", "cao nguyên", "thác", "rừng", "vườn quốc gia"]):
        return random.choice(["Xuân", "Thu", "Quanh năm"])

    # Thành phố, bảo tàng, quảng trường, nhà hát, trung tâm, cung
    if any(k in n for k in ["thành phố", "phố", "bảo tàng", "quảng trường", "nhà hát", "trung tâm", "cung"]):
        return "Quanh năm"

    # Mặc định
    return "Quanh năm"

# =========================
# HÀM GẮN activity_vibe_tags
# =========================

def choose_activity_tags(name: str) -> str:
    n = name.lower()
    tags = set()

    # Núi, đèo, cao nguyên
    if any(k in n for k in ["núi", "đèo", "cao nguyên"]):
        tags.update(["leo núi", "phiêu lưu", "ngắm cảnh", "thiên nhiên"])

    # Thác, suối, sông, hồ, đầm, phá
    if any(k in n for k in ["thác", "suối", "sông", "hồ", "đầm", "phá"]):
        tags.update(["hồ", "ngắm cảnh", "thiên nhiên"])

    # Biển, bãi, đảo, vịnh, cồn, cù lao
    if any(k in n for k in ["biển", "bãi", "đảo", "vịnh", "cồn", "cù lao"]):
        tags.update(["hồ", "ngắm cảnh", "chèo thuyền", "thiên nhiên"])

    # Rừng, vườn quốc gia, khu bảo tồn
    if any(k in n for k in ["rừng", "vườn quốc gia", "khu bảo tồn"]):
        tags.update(["thiên nhiên", "phiêu lưu", "ngắm cảnh"])

    # Hang, động
    if any(k in n for k in ["hang", "động"]):
        tags.update(["kỳ thú", "phiêu lưu", "thiên nhiên"])

    # Làng, bản, chợ, phố cổ, làng nghề
    if any(k in n for k in ["làng", "bản", "chợ", "phố cổ", "phố", "làng nghề"]):
        tags.update(["thân thiện", "check-in", "ngắm cảnh"])

    # Chùa, đền, nhà thờ, miếu, lăng, di tích, thánh địa
    if any(k in n for k in ["chùa", "đền", "nhà thờ", "miếu", "lăng", "di tích", "thánh địa"]):
        tags.update(["yên tĩnh", "thiên nhiên", "biểu tượng"])

    # Công viên, khu du lịch, khu sinh thái, khu vui chơi, resort
    if any(k in n for k in ["công viên", "khu du lịch", "khu sinh thái", "khu vui chơi", "resort", "safari"]):
        tags.update(["check-in", "thân thiện", "ngắm cảnh"])

    # Nếu chưa match gì → coi là điểm ngắm cảnh / check-in
    if not tags:
        tags.update(["ngắm cảnh", "check-in"])

    # Chỉ giữ tag hợp lệ
    tags = [t for t in tags if t in ACTIVITY_CHOICES]

    # Đảm bảo 2–5 tags
    desired = random.randint(2, 5)
    if len(tags) > desired:
        tags = random.sample(tags, desired)
    else:
        while len(tags) < desired:
            extra = random.choice(ACTIVITY_CHOICES)
            if extra not in tags:
                tags.append(extra)

    tags = sorted(tags)
    return ", ".join(tags)

# =========================
# HÀM HỖ TRỢ: CHỈ GHI ĐÈ KHI Ô ĐÓ ĐANG TRỐNG
# =========================

def fill_if_missing(existing_series: pd.Series, new_series: pd.Series) -> pd.Series:
    """
    Nếu ô đã có dữ liệu (không NaN, không chuỗi rỗng) → giữ lại.
    Nếu ô trống / NaN → dùng giá trị mới.
    """
    mask_has_value = existing_series.notna() & (existing_series.astype(str).str.strip() != "")
    return existing_series.where(mask_has_value, new_series)

# =========================
# CHƯƠNG TRÌNH CHÍNH
# =========================

def main():
    print(f"Đang đọc file: {INPUT_FILE}")
    df = pd.read_excel(INPUT_FILE)

    if PLACE_COL not in df.columns:
        raise ValueError(f"Không tìm thấy cột '{PLACE_COL}' trong file {INPUT_FILE}")

    names = df[PLACE_COL].astype(str)

    # Tạo series tag mới từ name
    comp_new = names.apply(choose_companion)
    season_new = names.apply(choose_season)
    act_new = names.apply(choose_activity_tags)

    # Nếu cột chưa tồn tại → tạo mới; nếu đã có → chỉ fill chỗ trống
    if COMPANION_COL in df.columns:
        df[COMPANION_COL] = fill_if_missing(df[COMPANION_COL], comp_new)
    else:
        df[COMPANION_COL] = comp_new

    if SEASON_COL in df.columns:
        df[SEASON_COL] = fill_if_missing(df[SEASON_COL], season_new)
    else:
        df[SEASON_COL] = season_new

    if ACTIVITY_COL in df.columns:
        df[ACTIVITY_COL] = fill_if_missing(df[ACTIVITY_COL], act_new)
    else:
        df[ACTIVITY_COL] = act_new

    # Lưu kết quả
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"✅ Xong! Đã lưu file gắn tag tại: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
