"""결제 실패 재시도 정책 및 재시도 안내 UX 테스트 (QPAY-3)."""

import logging

import pytest

from src.payment_retry import (
    GuideAction,
    PaymentFailureContext,
    RetryPolicy,
    RetryGuideResult,
    guide_on_failure,
    is_feature_enabled,
    mask_card_number,
    mask_cvc,
    set_feature_flag,
    should_retry,
)


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _ctx(
    error_code: str = "NETWORK_TIMEOUT",
    attempt: int = 0,
    card_number: str = "4111111111111111",
) -> PaymentFailureContext:
    return PaymentFailureContext(
        error_code=error_code,
        attempt=attempt,
        masked_card_number=mask_card_number(card_number),
        merchant_id="MRC-001",
        payment_id="PAY-999",
    )


@pytest.fixture(autouse=True)
def reset_feature_flags():
    """각 테스트 전후로 기능 플래그를 기본값으로 복원한다."""
    set_feature_flag("payment.retry.guide", True)
    yield
    set_feature_flag("payment.retry.guide", True)


# ---------------------------------------------------------------------------
# 기존 재시도 판단 테스트 (QPAY-1)
# ---------------------------------------------------------------------------


def test_retry_stops_at_max_attempts():
    policy = RetryPolicy(max_attempts=3)
    assert should_retry("NETWORK_TIMEOUT", attempt=3, policy=policy) is False


def test_retry_allowed_before_max_attempts():
    policy = RetryPolicy(max_attempts=3)
    assert should_retry("NETWORK_TIMEOUT", attempt=2, policy=policy) is True


def test_insufficient_funds_not_retryable():
    """잔액 부족(INSUFFICIENT_FUNDS)은 재시도하지 않는다."""
    policy = RetryPolicy(max_attempts=3)
    assert should_retry("INSUFFICIENT_FUNDS", attempt=0, policy=policy) is False


# ---------------------------------------------------------------------------
# 카드 정보 마스킹 테스트 (PCI-DSS 3.4)
# ---------------------------------------------------------------------------


def test_masking_keeps_first6_last4():
    assert mask_card_number("4111111111111111") == "411111******1111"


def test_masking_short_card_number():
    assert mask_card_number("123") == "***"


def test_cvc_fully_masked():
    assert mask_cvc("123") == "***"
    assert mask_cvc("1234") == "****"


# ---------------------------------------------------------------------------
# QPAY-3: 재시도 안내 UX 테스트
# ---------------------------------------------------------------------------


def test_guide_shows_retry_on_retryable_error():
    """재시도 가능한 오류 코드에서 재시도 안내(SHOW_RETRY)를 반환한다."""
    policy = RetryPolicy(max_attempts=3)
    result = guide_on_failure(_ctx("NETWORK_TIMEOUT", attempt=0), policy)
    assert result.action == GuideAction.SHOW_RETRY


def test_guide_redirects_after_max_retries_exceeded():
    """재시도 3회 초과 시 대체 결제수단 전환(REDIRECT_ALTERNATIVE)을 반환한다."""
    policy = RetryPolicy(max_attempts=3)
    result = guide_on_failure(_ctx("NETWORK_TIMEOUT", attempt=3), policy)
    assert result.action == GuideAction.REDIRECT_ALTERNATIVE


def test_guide_redirects_on_non_retryable_error():
    """비재시도 오류(카드 한도 초과 등)는 즉시 대체 결제수단 화면으로 전환한다."""
    policy = RetryPolicy(max_attempts=3)
    result = guide_on_failure(_ctx("CARD_LIMIT_EXCEEDED", attempt=0), policy)
    assert result.action == GuideAction.REDIRECT_ALTERNATIVE


def test_guide_response_within_3_seconds():
    """안내 응답이 3000ms 이내여야 한다 (수락 기준)."""
    policy = RetryPolicy(max_attempts=3)
    result = guide_on_failure(_ctx(), policy)
    assert result.elapsed_ms < 3000


def test_guide_response_uses_monotonic_clock():
    """elapsed_ms가 가짜 clock으로도 정확하게 계산된다."""
    calls = iter([0.0, 0.5])
    result = guide_on_failure(_ctx(), RetryPolicy(), _clock=lambda: next(calls))
    assert abs(result.elapsed_ms - 500.0) < 1e-6


def test_guide_logs_failure_reason_no_plain_card(caplog):
    """로그에 실패 사유 코드가 기록되고 평문 카드번호는 포함되지 않는다."""
    policy = RetryPolicy(max_attempts=3)
    with caplog.at_level(logging.WARNING, logger="src.payment_retry"):
        guide_on_failure(_ctx("NETWORK_TIMEOUT", attempt=1), policy)

    assert any("NETWORK_TIMEOUT" in r.message for r in caplog.records)
    # 평문 카드번호가 로그에 없는지 확인
    for record in caplog.records:
        assert "4111111111111111" not in record.message


def test_guide_logs_masked_card(caplog):
    """로그에 마스킹된 카드번호가 기록된다."""
    policy = RetryPolicy(max_attempts=3)
    with caplog.at_level(logging.WARNING, logger="src.payment_retry"):
        guide_on_failure(_ctx("NETWORK_TIMEOUT", attempt=1), policy)

    assert any("411111******1111" in r.message for r in caplog.records)


def test_guide_disabled_flag_returns_legacy_behavior():
    """기능 플래그 payment.retry.guide 비활성화 시 이전 동작으로 복귀한다."""
    set_feature_flag("payment.retry.guide", False)
    policy = RetryPolicy(max_attempts=3)

    # 재시도 가능한 오류: SHOW_RETRY 반환
    result = guide_on_failure(_ctx("NETWORK_TIMEOUT", attempt=0), policy)
    assert result.action == GuideAction.SHOW_RETRY

    # 재시도 불가: REDIRECT_ALTERNATIVE 반환
    result = guide_on_failure(_ctx("NETWORK_TIMEOUT", attempt=3), policy)
    assert result.action == GuideAction.REDIRECT_ALTERNATIVE


def test_guide_message_contains_attempt_count():
    """재시도 안내 메시지에 현재 시도 횟수가 포함된다."""
    policy = RetryPolicy(max_attempts=3)
    result = guide_on_failure(_ctx("NETWORK_TIMEOUT", attempt=1), policy)
    assert result.action == GuideAction.SHOW_RETRY
    assert "2/3" in result.message


def test_guide_slow_response_logs_error(caplog):
    """안내 응답이 3초를 초과하면 오류 로그를 남긴다."""
    # 가짜 clock으로 4초 경과를 시뮬레이션한다
    calls = iter([0.0, 4.0])
    with caplog.at_level(logging.ERROR, logger="src.payment_retry"):
        guide_on_failure(_ctx(), RetryPolicy(), _clock=lambda: next(calls))

    assert any("응답 지연" in r.message for r in caplog.records)
