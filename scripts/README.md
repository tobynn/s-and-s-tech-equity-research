# [재생성]

```bash
python scripts/rebuild_research.py
node scripts/build_model.mjs /path/to/repository
python scripts/build_report_pdf.py
```

Python 본문·CSV 계산은 표준 라이브러리를 씁니다. PDF는 reportlab과 Nanum Gothic을 사용하며 폰트가 없으면 Google Fonts 원본을 캐시에 받습니다. Excel 생성은 `@oai/artifact-tool` 설치 환경이 필요합니다. 일반 독자는 저장된 Excel에서 시나리오를 바꿀 수 있습니다.

이전 `run_valuation.py`, `src/valuation.py`, `build_models.mjs` 등은 과거 모델입니다. 현재 재생성에는 위 세 스크립트만 사용합니다.
