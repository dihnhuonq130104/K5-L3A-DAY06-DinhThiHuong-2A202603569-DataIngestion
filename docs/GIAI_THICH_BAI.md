# Hướng dẫn giải thích bài

## Giới thiệu ngắn

“Em xây dựng pipeline truy xuất cho 43 trang sách Python về Decisions và Loops. Em giữ metadata và offset nguồn, so sánh ba chiến lược A/B/C bằng embedding thật và Chroma, sau đó bổ sung chatbot GPT-5.4 có top-3 bằng chứng. Em chọn B trên dev trước khi chạy test. Câu hỏi và câu trả lời về sách dùng tiếng Anh; báo cáo và phần giải thích của em dùng tiếng Việt.”

## Các câu cần giải thích được

**Vì sao dùng tiếng Anh cho truy xuất?** Sách là tiếng Anh. Đồng bộ ngôn ngữ câu hỏi với sách giúp giảm lệch ngôn ngữ; không bảo đảm mọi truy xuất đều đúng.

**Ingestion là gì?** Đọc PDF, chuẩn hóa mà vẫn giữ thụt lề, thêm metadata, chia chunk, tạo embedding và lưu bền vững. Embedding biểu diễn ngữ nghĩa bằng vector; Chroma xếp hạng theo cosine.

**A/B/C khác gì?** A chia cửa sổ cố định 1.800 ký tự, overlap 200. B tôn trọng mục sách và ranh giới câu/dòng, tối đa 1.800, không overlap. C dùng cùng index B và chỉ thêm filter chương do người dùng cung cấp. B/C cô lập một yếu tố; A/B so sánh cả gói ranh giới và overlap.

**Vì sao chọn 1.800?** Kế hoạch thử 1.000/1.400/1.800 trên dev theo quy tắc đã lưu. Ký tự không phải token. Chunk lớn giữ ngữ cảnh tốt hơn nhưng có thể lẫn nhiều ý và tăng chi phí.

**Vì sao chọn B dù A có Hit@1 test cao hơn?** B thắng quy tắc chọn trên dev. Đổi người thắng sau khi xem test là dùng test để tinh chỉnh. Em báo cáo cả điểm tốt lẫn giới hạn, không đổi quy tắc theo kết quả.

**Hit được tính thế nào?** Đúng nguồn, trang PDF và đủ nguyên gold quote trong một chunk sau chuẩn hóa whitespace. Hit@1 xét hạng đầu; Hit@3 xét một trong ba. Metric này nghiêm ngặt hơn “có đoạn liên quan” và khác accuracy câu trả lời LLM.

**Vì sao C chưa cao hơn B?** Filter giới hạn phạm vi nhưng không chữa nội dung thiếu hoặc thứ hạng sai. Các câu trong mẫu vốn đã chỉ rõ chủ đề nên có thể không được lợi thêm. Không tạo chênh lệch giả để C trông tốt hơn.

**Coherence khác grounding thế nào?** Coherence xem chunk có đủ ý để hiểu độc lập không. Grounding xem top-3 có đủ bằng chứng trả lời một câu hỏi, gồm điều kiện cần thiết không. Nhãn có AI hỗ trợ được công khai; không suy ra từ cosine hay hit.

**Dẫn đúng trang có bảo đảm đáp án đúng không?** Không. Guard chỉ kiểm tra cặp trang hợp lệ và phản hồi hoàn tất. Khẳng định sai vẫn có thể dẫn đúng trang. Cần đọc nội dung và lưu ý lỗi trong sách.

**Lưu bền vững được chứng minh ra sao?** ID ổn định, upsert, xóa ID lỗi thời; nạp lại không tăng số chunk. Lệnh tái lập đối chiếu cả 75 danh sách top-3 và metric với lượt đầu.

**Cần thừa nhận giới hạn nào?** Test chỉ 10 câu, câu hỏi/nhãn có AI hỗ trợ trên cùng sách, chưa có người chấm độc lập, có thể lỗi trích bảng/code, metric exact-match và ledger chi phí lịch sử chưa đầy đủ. Phần giảng viên yêu cầu học viên tự chấm thủ công phải do em trực tiếp làm.
