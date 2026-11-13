# Kịch bản demo khoảng bốn phút

1. Chạy `python -m streamlit run app.py`. Giới thiệu corpus 43 trang, embedding OpenAI thật, Chroma và chatbot GPT-5.4. Nội dung hỏi đáp sách sử dụng tiếng Anh; phần trình bày dùng tiếng Việt.
2. Chọn B và hỏi: **When does a loop else block run, and what happens if the loop exits with break?** Mở top-3 và link đúng mục sách. Phân biệt trang PDF với trang in.
3. Chọn C, chương Loops và hỏi: **Can a while loop be nested inside a for loop?** Kiểm tra metadata của cả ba đoạn. Nói rõ chương là input của người dùng, không lấy từ gold answer.
4. Mở ABC experiments. Giải thích A cố định 1.800/overlap 200; B theo mục/câu; C dùng cùng index B và thêm filter. B được chọn từ 15 dev trước khi chạy 10 test.
5. Hiển thị dev Hit@3 A 10/15, B/C 13/15; test cả ba 8/10. A có test Hit@1 6/10 còn B/C 5/10; giữ và giải thích kết quả này thay vì đổi người thắng sau test.
6. Chọn một câu test bị miss. Đối chiếu gold, trang và phần quote bị thiếu. Đoạn liên quan chưa chắc đạt exact evidence hit.
7. Mở Source review. Phân biệt nhãn AI hỗ trợ với chấm thủ công. Người đọc chỉ lưu nhãn sau khi tự kiểm tra PDF; không nói thay rằng em đã trực tiếp chấm khi chưa làm.

Nếu API lỗi, dùng thông báo lỗi và xem trace đã lưu; không dùng câu trả lời mẫu để giả làm lần gọi live thành công. results/chat_demo.json là minh chứng request thật. Khi máy chưa có index, chat tạm khóa nhưng vẫn xem được kết quả.
