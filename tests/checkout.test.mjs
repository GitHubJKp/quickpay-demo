// 결제 금액 계산 테스트 — 실행: node --test tests/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { subtotal, discountAmount, shippingFee, calculateTotal, COUPONS } from '../web/checkout.js';

const CART = [
  { sku: 'BEAN-PREM-500', price: 18000, qty: 2 },
  { sku: 'DRIP-SET-10', price: 14000, qty: 1 },
];

test('상품 금액 합계', () => {
  assert.equal(subtotal(CART), 50000);
});

test('10% 쿠폰 할인액', () => {
  assert.equal(discountAmount(50000, COUPONS.WELCOME10), 5000);
});

test('3만 원 미만이면 배송비 3,000원', () => {
  assert.equal(shippingFee(14000), 3000);
  assert.equal(shippingFee(30000), 0);
});

test('쿠폰 없이 결제 금액 = 상품 금액 + 배송비', () => {
  assert.equal(calculateTotal([{ price: 14000, qty: 1 }]).total, 17000);
  assert.equal(calculateTotal(CART).total, 50000);
});

test('쿠폰 적용 시 할인 표시 금액', () => {
  assert.equal(calculateTotal(CART, 'WELCOME10').discount, 5000);
});

test('QPB-2: README 리허설 로그에 R4 자동 머지 검증 항목이 존재한다', () => {
  const readme = readFileSync(new URL('../README.md', import.meta.url), 'utf8');
  assert.ok(readme.includes('R4'), 'README에 R4 항목이 없습니다');
  assert.ok(readme.includes('QPB-2'), 'README에 QPB-2 항목이 없습니다');
  assert.ok(readme.includes('리허설 로그'), 'README에 리허설 로그 섹션이 없습니다');
});
