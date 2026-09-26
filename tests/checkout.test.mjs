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

// 회귀 테스트: QPB-1 — 쿠폰 적용 시 최종 결제 금액 이중 할인 버그
test('WELCOME10 쿠폰 적용 시 최종 결제 금액 = 45,000원 (이중 할인 없음)', () => {
  // 상품 합계 50,000 → 10% 할인 5,000 → 할인 후 45,000 (무료 배송)
  // 버그: applyCoupon을 두 번 적용하면 40,500이 나옴
  const r = calculateTotal(CART, 'WELCOME10');
  assert.equal(r.total, 45000, '쿠폰이 두 번 적용되면 안 됩니다');
});
