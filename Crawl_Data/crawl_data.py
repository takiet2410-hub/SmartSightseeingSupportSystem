import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from tqdm import tqdm 
import re 
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
# Thêm thư viện openpyxl để ghi file Excel
# (Hãy đảm bảo bạn đã chạy: pip install openpyxl)

# -------------------------------------------------------------------
# (HÀM GIAI ĐOẠN 2: ĐÃ SỬA LỖI H3/H4)
# (Giữ nguyên, không thay đổi)
# -------------------------------------------------------------------
def scrape_destination(item_id, driver): 
    """
    Cào thông tin và TẤT CẢ CÁC ẢNH của một địa điểm DÙNG SELENIUM.
    """
    url = f"https://csdl.vietnamtourism.gov.vn/dest/?item={item_id}"
    base_url = "https://csdl.vietnamtourism.gov.vn"
    
    try:
        driver.get(url) 
        # Chờ 2 giây để JavaScript của trang chi tiết kịp tải
        time.sleep(2) 
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
    except Exception as e:
        # Báo lỗi rõ ràng hơn, kèm theo stack trace nếu có
        print(f"\nLỗi khi tải trang {item_id}: {e}")
        # Nếu lỗi là 'invalid session id', ta nên để vòng lặp chính biết để khởi động lại
        if "invalid session id" in str(e):
            raise e # Ném lỗi ra ngoài để vòng lặp chính xử lý
        return None 

    # --- SỬA LỖI: TÌM H4 (TRONG DIV.HEADER) THAY VÌ H3 ---
    name = None
    header_div = soup.find('div', class_='header') # Tìm <div class="header">
    if header_div:
        name_tag = header_div.find('h4') # Tìm <h4> bên trong div đó
        if name_tag:
            name = name_tag.text.strip()
    
    if not name:
        # (Debug) Báo cho chúng ta biết nếu vẫn không tìm thấy tên
        print(f"DEBUG: Không tìm thấy tên (name) cho item {item_id}")
        return None
            
    address = None
    description = None
    province = None
    
    # THAY ĐỔI: Tìm mô tả trong class 'content-detail'
    # HTML cho thấy mô tả nằm trong <div class="col-12 py-2 content-detail">
    description_tags = soup.find_all('div', class_='content-detail')
    all_desc_text = []
    
    for tag in description_tags:
        all_desc_text.append(tag.text.strip())
    
    # Nối tất cả các đoạn mô tả lại
    description = "\n".join(all_desc_text) if all_desc_text else None
    
    # Lấy địa chỉ từ thẻ <span> riêng (dựa trên HTML bạn gửi)
    address_span = soup.find('span', class_='d-block')
    if address_span and address_span.find('i', class_='fa-map-marker'):
        address = address_span.text.strip().replace("Địa chỉ:", "").strip()
        if address and ',' in address:
            province = address.split(',')[-1].strip()

    # (Phần lấy ảnh giữ nguyên)
    image_urls = []
    # THAY ĐỔI: Dựa trên HTML, ảnh nằm trong 'album-content'
    gallery_container = soup.find('div', class_='album-content') 
    
    if gallery_container:
        img_links = gallery_container.find_all('a', href=re.compile(r'\.jpg|\.png', re.IGNORECASE)) # Tìm link <a> có .jpg hoặc .png
        for link in img_links:
            image_urls.append(link['href']) # Lấy link đầy đủ
    else: 
        # Fallback (nếu chỉ có 1 ảnh)
        img_tag_container = soup.find('div', class_='slider-for')
        if img_tag_container:
            img_tag = img_tag_container.find('img')
            if img_tag and img_tag.has_attr('src'):
                    image_urls.append(base_url + img_tag['src'])
    
    all_image_links = ";".join(image_urls) if image_urls else None

    return {
        "landmark_id": item_id,
        "name": name,
        "location_province": province,
        "specific_address": address,
        "budget_range": None,
        "available_time_needed": None,
        "companion_tags": None,
        "season_tags": None,
        "activity_tags & vibe_tags (Combined_tags)": None,
        "info_summary": description,
        "overall_rating": None,
        "image_urls": all_image_links
    }

# -------------------------------------------------------------------
# (Hàm Giai đoạn 1: Giữ nguyên)
# (Giữ nguyên, không thay đổi)
# -------------------------------------------------------------------
def get_all_destination_ids(driver):
    all_item_ids = set() 
    base_listing_url = "https://csdl.vietnamtourism.gov.vn/dest/"
    TOTAL_PAGES_TO_SCAN = 65 

    print("--- GIAI ĐOẠN 1: ĐANG THU THẬP TẤT CẢ ID (DÙNG SELENIUM) ---")
    
    for page_num in tqdm(range(1, TOTAL_PAGES_TO_SCAN + 1), desc="Đang quét các trang danh sách"):
        url = f"{base_listing_url}?page={page_num}"
        
        try:
            driver.get(url)
            time.sleep(3) # Chờ JS chạy
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Bộ chọn này đã đúng (vì GĐ1 đã chạy thành công)
            links = soup.select("div.verticle-listing-caption > h4 > a")
            
            if not links: 
                print(f"\nKhông tìm thấy link ở page={page_num}. Đã đến trang cuối.")
                break
                
            for link in links:
                href = link.get('href') 
                if href and 'item=' in href:
                    item_id = href.split('item=')[-1]
                    all_item_ids.add(item_id)
            
        except Exception as e:
            print(f"Lỗi khi quét trang {page_num}: {e}")
            # Nếu session sập ngay ở GĐ 1, ném lỗi ra để dừng
            if "invalid session id" in str(e):
                raise e
                
    print(f"\nĐã thu thập được {len(all_item_ids)} ID địa điểm duy nhất.")
    return list(all_item_ids) 

# -------------------------------------------------------------------
# (Phần Chạy Chính: ĐÃ SỬA LẠI)
# -------------------------------------------------------------------
def main():
    my_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    }

    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--log-level=3") 
    chrome_options.add_argument(f"user-agent={my_headers['User-Agent']}") 

    # Chỉ cài đặt service một lần
    service = Service(ChromeDriverManager().install())
    print("Đã cài đặt Chrome Driver Manager...")

    item_id_list = []
    all_results = []

    # --- BẮT ĐẦU GIAI ĐOẠN 1 ---
    try:
        print("\n--- GIAI ĐOẠN 1: ĐANG THU THẬP TẤT CẢ ID ---")
        # Khởi tạo driver CHỈ DÙNG cho Giai đoạn 1
        driver_gd1 = webdriver.Chrome(service=service, options=chrome_options)
        print("Đã khởi tạo Selenium Driver (Giai đoạn 1)...")
        
        item_id_list = get_all_destination_ids(driver_gd1) 

    finally:
        # Dù thành công hay thất bại, luôn đóng driver Giai đoạn 1
        if 'driver_gd1' in locals():
            driver_gd1.quit()
            print("Đã đóng Selenium Driver (Giai đoạn 1).")
    # --- KẾT THÚC GIAI ĐOẠN 1 ---


    # --- BẮT ĐẦU GIAI ĐOẠN 2 ---
    if item_id_list: 
        print("\n--- GIAI ĐOẠN 2: ĐANG CÀO CHI TIẾT TỪNG ĐỊA ĐIỂM ---")
        
        try:
            # Khởi tạo driver MỚI TINH cho Giai đoạn 2
            driver_gd2 = webdriver.Chrome(service=service, options=chrome_options)
            print("Đã khởi tạo Selenium Driver MỚI (Giai đoạn 2)...")

            for item_id in tqdm(item_id_list, desc="Đang cào chi tiết"):
                try:
                    data = scrape_destination(item_id, driver_gd2) # Dùng driver_gd2
                    if data:
                        all_results.append(data)
                    time.sleep(0.5) 
                
                except Exception as e:
                    # Nếu gặp lỗi 'invalid session id', ta khởi động lại driver GĐ 2
                    if "invalid session id" in str(e):
                        print(f"\nLỖI SESSION ID tại item {item_id}. Đang khởi động lại driver GĐ 2...")
                        driver_gd2.quit()
                        time.sleep(5) # Chờ 5 giây để đóng hoàn toàn
                        driver_gd2 = webdriver.Chrome(service=service, options=chrome_options)
                        print("Đã khởi động lại. Thử lại item...")
                        # Thử lại item vừa lỗi
                        data = scrape_destination(item_id, driver_gd2)
                        if data:
                            all_results.append(data)
                    else:
                        # Bỏ qua item này nếu là lỗi khác (ví dụ: không tìm thấy tên)
                        print(f"\nBỏ qua item {item_id} do lỗi: {e}")

        finally:
            # Đóng driver Giai đoạn 2 sau khi vòng lặp kết thúc
            if 'driver_gd2' in locals():
                driver_gd2.quit()
                print("\nĐã đóng Selenium Driver (Giai đoạn 2).")

    else:
        print("Không tìm thấy ID nào để cào chi tiết. Dừng chương trình.")

    # --- KẾT THÚC GIAI ĐOẠN 2 ---


    # --- BẮT ĐẦU GIAI ĐOẠN 3 ---
    print("\n--- GIAI ĐOẠN 3: ĐANG LƯU KẾT QUẢ ---")
    if all_results:
        df = pd.DataFrame(all_results)
        columns_in_order = [
            "landmark_id", "name", "location_province", "specific_address",
            "budget_range", "available_time_needed", "companion_tags", 
            "season_tags", "activity_tags & vibe_tags (Combined_tags)", 
            "info_summary", "overall_rating", "image_urls"
        ]
        df = df.reindex(columns=columns_in_order) 

        output_file_excel = "CRAWLED_DATASET_FULL.xlsx"
        df.to_excel(output_file_excel, index=False, engine='openpyxl')

        print(f"\n--- 🎉 HOÀN TẤT! Đã lưu {len(all_results)} địa điểm vào file {output_file_excel} ---")
    else:
        print("Không có kết quả nào để lưu.")
    # --- KẾT THÚC GIAI ĐOẠN 3 ---
    
if __name__ == "__main__":
    main()