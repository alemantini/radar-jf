import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { normBairro, placarVotos, rankPedidos } = require("../site/teste.js");

test("normBairro tira acento, caixa e espaços", () => {
  assert.equal(normBairro("  São   Pedro "), "sao pedro");
});

const Q = [{ id: "a", sim: [], nao: [13, 42] }, { id: "b", sim: [44], nao: [25] }];
test("placar: resposta não junta quem votou contra", () => {
  const r = placarVotos(Q, { a: "nao" });
  assert.equal(r.respondidas, 1);
  assert.deepEqual(r.lado, [{ id: 13, vezes: 1 }, { id: 42, vezes: 1 }]);
  assert.deepEqual(r.contra, []);
});
test("placar: resposta sim inverte", () => {
  const r = placarVotos(Q, { a: "sim", b: "sim" });
  assert.deepEqual(r.lado, [{ id: 44, vezes: 1 }]);
  assert.deepEqual(r.contra.map(x => x.id), [13, 25, 42]);
});
test("placar: sem respostas", () => {
  assert.equal(placarVotos(Q, {}).respondidas, 0);
});
test("placar: ordena por vezes", () => {
  const r = placarVotos([{ id: "a", sim: [], nao: [13, 42] }, { id: "c", sim: [], nao: [42] }], { a: "nao", c: "nao" });
  assert.deepEqual(r.lado[0], { id: 42, vezes: 2 });
});

const P = [
  { g: "pedidos", a: 2024, au: [1], tm: "Saúde", b: "São Pedro" },
  { g: "cobrancas", a: 2025, au: [1], tm: "Saúde", b: "São Pedro" },
  { g: "pedidos", a: 2025, au: [1], tm: "Saúde", b: "São Pedro" },
  { g: "pedidos", a: 2026, au: [1, 2], tm: "Saúde", b: "Centro" },
  { g: "pedidos", a: 2026, au: [3], tm: "Iluminação", b: "São Pedro" },
];
test("rank: ignora 2024 e cobranças, bairro vale triplo, coautoria conta", () => {
  const r = rankPedidos(P, ["Saúde"], "sao pedro");
  assert.equal(r.bairroAchado, true);
  assert.deepEqual(r.top[0], { id: 1, total: 2, noBairro: 1, pontos: 4 });
  assert.deepEqual(r.top[1], { id: 2, total: 1, noBairro: 0, pontos: 1 });
  assert.equal(r.top.length, 2);
});
test("rank: bairro sem pedido", () => {
  const r = rankPedidos(P, ["Saúde"], "Grama");
  assert.equal(r.bairroAchado, false);
  assert.equal(r.top[0].pontos, 2);
});
test("rank: no máximo 5", () => {
  const muitos = Array.from({ length: 8 }, (_, i) => ({ g: "pedidos", a: 2025, au: [i + 1], tm: "Saúde" }));
  assert.equal(rankPedidos(muitos, ["Saúde"], "").top.length, 5);
});
