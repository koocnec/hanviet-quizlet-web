HanViet Quizlet WebDeploy V7

Bản V7 thêm tính năng: trong mục Gõ văn bản, nếu trả lời sai thì app giữ nguyên câu đó. Người học bắt buộc phải gõ đúng mới tự chuyển sang câu tiếp theo. Nút Hiện đáp án chỉ xem đáp án, không cho qua câu.

HƯỚNG DẪN ĐƯA APP HANVIET FLASHCARDS LÊN WEB BẰNG STREAMLIT CLOUD

File này là bản V6 chuẩn deploy web.
Trong thư mục có:
- app.py
- requirements.txt
- .streamlit/config.toml
- chay_local.bat

============================================================
A. CHẠY THỬ TRÊN MÁY
============================================================
1. Giải nén thư mục này.
2. Mở thư mục vừa giải nén.
3. Double click chay_local.bat.
4. Nếu trình duyệt không tự mở, vào: http://localhost:8501

============================================================
B. CHUẨN BỊ GOOGLE SHEETS
============================================================
1. Mở Google Sheets chứa dữ liệu.
2. Bấm Share / Chia sẻ.
3. Đổi quyền thành: Anyone with the link -> Viewer.
4. Copy link Google Sheets.

Lưu ý sheet của bạn thường là:
- Tên sheet: nhaplieu
- Cột B: tiếng Hàn
- Cột A: nghĩa tiếng Việt
- Cột C: giải thích

============================================================
C. ĐẨY LÊN GITHUB
============================================================
1. Vào https://github.com
2. Đăng nhập hoặc tạo tài khoản.
3. Bấm New repository.
4. Đặt tên, ví dụ: hanviet-flashcards
5. Chọn Public.
6. Bấm Create repository.
7. Bấm Add file -> Upload files.
8. Kéo thả toàn bộ file trong thư mục này lên GitHub:
   - app.py
   - requirements.txt
   - thư mục .streamlit
   - README_DEPLOY.txt
9. Bấm Commit changes.

Quan trọng: Không upload file Excel riêng tư nếu bạn không muốn công khai dữ liệu.
App có thể đọc Google Sheets bằng link Viewer nên không cần upload file Excel lên GitHub.

============================================================
D. DEPLOY LÊN STREAMLIT COMMUNITY CLOUD
============================================================
1. Vào https://share.streamlit.io hoặc https://streamlit.io/cloud
2. Đăng nhập bằng GitHub.
3. Bấm New app.
4. Chọn repo: hanviet-flashcards
5. Branch: main
6. Main file path: app.py
7. Bấm Deploy.

Sau khi chạy xong, bạn sẽ có link dạng:
https://ten-app-cua-ban.streamlit.app

============================================================
E. DÙNG APP TRÊN WEB
============================================================
1. Mở link app.
2. Dán link Google Sheets.
3. Tên sheet: nhaplieu
4. Chọn cột:
   - Cột tiếng Hàn: B
   - Cột nghĩa tiếng Việt: A
   - Cột giải thích: C
5. Chọn số từ mỗi thư mục: 50.
6. Học bằng Flashcard, Quiz, Ghép cặp hoặc Gõ văn bản.

============================================================
F. LỖI THƯỜNG GẶP
============================================================
1. App báo không đọc được Google Sheets:
   - Kiểm tra đã share Anyone with the link -> Viewer chưa.
   - Kiểm tra tên sheet có đúng là nhaplieu không.

2. App chạy chậm:
   - Google Sheets quá nhiều công thức.
   - Nên tạo một sheet nhaplieu chỉ chứa dữ liệu dạng giá trị, không quá nhiều công thức nặng.

3. Dữ liệu thiếu:
   - Bản V6 chỉ cần có tiếng Hàn ở cột B là tạo thẻ.
   - Nếu cột nghĩa trống, app hiện Chưa có nghĩa.

