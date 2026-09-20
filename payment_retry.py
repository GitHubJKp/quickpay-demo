"""정기결제 실패 재시도 정책 (QPAY-1).

현재는 스텁이다. 재시도 대상 오류 분류, 간격, 상한이 아직 정해지지 않았다.
"""

from dataclasses import dataclass


RETRYABLE_ERROR_CODES = {
    "NETWORK_TIMEOUT",
    "ISSUER_TEMPORARY_DECLINE",
}


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    interval_hours: int = 24


def should_retry(error_code: str, attempt: int, policy: RetryPolicy) -> bool:
    """재시도 여부를 판단한다.

    TODO(QPAY-1): 잔액 부족과 일시적 네트워크 오류를 구분한다.
    TODO(QPAY-1): 최종 실패 시 구독 상태를 '결제 보류'로 전환한다.
    TODO(QPAY-1): PG(페이브릿지)의 재시도 제한 정책과 충돌하지 않는지 확인한다.
    """
    if attempt >= policy.max_attempts:
        return False
    return error_code in RETRYABLE_ERROR_CODES


def mask_card_number(card_number: str) -> str:
    """카드번호를 앞 6자리·뒤 4자리만 남기고 마스킹한다 (PCI-DSS 3.4)."""
    if len(card_number) < 10:
        return "*" * len(card_number)
    return f"{card_number[:6]}{'*' * (len(card_number) - 10)}{card_number[-4:]}"
