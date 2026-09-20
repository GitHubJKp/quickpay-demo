"""정기결제 실패 재시도 정책 (QPAY-1).

재시도 대상 오류와 비재시도 오류를 분류하고, 최종 실패 시 구독 상태를
'결제 보류'로 전환한다.
"""

from dataclasses import dataclass, field
from enum import Enum


# 일시적 장애로 재시도가 유효한 오류 코드
RETRYABLE_ERROR_CODES = {
    "NETWORK_TIMEOUT",
    "ISSUER_TEMPORARY_DECLINE",
}

# 재시도해도 성공 가능성이 없는 오류 코드 (예: 잔액 부족)
NON_RETRYABLE_ERROR_CODES = {
    "INSUFFICIENT_FUNDS",
    "CARD_EXPIRED",
    "DO_NOT_HONOR",
}


class SubscriptionStatus(str, Enum):
    ACTIVE = "활성"
    PAYMENT_PENDING = "결제 보류"
    CANCELLED = "해지"


@dataclass
class RetryPolicy:
    """재시도 정책 설정값."""

    max_attempts: int = 3
    interval_hours: int = 24


@dataclass
class Subscription:
    """구독 정보."""

    subscription_id: str
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE


def should_retry(error_code: str, attempt: int, policy: RetryPolicy) -> bool:
    """재시도 여부를 판단한다.

    - 잔액 부족 등 비재시도 오류는 즉시 False를 반환한다.
    - 재시도 가능한 오류라도 최대 시도 횟수에 도달하면 False를 반환한다.
    - PG 재시도 제한을 초과하지 않도록 max_attempts 설정값으로 제어한다.
    """
    if error_code in NON_RETRYABLE_ERROR_CODES:
        return False
    if attempt >= policy.max_attempts:
        return False
    return error_code in RETRYABLE_ERROR_CODES


def handle_final_failure(subscription: Subscription) -> None:
    """최종 실패 시 구독 상태를 '결제 보류'로 전환한다."""
    subscription.status = SubscriptionStatus.PAYMENT_PENDING


def mask_card_number(card_number: str) -> str:
    """카드번호를 앞 6자리·뒤 4자리만 남기고 마스킹한다 (PCI-DSS 3.4)."""
    if len(card_number) < 10:
        return "*" * len(card_number)
    return f"{card_number[:6]}{'*' * (len(card_number) - 10)}{card_number[-4:]}"
