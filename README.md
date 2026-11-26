# Market Lab — Outlook MVP

## Chạy ngay
Mở `index.html` trong trình duyệt để thử Scenario offline. Bấm **Kịch bản mẫu** hoặc chọn Giảm / Trung tính / Tăng trên từng yếu tố. Nút `?` đánh dấu chưa biết; `↺` bỏ giả định để quay về dữ liệu live. Reset xóa mọi giả định. Không cần cài thư viện.

## Live
Cần Python 3.10+ và kết nối Internet. Giải nén ZIP, mở terminal ở thư mục market-lab, chạy:

- macOS/Linux: `python3 server.py`
- Windows: `py server.py` (hoặc `python server.py`)

Mở http://127.0.0.1:8765. Server chỉ nghe trên máy local. Dữ liệu tự cập nhật mỗi 15 phút khi mở trang; có thể bấm cập nhật thủ công (cache server 5 phút). Ctrl+C để tắt.

## Dữ liệu và giới hạn
- CPI: FRED CPIAUCSL, YoY tính từ chỉ số đã điều chỉnh mùa vụ; thiếu consensus nên không tính tín hiệu live cho CPI. Chọn scenario thủ công để đánh giá surprise.
- Fed Rate: FRED DFEDTARU (trần mục tiêu); thay đổi 30 ngày.
- Unemployment: FRED UNRATE; thay đổi so với tháng trước.
- DXY: Live dùng **proxy** broad dollar index DTWEXBGS, không phải DXY chính xác.
- Global Liquidity: Live dùng **proxy** M2 Mỹ M2SL, không phải tổng thanh khoản toàn cầu.
- ETF: bảng Farside Investors, dòng tiền ròng gần nhất; có thể bị chặn hoặc thay đổi cấu trúc bảng.
- Các nguồn quá cũ hoặc lỗi được loại khỏi điểm. Không tạo dữ liệu giả. Dữ liệu công bố không phải tick real-time. Các kết nối nguồn ngoài chưa được xác thực end-to-end trong môi trường tạo bản MVP.

## Mô hình
Base weights ở 7D: Stock (25,25,20,10,20,0); Crypto (20,20,10,15,20,15), thứ tự CPI, Fed, Unemployment, USD, Liquidity, ETF. Các timeframe khác dùng multiplier minh họa rồi chuẩn hóa. Điểm = tổng(weight × directional signal) từ -100 đến +100. Không tái phân bổ trọng số khi thiếu dữ liệu. Mức |score| <10: neutral; 10–<30: nhẹ; 30–<60: tương đối; ≥60: mạnh. Độ phủ tín hiệu khác với độ tin cậy. Tín hiệu live được chuẩn hóa heuristic theo ngưỡng và có thể ở giữa -1 và +1; tín hiệu scenario chọn -1, 0, +1. Mô hình chưa backtest, chưa calibrate, chưa có mô hình tương tác phi tuyến; không dùng làm xác suất hoặc tín hiệu đầu tư trực tiếp.
