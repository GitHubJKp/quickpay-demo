from src.payment_retry import RetryPolicy, mask_card_number, should_retry


def test_retry_stops_at_max_attempts():
    policy = RetryPolicy(max_attempts=3)
    assert should_retry("NETWORK_TIMEOUT", attempt=3, policy=policy) is False


def test_masking_keeps_first6_last4():
    assert mask_card_number("4111111111111111") == "411111******1111"


# TODO(QPAY-1): 잔액 부족(INSUFFICIENT_FUNDS)은 재시도하지 않는다는 테스트 추가
# TODO(QPAY-1): 최종 실패 시 구독 상태 전환 테스트 추가
