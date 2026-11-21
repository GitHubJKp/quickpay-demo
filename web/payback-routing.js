// QuickPay 카드사별 할인(페이백) 승인 경로 선택 모듈 (가상 데모 코드)
// QPB-10: 페이백 행사에서 A카드 결제가 기본 경로로 나가 승인 거절(응답 05)된 장애의 재발 방지.

export const CARD_ROUTING_V2_FLAG = 'coupon.card-routing.v2';

/** 기능 플래그 기본값 — 라우팅 변경은 OFF로 배포한 뒤 카나리로 켭니다. */
export const DEFAULT_FLAGS = Object.freeze({ [CARD_ROUTING_V2_FLAG]: false });

export const ROUTES = Object.freeze({
  DEFAULT: 'pg-default',
  A_PAYBACK: 'pg-card-a-payback',
  B_PAYBACK: 'pg-card-b-payback',
  C_PAYBACK: 'pg-card-c-payback',
});

/** 카드사 코드 → 전용 승인 경로 */
const CARD_ROUTE_MAP = Object.freeze({
  A: ROUTES.A_PAYBACK,
  B: ROUTES.B_PAYBACK,
  C: ROUTES.C_PAYBACK,
});

export class PaybackRoutingResolver {
  constructor(flags = {}) {
    this.flags = { ...DEFAULT_FLAGS, ...flags };
  }

  isV2Enabled() {
    return this.flags[CARD_ROUTING_V2_FLAG] === true;
  }

  /**
   * 카드사 코드로 승인 경로를 고릅니다.
   * 플래그 OFF면 기존(v2.4.0)처럼 기본 경로, ON이면 카드사 전용 경로(매핑 없으면 기본 경로).
   */
  resolve(cardIssuer) {
    if (!this.isV2Enabled()) return ROUTES.DEFAULT;
    const key = String(cardIssuer ?? '').trim().toUpperCase();
    return CARD_ROUTE_MAP[key] ?? ROUTES.DEFAULT;
  }
}
