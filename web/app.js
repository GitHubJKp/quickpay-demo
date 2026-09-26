import { calculateTotal, COUPONS } from './checkout.js';

const CART = [
  { sku: 'BEAN-PREM-500', name: '달빛 프리미엄 원두 500g', price: 18000, qty: 2 },
  { sku: 'DRIP-SET-10', name: '드립백 10개입 세트', price: 14000, qty: 1 },
];
const COUPON_CODE = 'WELCOME10';

const won = (n) => '₩' + n.toLocaleString('ko-KR');
const $ = (id) => document.getElementById(id);

function render() {
  $('items').innerHTML = CART.map((i) => `
    <li><span class="name">${i.name}<small> × ${i.qty}</small></span>
        <span>${won(i.price * i.qty)}</span></li>`).join('');

  const r = calculateTotal(CART, COUPON_CODE);
  $('subtotal').textContent = won(r.subtotal);
  $('coupon-label').textContent = `${COUPON_CODE} · ${COUPONS[COUPON_CODE].label}`;
  $('discount').textContent = '−' + won(r.discount);
  $('shipping').textContent = r.shipping === 0 ? '무료' : won(r.shipping);
  $('total').textContent = won(r.total);
  $('pay').textContent = `${won(r.total)} 결제하기`;
  return r;
}

async function pay(displayed) {
  const btn = $('pay');
  btn.disabled = true;
  btn.textContent = '결제 승인 요청 중…';
  // 결제 서버(PG)에 주문 금액 검증 요청 (데모: 정적 JSON)
  const res = await fetch('./api/quote.json?order=ORD-20260930-0042', { cache: 'no-store' });
  const quote = await res.json();

  if (quote.expectedTotal !== displayed.total) {
    console.error('[QuickPay] E-AMOUNT-MISMATCH 결제 금액 불일치', {
      orderId: quote.orderId,
      displayedTotal: displayed.total,
      serverExpectedTotal: quote.expectedTotal,
      couponCode: COUPON_CODE,
    });
    showResult('error', `결제가 거절되었습니다. 결제 금액이 주문 금액과 다릅니다. (오류 코드 E-AMOUNT-MISMATCH)`);
  } else {
    console.info('[QuickPay] 결제 승인 완료', { orderId: quote.orderId, total: displayed.total });
    showResult('ok', `결제가 완료되었습니다. 주문번호 ${quote.orderId} · ${won(displayed.total)}`);
  }
  btn.disabled = false;
  btn.textContent = `${won(displayed.total)} 결제하기`;
}

function showResult(kind, msg) {
  const el = $('result');
  el.className = 'result ' + kind;
  el.textContent = msg;
}

async function showBuild() {
  try {
    const b = await (await fetch('./build.json', { cache: 'no-store' })).json();
    $('build').textContent = b.commit === 'local'
      ? '로컬 빌드'
      : `빌드 ${b.commit} · ${b.deployedAt} 배포${b.message ? ' · ' + b.message : ''}`;
  } catch { $('build').textContent = ''; }
}

const result = render();
$('pay').addEventListener('click', () => pay(result));
showBuild();
