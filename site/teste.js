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


// ---------- página ----------
const TT_TEMAS = ["Esgoto e drenagem", "Buraco e asfalto", "Iluminação", "Capina e limpeza", "Lixo e coleta", "Poda e árvores", "Água",
  "Trânsito e sinalização", "Ônibus e transporte", "Praças e lazer", "Saúde", "Escolas e creches", "Animais"];
const TT_ATA = "https://www.camarajf.mg.gov.br/sal/ata.php?cod=";
const TT = { parte: 1, resp: {}, temas: [], bairro: "" };

function ttVereador(id, extra) {
  const v = VER[id] || { id, apelido: "vereador " + id };
  const fora = v.fora_da_lista ? `<small class="tt-fora">não está mais na Câmara</small>` : "";
  const nome = `${avatar(v)}<span class="tt-cx"><b>${esc(v.apelido)}</b> <small>${esc(v.partido || "")}</small>${fora}</span>${extra}`;
  return VER[id] ? `<a class="tt-v" href="#/v/${id}">${nome}</a>` : `<div class="tt-v">${nome}</div>`;
}

async function pgTeste(arg) {
  await Promise.all([carregarResumo(), carregarPropostas()]);
  let dados = null;
  try { dados = await fetch("dados/teste.json").then(r => r.ok ? r.json() : null); } catch (e) { dados = null; }
  const perguntas = (dados && dados.perguntas) || [];
  if (arg === "2") TT.parte = 2; else if (arg === "1") TT.parte = 1;

  // bairros que aparecem nos pedidos (grafia mais comum de cada um)
  const grafias = {};
  PROPOSTAS.forEach(p => { if (p.g === "pedidos" && p.b) { const k = normBairro(p.b); (grafias[k] = grafias[k] || {})[p.b] = (grafias[k][p.b] || 0) + 1; } });
  const bairros = Object.values(grafias).filter(g => Object.values(g).reduce((a, b) => a + b, 0) >= 3)
    .map(g => Object.entries(g).sort((a, b) => b[1] - a[1])[0][0]).sort((a, b) => a.localeCompare(b, "pt-BR"));

  app.innerHTML = `
    <h1>Teste: qual vereador combina com você?</h1>
    <p class="sub">Responda e veja quais vereadores de Juiz de Fora votaram como você e quais trabalham pelo que importa para você. Tudo com dados oficiais da Câmara. Nada do que você responde é gravado.</p>
    <div class="aviso-forte"><b>Este teste não é recomendação de voto.</b> Ele compara as suas respostas com votos e pedidos registrados. Um vereador é muito mais do que essas votações.</div>
    <div class="chips-filtro" id="tt-partes"><a href="javascript:void 0" data-p="1">Parte 1: votações</a><a href="javascript:void 0" data-p="2">Parte 2: o que importa para você</a></div>
    <div id="tt-corpo"></div>
    <details class="info tt-como"><summary><b>Como o teste calcula</b></summary>
      <p><b>Parte 1.</b> São votações em que pelo menos um vereador votou diferente da maioria, tiradas das atas oficiais. As atas só dão o nome de quem votou contra (nos projetos da prefeita) ou de quem ficou de um lado no veto; quem votou com a maioria quase nunca aparece com nome, e as atas não trazem a lista de presença em cada votação. Por isso o teste não calcula "porcentagem de afinidade": ele mostra só quem, com nome na ata, ficou do seu lado ou votou contra a sua escolha. Respostas "Pular" não contam.</p>
      <p><b>Parte 2.</b> Contamos os pedidos de serviço (indicações e requerimentos) de 2025 em diante sobre os temas escolhidos. Cada pedido conta 1 ponto; se o pedido cita o seu bairro, conta 3. Pedido feito por mais de um vereador conta para cada um. Mais pedidos não quer dizer mais serviço feito.</p>
      <p>Fontes: atas e sistema de proposições da Câmara Municipal de Juiz de Fora. A votação do vigilante armado nas escolas (19/11/2026) usa o placar divulgado pela imprensa até a ata ser publicada.</p>
    </details>`;

  const corpo = document.getElementById("tt-corpo");

  const desenhaParte1 = () => {
    if (!perguntas.length) { corpo.innerHTML = `<p class="sub">As perguntas desta parte não carregaram. Tente de novo mais tarde.</p>`; return; }
    corpo.innerHTML = `
      <p class="sub">${perguntas.length} votações. Você votaria Sim ou Não? Se não tiver opinião, pule.</p>
      ${perguntas.map((q, i) => `
        <div class="tt-q" data-id="${esc(q.id)}">
          <div class="tt-n">${i + 1}/${perguntas.length}</div>
          <p class="tt-perg">${esc(q.pergunta)}</p>
          <p class="sub">${esc(q.explica)} ${q.ata ? `<a href="${TT_ATA}${q.ata}" target="_blank" rel="noopener">ver na ata</a>` : q.link ? `<a href="${q.link}">ver o placar</a>` : ""}</p>
          ${q.aviso ? `<p class="sub"><small>${esc(q.aviso)}</small></p>` : ""}
          <div class="tt-bts">${[["sim", "Sim"], ["nao", "Não"], ["pular", "Pular"]].map(([k, t]) => `<button type="button" data-r="${k}" class="${TT.resp[q.id] === k ? "on" : ""}">${t}</button>`).join("")}</div>
        </div>`).join("")}
      <button type="button" class="btn-grande camara" id="tt-ver1">${ic("balanca")}<span class="tx">Ver meu resultado<small>Quem votou como você</small></span>›</button>
      <div id="tt-res1"></div>`;
    corpo.querySelectorAll(".tt-q").forEach(div => div.querySelectorAll("button").forEach(b => b.onclick = () => {
      TT.resp[div.dataset.id] = b.dataset.r;
      div.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
    }));
    document.getElementById("tt-ver1").onclick = () => {
      const r = placarVotos(perguntas, TT.resp);
      const res = document.getElementById("tt-res1");
      if (!r.respondidas) { res.innerHTML = `<p class="aviso-forte">Responda Sim ou Não em pelo menos uma votação.</p>`; res.scrollIntoView({ behavior: "smooth" }); return; }
      const de = n => `<span class="tt-nota">${n}<small>de ${r.respondidas}</small></span>`;
      const semNome = perguntas.filter(q => TT.resp[q.id] === "sim" || TT.resp[q.id] === "nao").filter(q => !(TT.resp[q.id] === "sim" ? q.sim : q.nao).length).length;
      res.innerHTML = `
        <h2>Ficaram do seu lado</h2>
        <p class="sub">Vereadores que a ata registra votando como você, e em quantas das ${r.respondidas} votações que você respondeu.</p>
        ${r.lado.map(x => ttVereador(x.id, de(x.vezes))).join("") || `<p class="sub">Nenhum vereador aparece com nome do seu lado nessas votações.</p>`}
        ${semNome ? `<p class="sub">Em ${semNome} das suas respostas você ficou com a maioria, e a ata não dá o nome de quem votou com a maioria. Por isso esses vereadores não aparecem aqui.</p>` : ""}
        <h2>Votaram contra a sua escolha</h2>
        ${r.contra.map(x => ttVereador(x.id, de(x.vezes))).join("") || `<p class="sub">Nenhum vereador aparece com nome votando contra a sua escolha.</p>`}
        ${ttCompartilhar(`Fiz o teste do Radar JFlândia. Votaram como eu: ${r.lado.slice(0, 3).map(x => nomeAutor(x.id)).join(", ") || "ninguém com nome na ata"}.`)}`;
      res.scrollIntoView({ behavior: "smooth", block: "start" });
    };
  };

  const desenhaParte2 = () => {
    corpo.innerHTML = `
      <p class="sub">Escolha o seu bairro e até 3 temas. Veja quais vereadores mais pediram serviços sobre isso desde 2025.</p>
      <label class="tt-lab" for="tt-bairro">Seu bairro</label>
      <input type="search" id="tt-bairro" list="tt-bairros" placeholder="Digite o bairro" autocomplete="off" value="${esc(TT.bairro)}">
      <datalist id="tt-bairros">${bairros.map(b => `<option value="${esc(b)}">`).join("")}</datalist>
      <p class="tt-lab">Temas (até 3)</p>
      <div class="tt-temas">${TT_TEMAS.map(t => `<button type="button" data-t="${esc(t)}" class="${TT.temas.includes(t) ? "on" : ""}">${esc(t)}</button>`).join("")}</div>
      <button type="button" class="btn-grande camara" id="tt-ver2">${ic("pessoas")}<span class="tx">Ver meu resultado<small>Quem cuida do que importa para você</small></span>›</button>
      <div id="tt-res2"></div>`;
    corpo.querySelectorAll(".tt-temas button").forEach(b => b.onclick = () => {
      const t = b.dataset.t;
      if (TT.temas.includes(t)) TT.temas = TT.temas.filter(x => x !== t);
      else if (TT.temas.length < 3) TT.temas.push(t);
      corpo.querySelectorAll(".tt-temas button").forEach(x => x.classList.toggle("on", TT.temas.includes(x.dataset.t)));
    });
    const inp = document.getElementById("tt-bairro");
    inp.oninput = () => TT.bairro = inp.value;
    document.getElementById("tt-ver2").onclick = () => {
      const res = document.getElementById("tt-res2");
      if (!TT.temas.length) { res.innerHTML = `<p class="aviso-forte">Escolha pelo menos um tema.</p>`; return; }
      const r = rankPedidos(PROPOSTAS, TT.temas, TT.bairro);
      const alvo = normBairro(TT.bairro);
      const deles = id => PROPOSTAS.filter(p => p.g === "pedidos" && String(p.a) >= "2025" && TT.temas.includes(p.tm) && p.au.includes(id))
        .sort((a, b) => (alvo && normBairro(b.b) === alvo) - (alvo && normBairro(a.b) === alvo) || (b.d || "").localeCompare(a.d || ""));
      res.innerHTML = `
        <h2>Quem mais pediu</h2>
        <p class="sub">${esc(TT.temas.join(", "))}${TT.bairro && r.bairroAchado ? `, com peso maior para ${esc(TT.bairro)}` : ""}.</p>
        ${TT.bairro && !r.bairroAchado ? `<p class="aviso-forte">Nenhum pedido sobre esses temas cita o bairro "${esc(TT.bairro)}". O resultado abaixo considera a cidade toda.</p>` : ""}
        ${r.top.map((x, i) => `${ttVereador(x.id, `<span class="tt-nota">${fmt(x.total)}<small>pedidos${x.noBairro ? `<br>${fmt(x.noBairro)} no bairro` : ""}</small></span>`)}
          <details class="tt-ped"><summary>Ver os pedidos de ${esc(nomeAutor(x.id))}</summary>${deles(x.id).slice(0, 30).map(p => itemHTML(p, false)).join("")}</details>`).join("")
          || `<p class="sub">Nenhum pedido sobre esses temas desde 2025.</p>`}
        <p class="sub">Mais pedidos não quer dizer mais serviço feito: alguns vereadores fazem um pedido por rua, outros um para o bairro inteiro.</p>
        ${ttCompartilhar(`Fiz o teste do Radar JFlândia. Quem mais pediu ${TT.temas.join(", ").toLowerCase()}${TT.bairro && r.bairroAchado ? " para " + TT.bairro : ""}: ${r.top.slice(0, 3).map(x => nomeAutor(x.id)).join(", ")}.`)}`;
      res.scrollIntoView({ behavior: "smooth", block: "start" });
    };
  };

  const desenha = () => {
    document.querySelectorAll("#tt-partes a").forEach(a => a.classList.toggle("on", +a.dataset.p === TT.parte));
    history.replaceState(null, "", "#/teste/" + TT.parte);
    (TT.parte === 1 ? desenhaParte1 : desenhaParte2)();
  };
  document.querySelectorAll("#tt-partes a").forEach(a => a.onclick = () => { TT.parte = +a.dataset.p; desenha(); });
  desenha();
}

function ttCompartilhar(texto) {
  const msg = texto + " Faça o seu: https://jflandia.com.br/#/teste";
  return `<a class="btn-grande" href="https://wa.me/?text=${encodeURIComponent(msg)}" target="_blank" rel="noopener">${ic("fala")}<span class="tx">Compartilhar no WhatsApp<small>Manda o seu resultado, sem as suas respostas</small></span>›</a>`;
}

if (typeof module !== "undefined") module.exports = { normBairro, placarVotos, rankPedidos };
