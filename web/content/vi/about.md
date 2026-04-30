---
title: "Giới thiệu — InvestIQs Research"
url: "/vi/about/"
draft: false
reviewed: true
ShowToc: false
---

## InvestIQs Research

Nền tảng nghiên cứu dựa trên dữ liệu, tập trung vào **ETF Mỹ · ETF Việt Nam · tài sản cổ tức · phân bổ tài sản dài hạn**. Mọi bài viết kết hợp dữ liệu thị trường công khai với phân tích AI và đều trải qua hai bước xác minh trước khi xuất bản.

---

## Phương pháp

1. **Kiểm chéo dữ liệu thời gian thực**
   - Cập nhật cache yfinance mỗi ngày 08:00 KST.
   - Lợi suất cổ tức được tính trực tiếp từ `Ticker.dividends` và đối chiếu với yfinance.info; chênh lệch >30% sẽ chọn giá trị bảo thủ.
   - Loại bỏ giá trị bất thường (P/E âm, yield >15%).

2. **Phân tích AI đa tác nhân**
   - ai-hedge-fund với 5 tác nhân: Góc nhìn Warren Buffett / Kỹ thuật / Cơ bản / Tâm lý tin tức / Rủi ro.
   - Chỉ dùng làm tín hiệu tham khảo, không phải kết luận duy nhất.

3. **So sánh với Peer ETF**
   - Luôn so sánh với ít nhất một ETF đồng hạng về phí, cổ tức hoặc tổng lợi nhuận.

4. **Contrarian angle + Kịch bản phản biện**
   - Ít nhất một góc nhìn khác với đồng thuận thị trường.
   - Ít nhất một kịch bản mà luận điểm có thể sai.

5. **Xác minh hai bước**
   - Bước 1 (quy tắc): độ dài, bảng so sánh, cụm từ cấm, dữ liệu nguồn.
   - Bước 2 (Gemini ngữ nghĩa): ảo giác, mâu thuẫn nội bộ, rủi ro tuân thủ.

---

## Nguồn dữ liệu

| Mục | Nguồn |
|-----|-------|
| Giá, lợi nhuận, cổ tức | yfinance (Yahoo Finance API) |
| Góc nhìn AI | ai-hedge-fund đa tác nhân (Gemini 2.0 Flash) |
| Soạn thảo & xác minh | Codex + Gemini |

---

## Nguyên tắc biên tập

- **Thông tin chứ không phải tư vấn**: Tất cả chỉ là ghi chú nghiên cứu dựa trên dữ liệu công khai.
- **Tuân thủ quy định**: Không dùng chỉ thị dứt khoát ("nên mua", "chắc chắn tăng").
- **Minh bạch**: AI hỗ trợ được công khai qua banner và tuyên bố miễn trừ.
- **Xuất bản hàng ngày**: Tự động 06–08 KST, năm ngôn ngữ song song.

---

## Tuyên bố miễn trừ

Toàn bộ nội dung là nghiên cứu giáo dục dựa trên dữ liệu yfinance công khai và phân tích AI. Đây không phải là lời khuyên đầu tư, không phải lời mời mua/bán. Quyết định và rủi ro thuộc về bạn.
