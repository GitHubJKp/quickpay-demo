"""가맹점 월간 정산 리포트 생성 (QPAY-4).

매월 1일 00:00 에 전월 정산 데이터를 집계하고, PDF 리포트를 가맹점 담당자
이메일로 발송한 뒤 결과를 정산 DB에 기록한다.

기능 플래그 ``enable-auto-settlement-report`` 가 꺼져 있으면 자동 생성·발송을
차단하고 수기 생성 모드로 전환한다.

보안:
- 리포트 내 개인정보는 마스킹 처리한다.
- 카드정보는 저장·표시하지 않는다 (PCI-DSS 3.2.1).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

FEATURE_FLAG_KEY = "enable-auto-settlement-report"

# ---------------------------------------------------------------------------
# 도메인 모델
# ---------------------------------------------------------------------------


@dataclass
class MerchantInfo:
    merchant_id: str
    name: str
    contact_email: str


@dataclass
class TransactionRecord:
    """정산 집계용 거래 레코드.

    카드번호 등 민감 인증 데이터는 절대 포함하지 않는다 (PCI-DSS 3.2.1).
    """

    transaction_id: str
    merchant_id: str
    amount: int  # 원(KRW) 단위


@dataclass
class SettlementReport:
    merchant_id: str
    period: str          # YYYY-MM
    total_amount: int
    transaction_count: int
    status: str          # "generated" | "no_data"


@dataclass
class SendResult:
    merchant_id: str
    period: str
    sent_at: datetime
    status: str          # "sent" | "failed" | "no_data" | "skipped"
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# 포트(Port) — 외부 의존성 추상화
# ---------------------------------------------------------------------------


@runtime_checkable
class FeatureFlagClient(Protocol):
    def is_enabled(self, key: str) -> bool:
        ...


@runtime_checkable
class SettlementRepository(Protocol):
    def get_merchants(self) -> List[MerchantInfo]:
        ...

    def get_transactions(self, merchant_id: str, period: str) -> List[TransactionRecord]:
        ...

    def record_send_result(self, result: SendResult) -> None:
        ...


@runtime_checkable
class PdfGenerator(Protocol):
    def generate(self, report: SettlementReport, merchant: MerchantInfo) -> bytes:
        ...


@runtime_checkable
class EmailSender(Protocol):
    def send(
        self,
        to: str,
        subject: str,
        body: str,
        attachment: bytes,
        filename: str,
    ) -> None:
        ...


# ---------------------------------------------------------------------------
# 유틸리티
# ---------------------------------------------------------------------------


def mask_email(email: str) -> str:
    """이메일 주소를 로그용으로 마스킹한다 (개인정보 보호).

    예) ``hong@example.com`` → ``ho**@example.com``
    """
    if "@" not in email:
        return "****"
    local, domain = email.split("@", 1)
    visible_len = min(2, len(local))
    masked_local = local[:visible_len] + "*" * (len(local) - visible_len)
    return f"{masked_local}@{domain}"


def _previous_month(ref: date) -> str:
    """ref 날짜 기준 전월을 ``YYYY-MM`` 형식으로 반환한다."""
    if ref.month == 1:
        return f"{ref.year - 1}-12"
    return f"{ref.year}-{ref.month - 1:02d}"


# ---------------------------------------------------------------------------
# 하위 호환 스텁 (기존 build_report 시그니처 유지)
# ---------------------------------------------------------------------------


def build_report(merchant_id: str, period: date) -> SettlementReport:
    """전월 거래를 집계해 리포트를 만든다.

    .. deprecated::
        실제 집계·발송이 필요하다면 :func:`generate_and_send` 또는
        :func:`run_monthly_job` 을 사용한다.
    """
    return SettlementReport(
        merchant_id=merchant_id,
        period=period.strftime("%Y-%m"),
        total_amount=0,
        transaction_count=0,
        status="generated",
    )


# ---------------------------------------------------------------------------
# 핵심 비즈니스 로직
# ---------------------------------------------------------------------------


def generate_and_send(
    merchant: MerchantInfo,
    period: str,
    repo: SettlementRepository,
    pdf_gen: PdfGenerator,
    email_sender: EmailSender,
    feature_flags: FeatureFlagClient,
) -> SendResult:
    """단일 가맹점에 대해 리포트를 생성하고 발송한다.

    Args:
        merchant: 가맹점 정보 (이름, 연락처 이메일).
        period: 정산 대상 월 ``YYYY-MM``.
        repo: 거래 조회 및 발송 이력 저장 저장소.
        pdf_gen: PDF 바이트 생성기.
        email_sender: 이메일 발송기.
        feature_flags: 기능 플래그 클라이언트.

    Returns:
        :class:`SendResult` — 발송 결과 (상태, 시각, 오류).

    수락 기준:
    - 기능 플래그 꺼짐 → 자동 처리를 건너뛴다 (``status="skipped"``).
    - 전월 거래 0건 → PDF 생성 없이 ``status="no_data"`` 를 기록한다.
    - 이메일 발송 실패 → ``status="failed"`` 를 기록하고 오류 로그를 남긴다.
    - 발송 성공 → ``status="sent"`` 를 기록한다.
    """
    now = datetime.utcnow()

    # 기능 플래그 검사 — OFF 이면 수기 생성 모드
    if not feature_flags.is_enabled(FEATURE_FLAG_KEY):
        logger.info(
            "기능 플래그 비활성화 — 자동 발송 건너뜀 (merchant=%s)",
            merchant.merchant_id,
        )
        return SendResult(
            merchant_id=merchant.merchant_id,
            period=period,
            sent_at=now,
            status="skipped",
            error="feature flag disabled",
        )

    # 전월 거래 조회
    transactions = repo.get_transactions(merchant.merchant_id, period)

    # 경계값: 정산 대상 0건
    if not transactions:
        logger.info(
            "정산 대상 없음 — 빈 리포트 생성 안 함 (merchant=%s, period=%s)",
            merchant.merchant_id,
            period,
        )
        result = SendResult(
            merchant_id=merchant.merchant_id,
            period=period,
            sent_at=now,
            status="no_data",
        )
        repo.record_send_result(result)
        return result

    # 리포트 집계
    report = SettlementReport(
        merchant_id=merchant.merchant_id,
        period=period,
        total_amount=sum(t.amount for t in transactions),
        transaction_count=len(transactions),
        status="generated",
    )

    # PDF 생성
    pdf_bytes = pdf_gen.generate(report, merchant)

    # 이메일 발송 (실패 시 오류 기록)
    try:
        email_sender.send(
            to=merchant.contact_email,
            subject=f"[QuickPay] {period} 월간 정산 리포트",
            body=(
                f"{merchant.name} 귀중\n\n"
                f"{period} 월간 정산 리포트를 첨부 파일로 전달 드립니다.\n"
                "문의 사항은 QuickPay 고객센터로 연락해 주십시오."
            ),
            attachment=pdf_bytes,
            filename=f"settlement_{merchant.merchant_id}_{period}.pdf",
        )
        result = SendResult(
            merchant_id=merchant.merchant_id,
            period=period,
            sent_at=now,
            status="sent",
        )
        logger.info(
            "정산 리포트 발송 성공 (merchant=%s, period=%s, email=%s)",
            merchant.merchant_id,
            period,
            mask_email(merchant.contact_email),
        )
    except Exception as exc:  # noqa: BLE001
        result = SendResult(
            merchant_id=merchant.merchant_id,
            period=period,
            sent_at=now,
            status="failed",
            error=str(exc),
        )
        logger.error(
            "정산 리포트 발송 실패 (merchant=%s, period=%s, email=%s): %s",
            merchant.merchant_id,
            period,
            mask_email(merchant.contact_email),
            exc,
        )

    repo.record_send_result(result)
    return result


def run_monthly_job(
    repo: SettlementRepository,
    pdf_gen: PdfGenerator,
    email_sender: EmailSender,
    feature_flags: FeatureFlagClient,
    ref_date: Optional[date] = None,
) -> List[SendResult]:
    """매월 1일 00:00 에 실행되는 정산 리포트 일괄 생성·발송 잡.

    Args:
        repo: 저장소.
        pdf_gen: PDF 생성기.
        email_sender: 이메일 발송기.
        feature_flags: 기능 플래그 클라이언트.
        ref_date: 기준 날짜 (기본값: 오늘). 테스트·수동 재처리 시 지정한다.

    Returns:
        전체 가맹점 발송 결과 목록.

    수락 기준:
    - 매월 1일 00:00 에 전월 정산 데이터가 집계된다.
    - 생성된 PDF 리포트가 가맹점 담당자 이메일로 발송된다.
    - 발송 결과가 정산 DB에 기록된다.
    """
    today = ref_date or date.today()
    period = _previous_month(today)

    merchants = repo.get_merchants()
    logger.info(
        "월간 정산 잡 시작 (period=%s, merchants=%d)",
        period,
        len(merchants),
    )

    results: List[SendResult] = []
    for merchant in merchants:
        result = generate_and_send(
            merchant=merchant,
            period=period,
            repo=repo,
            pdf_gen=pdf_gen,
            email_sender=email_sender,
            feature_flags=feature_flags,
        )
        results.append(result)

    sent = sum(1 for r in results if r.status == "sent")
    failed = sum(1 for r in results if r.status == "failed")
    no_data = sum(1 for r in results if r.status == "no_data")
    skipped = sum(1 for r in results if r.status == "skipped")
    logger.info(
        "월간 정산 잡 완료 (period=%s, total=%d, sent=%d, failed=%d, no_data=%d, skipped=%d)",
        period,
        len(results),
        sent,
        failed,
        no_data,
        skipped,
    )
    return results
