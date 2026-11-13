"""Generate the English submission report from recorded ABC artifacts."""
from collections import Counter,defaultdict
import csv
import math
import statistics
from .project import ROOT,RESULTS,read_json,write_json,now


def main():
    lock=ROOT/'report/finalization.json'
    if lock.exists():
        from .project import digest
        final=read_json(lock)
        if digest(ROOT/final['report'])!=final['sha256']:
            raise ValueError('The finalized report has changed; review and re-finalize it before packaging.')
        print('Báo cáo đã được học viên chốt; giữ nguyên nội dung, không tạo lại.')
        return
    info=read_json(RESULTS/'ingestion.json');metrics=read_json(RESULTS/'metrics.json')
    plan=read_json(ROOT/'configs/english_plan.json');selection=read_json(RESULTS/'english_run/selection.json')
    audit=read_json(RESULTS/'qualitative_audit.json');traces=read_json(RESULTS/'traces.json')
    table='\n'.join(f"| {r['strategy']} | {r['split']} | {r['hit1_n']}/{r['n']} | {r['hit3_n']}/{r['n']} ({r['hit3']:.0%}) |" for r in metrics)
    resources=[];qual=[];summaries=[]
    for strategy in 'ABC':
        chunks=read_json(RESULTS/f'chunks_{"B" if strategy=="C" else strategy}.json')
        lengths=[len(c['text']) for c in chunks]
        resources.append(f"| {strategy} | {len(chunks)} | {min(lengths)} | {max(lengths)} | {statistics.mean(lengths):.1f} | {sum(lengths)} |")
        anchors=defaultdict(list)
        for row in audit['coherence']:
            if row['strategy']==strategy:anchors[(row['page'],row['anchor'])].append(row['score'])
        coherence=statistics.mean(statistics.mean(v) for v in anchors.values())
        ground=[r['score'] for r in audit['grounding'] if r['strategy']==strategy]
        counts=Counter(ground)
        md=[r for r in audit['metadata'] if r['strategy']==strategy]
        filtered=[r for r in traces if r['strategy']==strategy and r['split']=='test' and r['filter']]
        compliance=sum(len(r['hits'])==3 and all(h['metadata']['chapter']==r['filter']['chapter'] for h in r['hits']) for r in filtered)
        qual.append(f"| {strategy} | {coherence:.2f}/2 | {counts[0]}/{counts[1]}/{counts[2]} | {statistics.mean(ground):.2f}/2 | {sum(r['correct'] for r in md)}/{len(md)} | {compliance}/{len(filtered)} |")
        summaries.append({'strategy':strategy,'coherence_mean_per_anchor':coherence,'grounding_counts':dict(counts),'grounding_mean':statistics.mean(ground),'metadata_correct':sum(r['correct'] for r in md),'metadata_n':len(md),'chapter_compliance':compliance,'filtered_questions':len(filtered),'filter_applied':strategy=='C'})
    write_json(RESULTS/'audit_summary.json',{'at':now(),'assisted':summaries,'human_confirmed':False})
    profiles='\n'.join(f"| {p['size']} | "+' | '.join(f"{m['hit1_n']}/15; {m['hit3_n']}/15" for m in p['metrics'])+' |' for p in selection['profiles'])
    failures='\n'.join(f"- **{r['strategy']} / {r['question_id']}**: {r['question']} Gold PDF p.{r['gold_evidence'][0]['page']}; top-3 pages {[h['metadata']['page'] for h in r['hits']]}." for r in traces if r['split']=='test' and not r['hit3'])
    manual=read_json(RESULTS/'manual_audit.json')
    human_count=sum(r.get('correct' if group=='metadata' else 'score') is not None for group in ['coherence','grounding','metadata'] for r in manual[group])
    judge_usage=audit.get('usage',{})
    text=f'''# Báo cáo cá nhân — Data Ingestion Engineering

**Đinh Thị Hường · MSSV 2A202603569 · Lớp L3A**  
Báo cáo tổng hợp từ kết quả thực nghiệm; cập nhật {now()} (UTC, giờ Việt Nam UTC+7).

## 1. Mục tiêu và kết quả chính

Em xây dựng hệ thống truy xuất kiến thức từ hai chương Decisions và Loops của sách *Introduction to Python Programming* do OpenStax phát hành. Hệ thống gồm pipeline ingestion, kho vector Chroma, thí nghiệm A/B/C và chatbot GPT-5.4 có bằng chứng truy xuất. Vì tài liệu gốc bằng tiếng Anh, câu hỏi benchmark, đoạn bằng chứng và câu trả lời chatbot sử dụng tiếng Anh. Báo cáo này trình bày phương pháp và phân tích bằng tiếng Việt.

Em chọn **B trên tập dev**: Evidence Hit@3 đạt 13/15, so với 10/15 của A. Trên tập test 10 câu, cả A/B/C đạt **8/10 Hit@3**. Hit@1 test của A là 6/10, B/C là 5/10. Em giữ lựa chọn B theo quy tắc đã chốt trên dev, không đổi sang A sau khi xem test. Kết quả này không có nghĩa B luôn tốt nhất ở mọi chỉ số hoặc C luôn cải thiện truy xuất.

## 2. Dữ liệu, quyền sử dụng và xử lý

Corpus gồm **43 trang nội dung**: PDF 96–120 thuộc Decisions và 126–143 thuộc Loops. Số trang in trong sách bằng số trang PDF trừ 10. Không tính bìa/mục lục vào số trang nội dung. Manifest lưu URL nguồn, SHA-256 của PDF, danh sách trang và cách chọn dữ liệu. PDF gốc được giữ để đối chiếu với văn bản trích xuất.

Nguồn: OpenStax, Rice University. Trang PDF 4 ghi giấy phép **CC BY-NC-SA 4.0**. Ghi công: *Access for free at openstax.org*. `data/NOTICE.md` nêu quyền và thay đổi đối với dữ liệu dẫn xuất; không đánh đồng giấy phép sách với toàn bộ mã phần mềm.

Pipeline chuẩn hóa Unicode và khoảng trắng, giữ thụt lề của mã Python, đồng thời lưu document ID, URL, trang PDF, trang in và chương. Mỗi chunk có offset ký tự để đối chiếu chính xác với trang nguồn. Chỉ ở đầu vào embedding, em thêm tên chương/mục và bỏ URL, dòng video/footer gây nhiễu. **Đoạn bằng chứng trả cho người dùng vẫn là nguyên văn trích xuất**, không dùng văn bản đã diễn giải để giả làm nguồn.

Nguồn có lỗi, chẳng hạn cách viết lowercase true/false tại p96 và hệ số công thức Fahrenheit tại p104. Việc truy đúng nguồn không bảo đảm nguồn luôn đúng. Bảng, mã và định nghĩa vẫn có thể bị ngắt ở ranh giới trang PDF; hệ thống không tuyên bố đã xử lý được mọi trường hợp này.

## 3. Thiết kế ba cấu hình

| Cấu hình | Cách chia chunk | Giới hạn | Overlap | Filter |
|---|---|---|---|---|
| A | Cửa sổ ký tự cố định trong từng trang | 1.800 ký tự | 200 ký tự | Không |
| B | Theo ranh giới mục sách, sau đó ưu tiên câu/dòng | 1.800 ký tự | 0 | Không |
| C | Dùng đúng chunk và index của B | 1.800 ký tự | 0 | Chương do người dùng yêu cầu |

Cả ba dùng **text-embedding-3-small, 1.536 chiều**, cùng corpus, câu hỏi tiếng Anh, tiền xử lý embedding và cosine/HNSW trong Chroma. Mỗi câu lấy top-3. B–C chỉ thay một yếu tố là filter chương. A–B thay cả gói chunking gồm ranh giới và overlap; vì vậy không quy toàn bộ chênh lệch cho riêng ranh giới câu.

Kế hoạch thử kích thước **1.000, 1.400 và 1.800** được lưu trước khi chạy. Chọn kích thước chung theo tổng dev Hit@3 của A/B/C, sau đó tổng Hit@1, rồi ưu tiên kích thước nhỏ hơn nếu còn hòa. Trong cấu hình kích thước được chọn, chọn chiến lược theo dev Hit@3, Hit@1, số chunk thấp hơn và thứ tự chữ cái.

| Kích thước | A: Hit@1; Hit@3 | B: Hit@1; Hit@3 | C: Hit@1; Hit@3 |
|---|---|---|---|
{profiles}

Kết quả chọn **1.800 và B**, trước khi truy xuất test. Hash câu hỏi/mã và thời điểm kế hoạch nằm trong `configs/english_plan.json`; lựa chọn dev được lưu ở `results/english_run/selection.json`. `benchmark/freeze.json` là manifest chuẩn hóa khi đóng gói, được tạo sau thực nghiệm và dẫn tới các minh chứng đã khóa trước đó; không mô tả thời điểm đóng gói thành thời điểm đóng băng trước chạy.

## 4. Bộ câu hỏi và độ chính xác truy xuất

Có **25 câu tiếng Anh: 15 dev, 10 test**. Test chia đều hai chương và có bốn yêu cầu lọc chương. Mỗi câu chứa đáp án tham chiếu, source ID, trang PDF và gold quote. Gold quote đã được kiểm tra trong văn bản nguồn trước khi truy xuất test. Các câu dev đã biết được chuyển sang tiếng Anh để đồng bộ với sách; tập test được khóa trước lượt retrieval đầu tiên. Bộ câu hỏi có AI hỗ trợ tạo trên cùng sách và chọn có chủ đích, chưa phải benchmark độc lập do người ngoài xây dựng.

Một hit yêu cầu đúng document ID, đúng trang PDF và **toàn bộ gold quote nằm trong một chunk**, sau khi chuẩn hóa whitespace. Hit@1 xét hạng đầu; Evidence Hit@3 xét bất kỳ đoạn nào trong ba hạng đầu. Metric nghiêm ngặt này có thể bỏ sót bằng chứng tương đương về nghĩa hoặc bằng chứng bị chia giữa hai chunk. Em không sửa nhãn để tăng điểm sau khi xem test. Đây là độ chính xác truy xuất, không phải độ chính xác câu trả lời LLM.

| Cấu hình | Tập | Hit@1 | Evidence Hit@3 |
|---|---|---|---|
{table}

Test chỉ có 10 câu. Với 8/10, khoảng Wilson 95% xấp xỉ **49%–94%**, cho thấy độ bất định còn lớn; không suy rộng thành hiệu năng trên mọi câu hỏi. B/C bằng điểm trong mẫu này nên chưa có bằng chứng filter làm tăng accuracy. A có Hit@1 test cao hơn và kết quả đó được giữ nguyên trong phân tích.

| Cấu hình | Số chunk | Ký tự nhỏ nhất | Lớn nhất | Trung bình | Tổng ký tự |
|---|---|---|---|---|---|
{chr(10).join(resources)}

Toàn bộ **75 trace × top-3** lưu câu hỏi, gold, text, cosine, ID, metadata và nhãn hit. ID chunk ổn định; upsert và xóa ID lỗi thời tránh nhân đôi. Nạp lại cùng dữ liệu được kiểm tra giữ nguyên số chunk. C không tạo embedding tài liệu riêng vì chia sẻ B. Chạy tái lập ghi minh chứng riêng, không ghi đè kết quả test đầu tiên.

## 5. Tính mạch lạc, metadata và grounding

Phần này trình bày tiêu chí, mẫu đánh giá và kết quả. Nguồn gốc nhãn và phạm vi xác nhận được nêu tại mục 8.

Coherence dùng cùng mười vị trí nguồn cho mỗi cấu hình, phân tầng năm vị trí mỗi chương. Chấm mọi chunk phủ ký tự anchor; tính trung bình trong anchor rồi trung bình mười anchor để overlap không được tăng trọng số. Thang 0 = mảnh rời khó hiểu độc lập, 1 = hiểu một phần nhưng thiếu ngữ cảnh, 2 = đủ ý và sử dụng được. Grounding chấm cả mười câu test mỗi cấu hình dựa trên top-3 gộp lại: 0 = không liên quan, 1 = thiếu một phần, 2 = đủ bằng chứng/điều kiện và truy nguồn được. Không suy điểm này từ cosine hoặc exact-match hit.

Metadata được kiểm tra bằng mã: source ID/URL, chương, trang PDF/trang in và offset phải khớp bản ghi nguồn. Top-3 test tạo **90 lượt kiểm tra metadata**. Filter compliance đo trên bốn câu test có yêu cầu chương; A/B có thể tình cờ trả đúng chương dù không lọc.

| Cấu hình | Coherence /2 | Grounding số câu 0/1/2 | Grounding TB /2 | Metadata đúng | Đúng phạm vi chương |
|---|---|---|---|---|---|
{chr(10).join(qual)}

Nhãn và lý do từng mẫu nằm trong `results/qualitative_audit.json`; thống kê tổng hợp nằm trong `results/audit_summary.json`.

## 6. Phân tích lỗi và tác động chiến lược dữ liệu

Các trường hợp miss theo metric trên test được giữ lại, không tinh chỉnh sau test:

{failures}

Chunk lớn giữ được nhiều định nghĩa/bảng hơn nhưng tăng token và có thể trộn nhiều ý. B tôn trọng ranh giới mục nên tránh gộp nội dung từ hai mục khác nhau trong cùng chunk; vẫn chưa khắc phục ngắt trang. A có overlap giúp phủ ranh giới, đổi lại lặp nội dung. C giới hạn phạm vi chương theo yêu cầu nhưng không tạo thêm bằng chứng và không bảo đảm thay đổi thứ hạng theo hướng tốt hơn.

Dùng câu hỏi tiếng Anh đồng bộ với sách và thêm ngữ cảnh mục giúp giảm lệch ngôn ngữ, tăng tín hiệu chủ đề. Tuy nhiên kích thước, ranh giới và tiền xử lý chung được phát triển như một hệ thống; phép so sánh A/B/C không cô lập riêng đóng góp nhân quả của từng thay đổi tiền xử lý. Kết luận phù hợp là B thắng quy tắc chọn trên dev của corpus này, không phải B tốt nhất trong mọi tình huống.

## 7. Chatbot và kiểm tra nguồn

GPT-5.4 dùng các đoạn truy xuất làm bằng chứng; lịch sử hội thoại chỉ cung cấp ngữ cảnh. Prompt yêu cầu trả lời tiếng Anh, giữ thụt lề mã, bỏ qua chỉ dẫn nằm trong tài liệu và không khẳng định khi thiếu bằng chứng. Trích dẫn theo mẫu `[PDF p.N; printed p.M]`. Mã kiểm tra phản hồi đã hoàn tất và cặp trang trích dẫn thuộc evidence. Phản hồi không đạt được thay bằng thông báo rõ ràng. Kiểm tra này có thể từ chối đáp án đúng nhưng sai định dạng, và **không chứng minh mọi mệnh đề được nguồn hỗ trợ**.

Link mỗi đoạn top-3 dẫn đúng mục *View online* của OpenStax dựa trên offset; nếu chunk chạm hai mục thì hiện cả hai link. Có thể tải PDF gốc để đối chiếu. Cosine không được trình bày như xác suất đáp án đúng. Khi chưa có index, ô chat tạm khóa nhưng vẫn xem được kết quả đã lưu. Lượt gọi GPT-5.4 thật và token nằm trong `results/chat_demo.json`.

## 8. Tái lập, chi phí và sử dụng AI

Lệnh `python -m starter.src.run all` dựng lại index đã chọn và đối chiếu 75 trace. `python -m streamlit run app.py` mở giao diện. `python -m unittest discover -s tests -v` chạy kiểm thử. `python starter/scripts/verify_submission.py` kiểm tra hash, gold, offset, nguồn và metric mà không gọi API. Các thư viện trực tiếp được ghim phiên bản; dependency bắc cầu chưa được khóa toàn bộ. Kiểm tra ZIP trong thư mục tách riêng sử dụng môi trường Python hiện có, không được mô tả thành đã thử trên máy mới hoàn toàn.

OpenAI nhận nội dung câu hỏi/đoạn sách và có tính phí. Key nằm trong `.env`, bị loại khỏi ZIP. Log request/stage ghi usage và cache; cache không tạo phí embedding mới. Ledger chưa bao phủ đầy đủ các request đầu tiên trước khi bổ sung log chi tiết, nên không coi là hóa đơn lịch sử đầy đủ. Giá tham chiếu để ước tính: embedding $0.02/triệu input token; GPT-5.4 $2.50/triệu input và $15/triệu output token, chưa tính giảm giá cached input. Cần đối chiếu giá hiện hành/hóa đơn tài khoản. Đánh giá định tính ghi {judge_usage.get('input_tokens',0)} input và {judge_usage.get('output_tokens',0)} output token. Chi phí thử nhiều profile/chấm định tính khác với chi phí chỉ tái dựng index đã chọn bằng cache.

Em sử dụng Codex hỗ trợ viết mã, xây dựng câu hỏi, kiểm tra nguồn, phân tích và soạn thảo. GPT-5.4 sinh câu trả lời demo và hỗ trợ chấm coherence/grounding ở mục 5; metadata được kiểm tra bằng mã. Model đánh giá cùng họ với chatbot nên có nguy cơ thiên lệch. Hiện có **{human_count}** nhãn do người đọc trực tiếp xác nhận; các nhãn hỗ trợ chưa phải phần học viên tự chấm thủ công hoặc được người độc lập xác nhận. Nếu giảng viên yêu cầu học viên tự chấm, bộ nhãn này không thay thế yêu cầu đó. Nhãn của người đọc được lưu riêng tại `results/manual_audit.json`. Em cần hiểu và giải thích được mã nguồn khi trình bày. Bài đứng tên Đinh Thị Hường, giữ rõ nguồn dữ liệu, công cụ và giới hạn thực nghiệm.

Tài liệu tham khảo: https://developers.openai.com/api/docs/guides/embeddings ; https://developers.openai.com/api/docs/guides/text ; https://developers.openai.com/api/docs/models/gpt-5.4 ; giấy phép và nguồn OpenStax trong manifest.
'''
    (ROOT/'report/individual/2A202603569_DinhThiHuong.md').write_text(text,encoding='utf-8')
    with (ROOT/'artifacts/experiment_log.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['strategy','method','size','overlap','filter','model','hypothesis','dev_hit1','dev_hit3','test_hit1','test_hit3']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for s in 'ABC':
            dev=next(m for m in metrics if m['strategy']==s and m['split']=='dev');test=next(m for m in metrics if m['strategy']==s and m['split']=='test')
            w.writerow({'strategy':s,'method':'fixed' if s=='A' else 'section_sentence','size':1800,'overlap':200 if s=='A' else 0,'filter':'requested chapter' if s=='C' else 'none','model':info['model'],'hypothesis':{'A':'Overlap preserves evidence near boundaries','B':'Section boundaries preserve coherent context','C':'Chapter scope may reduce off-topic retrieval'}[s],'dev_hit1':dev['hit1'],'dev_hit3':dev['hit3'],'test_hit1':test['hit1'],'test_hit3':test['hit3']})
    print('Đã tạo báo cáo tiếng Việt và nhật ký từ kết quả A/B/C thực tế.')


if __name__=='__main__':main()
