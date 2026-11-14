"use strict";
const FONTE = id => `https://www.camarajf.mg.gov.br/sal/proposicaon.php?num=${id}`;
const BUSCA_CAMARA = "https://www.camarajf.mg.gov.br/sal/buscapropos.php";
const ORDEM = ["pedidos", "cobrancas", "homenagens", "leis", "outros"];
const CURTO = {pedidos: "Pedidos nos bairros", cobrancas: "Perguntas e cobranças", homenagens: "Homenagens", leis: "Propostas de lei", outros: "Outros"};
const TIPOS = {REQ: "Requerimento", IND: "Indicação", PEDIF: "Pedido de Informação", REP: "Representação", MOC: "Moção", PLEI: "Projeto de Lei", PLEIC: "Projeto de Lei Complementar", PELOR: "Emenda à Lei Orgânica", PRES: "Projeto de Resolução", PDL: "Projeto de Decreto Legislativo"};

// ícones simples (traço), usados nos botões
const ICONE = {
  camara: '<path d="M3 21h18M5 21V10M9.5 21V10M14.5 21V10M19 21V10M2 10l10-6 10 6z"/>',
  dinheiro: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h.01M18 12h.01"/>',
  pin: '<path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
  repete: '<path d="M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3"/>',
  lupa: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  pessoas: '<circle cx="9" cy="7" r="4"/><path d="M2 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2M16 3.1a4 4 0 0 1 0 7.8M22 21v-2a4 4 0 0 0-3-3.9"/>',
  predios: '<path d="M3 21h18M5 21V4h9v17M14 9h5v12M8 8h3M8 12h3M8 16h3"/>',
  maleta: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2M2 13h20"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
};
const ic = (n, cls = "") => `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONE[n] || ""}</svg>`;
const iniciais = n => String(n || "").replace(/^(Dr|Dra|Sargento|Prof|Profa)\.?\s+/i, "").split(/\s+/).filter(p => p.length > 2 || /^[A-ZÀ-Ý]/.test(p)).slice(0, 2).map(p => p[0]).join("").toUpperCase();

let RESUMO = null, PROPOSTAS = null, REPETIDOS = null, POR_ID = null, VER = {};
const app = document.getElementById("app");

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const norm = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const fmt = n => (n || 0).toLocaleString("pt-BR");
const dataBR = d => d ? d.split("-").reverse().join("/") : "";

async function carregarResumo() {
  if (RESUMO) return;
  RESUMO = await fetch("dados/resumo.json").then(r => r.json());
  RESUMO.vereadores.forEach(v => VER[v.id] = v);
  document.getElementById("atualizado").textContent = RESUMO.atualizado ? `Última coleta: ${RESUMO.atualizado}.` : "";
}
async function carregarPropostas() {
  if (PROPOSTAS) return;
  app.innerHTML = '<p class="carregando">Carregando todas as propostas (pode levar alguns segundos no celular)…</p>';
  PROPOSTAS = await fetch("dados/propostas.json").then(r => r.json());
  POR_ID = new Map(PROPOSTAS.map(p => [p.i, p]));
  PROPOSTAS.forEach(p => p._busca = norm(`${p.e} ${p.r || ""} ${p.b || ""}`));
}
async function carregarRepetidos() {
  if (REPETIDOS) return;
  REPETIDOS = await fetch("dados/repetidos.json").then(r => r.json());
}

function nomeAutor(id) {
  const v = VER[id];
  return v ? v.apelido : "?";
}

function itemHTML(p, mostrarAutor = true) {
  const autores = p.au.map(a => `<a href="#/v/${a}">${esc(nomeAutor(a))}</a>`).join(", ");
  return `<div class="item">
    <div class="topo"><span class="tag g-${p.g}">${CURTO[p.g]}</span>${esc(TIPOS[p.t] || p.t)} nº ${esc(p.n)}/${p.a}${p.d ? " · " + dataBR(p.d) : ""}</div>
    <div class="txt">${esc(p.e)}</div>
    <div class="pe">${mostrarAutor && autores ? "Autoria: " + autores + " · " : ""}${esc(p.s)} · <a href="${FONTE(p.i)}" target="_blank" rel="noopener">documento oficial</a></div>
  </div>`;
}

function lista(itens, alvo, porPagina = 40, mostrarAutor = true) {
  let n = 0;
  const box = document.createElement("div");
  const btn = document.createElement("button");
  btn.className = "mais";
  const mais = () => {
    box.insertAdjacentHTML("beforeend", itens.slice(n, n + porPagina).map(p => itemHTML(p, mostrarAutor)).join(""));
    n += porPagina;
    btn.style.display = n < itens.length ? "block" : "none";
    btn.textContent = `Mostrar mais (${fmt(itens.length - n)} restantes)`;
  };
  btn.onclick = mais;
  alvo.append(box, btn);
  mais();
}

function barras(c) {
  const max = Math.max(1, ...ORDEM.map(g => c[g] || 0));
  return ORDEM.map(g => `<div class="barra"><span class="r">${CURTO[g]}</span><span class="b g-${g}" style="width:${Math.round(110 * (c[g] || 0) / max)}px"></span><span class="n">${fmt(c[g])}</span></div>`).join("");
}

function ordenaData(a, b) {
  return (b.d || "").localeCompare(a.d || "") || b.a - a.a || (parseInt(b.n) || 0) - (parseInt(a.n) || 0);
}

// ---------- páginas ----------
function pgInicio() {
  const anos = RESUMO.anos;
  const periodo = anos.length > 1 ? `${anos[0]} a ${anos[anos.length - 1]}` : anos[0];
  const atuais = RESUMO.vereadores.filter(v => !v.fora_da_lista);
  const fora = RESUMO.vereadores.filter(v => v.fora_da_lista);
  const card = v => `<a class="card${v.fora_da_lista ? " fora" : ""}" href="#/v/${v.id}">
      <span class="avatar" aria-hidden="true">${esc(iniciais(v.apelido))}</span>
      <span class="cx">
        <div class="nome">${esc(v.apelido)}</div>
        <div class="partido">${esc(v.partido || "não está na lista atual da Câmara")}</div>
        <div class="barras">${barras(v.contagem)}</div>
      </span>
    </a>`;
  app.innerHTML = `
    <h1>O que fazem os vereadores de Juiz de Fora</h1>
    <p class="sub">Tudo o que cada vereador apresentou na Câmara de ${periodo}, contado com a mesma regra para todos. Só dados oficiais, com link para cada documento.</p>
    <a class="btn-grande camara" href="#/busca">${ic("pin")}<span class="tx">O que foi pedido para o seu bairro<small>Digite o nome da rua ou do bairro</small></span>›</a>
    <a class="btn-grande camara" href="#/repetidos">${ic("repete")}<span class="tx">Pedidos que voltam<small>Mesmo pedido, mesma rua, várias vezes</small></span>›</a>
    <h2>Os ${atuais.length} vereadores</h2>
    <div class="info">Em ordem alfabética. O site não dá nota nem faz ranking: mostra os números para você tirar suas conclusões. <a href="#/sobre">Entenda cada grupo</a>.</div>
    <div class="cards">${atuais.map(card).join("")}</div>
    ${fora.length ? `<h2>Outros autores nesta legislatura</h2><p class="sub">Pessoas que apresentaram propostas mas não aparecem hoje na lista oficial de vereadores (por exemplo, suplentes que já saíram).</p><div class="cards">${fora.map(card).join("")}</div>` : ""}`;
}

async function pgVereador(id) {
  const v = VER[id];
  if (!v) { app.innerHTML = "<p>Vereador não encontrado.</p>"; return; }
  await carregarPropostas();
  const meus = PROPOSTAS.filter(p => p.au.includes(v.id)).sort(ordenaData);
  const c = v.contagem;
  app.innerHTML = `
    <h1>${esc(v.apelido)}</h1>
    <p class="sub">${esc(v.nome)}${v.partido ? " · " + esc(v.partido) : ""}${v.observacao ? "<br>" + esc(v.observacao[0].toUpperCase() + v.observacao.slice(1)) : ""}</p>
    ${v.email_gabinete || v.telefone_gabinete ? `<p class="contato">Gabinete: ${v.email_gabinete ? `<a href="mailto:${esc(v.email_gabinete)}">${esc(v.email_gabinete)}</a>` : ""} ${esc(v.telefone_gabinete)}</p>` : ""}
    ${v.ficha ? `<p class="contato"><a href="${esc(v.ficha)}" target="_blank" rel="noopener">Ficha oficial na Câmara</a></p>` : ""}
    <h2>${fmt(c.total)} propostas apresentadas</h2>
    ${c.coautoria ? `<p class="sub">${fmt(c.coautoria)} delas foram assinadas junto com outros vereadores.</p>` : ""}
    <div id="grupos"></div>
    <div id="lista"></div>`;
  const grupos = document.getElementById("grupos");
  const alvo = document.getElementById("lista");
  const mostra = g => {
    alvo.innerHTML = `<h2>${g ? CURTO[g] : "Todas"}</h2>`;
    lista(g ? meus.filter(p => p.g === g) : meus, alvo, 40, true);
    grupos.querySelectorAll("button").forEach(b => b.classList.toggle("on", b.dataset.g === (g || "")));
  };
  grupos.className = "grupos";
  grupos.innerHTML = ORDEM.map(g => `<button class="grupo-link" data-g="${g}"><span class="gn"><span class="ponto g-${g}"></span>${CURTO[g]}</span><b>${fmt(c[g])}</b></button>`).join("");
  grupos.querySelectorAll("button").forEach(b => b.onclick = () => { mostra(b.dataset.g); alvo.scrollIntoView({behavior: "smooth"}); });
  mostra(null);
}

async function pgBusca(q0) {
  await carregarPropostas();
  app.innerHTML = `
    <h1>O que foi pedido para o seu bairro</h1>
    <p class="sub">Digite o nome do bairro ou da rua. Aparecem todos os pedidos e cobranças que citam esse lugar, e quem pediu.</p>
    <input type="search" id="q" placeholder="Ex.: São Pedro, Rua Halfeld, Benfica" value="${esc(q0 || "")}" autocomplete="off">
    <div class="filtros" id="f"></div>
    <div id="res"></div>`;
  const inp = document.getElementById("q");
  let filtro = "todos";
  const f = document.getElementById("f");
  const opcoes = [["todos", "Tudo"], ["pedidos", "Pedidos"], ["cobrancas", "Cobranças"]];
  f.innerHTML = opcoes.map(([k, t]) => `<button data-k="${k}" class="${k === filtro ? "on" : ""}">${t}</button>`).join("");
  const busca = () => {
    const q = norm(inp.value.trim());
    history.replaceState(null, "", "#/busca/" + encodeURIComponent(inp.value.trim()));
    const res = document.getElementById("res");
    if (q.length < 3) { res.innerHTML = '<p class="sub">Digite pelo menos 3 letras.</p>'; return; }
    const termos = q.split(/\s+/);
    const achados = PROPOSTAS.filter(p => (p.g === "pedidos" || p.g === "cobrancas") && (filtro === "todos" || p.g === filtro) && termos.every(t => p._busca.includes(t))).sort(ordenaData);
    const quem = {};
    achados.forEach(p => p.au.forEach(a => quem[a] = (quem[a] || 0) + 1));
    const top = Object.entries(quem).sort((a, b) => b[1] - a[1]).map(([a, n]) => `<a href="#/v/${a}">${esc(nomeAutor(+a))}</a> (${n})`).join(", ");
    res.innerHTML = `<h2>${fmt(achados.length)} resultados</h2>${achados.length ? `<p class="sub">Quem pediu: ${top}</p>` : ""}`;
    lista(achados, res, 40, true);
  };
  f.querySelectorAll("button").forEach(b => b.onclick = () => { filtro = b.dataset.k; f.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b)); busca(); });
  let t; inp.oninput = () => { clearTimeout(t); t = setTimeout(busca, 250); };
  inp.focus();
  busca();
}

async function pgRepetidos() {
  await Promise.all([carregarRepetidos(), carregarPropostas()]);
  app.innerHTML = `
    <h1>Pedidos que voltam</h1>
    <p class="sub">Quando o mesmo tipo de pedido (por exemplo, iluminação ou buraco) é feito várias vezes para a mesma rua.</p>
    <div class="aviso"><b>Atenção:</b> pedido repetido não prova que a Prefeitura ignorou. O problema pode ter sido resolvido e voltado, o pedido pode ser para trechos diferentes da rua, ou mais de um vereador pode ter pedido a mesma coisa. Abra cada documento para conferir.</div>
    <input type="search" id="q" placeholder="Filtrar por bairro, rua ou tipo de pedido" autocomplete="off">
    <div id="res"></div>`;
  const inp = document.getElementById("q");
  const mostra = () => {
    const q = norm(inp.value.trim());
    const itens = REPETIDOS.filter(r => !q || norm(`${r.r} ${r.b} ${r.tm}`).includes(q));
    const res = document.getElementById("res");
    res.innerHTML = `<p class="sub">${fmt(itens.length)} ruas com pedidos repetidos.</p>`;
    let n = 0;
    const btn = document.createElement("button"); btn.className = "mais";
    const box = document.createElement("div");
    const mais = () => {
      box.insertAdjacentHTML("beforeend", itens.slice(n, n + 30).map((r, k) => {
        const ps = r.ids.map(i => POR_ID.get(i)).filter(Boolean);
        const datas = ps.map(p => p.d ? dataBR(p.d) : `${p.n}/${p.a}`).join(", ");
        const quem = [...new Set(ps.flatMap(p => p.au))].map(a => esc(nomeAutor(a))).join(", ");
        return `<div class="rep"><div><span class="q">${r.q}×</span> <b>${esc(r.tm)}</b></div>
          <div>${esc(r.r)}${r.b ? ", " + esc(r.b) : ""}</div>
          <div class="pe" style="font-size:14px;color:#555">Quando: ${datas}<br>Quem pediu: ${quem}</div>
          <details><summary>Ver os ${r.q} pedidos</summary>${ps.map(p => itemHTML(p, true)).join("")}</details></div>`;
      }).join(""));
      n += 30;
      btn.style.display = n < itens.length ? "block" : "none";
      btn.textContent = `Mostrar mais (${fmt(itens.length - n)} restantes)`;
    };
    btn.onclick = mais;
    res.append(box, btn);
    mais();
  };
  let t; inp.oninput = () => { clearTimeout(t); t = setTimeout(mostra, 250); };
  mostra();
}

function pgSobre() {
  const t = RESUMO.totais;
  app.innerHTML = `
    <h1>Como funciona</h1>
    <div class="placa camara">${ic("camara")}<span class="tx"><span class="tt">Câmara Municipal</span></span></div>
    <p>Este site reúne o que cada vereador de Juiz de Fora apresentou na Câmara Municipal. Todos os dados vêm do <a href="${BUSCA_CAMARA}" target="_blank" rel="noopener">sistema oficial da Câmara (iS@l)</a> e cada proposta tem link para o documento original. Um robô baixa tudo de novo toda madrugada.</p>
    <h2>Os cinco grupos</h2>
    <ul>${RESUMO.regras.map(r => `<li>${esc(r)}</li>`).join("")}</ul>
    <p class="sub">No total: ${ORDEM.map(g => `${CURTO[g]} ${fmt(t[g])}`).join(" · ")}.</p>
    <h2>Regras que valem para todos</h2>
    <ul>
      <li>Só dado oficial. Nada de print, boato ou reportagem como fonte de número.</li>
      <li>Todos os vereadores, de todos os partidos, contados com a mesma regra.</li>
      <li>Quando uma proposta tem mais de um autor, ela conta para cada um deles.</li>
      <li>Só contato público: e-mail e telefone do gabinete, como estão no site da Câmara.</li>
    </ul>
    <h2>O que é estimativa</h2>
    <ul>
      <li>A divisão em grupos e a identificação de rua, bairro e tipo de pedido são feitas automaticamente pelo texto oficial. Pode haver erro pontual.</li>
      <li>A data de cada proposta é a primeira data de tramitação registrada no sistema. ${RESUMO.sem_data ? `Ainda faltam as datas de ${fmt(RESUMO.sem_data)} propostas, que o robô busca aos poucos para não sobrecarregar o site da Câmara.` : ""}</li>
    </ul>
    <h2>O que este site ainda não mostra</h2>
    <p>Presença dos vereadores nas reuniões e como cada um votou. A Câmara de Juiz de Fora não publica esses registros de forma que possam ser baixados (as atas aparecem na lista, mas o texto não abre). Sem dado oficial, o site não mostra número nenhum, e falta de registro não é tratada como falta do vereador.</p>
    <h2>Achou um erro?</h2>
    <p><a href="https://github.com/alemantini/radar-jf/issues/new" target="_blank" rel="noopener">Avise aqui</a>. Erros são corrigidos o mais rápido possível. O código do site é aberto e pode ser conferido por qualquer pessoa.</p>`;
}

// ---------- rotas ----------
const SUBNAV = {
  camara: [["#/camara", "Vereadores", "pessoas"], ["#/busca", "Meu bairro", "pin"], ["#/repetidos", "Pedidos que voltam", "repete"]],
  prefeitura: [["#/prefeitura", "Gastos por secretaria", "predios"], ["#/prefeitura/fornecedores", "Quem recebe", "maleta"], ["#/prefeitura/busca", "Buscar gasto", "lupa"]],
};
const SELO = {
  camara: () => `<div class="placa camara">${ic("camara")}<span class="tx"><span class="tt">Câmara Municipal de Juiz de Fora</span><span class="ds">O que os vereadores apresentam. Fonte: sistema oficial da Câmara.</span></span></div>`,
  prefeitura: () => `<div class="placa prefeitura">${ic("dinheiro")}<span class="tx"><span class="tt">Prefeitura de Juiz de Fora</span><span class="ds">Para onde vai o dinheiro. Fonte: Portal da Transparência.</span></span></div>`,
};

function pgEscolha() {
  const nV = RESUMO.vereadores.filter(v => !v.fora_da_lista).length;
  app.innerHTML = `
    <h1>Câmara e Prefeitura de Juiz de Fora, com dados oficiais</h1>
    <p class="sub">Escolha o que você quer acompanhar. Cada número tem a fonte oficial ao lado.</p>
    <div class="escolhas">
      <a class="placa camara" href="#/camara">${ic("camara")}<span class="tx"><span class="tt">Câmara</span><span class="ds">O que cada um dos ${nV} vereadores apresentou, e o que foi pedido para o seu bairro.</span><span class="num">${fmt(RESUMO.total)} propostas</span></span><span class="seta">›</span></a>
      <a class="placa prefeitura" href="#/prefeitura">${ic("dinheiro")}<span class="tx"><span class="tt">Prefeitura</span><span class="ds">Para onde vai o dinheiro: quanto cada secretaria gasta, com quem e em quê.</span><span class="num">Gastos por secretaria</span></span><span class="seta">›</span></a>
    </div>
    <a class="btn-grande camara" href="#/busca">${ic("pin")}<span class="tx">Pesquisar meu bairro<small>Pedidos dos vereadores para a sua rua</small></span>›</a>
    <a class="btn-grande prefeitura" href="#/prefeitura/busca">${ic("lupa")}<span class="tx">Pesquisar um gasto<small>Empresa, CNPJ ou palavra, como asfalto ou merenda</small></span>›</a>
    <div class="info">Câmara e Prefeitura são poderes diferentes. A Câmara (vereadores) faz leis, fiscaliza e pede melhorias. A Prefeitura (prefeita e secretarias) executa os serviços e gasta o orçamento.</div>`;
}

async function rota() {
  await carregarResumo();
  const h = location.hash.replace(/^#\/?/, "");
  const partes = h.split("/").map(decodeURIComponent);
  const pag = partes[0], arg = partes.slice(1).join("/");
  const area = pag === "prefeitura" ? "prefeitura" : ["camara", "v", "busca", "repetidos"].includes(pag) ? "camara" : pag === "sobre" ? "sobre" : "";
  document.querySelectorAll("nav.areas a").forEach(a => a.classList.toggle("ativo", a.dataset.area === area));
  const sub = document.getElementById("subnav");
  const atual = "#/" + h;
  sub.className = area;
  sub.innerHTML = (SUBNAV[area] || []).map(([href, t, i]) => `<a href="${href}" class="${atual === href || (atual.startsWith(href + "/") && href !== "#/prefeitura") || (href === "#/prefeitura" && /^#\/prefeitura\/(ano|s)\b/.test(atual)) || (href === "#/camara" && atual.startsWith("#/v/")) ? "ativo" : ""}">${ic(i)}${t}</a>`).join("");
  document.getElementById("selo").innerHTML = SELO[area] ? SELO[area]() : "";
  window.scrollTo(0, 0);
  try {
    if (pag === "v") await pgVereador(+arg);
    else if (pag === "busca") await pgBusca(arg);
    else if (pag === "repetidos") await pgRepetidos();
    else if (pag === "sobre") { pgSobre(); if (window.sobrePrefeitura) await sobrePrefeitura(); }
    else if (pag === "camara") pgInicio();
    else if (pag === "prefeitura" && window.rotaPrefeitura) await rotaPrefeitura(partes.slice(1));
    else pgEscolha();
  } catch (e) {
    app.innerHTML = `<p>Não foi possível carregar os dados agora. Tente de novo em instantes.</p>`;
    console.error(e);
  }
}
window.addEventListener("hashchange", rota);
window.addEventListener("load", () => {
  document.querySelectorAll("[data-ic]").forEach(e => e.outerHTML = ic(e.dataset.ic));
  rota();
});
