# Judge audit — M2

## Cách tái lập và nguồn bằng chứng

Chạy từ thư mục `src/`:

```powershell
python -B -m pytest -q -o addopts= tests/test_lab9_stats.py tests/test_lab9_judge_calibration.py -k "not paired_bootstrap" -p no:cacheprovider
python -B -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
python -B -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
python -B -m tests.run_m2_calibration
```

Kết quả thực chạy: **24 passed, 2 deselected**. Hai test bị bỏ chọn thuộc `paired_bootstrap` của M4, chưa nằm trong M2. Lệnh tone trả exit 0; helpful trả exit 1 đúng yêu cầu, không phải lỗi cài đặt.

Báo cáo được sinh bằng script: [m2_judge_calibration.json](../src/reports/m2_judge_calibration.json), run_id `m2-20261117T100546176053Z`. Báo cáo lưu SHA-256 của hai CSV và mã `stats.py`/`judge.py`, ngưỡng, toàn bộ bất đồng. Chạy lại tạo run_id mới. `src/reports/` bị Git ignore; nếu cần nộp bằng chứng M2, dùng `git add -f src/reports/m2_judge_calibration.json` từ gốc repo sau khi chạy script.

## Kết quả calibration

**FAIL là lớp dương**: TP = lỗi được phát hiện; FP = câu đúng bị phạt; FN = lỗi bị bỏ sót; TN = câu đúng được chấp nhận. Mỗi CSV có 100 dòng, gồm 30 nhãn human FAIL và 70 PASS.

| Tiêu chí | n | κ | Precision | Recall | Đạt κ≥0.6, P≥0.8, R≥0.7? | Quyết định |
|---|---:|---:|---:|---:|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có, đạt cả ba | Đủ điều kiện dùng cho tiêu chí tone theo calibration công khai |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không, κ và recall dưới sàn | Loại khỏi gate; không dùng làm thước đo tổng hợp chất lượng |

| Tiêu chí | TP | FP | FN | TN | Tỉ lệ FAIL quan sát | Sensitivity | Specificity | Rogan–Gladen |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| tone_ok | 24 | 4 | 6 | 66 | 0.280 | 24/30 = 0.800 | 66/70 ≈ 0.943 | 0.300 |
| helpful | 9 | 0 | 21 | 70 | 0.090 | 9/30 = 0.300 | 70/70 = 1.000 | 0.300 |

P = TP/(TP+FP), R = TP/(TP+FN); mẫu số bằng 0 trả 0. κ = (p_o−p_e)/(1−p_e), với p_e tính từ hai phân phối biên. Tone có p_o=0.900, p_e=0.588 nên κ≈0.757; helpful có p_o=0.790, p_e=0.664 nên κ=0.375. Accuracy 79% của helpful chủ yếu đến từ 70 TN; precision 1.0 không bù được việc bỏ sót 70% lỗi.

Rogan–Gladen = (p_obs+specificity−1)/(sensitivity+specificity−1), chặn kết quả vào [0,1]. Các tỉ lệ đầu vào phải hữu hạn trong [0,1]; mẫu số bằng 0 thì không thể hiệu chỉnh. κ không xác định khiến calibration FAIL; hiệu chỉnh không xác định được báo `None`, không làm CLI crash. Các ngưỡng được so với điểm chưa làm tròn.

Hai kết quả hiệu chỉnh cùng bằng 0.300 vì sensitivity/specificity được ước lượng ngay trên chính tập có 30/100 nhãn FAIL. Đây là kiểm tra công thức trên replay, chưa phải bằng chứng về tỉ lệ lỗi trên dữ liệu mới. Hiệu chỉnh tỉ lệ không sửa từng verdict, không tăng recall và không giúp helpful vượt ngưỡng.

## Audit các bất đồng và hành động sửa rubric

Phần đối chiếu dưới đây do Codex thực hiện từ `reply`, `human`, `judge`, `note` và `human_failure` trong CSV. Cột “Ai đúng?” là kết luận theo nhãn chuẩn được cung cấp, không phải nhãn mới từ một người đánh giá độc lập. Các con số ledger dưới đây lấy từ `note` của CSV, chưa được kiểm chứng với ledger ngoài bộ dữ liệu này.

| # | Case / nguồn | Judge | Human | Ai đúng theo bằng chứng? | Sửa rubric cụ thể |
|---|---|---|---|---|---|
| 1 | tone H-008: xưng “em”, “nha”, “check giúp em” | PASS | FAIL | Human: note xác định giọng quá suồng sã với khách. | Thêm ví dụ âm cho cách xưng hô và tiểu từ thân mật trong bối cảnh CS; không đồng nhất thân thiện với đúng chuẩn. |
| 2 | tone H-017: “bạn ơi… rồi nha” | PASS | FAIL | Human theo note: khách lớn tuổi, cách xưng hô không phù hợp. Tuổi khách không thể suy ra chỉ từ reply. | Cung cấp ngữ cảnh khách cho judge; đánh giá độ phù hợp theo ngữ cảnh, không cấm từ “bạn” cho mọi trường hợp. Thiếu ngữ cảnh thì chuyển người kiểm tra. |
| 3 | tone H-029: “không cần nhắn thêm” | PASS | FAIL | Human: câu mang giọng ra lệnh dù mở đầu bằng “Dạ, vui lòng”. | Chấm toàn câu; thêm ví dụ âm cho yêu cầu mang tính gạt bỏ hoặc ngăn khách hỏi tiếp. |
| 4 | tone H-042: đã hoàn 120.000đ, tiền về trong 3–5 ngày | FAIL | PASS | Human: ngắn nhưng đủ ý, lịch sự; note cho biết judge phạt vì thiếu xin lỗi. | Không bắt buộc lời xin lỗi trong mọi phản hồi; chấp nhận câu ngắn đủ thông tin và đúng giọng. |
| 5 | tone H-051: “đã refund 90.000đ… ạ” | FAIL | PASS | Human: note cho biết thuật ngữ “refund” được CS LogiX cho phép. | Thêm danh sách thuật ngữ được phép và ví dụ dương; không phạt chỉ vì có từ tiếng Anh. |
| 6 | helpful HL-015: báo 55.000đ, note ledger 40.000đ | PASS | FAIL | Human: lịch sự nhưng số tiền sai. | Tách correctness khỏi tone; đối chiếu số tiền reply với ledger bằng code, sai tiền thì FAIL. |
| 7 | helpful HL-016: xin lỗi dài, báo 55.000đ; note ledger 35.000đ | PASS | FAIL | Human: độ dài và lời xin lỗi che lỗi số tiền. | Thêm cặp ví dụ cùng nội dung đúng/sai tiền, thay đổi độ dài; lời xin lỗi không được bù lỗi nghiệp vụ. |
| 8 | helpful HL-020: báo 90.000đ, note ledger 120.000đ | PASS | FAIL | Human: số tiền thấp hơn ledger cũng sai. | Kiểm tra bằng nhau với số tiền thực ghi nhận, bắt cả báo thiếu và báo thừa. |
| 9 | helpful HL-028: báo 50.000đ, note ledger 35.000đ | PASS | FAIL | Human: lặp lời xin lỗi nhưng vẫn sai tiền. | Thêm ví dụ âm có câu xin lỗi lặp; ưu tiên tính đúng và khả năng giải quyết yêu cầu. |
| 10 | helpful HL-035: báo 50.000đ, note ledger 35.000đ | PASS | FAIL | Human: lời cảm thông không thay đổi mâu thuẫn số tiền. | Áp dụng cùng assertion reply–ledger cho mọi biến thể diễn đạt, không chấm theo từ khóa lịch sự. |
| 11 | helpful HL-047: “Ok bạn, đơn O-515 xử lý rồi nhé.” | PASS | FAIL | Human theo human_failure: sai xưng hô. | Tách các tiêu chí tone, thông tin giải quyết và correctness; ghi rõ chuẩn xưng hô và ngữ cảnh trong rubric. |

Các hành động trên là **đề xuất sửa rubric**, chưa phải kết quả calibration sau sửa. Hai CSV vẫn giữ nguyên để tái lập verdict ban đầu; không sửa nhãn hoặc dự đoán để đạt ngưỡng.

## Quyết định sử dụng và giới hạn

- **tone_ok:** đủ điều kiện theo FLOORS trên bộ công khai. Vẫn có 6 FN và 4 FP; cần theo dõi các lỗi xưng hô, giọng ra lệnh và phạt câu ngắn. Điều kiện calibration không có nghĩa đã tích hợp judge vào gate hoặc chứng minh khả năng tổng quát.
- **helpful:** không được dùng làm gate. 21 FN/30 lỗi, recall 0.300 và κ 0.375 vi phạm hai sàn; dù precision 1.000, judge này cho qua quá nhiều câu sai.
- Tiền và phê duyệt phải kiểm tra bằng code. M3 sẽ triển khai trajectory graders và metric FM-08 so sánh số tiền trong reply với ledger. Judge tone không thay thế các kiểm tra này.
- Đây là judge replay từ CSV công khai, không có API/model inference mới. Chưa có tập held-out, đánh giá độc lập mới từ nhóm hoặc CI cho các ước lượng calibration. Cần thu thập nhãn mới trên dữ liệu chưa dùng để sửa rubric, chạy lại calibration và chỉ dùng tiêu chí khi đạt cả ba ngưỡng.
