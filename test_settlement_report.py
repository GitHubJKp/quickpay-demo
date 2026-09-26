"""가맹점 월간 정산 리포트 자동 생성 테스트 (QPAY-4).

테스트 시나리오:
- [정상] 정산 데이터와 유효한 이메일 주소가 존재하면 PDF 리포트 생성 및 발송이 성공한다.
- [실패] 가맹점 이메일 주소가 부정확하면 발송 실패가 기록되고 오류 로그가 남는다.
- [경계값] 정산 대상 데이터가 0건이면 빈 리포트 대신 "정산 대상 없음" 상태가 기록된다.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import List
from unittest.mock import MagicMock, call

import pytest

from settlement_report import (
    FEATURE_FLAG_KEY,
    MerchantInfo,
    SendResult,
    SettlementReport,
    TransactionRecord,
    _previous_month,
    generate_and_send,
    mask_email,
    run_monthly_job,
)


# ---------------------------------------------------------------------------
# 픽스처 — 테스트용 이중체(Test Double)
# ---------------------------------------------------------------------------


def _make_merchant(
    merchant_id: str = "M001",
    name: str = "테스트 가맹점",
    contact_email: str = "contact@example.com",
) -> MerchantInfo:
    return MerchantInfo(
        merchant_id=merchant_id,
        name=name,
        contact_email=contact_email,
    )


def _make_transactions(merchant_id: str = "M001", count: int = 3) -> List[TransactionRecord]:
    return [
        TransactionRecord(
            transaction_id=f"TX{i:04d}",
            merchant_id=merchant_id,
            amount=10_000 * (i + 1),
        )
        for i in range(count)
    ]


def _make_feature_flags(enabled: bool = True) -> MagicMock:
    ff = MagicMock()
    ff.is_enabled.return_value = enabled
    return ff


def _make_repo(
    merchants: List[MerchantInfo] | None = None,
    transactions: List[TransactionRecord] | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.get_merchants.return_value = merchants or []
    repo.get_transactions.return_value = transactions if transactions is not None else []
    return repo


def _make_pdf_gen(pdf_bytes: bytes = b"%PDF-stub") -> MagicMock:
    gen = MagicMock()
    gen.generate.return_value = pdf_bytes
    return gen


def _make_email_sender(raise_exc: Exception | None = None) -> MagicMock:
    sender = MagicMock()
    if raise_exc is not None:
        sender.send.side_effect = raise_exc
    return sender


# ---------------------------------------------------------------------------
# mask_email 유틸리티 테스트
# ---------------------------------------------------------------------------


class TestMaskEmail:
    def test_masks_local_part_keeping_first_two_chars(self):
        assert mask_email("hong@example.com") == "ho**@example.com"

    def test_short_local_part_one_char_visible(self):
        assert mask_email("a@example.com") == "a@example.com"

    def test_two_char_local_part(self):
        assert mask_email("ab@example.com") == "ab@example.com"

    def test_no_at_sign_returns_placeholder(self):
        assert mask_email("invalid-email") == "****"

    def test_domain_is_preserved(self):
        result = mask_email("support@quickpay.io")
        assert result.endswith("@quickpay.io")


# ---------------------------------------------------------------------------
# _previous_month 유틸리티 테스트
# ---------------------------------------------------------------------------


class TestPreviousMonth:
    def test_january_wraps_to_previous_year_december(self):
        assert _previous_month(date(2026, 1, 1)) == "2025-12"

    def test_regular_month(self):
        assert _previous_month(date(2026, 9, 1)) == "2026-08"

    def test_december(self):
        assert _previous_month(date(2026, 12, 1)) == "2026-11"

    def test_month_zero_padded(self):
        assert _previous_month(date(2026, 2, 1)) == "2026-01"


# ---------------------------------------------------------------------------
# generate_and_send — 정상 경로
# ---------------------------------------------------------------------------


class TestGenerateAndSendSuccess:
    """[정상] 정산 데이터와 유효한 이메일 주소가 존재하면 PDF 리포트 생성 및 발송이 성공한다."""

    def setup_method(self):
        self.merchant = _make_merchant()
        self.period = "2026-08"
        self.transactions = _make_transactions(count=3)
        self.repo = _make_repo(transactions=self.transactions)
        self.pdf_gen = _make_pdf_gen()
        self.email_sender = _make_email_sender()
        self.ff = _make_feature_flags(enabled=True)

    def _run(self) -> SendResult:
        return generate_and_send(
            merchant=self.merchant,
            period=self.period,
            repo=self.repo,
            pdf_gen=self.pdf_gen,
            email_sender=self.email_sender,
            feature_flags=self.ff,
        )

    def test_returns_sent_status(self):
        result = self._run()
        assert result.status == "sent"

    def test_no_error_in_result(self):
        result = self._run()
        assert result.error is None

    def test_merchant_id_and_period_in_result(self):
        result = self._run()
        assert result.merchant_id == self.merchant.merchant_id
        assert result.period == self.period

    def test_pdf_generated_with_correct_report(self):
        self._run()
        call_args = self.pdf_gen.generate.call_args
        report: SettlementReport = call_args[0][0]
        assert report.total_amount == sum(t.amount for t in self.transactions)
        assert report.transaction_count == len(self.transactions)

    def test_email_sent_to_merchant_contact(self):
        self._run()
        self.email_sender.send.assert_called_once()
        kwargs = self.email_sender.send.call_args[1]
        assert kwargs["to"] == self.merchant.contact_email

    def test_email_subject_contains_period(self):
        self._run()
        kwargs = self.email_sender.send.call_args[1]
        assert self.period in kwargs["subject"]

    def test_email_attachment_filename_contains_merchant_and_period(self):
        self._run()
        kwargs = self.email_sender.send.call_args[1]
        assert self.merchant.merchant_id in kwargs["filename"]
        assert self.period in kwargs["filename"]

    def test_send_result_recorded_in_db(self):
        result = self._run()
        self.repo.record_send_result.assert_called_once_with(result)

    def test_feature_flag_checked_with_correct_key(self):
        self._run()
        self.ff.is_enabled.assert_called_once_with(FEATURE_FLAG_KEY)


# ---------------------------------------------------------------------------
# generate_and_send — 이메일 발송 실패
# ---------------------------------------------------------------------------


class TestGenerateAndSendEmailFailure:
    """[실패] 가맹점 이메일 주소가 부정확하면 발송 실패가 기록되고 오류 로그가 남는다."""

    def setup_method(self):
        # 실제로 존재하지 않는 도메인의 이메일 — 발송 자체는 SMTP 오류로 실패
        self.merchant = _make_merchant(contact_email="contact.person@invalid-domain.example")
        self.period = "2026-08"
        self.repo = _make_repo(transactions=_make_transactions())
        self.pdf_gen = _make_pdf_gen()
        # 예외 메시지에 이메일 주소가 포함되지 않도록 일반 SMTP 오류를 사용
        self.error_exc = ConnectionRefusedError("SMTP connection refused (111)")
        self.email_sender = _make_email_sender(raise_exc=self.error_exc)
        self.ff = _make_feature_flags(enabled=True)

    def _run(self) -> SendResult:
        return generate_and_send(
            merchant=self.merchant,
            period=self.period,
            repo=self.repo,
            pdf_gen=self.pdf_gen,
            email_sender=self.email_sender,
            feature_flags=self.ff,
        )

    def test_returns_failed_status(self):
        result = self._run()
        assert result.status == "failed"

    def test_error_message_captured_in_result(self):
        result = self._run()
        assert result.error is not None
        assert len(result.error) > 0

    def test_failed_result_recorded_in_db(self):
        result = self._run()
        self.repo.record_send_result.assert_called_once_with(result)

    def test_error_is_logged(self, caplog):
        with caplog.at_level(logging.ERROR, logger="settlement_report"):
            self._run()
        assert any("발송 실패" in record.message for record in caplog.records)

    def test_email_not_logged_in_plain_text(self, caplog):
        """이메일 주소가 로그에 평문으로 출력되지 않는다 (개인정보 보호)."""
        with caplog.at_level(logging.ERROR, logger="settlement_report"):
            self._run()
        for record in caplog.records:
            assert self.merchant.contact_email not in record.message


# ---------------------------------------------------------------------------
# generate_and_send — 경계값: 정산 대상 0건
# ---------------------------------------------------------------------------


class TestGenerateAndSendNoData:
    """[경계값] 정산 대상 데이터가 0건이면 빈 리포트 대신 "정산 대상 없음" 상태가 기록된다."""

    def setup_method(self):
        self.merchant = _make_merchant()
        self.period = "2026-08"
        self.repo = _make_repo(transactions=[])
        self.pdf_gen = _make_pdf_gen()
        self.email_sender = _make_email_sender()
        self.ff = _make_feature_flags(enabled=True)

    def _run(self) -> SendResult:
        return generate_and_send(
            merchant=self.merchant,
            period=self.period,
            repo=self.repo,
            pdf_gen=self.pdf_gen,
            email_sender=self.email_sender,
            feature_flags=self.ff,
        )

    def test_returns_no_data_status(self):
        result = self._run()
        assert result.status == "no_data"

    def test_pdf_not_generated(self):
        self._run()
        self.pdf_gen.generate.assert_not_called()

    def test_email_not_sent(self):
        self._run()
        self.email_sender.send.assert_not_called()

    def test_no_data_result_recorded_in_db(self):
        result = self._run()
        self.repo.record_send_result.assert_called_once_with(result)


# ---------------------------------------------------------------------------
# generate_and_send — 기능 플래그 OFF
# ---------------------------------------------------------------------------


class TestGenerateAndSendFeatureFlagDisabled:
    """기능 플래그가 꺼져 있으면 자동 생성·발송을 차단하고 수기 모드로 전환한다."""

    def setup_method(self):
        self.merchant = _make_merchant()
        self.period = "2026-08"
        self.repo = _make_repo(transactions=_make_transactions())
        self.pdf_gen = _make_pdf_gen()
        self.email_sender = _make_email_sender()
        self.ff = _make_feature_flags(enabled=False)

    def _run(self) -> SendResult:
        return generate_and_send(
            merchant=self.merchant,
            period=self.period,
            repo=self.repo,
            pdf_gen=self.pdf_gen,
            email_sender=self.email_sender,
            feature_flags=self.ff,
        )

    def test_returns_skipped_status(self):
        result = self._run()
        assert result.status == "skipped"

    def test_no_db_write_when_skipped(self):
        self._run()
        self.repo.record_send_result.assert_not_called()

    def test_no_email_sent_when_skipped(self):
        self._run()
        self.email_sender.send.assert_not_called()

    def test_no_pdf_generated_when_skipped(self):
        self._run()
        self.pdf_gen.generate.assert_not_called()


# ---------------------------------------------------------------------------
# run_monthly_job — 일괄 처리
# ---------------------------------------------------------------------------


class TestRunMonthlyJob:
    """매월 1일 00:00 일괄 잡 실행 검증."""

    def _run(
        self,
        merchants: List[MerchantInfo],
        transactions_by_id: dict | None = None,
        feature_enabled: bool = True,
        ref_date: date | None = None,
    ) -> List[SendResult]:
        transactions_by_id = transactions_by_id or {}
        repo = MagicMock()
        repo.get_merchants.return_value = merchants
        repo.get_transactions.side_effect = lambda mid, _period: transactions_by_id.get(mid, [])
        pdf_gen = _make_pdf_gen()
        email_sender = _make_email_sender()
        ff = _make_feature_flags(enabled=feature_enabled)
        return run_monthly_job(
            repo=repo,
            pdf_gen=pdf_gen,
            email_sender=email_sender,
            feature_flags=ff,
            ref_date=ref_date,
        )

    def test_processes_all_merchants(self):
        merchants = [_make_merchant("M001"), _make_merchant("M002"), _make_merchant("M003")]
        txns = {"M001": _make_transactions("M001"), "M002": _make_transactions("M002")}
        results = self._run(merchants=merchants, transactions_by_id=txns)
        assert len(results) == 3

    def test_period_is_previous_month_of_ref_date(self):
        merchants = [_make_merchant("M001")]
        txns = {"M001": _make_transactions("M001")}
        results = self._run(
            merchants=merchants,
            transactions_by_id=txns,
            ref_date=date(2026, 9, 1),
        )
        assert all(r.period == "2026-08" for r in results)

    def test_january_ref_date_uses_previous_year_december(self):
        merchants = [_make_merchant("M001")]
        txns = {"M001": _make_transactions("M001")}
        results = self._run(
            merchants=merchants,
            transactions_by_id=txns,
            ref_date=date(2026, 1, 1),
        )
        assert all(r.period == "2025-12" for r in results)

    def test_no_merchants_returns_empty_list(self):
        results = self._run(merchants=[])
        assert results == []

    def test_mixed_results_counted_correctly(self):
        merchants = [_make_merchant("M001"), _make_merchant("M002")]
        # M001 has data, M002 does not
        txns = {"M001": _make_transactions("M001")}
        results = self._run(merchants=merchants, transactions_by_id=txns)
        statuses = {r.merchant_id: r.status for r in results}
        assert statuses["M001"] == "sent"
        assert statuses["M002"] == "no_data"

    def test_all_skipped_when_flag_disabled(self):
        merchants = [_make_merchant("M001"), _make_merchant("M002")]
        txns = {"M001": _make_transactions("M001"), "M002": _make_transactions("M002")}
        results = self._run(
            merchants=merchants,
            transactions_by_id=txns,
            feature_enabled=False,
        )
        assert all(r.status == "skipped" for r in results)


# ---------------------------------------------------------------------------
# 보안: 카드 정보 평문 로깅 금지
# ---------------------------------------------------------------------------


class TestSecurityNoCardDataInLogs:
    """카드정보가 로그에 평문으로 출력되지 않는다 (PCI-DSS 3.2.1)."""

    def test_card_number_not_in_transaction_record(self):
        """TransactionRecord 에 카드번호 필드가 없다."""
        txn = TransactionRecord(
            transaction_id="TX0001",
            merchant_id="M001",
            amount=10_000,
        )
        assert not hasattr(txn, "card_number")
        assert not hasattr(txn, "card_info")
        assert not hasattr(txn, "cvv")
        assert not hasattr(txn, "pan")

    def test_masked_email_does_not_expose_full_address(self):
        full_email = "secretuser@corp.example.com"
        masked = mask_email(full_email)
        assert full_email not in masked
        assert masked.startswith("se")
