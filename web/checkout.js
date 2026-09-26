// QuickPay 결제 금액 계산 모듈 (가상 데모 코드)
// 화면(app.js)과 테스트(tests/checkout.test.mjs)가 같은 함수를 사용합니다.

export const COUPONS = {
  WELCOME10: { type: 'percent', value: 10, label: '신규 고객 10% 할인' },
};

export const FREE_SHIPPING_THRESHOLD = 30000; // 3만 원 이상 무료 배송
export const SHIPPING_FEE = 3000;

/** 상품 금액 합계 */
export function subtotal(items) {
  return items.reduce((sum, item) => sum + item.price * item.qty, 0);
}

/** 쿠폰 할인액 (원 단위 절사) */
export function discountAmount(amount, coupon) {
  if (!coupon) return 0;
  if (coupon.type === 'percent') return Math.floor((amount * coupon.value) / 100);
  return 0;
}

/** 금액에 쿠폰을 적용한 결과 */
export function applyCoupon(amount, coupon) {
  return amount - discountAmount(amount, coupon);
}

/** 배송비: 할인 적용 후 금액 기준 */
export function shippingFee(amount) {
  return amount >= FREE_SHIPPING_THRESHOLD ? 0 : SHIPPING_FEE;
}

/**
 * 주문서에 표시할 금액 계산
 * @returns {{subtotal:number, discount:number, shipping:number, total:number}}
 */
export function calculateTotal(items, couponCode) {
  const coupon = COUPONS[couponCode];
  const sub = subtotal(items);
  const discounted = applyCoupon(sub, coupon);
  const discount = sub - discounted;
  const shipping = shippingFee(discounted);

  // 결제 금액 = 할인 적용 금액 + 배송비
  const total = applyCoupon(discounted, coupon) + shipping;

  return { subtotal: sub, discount, shipping, total };
}
