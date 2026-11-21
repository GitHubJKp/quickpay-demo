from src.payment_retry import (
    NON_RETRYABLE_ERROR_CODES,
    RETRYABLE_ERROR_CODES,
    RetryPolicy,
    Subscription,
    SubscriptionStatus,
    handle_final_failure,
    mask_card_number,
    should_retry,
)


# ── 재시도 여부 판단 ──────────────────────────────────────────────────────────

def test_retry_stops_at_max_attempts():
    policy = RetryPolicy(max_attempts=3)
    assert should_retry("NETWORK_TIMEOUT", attempt=3, policy=policy) is False


def test_retryable_error_within_limit_returns_true():
    policy = RetryPolicy(max_attempts=3)
    assert should_retry("NETWORK_TIMEOUT", attempt=0, policy=policy) is True
    assert should_retry("ISSUER_TEMPORARY_DECLINE", attempt=2, policy=policy) is True


def test_insufficient_funds_is_not_retried():
    """잔액 부족은 재시도해도 성공 가능성이 없으므로 즉시 False를 반환한다."""
    policy = RetryPolicy(max_attempts=3)
    assert should_retry("INSUFFICIENT_FUNDS", attempt=0, policy=policy) is False


def test_non_retryable_codes_are_not_retried():
    policy = RetryPolicy(max_attempts=5)
    for code in NON_RETRYABLE_ERROR_CODES:
        assert should_retry(code, attempt=0, policy=policy) is False, (
            f"{code} should not be retried"
        )


def test_unknown_error_code_is_not_retried():
    policy = RetryPolicy(max_attempts=3)
    assert should_retry("UNKNOWN_ERROR", attempt=0, policy=policy) is False


# ── 설정값(RetryPolicy) 관리 ─────────────────────────────────────────────────

def test_retry_policy_custom_values():
    """재시도 간격과 최대 횟수를 설정값으로 관리할 수 있다."""
    policy = RetryPolicy(max_attempts=5, interval_hours=12)
    assert policy.max_attempts == 5
    assert policy.interval_hours == 12
    assert should_retry("NETWORK_TIMEOUT", attempt=4, policy=policy) is True
    assert should_retry("NETWORK_TIMEOUT", attempt=5, policy=policy) is False


# ── 최종 실패 시 구독 상태 전환 ───────────────────────────────────────────────

def test_handle_final_failure_sets_payment_pending():
    """최종 실패 시 구독 상태가 '결제 보류'로 변경된다."""
    subscription = Subscription(subscription_id="sub-001")
    assert subscription.status == SubscriptionStatus.ACTIVE

    handle_final_failure(subscription)

    assert subscription.status == SubscriptionStatus.PAYMENT_PENDING


def test_handle_final_failure_idempotent():
    """이미 결제 보류 상태인 구독에 재호출해도 안전하다."""
    subscription = Subscription(
        subscription_id="sub-002", status=SubscriptionStatus.PAYMENT_PENDING
    )
    handle_final_failure(subscription)
    assert subscription.status == SubscriptionStatus.PAYMENT_PENDING


# ── 카드번호 마스킹 ──────────────────────────────────────────────────────────

def test_masking_keeps_first6_last4():
    assert mask_card_number("4111111111111111") == "411111******1111"


def test_masking_short_card_number():
    assert mask_card_number("123") == "***"
