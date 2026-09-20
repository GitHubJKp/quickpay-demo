"""가맹점 월간 정산 리포트 생성 (QPAY-4).

현재는 스텁이다. 스케줄링과 발송 이력 기록이 아직 구현되지 않았다.
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class SettlementReport:
    merchant_id: str
    period: str
    total_amount: int


def build_report(merchant_id: str, period: date) -> SettlementReport:
    """전월 거래를 집계해 리포트를 만든다.

    TODO(QPAY-4): 매월 1일 00:00 스케줄 실행을 붙인다.
    TODO(QPAY-4): 가맹점 관리자 이메일 발송과 재시도(3회)를 구현한다.
    TODO(QPAY-4): 발송 이력(가맹점ID, 발송 시각, 결과)을 정산 DB에 기록한다.
    TODO(QPAY-4): 전월 거래 0건이면 빈 리포트를 만들지 않는다.
    """
    return SettlementReport(merchant_id=merchant_id, period=period.strftime("%Y-%m"), total_amount=0)
