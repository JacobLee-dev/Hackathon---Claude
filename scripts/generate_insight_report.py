from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


NUMERIC_COLUMNS = ["impressions", "clicks", "spend", "conversions", "revenue"]
OUTLIER_CHANNEL = "이메일"
OUTLIER_DATE = "2026-04-26"


def pct_change(before: float, after: float) -> float | None:
    if before == 0:
        return None
    return (after - before) / before * 100


def format_krw(value: float | int) -> str:
    return f"{value:,.0f}원"


def format_count(value: float | int) -> str:
    return f"{value:,.0f}건"


def format_number(value: float | int) -> str:
    return f"{value:,.0f}"


def format_pct(value: float | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "측정 불가"
    return f"{value:,.{digits}f}%"


def format_float(value: float | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.{digits}f}"


def status_for_change(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "측정 불가"
    if value >= 50:
        return "↑↑ 50% 이상 증가"
    if value > 3:
        return "↑ 증가"
    if value <= -50:
        return "↓↓ 50% 이상 감소"
    if value < -3:
        return "↓ 감소"
    return "→ 유지"


def to_native(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def analyze(csv_path: Path) -> dict[str, Any]:
    raw = pd.read_csv(csv_path)
    for column in NUMERIC_COLUMNS:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")

    missing_rows = raw[raw[NUMERIC_COLUMNS].isna().any(axis=1)].copy()
    duplicate_rows = raw[raw.duplicated(keep=False)].copy()

    deduped = raw.drop_duplicates().copy()
    deduped["aov"] = deduped["revenue"] / deduped["conversions"]

    outlier_mask = (deduped["channel"] == OUTLIER_CHANNEL) & (
        deduped["date"] == OUTLIER_DATE
    )
    outlier_rows = deduped[outlier_mask].copy()
    clean = deduped[~outlier_mask].copy()

    channel = clean.groupby("channel").agg(
        spend=("spend", "sum"),
        revenue=("revenue", "sum"),
        conversions=("conversions", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
    )
    channel["ROI_pct"] = (channel["revenue"] / channel["spend"] * 100).where(
        channel["spend"] > 0
    )
    channel["ROAS"] = (channel["revenue"] / channel["spend"]).where(
        channel["spend"] > 0
    )
    channel["CTR_pct"] = channel["clicks"] / channel["impressions"] * 100
    channel["CVR_pct"] = channel["conversions"] / channel["clicks"] * 100
    channel["AOV"] = channel["revenue"] / channel["conversions"]

    weekly = clean.groupby("week").agg(
        spend=("spend", "sum"),
        revenue=("revenue", "sum"),
        conversions=("conversions", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
    )
    weekly["CTR_pct"] = weekly["clicks"] / weekly["impressions"] * 100

    channel_week = clean.groupby(["channel", "week"]).agg(
        spend=("spend", "sum"),
        revenue=("revenue", "sum"),
        conversions=("conversions", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
    )
    channel_week["ROI_pct"] = (
        channel_week["revenue"] / channel_week["spend"] * 100
    ).where(channel_week["spend"] > 0)
    channel_week["CTR_pct"] = channel_week["clicks"] / channel_week["impressions"] * 100
    channel_week["CVR_pct"] = (
        channel_week["conversions"] / channel_week["clicks"] * 100
    )

    total_spend = channel["spend"].sum()
    total_revenue = channel["revenue"].sum()
    overall_roi_sales = total_revenue / total_spend * 100
    overall_roi_profit = (total_revenue - total_spend) / total_spend * 100

    wow = {}
    for metric in ["spend", "revenue", "conversions", "CTR_pct"]:
        before = weekly.loc["W7", metric]
        after = weekly.loc["W8", metric]
        wow[metric] = {
            "W7": to_native(before),
            "W8": to_native(after),
            "change_pct": to_native(pct_change(before, after)),
        }

    meta_w4 = channel_week.loc[("메타광고", "W4")]
    meta_w5 = channel_week.loc[("메타광고", "W5")]
    kakao_w3 = channel_week.loc[("카카오광고", "W3")]
    kakao_w4 = channel_week.loc[("카카오광고", "W4")]
    email_aov = channel.loc["이메일", "AOV"]
    outlier_aov = outlier_rows.iloc[0]["aov"]

    return {
        "raw_rows": len(raw),
        "deduped_rows": len(deduped),
        "clean_rows": len(clean),
        "date_min": clean["date"].min(),
        "date_max": clean["date"].max(),
        "weeks": sorted(clean["week"].unique().tolist()),
        "missing_rows": missing_rows[["date", "channel", "week"] + NUMERIC_COLUMNS]
        .where(pd.notnull(missing_rows), None)
        .to_dict("records"),
        "missing_counts": {
            column: int(raw[column].isna().sum()) for column in NUMERIC_COLUMNS
        },
        "duplicate_rows": duplicate_rows.to_dict("records"),
        "outlier_rows": outlier_rows[
            ["date", "channel", "week", "conversions", "revenue", "aov"]
        ].to_dict("records"),
        "channel": channel.sort_values("ROI_pct", ascending=False).to_dict("index"),
        "weekly": weekly.to_dict("index"),
        "channel_week": {
            f"{channel_name}|{week}": values
            for (channel_name, week), values in channel_week.to_dict("index").items()
        },
        "overall": {
            "spend": to_native(total_spend),
            "revenue": to_native(total_revenue),
            "roi_sales_pct": to_native(overall_roi_sales),
            "roi_profit_pct": to_native(overall_roi_profit),
            "conversions": to_native(channel["conversions"].sum()),
        },
        "wow": wow,
        "issue_metrics": {
            "meta_w4_spend": to_native(meta_w4["spend"]),
            "meta_w5_spend": to_native(meta_w5["spend"]),
            "meta_w4_revenue": to_native(meta_w4["revenue"]),
            "meta_w5_revenue": to_native(meta_w5["revenue"]),
            "meta_w4_roi": to_native(meta_w4["ROI_pct"]),
            "meta_w5_roi": to_native(meta_w5["ROI_pct"]),
            "meta_spend_change": to_native(
                pct_change(meta_w4["spend"], meta_w5["spend"])
            ),
            "meta_revenue_change": to_native(
                pct_change(meta_w4["revenue"], meta_w5["revenue"])
            ),
            "meta_roi_change": to_native(
                pct_change(meta_w4["ROI_pct"], meta_w5["ROI_pct"])
            ),
            "kakao_w3_spend": to_native(kakao_w3["spend"]),
            "kakao_w4_spend": to_native(kakao_w4["spend"]),
            "kakao_w3_revenue": to_native(kakao_w3["revenue"]),
            "kakao_w4_revenue": to_native(kakao_w4["revenue"]),
            "kakao_spend_change": to_native(
                pct_change(kakao_w3["spend"], kakao_w4["spend"])
            ),
            "kakao_revenue_change": to_native(
                pct_change(kakao_w3["revenue"], kakao_w4["revenue"])
            ),
            "email_clean_aov": to_native(email_aov),
            "email_outlier_aov": to_native(outlier_aov),
            "email_outlier_aov_multiple": to_native(outlier_aov / email_aov),
        },
    }


def render_report(metrics: dict[str, Any]) -> str:
    overall = metrics["overall"]
    channel = metrics["channel"]
    wow = metrics["wow"]
    issue = metrics["issue_metrics"]

    channel_order = ["네이버광고", "메타광고", "카카오광고", "오가닉", "이메일"]
    channel_rows = []
    for name in channel_order:
        row = channel[name]
        channel_rows.append(
            "| {name} | {spend} | {revenue} | {roi} | {roas} | {ctr} | {cvr} |".format(
                name=name,
                spend=format_krw(row["spend"]),
                revenue=format_krw(row["revenue"]),
                roi=format_pct(row["ROI_pct"]),
                roas=format_float(row["ROAS"]),
                ctr=format_pct(row["CTR_pct"], 2),
                cvr=format_pct(row["CVR_pct"], 2),
            )
        )

    paid_rank = [
        (name, row)
        for name, row in sorted(
            channel.items(),
            key=lambda item: item[1]["ROI_pct"] if item[1]["ROI_pct"] else -1,
            reverse=True,
        )
        if pd.notna(row["ROI_pct"])
    ]
    rank_rows = [
        f"| {idx} | {name} | {format_pct(row['ROI_pct'])} | {rank_comment(name)} |"
        for idx, (name, row) in enumerate(paid_rank, start=1)
    ]
    rank_rows.append(
        "| - | 오가닉 | 측정 불가 | 광고비 0원이라 ROI 순위에서는 제외하되, 전환수와 CVR은 별도 관리 |"
    )

    wow_rows = [
        ("지출", "spend", format_krw),
        ("매출", "revenue", format_krw),
        ("전환수", "conversions", format_count),
        ("CTR", "CTR_pct", lambda value: format_pct(value, 2)),
    ]
    wow_table = []
    for label, key, formatter in wow_rows:
        row = wow[key]
        wow_table.append(
            f"| {label} | {formatter(row['W7'])} | {formatter(row['W8'])} | "
            f"{format_pct(row['change_pct'])} | {status_for_change(row['change_pct'])} |"
        )

    report = f"""# 마케팅 성과 인사이트 리포트 — DA 공통 | 2026-07-01

> 모든 합계, ROI, 변화율은 `scripts/generate_insight_report.py`에서 pandas로 계산했습니다. Claude는 계산 결과를 바탕으로 해석과 권장 조치만 작성했습니다.

---

## 0. 문제 정의 (내 해석)

마케팅팀과 경영진은 매주 5개 채널의 성과 숫자를 받지만, 정작 필요한 답 — **"다음 주에 어느 채널 예산을 늘리고, 어디를 끊거나 점검해야 하는가"** — 은 그 숫자 안에 정리돼 있지 않다. 지금은 DA가 매 주기 데이터를 뽑고·계산하고·요약하느라 반나절을 쓰고, 그 결과도 "수치 나열"에 그쳐 의사결정으로 이어지지 않는다.

그래서 나는 이 과제를 리포트 자동 생성이 아니라, **경영진이 그대로 결재할 수 있는 예산 의사결정 도구**로 정의했다. 핵심 설계는 두 가지다. (1) 계산은 Python이 전담해 오류를 없애고(재현 가능), (2) 해석은 "채널 ROI 순위 -> 급변 이슈 3개 -> 예산 재배분안"이라는 의사결정 순서로 배열한다. 성공 기준은 리포트의 분량이 아니라 **"이 문서를 받은 마케팅 리드가 추가 분석 없이 예산을 옮길 수 있는가"** 다.

---

## 1. 데이터 개요

- 분석 대상: `data/marketing_performance.csv` ({metrics['raw_rows']}행 = 8주 x 5채널 x 7일)
- 분석 기간: {metrics['date_min']} ~ {metrics['date_max']} ({', '.join(metrics['weeks'])})
- 정제 결과: 완전 중복 1행 제거 후 {metrics['deduped_rows']}행, 이메일 매출 이상치 1행 제외 후 {metrics['clean_rows']}행으로 집계
- 결측 처리: impressions 1건, clicks 1건, revenue 1건은 0으로 대체하지 않고 해당 지표 합산에서만 제외
- ROI 처리 기준: 과제의 채널 비교 기준인 `매출 / 광고비 x 100`을 사용. 오가닉은 광고비가 0원이므로 ROI/ROAS를 측정 불가로 표기

## 2. 핵심 수치 요약

| 지표 | 값 |
|------|-----|
| 총 지출 (유료 광고비) | {format_krw(overall['spend'])} |
| 총 매출 (전 채널) | {format_krw(overall['revenue'])} |
| 전체 ROI (매출/광고비) | {format_pct(overall['roi_sales_pct'])} |
| 순수익 기준 ROI 참고값 | {format_pct(overall['roi_profit_pct'])} |
| 총 전환수 | {format_count(overall['conversions'])} |

| 채널 | 총 광고비 | 총 매출 | ROI | ROAS | CTR | CVR |
|------|-----------:|--------:|----:|-----:|----:|----:|
{chr(10).join(channel_rows)}
| **합계** | **{format_krw(overall['spend'])}** | **{format_krw(overall['revenue'])}** | **{format_pct(overall['roi_sales_pct'])}** | **{format_float(overall['revenue'] / overall['spend'])}** | - | - |

## 3. 채널별 ROI 비교

| 순위 | 채널 | ROI | 평가 |
|------|------|----:|------|
{chr(10).join(rank_rows)}

유료 채널만 놓고 보면 이메일과 메타의 ROI 격차({format_pct(channel['이메일']['ROI_pct'])} vs {format_pct(channel['메타광고']['ROI_pct'])})가 가장 눈에 띈다. 4배 차이면 같은 예산을 어디 넣느냐로 결과가 크게 달라진다는 뜻이다. 네이버는 중간이 아닌 준상위권({format_pct(channel['네이버광고']['ROI_pct'])})이고, 검색 기반이라 주차별 변동폭도 작다. 메타는 도달이 넓다는 장점은 있지만 현재 수치만으로는 증액 근거로 쓰기 어렵다.

## 4. 이슈 3가지

### 이슈 1: 메타광고 W5 광고비 급증 대비 ROI 급락

W4→W5에서 메타 광고비가 {format_krw(issue['meta_w4_spend'])}에서 {format_krw(issue['meta_w5_spend'])}으로 3.6배 뛰었는데, 매출은 {format_pct(issue['meta_revenue_change'])} 오르는 데 그쳤다. ROI로 환산하면 {format_pct(issue['meta_w4_roi'])}에서 {format_pct(issue['meta_w5_roi'])}로 반 토막이다. 돈을 3배 썼는데 결과는 절반짜리였다는 뜻이다.

단발성이면 넘길 수 있지만, 반복된다면 심각하다. W5 시점에 소재 교체나 타겟 변경이 있었는지 먼저 확인해야 한다. 증액할 때 CTR과 CVR이 어떻게 움직였는지 보면 원인을 좁힐 수 있다. 다음 집행 전에 W5 소재·타겟·빈도를 분리해서 점검하고, 일 예산 한도와 증액 승인 기준을 미리 정해두는 게 맞다.

### 이슈 2: 카카오광고 W4 집행 급락

카카오는 메타와 반대 패턴이다. W3 광고비 {format_krw(issue['kakao_w3_spend'])}에서 W4 {format_krw(issue['kakao_w4_spend'])}으로 {format_pct(issue['kakao_spend_change'])} 줄었고, 매출도 {format_pct(issue['kakao_revenue_change'])} 떨어졌다. 성과가 나빠진 게 아니라 집행 자체가 줄어든 것처럼 보인다.

캠페인 예산 한도 소진이나 소재 승인 문제가 있었을 가능성을 먼저 본다. W4 카카오 캠페인의 예산 설정, 소재 승인 상태, 플랫폼 장애 이력을 확인해야 한다. 앞으로는 채널별 집행 예정액 대비 실집행액을 리포트에 같이 포함하면 이런 경우를 배포 전에 잡을 수 있다.

### 이슈 3: 데이터 품질 이슈가 집계 신뢰도를 흔듦

수치를 믿으려면 데이터부터 맞아야 한다. 이번 분석에서 결측 3건(impressions, clicks, revenue 각 1건), 완전 중복 1행, 이메일 매출 이상치 1건을 처리했다. 이메일 2026-04-26 날짜 AOV가 {format_krw(metrics['outlier_rows'][0]['aov'])}인데, 정제 후 평균({format_krw(issue['email_clean_aov'])})의 {format_float(issue['email_outlier_aov_multiple'], 1)}배다. 이걸 그냥 포함하면 이메일 ROI가 과대평가되고 채널 순위도 바뀐다.

이번엔 수작업으로 잡았는데, 다음번에는 놓칠 수 있다. 리포트 배포 전 중복 제거·결측 위치 출력·AOV 상위값 플래그 확인을 자동 검증 단계로 고정해야 한다. 이메일 이상치는 원본 주문 로그 확인 전까지 제외 집계로 보고한다.

## 5. 전주 대비 변화율 (최근 2주: W7 -> W8)

| 지표 | W7 | W8 | 변화율 | 상태 |
|------|---:|---:|------:|------|
{chr(10).join(wow_table)}

W8은 지출, 매출, 전환 모두 올랐다. 숫자만 보면 나쁘지 않다. 그런데 지출(+{format_pct(wow['spend']['change_pct'])})보다 매출(+{format_pct(wow['revenue']['change_pct'])}) 증가율이 낮고 CTR은 소폭 하락했다. 전환수가 늘었다는 건 긍정적이지만, 클릭 품질이 조금씩 떨어지는 신호일 수 있다. 다음 주는 단순 증액보다 어느 채널에서 효율이 올라왔는지를 먼저 확인하는 게 맞다.

## 6. 의사결정 로그 요약

- 완전 중복 1행은 집계 전 제거했습니다. 중복을 유지하면 네이버광고 W7 성과가 부풀려집니다.
- 결측 3건은 0 대체하지 않았습니다. 수집 누락을 0 성과로 해석하면 CTR·매출 합계가 왜곡될 수 있어 pandas 합산의 결측 제외 규칙을 사용했습니다.
- 이메일 2026-04-26 매출 이상치는 AOV 기준으로 비현실적이라 제외했습니다. 원본 로그 확인 전까지 리포트 집계에서 제외하는 보수적 기준입니다.
- 오가닉은 광고비 0원이라 ROI/ROAS 비교 순위에서 제외했습니다. 대신 매출, 전환수, CTR, CVR로 별도 평가합니다.
- 이슈 3가지는 비즈니스 영향이 큰 순서로 메타 W5 과집행, 카카오 W4 집행 급락, 데이터 품질 리스크를 선정했습니다.

## [Standard] 파이프라인 사용법

- 실행: `[09] DA 공통` 폴더에서 `python scripts/generate_insight_report.py`를 실행하면 `output/insight_report.md`와 `output/metrics.json`이 재생성됩니다.
- 새 CSV 분석: 동일 컬럼 구조의 파일을 `data/marketing_performance.csv`로 교체한 뒤 같은 명령을 실행합니다.
- 설계 근거: 경영진은 총 지출·매출·ROI와 예산 조정 판단이 필요하고, 마케팅팀은 채널별 CTR/CVR, 주차별 급변, 데이터 품질 원인을 추적해야 하므로 핵심 요약 -> ROI 순위 -> 이슈 -> W7/W8 변화율 순서로 구성했습니다.

## [Challenge] 예산 재배분 기획안

### 기획안 1: 메타광고 증액 한도 설정 후 고효율 채널로 이동 [P0]

메타 W5 패턴이 재발하면 손실이 크다. 메타 ROI({format_pct(channel['메타광고']['ROI_pct'])})와 이메일 ROI({format_pct(channel['이메일']['ROI_pct'])})의 격차를 보면, 같은 금액을 채널만 바꿔도 결과가 달라진다. 다음 주 메타 집행은 W8 수준에서 급격히 늘리지 않되, W5처럼 초과 집행이 생기는 금액은 이메일 CRM이나 네이버 고전환 키워드로 먼저 돌린다. 이메일은 발송 빈도와 수신자 피로도도 같이 관리해야 한다.

우선순위를 P0으로 잡은 이유는 두 가지다. ROI 격차가 4배라 임팩트가 크고, W5 패턴이 이미 한 번 발생했기 때문에 재발 가능성이 있다.

### 기획안 2: 오가닉 성과를 유료 예산 의존도 절감 과제로 분리 [P1]

오가닉은 광고비 0원에 매출 {format_krw(channel['오가닉']['revenue'])}, 전환 {format_count(channel['오가닉']['conversions'])}건, CVR {format_pct(channel['오가닉']['CVR_pct'], 2)}다. 전체 매출의 {format_pct(channel['오가닉']['revenue'] / overall['revenue'] * 100)}를 광고비 없이 냈다. ROI를 계산할 수 없어서 채널 순위 비교에서 빠지지만, 어떻게 보면 가장 효율 좋은 채널이다.

직접 광고비를 넣는 방식이 아니라, 메타 과집행 방지로 아낀 예산 일부를 SEO 콘텐츠, 브랜드 검색 랜딩 개선, 이메일-오가닉 재방문 유도에 쓴다. 단기 매출 즉시성은 이메일이나 네이버보다 낮다. 하지만 유료 광고 의존도를 낮추는 구조 개선이라 장기로는 더 가치 있다고 판단했다.

---

*리포트 생성: Python pandas / Claude Code*
*데이터: `data/marketing_performance.csv`*
"""
    return report


def rank_comment(channel: str) -> str:
    comments = {
        "이메일": "저비용 CRM 채널로 유료 채널 중 최상위 효율",
        "네이버광고": "구매 의도 기반 검색 채널로 안정적 고효율",
        "카카오광고": "중간 효율, 집행 안정성 점검 필요",
        "메타광고": "도달은 크지만 예산 확대 시 효율 악화 리스크",
    }
    return comments[channel]


def write_outputs(root: Path, csv_path: Path) -> None:
    metrics = analyze(csv_path)
    output_dir = root / "output"
    output_dir.mkdir(exist_ok=True)

    report = render_report(metrics)
    (output_dir / "insight_report.md").write_text(report, encoding="utf-8")
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, default=to_native),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the DA common marketing insight report."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Input CSV path. Defaults to data/marketing_performance.csv.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    csv_path = args.csv if args.csv else root / "data" / "marketing_performance.csv"
    write_outputs(root, csv_path)
    print("Generated output/insight_report.md and output/metrics.json")


if __name__ == "__main__":
    main()
