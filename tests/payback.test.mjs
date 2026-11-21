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

test('B카드 페이백은 B 전용 경로로 승인된다', () => {
  const r = requestApproval({ card: 'B', benefit: 'PAYBACK', amount: AMOUNT });
  assert.equal(r.route, 'B_PAYBACK');
  assert.equal(r.code, '00');
});

test('C카드 페이백은 C 전용 경로로 승인된다', () => {
  const r = requestApproval({ card: 'C', benefit: 'PAYBACK', amount: AMOUNT });
  assert.equal(r.route, 'C_PAYBACK');
  assert.equal(r.code, '00');
});

test('지원하지 않는 카드사는 오류', () => {
  assert.throws(() => requestApproval({ card: 'Z', benefit: 'PAYBACK', amount: AMOUNT }));
});

test('QPB-11 회귀: A카드 페이백은 A_PAYBACK 경로로 승인된다', () => {
  const r = requestApproval({ card: 'A', benefit: 'PAYBACK', amount: AMOUNT });
  assert.equal(r.route, 'A_PAYBACK');
  assert.equal(r.code, '00');
});
