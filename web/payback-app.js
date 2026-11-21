import { requestApproval, BENEFITS } from './payback.js';

const AMOUNT = 30000;
const $ = (id) => document.getElementById(id);
const won = (n) => '₩' + n.toLocaleString('ko-KR');
const picked = (name) => document.querySelector(`input[name="${name}"]:checked`).value;

$('amount').textContent = won(AMOUNT);

$('approve').addEventListener('click', () => {
  const card = picked('card');
  const benefit = picked('benefit');
  const r = requestApproval({ card, benefit, amount: AMOUNT });
  const box = $('answer');
  box.className = 'result ' + (r.approved ? 'ok' : 'error');
  box.innerHTML = r.approved
    ? `<b>응답 00 · 승인 완료</b><br>${card}카드 · ${BENEFITS[benefit]} · ${won(AMOUNT)} · 승인 경로 ${r.route}`
    : `<b>응답 05 · 승인 거절</b><br>${card}카드 · ${BENEFITS[benefit]} · ${won(AMOUNT)} · 승인 경로 ${r.route}`;
});

fetch('./build.json', { cache: 'no-store' })
  .then((res) => res.json())
  .then((b) => { if (b.commit && b.commit !== 'local') $('build').textContent = `빌드 ${b.commit} · ${b.deployedAt} · ${b.message}`; })
  .catch(() => {});
