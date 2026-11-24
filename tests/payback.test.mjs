// 쿠폰·페이백 카드사별 승인 경로 테스트 — 실행: npm test
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { requestApproval } from '../web/payback.js';

const AMOUNT = 30000;

test('일반 결제는 기본 경로로 승인된다', () => {
  for (const card of ['A', 'B', 'C']) {
    const r = requestApproval({ card, benefit: 'NONE', amount: AMOUNT });
    assert.equal(r.route, 'DEFAULT');
    assert.equal(r.code, '00');
  }
});

// v2.5.0: 카드사별 페이백 경로 테스트를 표 기반으로 정리
for (const [card, route] of [['B', 'B_PAYBACK'], ['C', 'C_PAYBACK']]) {
  test(`${card}카드 페이백은 ${route} 경로로 승인된다`, () => {
    const r = requestApproval({ card, benefit: 'PAYBACK', amount: AMOUNT });
    assert.equal(r.route, route);
    assert.equal(r.code, '00');
  });
}

test('지원하지 않는 카드사는 오류', () => {
  assert.throws(() => requestApproval({ card: 'Z', benefit: 'PAYBACK', amount: AMOUNT }));
});

