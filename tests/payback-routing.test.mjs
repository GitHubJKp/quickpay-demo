// 카드사별 할인 라우팅 테스트 (QPB-10) — 실행: node --test tests/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  PaybackRoutingResolver,
  ROUTES,
  CARD_ROUTING_V2_FLAG,
  DEFAULT_FLAGS,
} from '../web/payback-routing.js';

const v2On = new PaybackRoutingResolver({ [CARD_ROUTING_V2_FLAG]: true });
const v2Off = new PaybackRoutingResolver({ [CARD_ROUTING_V2_FLAG]: false });

test('기능 플래그 coupon.card-routing.v2 기본값은 OFF', () => {
  assert.equal(DEFAULT_FLAGS[CARD_ROUTING_V2_FLAG], false);
  assert.equal(new PaybackRoutingResolver().isV2Enabled(), false);
});

test('[회귀] 플래그 ON: A카드는 기본 경로가 아니라 A카드 전용 승인 경로를 반환', () => {
  const route = v2On.resolve('A');
  assert.notEqual(route, ROUTES.DEFAULT);
  assert.equal(route, ROUTES.A_PAYBACK);
});

test('플래그 ON: B카드·C카드는 각 카드사 경로를 반환', () => {
  assert.equal(v2On.resolve('B'), ROUTES.B_PAYBACK);
  assert.equal(v2On.resolve('C'), ROUTES.C_PAYBACK);
});

test('플래그 ON: 카드사 코드는 대소문자·공백을 무시', () => {
  assert.equal(v2On.resolve(' a '), ROUTES.A_PAYBACK);
});

test('플래그 ON: 매핑이 없는 카드사는 기본 경로', () => {
  assert.equal(v2On.resolve('Z'), ROUTES.DEFAULT);
  assert.equal(v2On.resolve(undefined), ROUTES.DEFAULT);
});

test('플래그 OFF: 기존(v2.4.0) 동작 유지 — 모든 카드사 기본 경로', () => {
  for (const card of ['A', 'B', 'C']) assert.equal(v2Off.resolve(card), ROUTES.DEFAULT);
});
