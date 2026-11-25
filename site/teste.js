// Teste "Qual vereador combina com você?" (#/teste)
// Parte 1: votações das atas (dados/teste.json). Parte 2: pedidos por tema e bairro (dados/propostas.json).

function normBairro(s) {
  return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/\s+/g, " ").trim();
}

// Para cada vereador nomeado: quantas vezes ficou do lado da resposta e quantas contra.
function placarVotos(perguntas, respostas) {
  const lado = new Map(), contra = new Map();
  let respondidas = 0;
  const soma = (m, id) => m.set(id, (m.get(id) || 0) + 1);
  for (const q of perguntas) {
    const r = respostas[q.id];
    if (r !== "sim" && r !== "nao") continue;
    respondidas++;
    (r === "sim" ? q.sim : q.nao).forEach(id => soma(lado, id));
    (r === "sim" ? q.nao : q.sim).forEach(id => soma(contra, id));
  }
  const lista = m => [...m].map(([id, vezes]) => ({ id, vezes })).sort((x, y) => y.vezes - x.vezes || x.id - y.id);
  return { respondidas, lado: lista(lado), contra: lista(contra) };
}

// Pedidos (indicações e requerimentos) nos temas escolhidos; cada pedido do bairro vale 3 (1 + 2 de bônus).
function rankPedidos(propostas, temas, bairro, desde = "2025") {
  const alvo = normBairro(bairro), tem = new Set(temas), conta = new Map();
  let bairroAchado = false;
  for (const p of propostas) {
    if (p.g !== "pedidos" || String(p.a) < desde || !tem.has(p.tm)) continue;
    const noB = !!alvo && normBairro(p.b) === alvo;
    if (noB) bairroAchado = true;
    for (const id of new Set(p.au)) {
      const c = conta.get(id) || { id, total: 0, noBairro: 0, pontos: 0 };
      c.total++; if (noB) c.noBairro++;
      c.pontos = c.total + 2 * c.noBairro;
      conta.set(id, c);
    }
  }
  const top = [...conta.values()].sort((x, y) => y.pontos - x.pontos || y.total - x.total || x.id - y.id).slice(0, 5);
  return { top, bairroAchado };
}

if (typeof module !== "undefined") module.exports = { normBairro, placarVotos, rankPedidos };
