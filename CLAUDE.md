# 코딩 에이전트 작업 규칙 (QuickPay 데모 저장소)

이 저장소는 Atlassian AI 데모용 **가상** 저장소입니다. Jira 작업 항목을 받아 작업하는 코딩 에이전트(Claude Agent for Jira 등)는 아래 규칙을 따릅니다.

## 구조
- `web/` — 결제 화면(정적 페이지, GitHub Pages로 production 배포)
  - `web/checkout.js` — 결제 금액 계산 로직 (상품 금액, 쿠폰 할인, 배송비, 최종 결제 금액)
  - `web/app.js` — 화면 렌더링과 결제 승인 요청
  - `web/api/quote.json` — 결제 서버(PG)가 계산한 기대 금액 (데모용 정적 응답)
- `tests/*.test.mjs` — 결제 화면 테스트 (`npm test`)
- `*.py`, `test_*.py` — 백엔드 모듈과 테스트 (`pytest -q`)
- `.github/workflows/deploy.yml` — main 머지 시 테스트 후 production 배포 (수정하지 말 것)

## 작업 규칙
1. **브랜치·커밋·PR 제목에 Jira 작업 항목 키를 넣습니다.** 예: 브랜치 `claude/QPB-1/fix-coupon`, 커밋 `QPB-1 쿠폰 할인 중복 적용 수정`, PR 제목 `QPB-1 …`. (Jira 개발 패널과 배포 추적이 이 키로 연결됩니다.)
2. **변경은 최소한으로.** 원인이 된 코드만 고치고 관련 없는 리팩터링은 하지 않습니다.
3. **버그 수정에는 회귀 테스트를 반드시 추가합니다.** 수정 전에는 실패하고 수정 후에는 통과하는 테스트여야 합니다.
4. **`npm test`와 `pytest -q test_settlement_report.py`가 모두 통과해야** PR을 엽니다. (`test_payment_retry.py`는 QPAY-1 작업 중인 스텁이라 제외)
5. **PR 본문 형식** (한국어):
   - `## 인계받은 분석` — Jira 작업 항목의 Rovo 분류 리포트에서 핵심 2~3줄을 인용
   - `## 원인`
   - `## 변경 내용`
   - `## 테스트` — 추가한 테스트와 실행 결과
   - `## 확인 방법` — 배포 후 화면에서 확인할 수 있는 방법
