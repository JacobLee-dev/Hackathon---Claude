# 마케팅 성과 인사이트 리포트 자동 생성기 — DA 공통 [09]

마케팅 성과 CSV(8주 · 5채널 · 일별)를 **경영진이 추가 분석 없이 예산을 옮길 수 있는 의사결정 리포트**로 자동 전환한다.
설계 원칙은 하나다 — **계산은 Python(pandas)이 전담해 오류를 없애고, 해석은 Claude가 담당한다.** 
(목표 레벨: Basic + Standard + Challenge 전부 충족.)

## 핵심 결과

| 지표 | 값 |
|------|-----|
| 총 지출 (유료 광고비) | 50,683,819원 |
| 총 매출 (전 채널) | 439,553,059원 |
| 전체 ROI (매출/광고비) | 867.2% (ROAS 8.67배) |
| 총 전환수 | 22,694건 |
| 채널 ROI 순위 | 이메일 1,042% → 네이버 659% → 카카오 343% → 메타 259% (오가닉 측정 불가) |

정제: raw 280행 → 완전 중복 1행 제거(279) → 이메일 매출 이상치 1건 제외(278) → 집계. 결측 3건 NaN 유지. 오가닉 광고비 0원이라 ROI/ROAS 측정 불가 표기.

## 폴더 구조

```
.
├── insight_report.md              # 메인 산출물 (Challenge 보강판: 시나리오 레인지 + 액션 KPI)
├── insight_report_스크립트출력.md  # 스크립트 원본 출력 (재현 증거)
├── 기획안.md                       # 접근 전략 A to Z + 근거 출처
├── decisions.md                   # 중복·결측·이상치·오가닉 처리 기준 로그
├── metrics.json                   # pandas 계산 결과 (모든 수치의 단일 출처)
├── data/
│   └── marketing_performance.csv  # 입력 데이터 (280행)
├── scripts/
│   └── generate_insight_report.py # 재현 파이프라인
└── web/
    ├── 리포트-디자인1-대시보드.html   # 인터랙티브 (탭 + 지표 스위처 + 예측 차트)
    └── 리포트-디자인2-주최양식.html   # 주최 제출 양식 그대로
```

## 읽는 순서

1. **`insight_report.md`** — 메인. 문제정의 → 핵심수치 → 채널 ROI 순위 → 이슈 3가지 → W7→W8 변화율 → 예산 재배분 기획안 → 기대효과 시나리오
2. `기획안.md` — 접근 전략과 근거 출처
3. `decisions.md` — 데이터 처리 의사결정
4. `scripts/generate_insight_report.py` + `metrics.json` — 재현 파이프라인
5. `web/*.html` — 브라우저로 열어보는 시각화 (2종)

> HTML은 **브라우저(Chrome/Edge)로 열어야** 렌더된다. 파일 탐색기 → 우클릭 → 연결 프로그램. 디자인1의 탭·차트 인터랙션도 브라우저에서만 작동.

## 재현 방법 (Standard)

```bash
# 기본 CSV로 리포트 재생성
python scripts/generate_insight_report.py

# 다른 CSV 지정 (동일 컬럼 구조)
python scripts/generate_insight_report.py --csv 경로.csv
```

→ `output/insight_report.md` + `output/metrics.json` 재생성. 필요: `pandas`.

## 채점 기준 매핑

| 레벨 | 충족 |
|---|---|
| 🟢 Basic (100) | `insight_report.md` — 핵심수치 · ROI 순위 · 이슈 3 · 변화율 |
| 🟡 Standard (+30) | `scripts/generate_insight_report.py` + `metrics.json` 재현 + 리포트 [Standard] 설계 근거 |
| 🔴 Challenge (+30) | 리포트 [Challenge] 재배분 기획안 P0/P1 + 시나리오 레인지 + 액션 KPI 표 + `기획안.md` |

## 계산 검증

모든 합계·ROI·변화율·기대효과는 pandas 계산값이며 수기 추정이 없다. Claude는 계산 완료된 수치의 해석만 담당한다. `metrics.json`이 모든 수치의 단일 출처(single source of truth)다.

---

*계산: Python pandas · 해석: Claude Code · 데이터: 280행 (8주 × 5채널 × 7일)*
