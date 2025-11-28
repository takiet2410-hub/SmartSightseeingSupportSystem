import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from tqdm import tqdm
import urllib.parse
import os

# --- CẤU HÌNH ---
INPUT_FILE = 'destinations_input_resumed.xlsx'
OUTPUT_FILE = 'destinations_with_rating_FINAL.xlsx'
TEMP_FILE = 'temp_crawling_progress.xlsx' # File lưu tạm để check giữa giờ
DELIMITER = ';' 
BATCH_SAVE = 10 # Cứ 10 dòng thì lưu file 1 lần (để bạn check)

def init_driver():
    """Khởi tạo Selenium Driver"""
    options = Options()
    # options.add_argument("--headless") # KHUYÊN DÙNG: Tắt headless để bạn nhìn thấy trình duyệt chạy, dễ debug hơn
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=vi")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def get_rating_from_maps(driver, query):
    search_url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"
    driver.get(search_url)
    
    try:
        wait = WebDriverWait(driver, 4) # Giảm thời gian chờ xuống chút cho nhanh
        
        # Hàm con để lấy text
        def extract_data():
            r = driver.find_element(By.XPATH, "//div[contains(@class, 'F7nice')]/span[1]/span[@aria-hidden='true']").text.strip()
            c = driver.find_element(By.XPATH, "//div[contains(@class, 'F7nice')]/span[2]/span/span").text.strip().replace('(', '').replace(')', '')
            return r, c

        try:
            # Case 1: Vào thẳng trang chi tiết
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'F7nice')]/span[1]/span[@aria-hidden='true']")))
            return extract_data()
        except:
            # Case 2: Vào list, click cái đầu tiên
            first_result = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.hfpxzc")))
            first_result.click()
            time.sleep(2) # Đợi load chi tiết
            return extract_data()
            
    except Exception:
        return None, None
    
    return None, None

def main():
    # 1. Đọc dữ liệu
    print("--- Đang đọc file CSV ---")
    df = pd.read_excel(INPUT_FILE, engine='openpyxl')
    
    # Tạo cột nếu chưa có
    if 'google_rating' not in df.columns:
        df['google_rating'] = None
    if 'google_review_count' not in df.columns:
        df['google_review_count'] = None

    # 2. Khởi tạo Driver
    driver = init_driver()
    print("--- Đã khởi tạo Selenium. Bắt đầu crawl... ---")
    print(f"👉 Dữ liệu tạm sẽ được lưu vào: {TEMP_FILE} (mỗi {BATCH_SAVE} dòng)")

    # Biến đếm thành công/thất bại để thống kê
    success_count = 0
    fail_count = 0

    try:
        # Sử dụng tqdm để hiện thanh tiến trình
        pbar = tqdm(df.iterrows(), total=df.shape[0], unit="địa điểm")
        
        for index, row in pbar:
            # Resume: Bỏ qua nếu đã có dữ liệu
            if pd.notna(row['google_rating']) and row['google_rating'] != '':
                continue

            name = str(row['name'])
            specific_addr = str(row.get('specific_address', '')).replace('nan', '').strip()
            province = str(row.get('location_province', '')).replace('nan', '').strip()

            # --- CHIẾN THUẬT 2 LỚP ---
            
            # 1. Tạo Query ưu tiên (Cụ thể)
            # Chỉ dùng nếu địa chỉ cụ thể đủ dài (> 5 ký tự)
            query_specific = f"{name} {specific_addr}".strip()
            
            # 2. Tạo Query dự phòng (Chung chung)
            query_generic = f"{name} {province}".strip()

            rating = None
            count = None

            # --- BƯỚC 1: Thử tìm cụ thể trước ---
            if len(specific_addr) > 5:
                rating, count = get_rating_from_maps(driver, query_specific)

            # --- BƯỚC 2: Nếu Bước 1 thất bại (không lấy được rating), thử tìm chung chung ---
            if not rating:
                # Nếu lúc nãy chưa tìm (do không có địa chỉ cụ thể) HOẶC tìm rồi mà không thấy
                # tqdm.write(f"⚠️ Thử lại với query chung: {query_generic}")
                rating, count = get_rating_from_maps(driver, query_generic)

            # Lưu kết quả (Dù có hay không)
            df.at[index, 'google_rating'] = rating
            df.at[index, 'google_review_count'] = count
            
            # --- LOGGING ---
            if rating:
                success_count += 1
                pbar.set_postfix_str(f"✅ OK: {rating}* | {name[:15]}...")
            else:
                fail_count += 1
                pbar.set_postfix_str(f"❌ Miss: {name[:15]}...")
            
            # Lưu checkpoint (Giữ nguyên code cũ)
            if (index + 1) % BATCH_SAVE == 0:
                try:
                    df.to_excel(TEMP_FILE, index=False, engine='openpyxl')
                except: pass

            time.sleep(1.5)

    except KeyboardInterrupt:
        print("\n🛑 Bạn đã dừng chương trình thủ công!")
    finally:
        driver.quit()

    # 4. Xuất kết quả cuối cùng
    print(f"\n--- TỔNG KẾT ---")
    print(f"✅ Tìm thấy: {success_count}")
    print(f"❌ Không thấy: {fail_count}")
    print(f"💾 Đang lưu file cuối cùng: {OUTPUT_FILE}")
    df.to_excel(OUTPUT_FILE, index=False, engine='openpyxl')
    
    # Xóa file tạm cho gọn (tùy chọn)
    if os.path.exists(TEMP_FILE):
        # os.remove(TEMP_FILE) 
        print(f"(File tạm {TEMP_FILE} vẫn được giữ lại để backup)")

if __name__ == "__main__":
    main()