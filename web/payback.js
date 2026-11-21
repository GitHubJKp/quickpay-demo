// 쿠폰·페이백 서비스 v2.4.0 — 카드사별 할인 라우팅 프로필 (가상 데모 코드)
// 페이백 결제는 카드사별 전용 승인 경로로 보내야 카드사가 승인합니다.
// 화면(payback-app.js)과 테스트(tests/payback.test.mjs)가 같은 함수를 사용합니다.

export const CARDS = ['A', 'B', 'C'];
export const BENEFITS = { PAYBACK: '페이백', NONE: '일반 결제' };

export class PaybackRoutingResolver {
  static resolve({ card, benefit }) {
    if (benefit !== 'PAYBACK') return 'DEFAULT';
    if (card === 'A') return 'DEFAULT';
    return `${card}_PAYBACK`;
  }
}

// 카드사 승인 모의 응답표(가상): 경로가 카드사·혜택과 맞으면 승인(00), 아니면 거절(05)
const ISSUER_ACCEPTS = {
  DEFAULT: ['A:NONE', 'B:NONE', 'C:NONE'],
  A_PAYBACK: ['A:PAYBACK'],
  B_PAYBACK: ['B:PAYBACK'],
  C_PAYBACK: ['C:PAYBACK'],
};

/** 카드 승인 요청 (데모용 모의 응답) */
export function requestApproval({ card, benefit, amount }) {
  if (!CARDS.includes(card)) throw new Error(`지원하지 않는 카드사: ${card}`);
  if (!(benefit in BENEFITS)) throw new Error(`지원하지 않는 혜택: ${benefit}`);
  const route = PaybackRoutingResolver.resolve({ card, benefit });
  const approved = (ISSUER_ACCEPTS[route] || []).includes(`${card}:${benefit}`);
  return { card, benefit, amount, route, approved, code: approved ? '00' : '05' };
}
