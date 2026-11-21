"""결제 실패 재시도 정책 및 재시도 안내 UX (QPAY-3).

QPAY-3: 결제 실패 재시도 안내 UX 개선
- 결제 실패 후 3초 이내에 재시도 안내가 화면에 표시된다.
- 재시도 3회 초과 시 대체 결제수단 선택 화면으로 전환된다.
- 실패 사유 코드가 결제 로그에 기록된다 (카드정보는 마스킹, PCI-DSS 3.4).
- 기능 플래그: payment.retry.guide
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 기능 플래그
# ---------------------------------------------------------------------------

_FEATURE_FLAGS: dict[str, bool] = {
    "payment.retry.guide": True,
}


def is_feature_enabled(flag: str) -> bool:
    """기능 플래그 활성화 여부를 반환한다."""
    return _FEATURE_FLAGS.get(flag, False)


def set_feature_flag(flag: str, enabled: bool) -> None:
    """테스트 및 운영 롤백용 플래그 설정."""
    _FEATURE_FLAGS[flag] = enabled


# ---------------------------------------------------------------------------
# 재시도 대상 오류 코드
# ---------------------------------------------------------------------------

RETRYABLE_ERROR_CODES = {
    "NETWORK_TIMEOUT",
    "ISSUER_TEMPORARY_DECLINE",
}

# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    interval_hours: int = 24


class GuideAction(Enum):
    SHOW_RETRY = "show_retry"
    REDIRECT_ALTERNATIVE = "redirect_alternative"


@dataclass
class RetryGuideResult:
    action: GuideAction
    message: str
    attempt: int
    elapsed_ms: float


@dataclass
class PaymentFailureContext:
    error_code: str
    attempt: int
    masked_card_number: str
    merchant_id: str
    payment_id: str
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 카드 정보 마스킹 (PCI-DSS 3.4)
# ---------------------------------------------------------------------------


def mask_card_number(card_number: str) -> str:
    """카드번호를 앞 6자리·뒤 4자리만 남기고 마스킹한다 (PCI-DSS 3.4)."""
    if len(card_number) < 10:
        return "*" * len(card_number)
    return f"{card_number[:6]}{'*' * (len(card_number) - 10)}{card_number[-4:]}"


def mask_cvc(cvc: str) -> str:
    """CVC를 완전히 마스킹한다 (PCI-DSS 3.4)."""
    return "*" * len(cvc)


# ---------------------------------------------------------------------------
# 재시도 판단
# ---------------------------------------------------------------------------


def should_retry(error_code: str, attempt: int, policy: RetryPolicy) -> bool:
    """재시도 여부를 판단한다."""
    if attempt >= policy.max_attempts:
        return False
    return error_code in RETRYABLE_ERROR_CODES


# ---------------------------------------------------------------------------
# 결제 실패 로깅 (카드 정보 마스킹 보장)
# ---------------------------------------------------------------------------


def log_payment_failure(ctx: PaymentFailureContext) -> None:
    """결제 실패 사유를 로그에 기록한다. 카드번호·CVC는 마스킹된 값만 기록된다."""
    logger.warning(
        "결제 실패 기록 | payment_id=%s merchant_id=%s error_code=%s attempt=%d "
        "masked_card=%s",
        ctx.payment_id,
        ctx.merchant_id,
        ctx.error_code,
        ctx.attempt,
        ctx.masked_card_number,
    )


# ---------------------------------------------------------------------------
# 재시도 안내 UX (QPAY-3)
# ---------------------------------------------------------------------------

_RETRY_GUIDE_DEADLINE_SEC = 3.0  # 수락 기준: 3초 이내 안내 노출


def guide_on_failure(
    ctx: PaymentFailureContext,
    policy: RetryPolicy,
    *,
    _clock: Optional[callable] = None,
) -> RetryGuideResult:
    """결제 실패 시 재시도 안내 또는 대체 결제수단 전환을 결정한다.

    - 기능 플래그 payment.retry.guide 가 꺼진 경우 이전 동작(단순 재시도 판단)으로 복귀.
    - 안내 결과는 _RETRY_GUIDE_DEADLINE_SEC(3초) 이내에 반환된다.
    - 실패 사유 코드와 마스킹된 카드번호를 로그에 기록한다.
    """
    start = (_clock or time.monotonic)()

    log_payment_failure(ctx)

    if not is_feature_enabled("payment.retry.guide"):
        # 롤백 경로: 플래그 비활성화 시 즉시 이전 동작
        retryable = should_retry(ctx.error_code, ctx.attempt, policy)
        action = GuideAction.SHOW_RETRY if retryable else GuideAction.REDIRECT_ALTERNATIVE
        elapsed_ms = ((_clock or time.monotonic)() - start) * 1000
        return RetryGuideResult(
            action=action,
            message="",
            attempt=ctx.attempt,
            elapsed_ms=elapsed_ms,
        )

    retryable = should_retry(ctx.error_code, ctx.attempt, policy)

    if retryable:
        action = GuideAction.SHOW_RETRY
        message = (
            f"결제에 실패했습니다 (사유: {ctx.error_code}). "
            f"잠시 후 다시 시도해 주세요. "
            f"({ctx.attempt + 1}/{policy.max_attempts}회)"
        )
    else:
        action = GuideAction.REDIRECT_ALTERNATIVE
        message = (
            "결제를 완료하지 못했습니다. "
            "다른 결제수단을 선택해 주세요."
        )

    elapsed_ms = ((_clock or time.monotonic)() - start) * 1000

    # 수락 기준: 3초 이내 안내 노출 (초과 시 경고 로그)
    if elapsed_ms > _RETRY_GUIDE_DEADLINE_SEC * 1000:
        logger.error(
            "재시도 안내 응답 지연 | payment_id=%s elapsed_ms=%.1f (기준: %.0fms)",
            ctx.payment_id,
            elapsed_ms,
            _RETRY_GUIDE_DEADLINE_SEC * 1000,
        )

    return RetryGuideResult(
        action=action,
        message=message,
        attempt=ctx.attempt,
        elapsed_ms=elapsed_ms,
    )
