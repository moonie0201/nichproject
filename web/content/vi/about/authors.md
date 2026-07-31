---
title: "Quy trình sản xuất và kiểm chứng nội dung"
description: "Nội dung InvestIQs được tạo bằng quy trình biên tập có hỗ trợ AI, sau đó qua kiểm tra theo quy tắc và đối chiếu dữ liệu công khai. Chúng tôi công bố minh bạch quy trình và giới hạn của nó."
date: 2026-05-26
lastmod: 2026-07-31
draft: false
layout: "about"
ai_generated: true
human_reviewed: false
---

## Ai xuất bản trang này

InvestIQs được xuất bản bởi **đội ngũ biên tập InvestIQs** — một tổ chức, không phải một chuyên viên phân tích cá nhân. Chúng tôi không tuyên bố rằng mỗi bài viết có một nhà phân tích thật đứng tên, vì điều đó không đúng sự thật. Trang này giải thích chính xác cách nội dung được tạo ra, điều gì được kiểm tra và điều gì không.

## Cách nội dung được tạo (minh bạch)

Toàn bộ bài phân tích, tóm tắt thị trường và kịch bản video trên InvestIQs được **tạo bằng quy trình biên tập có hỗ trợ AI sử dụng mô hình ngôn ngữ lớn (LLM)**. Chúng không được viết từng dòng bởi chuyên viên phân tích. Chúng tôi nêu rõ điều này thay vì ngụ ý có tác giả là người.

### Các mô hình được dùng
- **Nội dung bài viết**: Anthropic Claude (Haiku 4.5 / Sonnet 4.6)
- **Dịch và bản địa hóa**: Google Gemini, dự phòng OpenRouter
- **Hỗ trợ kiểm chứng**: Gemini 3.1 Pro Preview

Trường `ai_models` trong front matter của mỗi bài ghi lại ID mô hình thực tế đã dùng.

## Quy trình kiểm chứng

Người biên tập không đọc kỹ từng bài. Thay vào đó, các bước tự động sau được áp dụng:

1. **Trích dẫn dữ liệu công khai**: Chỉ trích dẫn số liệu từ nguồn công khai — yfinance, hồ sơ công bố của cơ quan quản lý, tài liệu chính thức của nhà phát hành ETF.
2. **Kiểm tra theo quy tắc**: Tự động chặn ngôn từ phóng đại, từ cấm và các cụm kiểu "bảo đảm vốn gốc".
3. **Kiểm tra cân bằng kịch bản**: Bài chỉ nêu mặt tích cực sẽ bị từ chối; bắt buộc có phần rủi ro và kịch bản giảm.
4. **Cổng SEO và cấu trúc**: Tự động kiểm tra mật độ từ khóa, cấu trúc H2, độ dài mô tả meta.

**Quy trình này không thay thế phán đoán của chuyên gia.** AI có thể sai: trích dẫn sai số liệu, chưa cập nhật quy định thuế mới nhất, bỏ sót bối cảnh thị trường.

## Giới hạn và miễn trừ

- **Không phải lời khuyên đầu tư.** Mọi nội dung chỉ nhằm cung cấp thông tin, không khuyến nghị mua bán bất kỳ chứng khoán nào.
- **Không phải tư vấn thuế hay pháp lý.** Nội dung về tài khoản ưu đãi thuế và thuế thu nhập chỉ mang tính khái quát. Hãy xác nhận tình huống của bạn với chuyên gia có chứng chỉ.
- **Khác biệt thời điểm**: Số liệu phản ánh thời điểm viết bài (xem trường `data_fetched_at`). Thị trường thay đổi nhanh — hãy kiểm tra dữ liệu mới nhất.
- **Báo lỗi**: Nếu bạn phát hiện lỗi dữ kiện, sai số liệu hoặc trích dẫn sai, hãy báo qua [Liên hệ](/vi/contact/). Chúng tôi xác minh và đính chính.

## Nguyên tắc biên tập

1. **Dữ liệu trước tiên**: Chỉ trích dẫn dữ liệu công khai có thể kiểm chứng.
2. **Trình bày hai mặt**: Nêu cả lợi ích và rủi ro; bài thiên lệch một chiều bị từ chối tự động.
3. **Minh bạch**: Việc dùng AI, mô hình sử dụng và thời điểm dữ liệu được công bố trong front matter của mọi bài.

---

*Cập nhật lần cuối: 2026-07-31*
