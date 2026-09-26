# QuickPay (한빛페이) — 데모 저장소

2026-09-30 Atlassian MVP Leaders Circle Tech Session 데모용 **가상** 저장소입니다.
실제 서비스가 아니며 모든 코드와 데이터는 가상입니다.

## 구성

| 경로 | 내용 | 연결된 Jira |
|---|---|---|
| `web/` | 가맹점 주문 결제 화면 (GitHub Pages로 production 배포) | QPB (버그 수정 파이프라인) |
| `tests/checkout.test.mjs` | 결제 금액 계산 테스트 (`npm test`) | QPB |
| `payment_retry.py` | 정기결제 실패 재시도 정책 | QPAY-1 |
| `settlement_report.py` | 가맹점 월간 정산 리포트 생성 | QPAY-4 |
| `test_*.py` | 백엔드 테스트 (`pytest -q`) | QPAY |

## 배포

`main`에 머지되면 GitHub Actions(`.github/workflows/deploy.yml`)가 테스트 후 `production` 환경(GitHub Pages)에 배포합니다.
배포 기록은 GitHub for Atlassian을 통해 Jira 작업 항목의 개발 패널에 표시됩니다.

## 연결된 Jira

- osci.atlassian.net 프로젝트 **QPB** — [DEMO] QuickPay 버그 수정 파이프라인 (Loom → Rovo → Claude → 사람 승인 → 배포 → 문서)
- osci.atlassian.net 프로젝트 **QPAY** — [DEMO] QuickPay 출시 파이프라인

코딩 에이전트 작업 규칙은 [`CLAUDE.md`](./CLAUDE.md)를 참고하세요.
