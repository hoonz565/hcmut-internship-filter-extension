import json
import re

def parse_copied_text(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    data = {} # Lần này dùng Dictionary (Object) luôn cho giống kết quả AI
    current_full_name = None

    for i in range(len(lines)):
        line = lines[i]

        # 1. BẮT TÊN ĐẦY ĐỦ (Nằm ngay dưới chữ logologo preview 1 dòng)
        if line == "logologo preview":
            if i + 1 < len(lines):
                # Xóa chữ " (Gọi tắt là...)" nếu có để tên sạch sẽ khớp với web trường
                raw_name = lines[i + 1]
                clean_name = re.sub(r'\s*\(Gọi tắt là.*?\)', '', raw_name)
                current_full_name = clean_name

        # 2. Bắt Tên Đề Tài
        elif re.match(r'^\d{2}:\d{2}$', line):
            if current_full_name and i + 1 < len(lines):
                ten_de_tai = lines[i + 1]
                
                data[current_full_name] = {
                    "Tên đề tài": ten_de_tai
                }
                current_full_name = None 

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"✅ Đã bóc thành công {len(data)} công ty (dùng TÊN ĐẦY ĐỦ) vào '{output_file}'.")

if __name__ == "__main__":
    parse_copied_text('input.txt', 'data.json')