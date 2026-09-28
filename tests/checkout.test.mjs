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
