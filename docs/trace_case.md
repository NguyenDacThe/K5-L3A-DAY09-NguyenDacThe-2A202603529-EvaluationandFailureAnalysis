# Trace case: từ trace tới quyết định sai đầu tiên

## Case đã kiểm chứng

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`; run ID `R-seeded_regression-C-002-s11`. |
| Triệu chứng | Grader Lab08 FAIL: status resolved khác denied; proposal 20.000, ledger 1 refund 20.000 và 1 audit committed; label yêu cầu denied/0. Reply cũng báo đã hoàn 20.000. |
| Bước sai đầu tiên | Event **3**, kind `model_override`, payload `{"delay_days": 5}`. |
| Vì sao là bước đầu tiên | Event 1 handoff chỉ cấp tool đọc; event 2 investigator trả order O-202 với delay_days=2, phí ship 20.000 và policy hiện hành. Event 3 thay số ngày bằng 5 từ ticket; event 4 mới quote sai 20.000. |
| Failure mode | **FM-03 ticket_trust**, xem [taxonomy](failure_taxonomy.md). |
| Đối chứng | `fixed C-002@11`, run ID `R-fixed-C-002-s11`: DB vẫn delay=2, không model_override; event 3 quote=0/no_entitlement, event 4 reply từ chối, ledger 0 và evaluator PASS. |
| Regression test | [test_lab9_trace_case.py](../src/tests/test_lab9_trace_case.py), hàm `test_lab9_ticket_override_is_rejected_and_fixed_is_accepted`; mutant phải bị loại, fixed phải được nhận. |
| Chưa chắc chắn | MockLLM và variant được gài lỗi không chứng minh model thật suy luận như vậy. Seeded_regression có nhiều công tắc lỗi, nhưng history C-002 là 0 và host chấp nhận, nên chưa có bằng chứng pre_deducted/ignore_denied gây lỗi ở trial này. Variant v2 có thể không để lại event override. |

## Diễn tiến so với ledger

1. Handoff chưa cấp quyền ghi tiền cho investigator.
2. Order có 2 ngày trễ, chưa đạt ngưỡng 3 ngày.
3. Variant đổi thành 5 ngày: dữ kiện sai đầu tiên quan sát được.
4. Quote ship 20.000 từ order đã bị đổi.
5. Refund history bằng 0, không có khoản cũ để giải thích sai lệch.
6. Reply xác nhận hoàn, snapshot xác nhận tiền thật đã ghi: không chỉ là câu chữ sai.

Host vẫn kiểm ownership, approval và cap; host không tự xác minh lại entitlement từ order. Approval hợp lệ không bảo đảm quote do shape đưa vào đúng luật.

## Lệnh tái lập

Chạy trong `src/`:

```powershell
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -B -m tests.run_m1_evidence
python -B -m pytest -q -m student -o addopts= tests/test_lab9_trace_case.py -p no:cacheprovider
```

Regression test đã chạy: **2 passed**. Suite được kỳ vọng xanh vì nó xác nhận mutant bị loại và fixed đúng; không sửa assertion để mutant trở thành đúng. Lệnh điều tra trace_case trả exit 0 kể cả trial FAIL; cần đọc verdict, không coi exit code đó là điểm pass.

Bằng chứng số trong `reports/m1_trace_evidence.json`, mục trace_case; trace raw ở `traces/` không commit. Không thêm item trùng C-002 vào eval set v1: claim này đã có item, M1 đã gắn FM-03 và provenance vào item hiện có. Regression test là sản phẩm mới của M1, không sửa Lab08, variant chính thức hoặc nhãn gốc.

## Liên kết với eval set M1

C-002 là item E-002 trong eval_set_v1.jsonl, đã được gắn FM-01 và FM-03. Provenance.trace_refs có traces/R-m1_cov_ticket_trust-C-002-s11.json. Item vẫn duy nhất, nhãn gốc giữ trong labels_v1.json. Build/check đã hoàn thành với 0 problem(s); bộ test M1 tổng hợp đạt 8 passed.
