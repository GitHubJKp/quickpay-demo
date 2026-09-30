// 결제 금액 계산 테스트 — 실행: node --test tests/
import { test } from 'node:test';
import assert from 'node:assert/strict';
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

// QPB-8 회귀 테스트: 쿠폰 할인이 두 번 적용되어 최종 금액이 잘못 계산되는 버그
test('WELCOME10 쿠폰 적용 시 최종 결제 금액은 쿠폰 한 번만 적용한 금액이어야 함', () => {
  // 상품 50,000원에 10% 할인 → 45,000원, 3만 원 이상이므로 배송비 무료
  // 서버(quote.json)의 expectedTotal과 일치해야 결제 승인됨
  const result = calculateTotal(CART, 'WELCOME10');
  assert.equal(result.total, 45000, '쿠폰이 두 번 적용되면 40,500원이 되어 amount mismatch 오류 발생');
});

test('WELCOME10 쿠폰 적용 시 각 항목 금액 검증', () => {
  const result = calculateTotal(CART, 'WELCOME10');
  assert.equal(result.subtotal, 50000);
  assert.equal(result.discount, 5000);
  assert.equal(result.shipping, 0);
  assert.equal(result.total, 45000);
});
