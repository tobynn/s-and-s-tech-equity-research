# [가정에서 주당가치까지]

현재 모델은 [Equity_Research_Model.xlsx](Equity_Research_Model.xlsx)입니다.

`Inputs!D3`에서 Bear·Base·Bull을 선택합니다. Forecast·Cash Equity Bridge·DCF·RIM·PER·Summary가 같은 입력을 사용합니다. Actuals Sources는 공시 실제치와 출처입니다.

- [전체 보고서와 가정 설명](../report/FINAL_REPORT.md)
- [독립 계산 결과](research_results.json)
- [3개 시나리오 Excel 대조 결과](model_validation.json)
- [이전 모델 원본](../archive/pre-v2/model/)

DCF는 2026년 말 평가이며 2027~2031 FCFF를 할인합니다. RIM은 2026E 말 지배주주 자본에서 시작합니다. PER는 정상화 EPS와 이론 배수를 곱하며 관측 peer 평균 배수로 표시하지 않습니다.

## [v3 가정 심화]

Diagnostics는 장기 재투자·현금 분리·가격 역산·단일 가정 비용 충격을 계산합니다. Special Cases는 기업 고유 자본거래 또는 사업 조건의 민감도입니다. 모두 `Inputs!D3`의 동일 시나리오를 따릅니다. `Inputs` 60행 이후 파란 입력은 공통 스트레스·기업별 조건입니다. 이 값이 Base 전망을 자동으로 대체하지 않습니다.

[심화 결과 CSV](valuation_review.csv) · [검토 메모](../research/ASSUMPTION_REVIEW.md)
