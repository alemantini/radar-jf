"use strict";
const FONTE = id => `https://www.camarajf.mg.gov.br/sal/proposicaon.php?num=${id}`;
const BUSCA_CAMARA = "https://www.camarajf.mg.gov.br/sal/buscapropos.php";
const ORDEM = ["pedidos", "cobrancas", "homenagens", "leis", "outros"];
const CURTO = {pedidos: "Pedidos nos bairros", cobrancas: "Perguntas e cobranças", homenagens: "Homenagens", leis: "Propostas de lei", outros: "Outros"};
const TIPOS = {REQ: "Requerimento", IND: "Indicação", PEDIF: "Pedido de Informação", REP: "Representação", MOC: "Moção", PLEI: "Projeto de Lei", PLEIC: "Projeto de Lei Complementar", PELOR: "Emenda à Lei Orgânica", PRES: "Projeto de Resolução", PDL: "Projeto de Decreto Legislativo"};

// ícones simples (traço), usados nos botões
const ICONE = {
  carro: '<path d="M5 16V11l2-5h10l2 5v5M3 16h18M7 16v2M17 16v2M7 12.5h.01M17 12.5h.01"/>',
  coracao: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
  alerta: '<path d="M12 3 2 20h20zM12 10v4M12 17h.01"/>',
  placar: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  balanca: '<path d="M12 3v18M5 21h14M3 7h18M6 7l-3 7a3 3 0 0 0 6 0zM18 7l-3 7a3 3 0 0 0 6 0z"/>',
  camara: '<path d="M3 21h18M5 21V10M9.5 21V10M14.5 21V10M19 21V10M2 10l10-6 10 6z"/>',
  dinheiro: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h.01M18 12h.01"/>',
  agenda: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  pin: '<path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
  repete: '<path d="M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3"/>',
  fala: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
  lupa: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  pessoas: '<circle cx="9" cy="7" r="4"/><path d="M2 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2M16 3.1a4 4 0 0 1 0 7.8M22 21v-2a4 4 0 0 0-3-3.9"/>',
  predios: '<path d="M3 21h18M5 21V4h9v17M14 9h5v12M8 8h3M8 12h3M8 16h3"/>',
  maleta: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2M2 13h20"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  jornal: '<path d="M4 4h13v16H6a2 2 0 0 1-2-2zM17 8h3v10a2 2 0 0 1-2 2M8 8h5M8 12h5M8 16h3"/>',
};
const ic = (n, cls = "") => `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONE[n] || ""}</svg>`;
const iniciais = n => String(n || "").replace(/^(Dr|Dra|Sargento|Prof|Profa)\.?\s+/i, "").split(/\s+/).filter(p => p.length > 2 || /^[A-ZÀ-Ý]/.test(p)).slice(0, 2).map(p => p[0]).join("").toUpperCase();

let FOTOS = new Set(), CREDITO_FOTO = "", EMENDAS_R = null, GAB_R = null, TSE_R = null, FALAS = null, FALAS_T = null;
// emendas do vereador: a planilha da Prefeitura usa o nome completo
function emendasDe(v) {
  if (!EMENDAS_R || !v) return null;
  const alvo = norm(v.nome);
  const k = Object.keys(EMENDAS_R.proponentes).find(p => norm(p) === alvo) || Object.keys(EMENDAS_R.proponentes).find(p => norm(p).includes(alvo) || alvo.includes(norm(p)));
  return k ? {nome: k, ...EMENDAS_R.proponentes[k]} : null;
}
function cargoCurto(v) {
  const pres = (v.comissoes || []).filter(c => c.papel === "presidente").length;
  const memb = (v.comissoes || []).filter(c => c.papel !== "suplente").length;
  const partes = [];
  if (v.mesa) partes.push(`${v.mesa} da Câmara`);
  if (pres) partes.push(`preside ${pres} ${pres > 1 ? "comissões" : "comissão"}`);
  else if (memb) partes.push(`${memb} ${memb > 1 ? "comissões" : "comissão"}`);
  return partes.join(", ");
}
const avatar = v => FOTOS.has(v.id) ? `<img class="avatar foto" src="fotos/${v.id}.jpg" alt="Foto de ${esc(v.apelido)}" title="${esc(CREDITO_FOTO)}" loading="lazy" width="46" height="58">` : `<span class="avatar" aria-hidden="true">${esc(iniciais(v.apelido))}</span>`;
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
  try { EMENDAS_R = await fetch("dados/prefeitura/emendas_resumo.json").then(r => r.ok ? r.json() : null); } catch (e) { EMENDAS_R = null; }
  try { GAB_R = await fetch("dados/gabinetes.json").then(r => r.ok ? r.json() : null); } catch (e) { GAB_R = null; }
  try { TSE_R = await fetch("dados/tse.json").then(r => r.ok ? r.json() : null); } catch (e) { TSE_R = null; }
  try { FALAS = await fetch("dados/atas_falas.json").then(r => r.ok ? r.json() : null); } catch (e) { FALAS = null; }
  try { const f = await fetch("fotos/fotos.json").then(r => r.json()); FOTOS = new Set(f.ids); CREDITO_FOTO = f.credito; } catch (e) { /* sem fotos: ficam as iniciais */ }
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
const MES_CURTO = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const mesAno = d => d ? `${MES_CURTO[+d.slice(5, 7) - 1]} ${d.slice(0, 4)}` : "";
const periodo = (d1, d2) => d1 && d2 ? (mesAno(d1) === mesAno(d2) ? `em ${mesAno(d1)}` : `de ${mesAno(d1)} a ${mesAno(d2)}`) : "";
const GRUPO_DESC = {
  pedidos: "Trocar lâmpada, tapar buraco, podar árvore, capinar. É um pedido: quem decide se faz é a Prefeitura.",
  cobrancas: "Pedidos de explicação à Prefeitura, convites a autoridades e apelos a outros órgãos.",
  homenagens: "Votos de congratulação ou pesar, título de cidadão, nome de rua e datas comemorativas.",
  leis: "Projetos que criam regra, programa ou obrigação na cidade.",
  outros: "Utilidade pública, notas de apoio ou repúdio e pedidos internos da Câmara.",
};

function subsidioMes(ano) {
  const S = RESUMO.subsidio; return S ? (S.por_ano[String(ano)] || 0) : 0;
}
function salarioAcumulado(agora = new Date()) {
  const S = RESUMO.subsidio; if (!S) return 0;
  let total = 0;
  for (let ano = 2025; ano <= agora.getFullYear(); ano++) {
    const valor = S.por_ano[String(ano)] || 0;
    for (let m = 0; m < 12; m++) {
      const ini = new Date(ano, m, 1), fim = new Date(ano, m + 1, 1);
      if (agora <= ini) break;
      const fracao = agora >= fim ? 1 : (agora - ini) / (fim - ini);
      total += valor * S.vereadores * fracao;
    }
    if (S.decimo_terceiro && agora >= new Date(ano, 11, 20)) total += valor * S.vereadores;
  }
  return total;
}
const reaisCurto = v => v >= 1e6 ? "R$ " + (v / 1e6).toLocaleString("pt-BR", {maximumFractionDigits: 1}) + " mi" : v >= 1e3 ? "R$ " + Math.round(v / 1e3).toLocaleString("pt-BR") + " mil" : "R$ " + Math.round(v).toLocaleString("pt-BR");
const reaisBR = v => "R$ " + v.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});

function cracha(v) {
  const c = v.contagem || {};
  const sal = v.fora_da_lista ? 0 : subsidioMes(new Date().getFullYear());
  return `<a class="cracha${v.fora_da_lista ? " fora" : ""}" href="#/v/${v.id}">
    <span class="cr-topo">${avatar(v)}
      <span class="cx"><span class="nome">${esc(v.apelido)}</span><span class="partido">${esc(v.partido || "não está na lista atual da Câmara")}</span>${cargoCurto(v) ? `<span class="cargo">${esc(cargoCurto(v))}</span>` : ""}</span></span>
    <span class="cr-nums">
      <span><b>${fmt(c.total)}</b>propostas</span>
      ${sal ? `<span><b>${"R$ " + Math.round(sal).toLocaleString("pt-BR")}</b>salário por mês</span>` : ""}
      ${votos24(v) ? `<span><b>${fmt(votos24(v))}</b>votos em 2024</span>` : ""}
    </span>
    ${(() => { const e = emendasDe(v); return e ? `<span class="cr-emendas">Emendas desde ${EMENDAS_R.desde}: <b>${reaisCurto(e.previsto)}</b> indicados, <b>${reaisCurto(e.pago)}</b> já pagos</span>` : ""; })()}
    <span class="barras">${barras(c)}</span>
  </a>`;
}


// ---------- cobrar o vereador ----------
const SITE = "https://jflandia.com.br/";
function mensagemCobranca(v, r, n) {
  const tema = (r.tm || "melhoria").toLowerCase();
  return `Olá, ${v.apelido}. Sou morador(a) de Juiz de Fora. A Câmara já recebeu ${r.q} pedidos de ${tema} para a ${r.r}${r.b ? ", " + r.b : ""}${periodo(r.d1, r.d2) ? ", " + periodo(r.d1, r.d2) : ""}. ${n} ${n > 1 ? "deles saíram" : "deles saiu"} do seu gabinete. O problema continua? O que a Prefeitura respondeu e o que ainda pode ser feito?\n\nFonte: ${SITE}#/repetidos/${encodeURIComponent(r.r)}`;
}
function painelCobrar(r, ps) {
  const cont = {};
  ps.forEach(p => p.au.forEach(a => cont[a] = (cont[a] || 0) + 1));
  const ids = Object.keys(cont).map(Number).filter(a => VER[a]).sort((a, b) => cont[b] - cont[a]);
  if (!ids.length) return "";
  const uid = "cb" + Math.random().toString(36).slice(2, 8);
  setTimeout(() => {
    const box = document.getElementById(uid); if (!box) return;
    const sel = box.querySelector("select"), txt = box.querySelector("textarea"), info = box.querySelector(".contato-gab");
    const atual = () => VER[+sel.value];
    const atualiza = () => {
      const v = atual(); txt.value = mensagemCobranca(v, r, cont[v.id]);
      info.innerHTML = v.email_gabinete || v.telefone_gabinete ? `E-mail oficial: <b>${esc(v.email_gabinete || "não informado")}</b>${v.telefone_gabinete ? ` · Telefone do gabinete: <b>${esc(v.telefone_gabinete)}</b>` : ""}` : "A Câmara não informa contato deste vereador.";
      box.querySelector(".b-email").style.display = v.email_gabinete ? "" : "none";
    };
    sel.onchange = atualiza; atualiza();
    box.querySelector(".b-email").onclick = () => { const v = atual(); location.href = `mailto:${v.email_gabinete}?subject=${encodeURIComponent("Pedido repetido: " + r.r)}&body=${encodeURIComponent(txt.value)}`; };
    box.querySelector(".b-zap").onclick = () => window.open(`https://wa.me/?text=${encodeURIComponent(txt.value)}`, "_blank", "noopener");
    box.querySelector(".b-copiar").onclick = async e => { try { await navigator.clipboard.writeText(txt.value); e.target.textContent = "Mensagem copiada"; } catch (_) { txt.select(); } };
  });
  return `<details class="cobrar-box" id="${uid}"><summary>Cobrar uma resposta</summary>
    <p class="sub">A mensagem já vem pronta. Escolha o vereador, ajuste o texto se quiser e envie.</p>
    <label>Para quem<select>${ids.map(a => `<option value="${a}">${esc(VER[a].apelido)} (${cont[a]} ${cont[a] > 1 ? "pedidos" : "pedido"} para esta rua)</option>`).join("")}</select></label>
    <label>Mensagem<textarea rows="7"></textarea></label>
    <div class="acoes"><button class="b-email" type="button">Enviar por e-mail</button><button class="b-zap" type="button">Compartilhar no WhatsApp</button><button class="b-copiar" type="button">Copiar mensagem</button></div>
    <p class="contato-gab"></p>
  </details>`;
}

let _relogio = null;
// faixa "Hoje no plenário" (Câmara e página inicial)
async function faixaHoje(alvo) {
  const A = await fetch("dados/agenda.json").then(r => r.ok ? r.json() : null).catch(() => null);
  const el = document.getElementById(alvo);
  if (!A || !el) return;
  const hoje = new Date().toLocaleDateString("sv-SE", {timeZone: "America/Sao_Paulo"});
  const ps = (A.pautas || []).filter(p => p.data >= hoje);
  if (!ps.length) return;
  const d = ps[0].data, doDia = ps.filter(p => p.data === d), itens = doDia.flatMap(p => p.itens);
  const [y, m, dd] = d.split("-").map(Number);
  const quando = d === hoje ? "Hoje" : ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"][new Date(y, m - 1, dd).getDay()] + ", " + dd + "/" + String(m).padStart(2, "0");
  const conta = {};
  itens.forEach(i => i.temas.forEach(t => { if (t !== "Homenagens") conta[t] = (conta[t] || 0) + 1; }));
  const tops = Object.entries(conta).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([t, n]) => `${n} sobre ${t.toLowerCase()}`);
  el.innerHTML = `<a class="faixa-hoje" href="#/agenda">${ic("agenda")}<span><b>${quando} no plenário, às ${esc(doDia[0].hora.replace(":", "h"))}</b>
    <small>${itens.length ? `${itens.length} ${itens.length === 1 ? "item" : "itens"}${tops.length ? ", " + tops.join(" e ") : ""}` : "Pauta ainda não publicada"}</small></span><span class="fh-seta" aria-hidden="true">›</span></a>`;
}
function pgInicio() {
  const R = RESUMO, t = R.totais;
  const atuais = R.vereadores.filter(v => !v.fora_da_lista);
  const fora = R.vereadores.filter(v => v.fora_da_lista);
  const S = R.subsidio;
  const maxT = Math.max(1, ...(R.temas || []).map(x => x[1]));
  app.innerHTML = `
    <h1>O que cada vereador de Juiz de Fora fez desde a posse, contado todo dia</h1>
    ${S ? `<div class="placa camara contador">
      <span class="tx"><span class="ds">Salário pago aos ${S.vereadores} vereadores desde a posse</span>
      <span class="tt num" id="salario">${reaisBR(salarioAcumulado())}</span>
      <span class="ds">e subindo agora. Estimativa: ${S.vereadores} salários de ${reaisBR(S.por_ano["2025"])} por mês em 2025 e ${reaisBR(S.por_ano["2026"])} em 2026, mais o 13º, desde 1º de janeiro de 2025. <a href="${S.fonte}" target="_blank" rel="noopener">Ver a lei</a>.</span></span></div>` : ""}
    <div class="nums">
      <a href="#/grupo/todas"><b>${fmt(R.total)}</b>propostas até agora</a>
      <a href="#/grupo/pedidos"><b>${fmt(t.pedidos)}</b>pedidos nos bairros</a>
      <a href="#/grupo/homenagens"><b>${fmt(t.homenagens)}</b>homenagens</a>
      <a href="#/grupo/leis"><b>${fmt(t.leis)}</b>propostas de lei</a>
    </div>
    <p class="sub">Última conferência na Câmara: ${esc(R.atualizado || "")}. O robô volta lá três vezes por dia.</p>
    <div id="hoje-camara"></div>

    <h2>O que pediram para o seu bairro?</h2>
    <form class="busca-rapida" onsubmit="event.preventDefault(); location.hash='#/busca/'+encodeURIComponent(this.q.value.trim())">
      <input type="search" name="q" placeholder="Digite o bairro ou a rua" autocomplete="off">
    </form>
    <div class="chips">${(R.bairros || []).slice(0, 10).map(([b]) => `<a href="#/busca/${encodeURIComponent(b)}">${esc(b)}</a>`).join("")}</div>

    <div class="duas">
      <section><h2>O que mais pedem</h2>
        ${(R.temas || []).slice(0, 6).map(([n, q]) => `<div class="linha-t"><span>${esc(n)}</span><b>${fmt(q)}</b><i style="width:${Math.round(100 * q / maxT)}%"></i></div>`).join("")}
      </section>
      <section><h2>Bairros mais citados</h2>
        ${(R.bairros || []).slice(0, 6).map(([b, q]) => `<a class="linha-t" href="#/busca/${encodeURIComponent(b)}"><span>${esc(b)}</span><b>${fmt(q)}</b></a>`).join("")}
      </section>
    </div>

    <h2>O problema que não some</h2>
    <p class="sub">Quando o mesmo pedido volta várias vezes para a mesma rua. O site da Câmara não mostra isso: o robô cruza os pedidos um por um.</p>
    <div id="rep-top" class="rep-grid"><p class="carregando">Carregando…</p></div>
    <a class="btn-grande camara" href="#/repetidos">${ic("repete")}<span class="tx">Ver todas as ruas com pedidos repetidos</span>›</a>

    <h2>Quem mais propôs</h2>
    <div class="aviso">Quantidade não mede qualidade: um pedido de troca de lâmpada e um projeto de lei contam igual aqui. Veja os grupos de cada vereador antes de tirar conclusões.</div>
    ${[...atuais].sort((a, b) => (b.contagem.total || 0) - (a.contagem.total || 0)).slice(0, 5).map(v => `<a class="linha-t" href="#/v/${v.id}"><span>${esc(v.apelido)}${v.partido ? ", " + esc(v.partido) : ""}</span><b>${fmt(v.contagem.total)}</b></a>`).join("")}
    <p class="sub" style="margin-top:8px">Os outros ${atuais.length - 5} estão nos crachás, mais abaixo, em ordem alfabética.</p>

    <h2>Homenagem ou trabalho?</h2>
    <p class="sub">Toque em um grupo para ler cada proposta.</p>
    <div class="grupos-desc">${ORDEM.map(g => `<a href="#/grupo/${g}"><span class="gn"><span class="ponto g-${g}"></span>${CURTO[g]}</span><b>${fmt(t[g])}</b><small>${GRUPO_DESC[g]}</small></a>`).join("")}</div>

    <h2>As propostas mais recentes</h2>
    <div>${(R.recentes || []).map(p => itemHTML(p, true)).join("")}</div>

    <h2>Os ${atuais.length} vereadores</h2>
    <div class="info">Em ordem alfabética. O site não dá nota nem faz ranking: mostra os números para você tirar suas conclusões.</div>
    <input type="search" id="fv" placeholder="Buscar por nome ou partido" autocomplete="off">
    <div class="crachas" id="crachas">${atuais.map(cracha).join("")}</div>
    ${fora.length ? `<h2>Outros autores nesta legislatura</h2><p class="sub">Apresentaram propostas mas não estão hoje na lista oficial de vereadores (por exemplo, suplentes que já saíram).</p><div class="crachas">${fora.map(cracha).join("")}</div>` : ""}`;

  // contador de salário: atualiza a cada segundo (a cada minuto se a pessoa prefere menos movimento)
  clearInterval(_relogio);
  const el = document.getElementById("salario");
  if (el) {
    const passo = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 60000 : 1000;
    _relogio = setInterval(() => { if (!document.body.contains(el)) return clearInterval(_relogio); el.textContent = reaisBR(salarioAcumulado()); }, passo);
  }
  const fv = document.getElementById("fv");
  fv.oninput = () => { const q = norm(fv.value); document.getElementById("crachas").innerHTML = atuais.filter(v => !q || norm(`${v.apelido} ${v.nome} ${v.partido}`).includes(q)).map(cracha).join("") || '<p class="sub">Ninguém encontrado.</p>'; };
  carregarRepetidos().then(() => {
    const box = document.getElementById("rep-top"); if (box) box.innerHTML = REPETIDOS.slice(0, 4).map(repCard).join("");
  }).catch(() => {});
}

function repCard(r) {
  return `<a class="rep-card" href="#/repetidos/${encodeURIComponent(r.r)}">
    <span class="q">${r.q}<small>vezes</small></span>
    <span class="cx"><b>${esc(r.r)}</b>${r.b ? `<span>${esc(r.b)}</span>` : ""}
      <span class="pe"><span class="tag g-pedidos">${esc(r.tm)}</span>${r.nv ? `${r.nv} ${r.nv > 1 ? "vereadores pediram" : "vereador pediu"}` : ""}${periodo(r.d1, r.d2) ? ", " + periodo(r.d1, r.d2) : ""}</span>
      <span class="cobrar">Ver pedidos e cobrar ›</span></span>
  </a>`;
}

async function pgGrupo(g) {
  await carregarPropostas();
  const todas = g === "todas" || !CURTO[g];
  const itens = PROPOSTAS.filter(p => todas || p.g === g).sort(ordenaData);
  app.innerHTML = `
    <h1>${todas ? "Todas as propostas" : CURTO[g]}</h1>
    <p class="sub">${todas ? "Tudo o que os vereadores apresentaram desde a posse." : GRUPO_DESC[g]} ${fmt(itens.length)} no total.</p>
    <div class="filtros">${["todas", ...ORDEM].map(x => `<a class="${(todas ? "todas" : g) === x ? "on" : ""}" href="#/grupo/${x}">${x === "todas" ? "Todas" : CURTO[x]}</a>`).join("")}</div>
    <input type="search" id="q" placeholder="Filtrar por palavra" autocomplete="off">
    <div id="lista"></div>`;
  const alvo = document.getElementById("lista"), inp = document.getElementById("q");
  const mostra = () => { const q = norm(inp.value.trim()); alvo.innerHTML = ""; lista(q ? itens.filter(p => p._busca.includes(q) || norm(p.au.map(nomeAutor).join(" ")).includes(q)) : itens, alvo, 40, true); };
  let tm; inp.oninput = () => { clearTimeout(tm); tm = setTimeout(mostra, 250); };
  mostra();
}

async function carregarFalasTrechos() {
  if (!FALAS_T) FALAS_T = await fetch("dados/atas_falas_trechos.json").then(r => r.ok ? r.json() : null).catch(() => null);
  return FALAS_T;
}
const fonteAta = c => ((FALAS && FALAS.fonte) || "https://www.camarajf.mg.gov.br/sal/ata.php?cod={}").replace("{}", c);
const temasFortes = f => (f && f.temas || []).filter(([, n]) => n >= 2).slice(0, 6);
const falaHTML = (t, rotulo) => `<div class="ag-item fala"><div class="ag-tx"><small class="sub">${dataBR(t.d)}${rotulo ? " · " + esc(rotulo) : ""}</small>
  <p>${esc(t.x)}</p><div class="ag-bt"><a href="${fonteAta(t.c)}" target="_blank" rel="noopener">Ler a ata completa</a></div></div></div>`;
const NOTA_TEMAS = `Os assuntos são encontrados por computador no trecho da ata em que o próprio vereador fala, e só contam quando o tema aparece mais de uma vez nesse trecho. Mostram do que ele falou, não a posição dele: para saber o que defendeu, leia as falas, que levam à ata oficial. As atas são um resumo escrito pela Câmara, não uma transcrição palavra por palavra.`;

function blocoFalas(v) {
  const f = falasDe(v);
  if (!f || !f.reunioes) return "";
  const pres = ehPresidente(v), pct = Math.round(100 * f.falou / f.reunioes), tm = temasFortes(f);
  setTimeout(async () => {
    const T = await carregarFalasTrechos(), d = T && T.vereadores[v.id];
    const alvo = document.getElementById("falas-det");
    if (!alvo || !d) return;
    alvo.innerHTML = `
      ${tm.length ? `<h3>Assuntos que mais levou às reuniões</h3>
        <div class="chips-filtro" id="tm-abas">${tm.map(([t, n], k) => `<a href="javascript:void 0" data-t="${esc(t)}"${k ? "" : ' class="on"'}>${esc(t)} <b>${fmt(n)}</b></a>`).join("")}</div>
        <p class="sub" id="tm-expl"></p><div id="tm-ex"></div>` : `<p class="sub">Ainda há poucas falas registradas para mostrar os assuntos principais.</p>`}
      ${f.homenagens ? `<p class="sub">Também fez homenagens, cumprimentos ou votos de pesar em ${fmt(f.homenagens)} reuniões.</p>` : ""}
      ${d.trechos.length ? `<h3>Falas mais recentes</h3>${d.trechos.slice(0, 5).map(t => falaHTML(t, t.t)).join("")}` : ""}`;
    const mostra = t => {
      const n = (tm.find(x => x[0] === t) || [])[1] || 0;
      document.getElementById("tm-expl").textContent = `Falou sobre ${t.toLowerCase()} em ${fmt(n)} ${n === 1 ? "reunião" : "reuniões"}. Exemplos mais recentes:`;
      document.getElementById("tm-ex").innerHTML = (d.temas[t] || []).map(x => falaHTML(x, t)).join("");
    };
    if (tm.length) {
      alvo.querySelectorAll("#tm-abas a").forEach(a => a.onclick = () => { alvo.querySelectorAll("#tm-abas a").forEach(b => b.classList.toggle("on", b === a)); mostra(a.dataset.t); });
      mostra(tm[0][0]);
    }
  }, 0);
  return `<h2>Nas reuniões da Câmara</h2>
    <div class="nums"><span><b>${fmt(f.falou)}</b>reuniões em que falou</span><span><b>${fmt(f.reunioes)}</b>reuniões no período</span>${pres ? "" : `<span><b>${pct}%</b>das reuniões</span>`}</div>
    ${pres ? `<p class="sub">Como presidente da Câmara, conduz as reuniões. As falas dele como presidente aparecem nas atas como "o Presidente" e não entram nesta conta.</p>` : ""}
    ${f.reunioes < 60 ? `<p class="sub">Esteve no mandato de ${dataBR(f.de)} a ${dataBR(f.ate)}.</p>` : ""}
    <div id="falas-det"><p class="carregando">Carregando as falas…</p></div>
    <p><a href="#/atas/v=${v.id}">Ver todas as atas em que ${esc(v.apelido)} falou</a> · <a href="#/defende">Comparar os assuntos dos vereadores</a> · <a href="#/placar/tribuna">Quem mais fala</a></p>
    <p class="sub">${NOTA_FALAS()} ${NOTA_TEMAS}</p>`;
}

// ---------- Assunto quente do mês ----------
const MESES_LONGOS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
const nomeMes = m => `${MESES_LONGOS[+m.slice(5, 7) - 1]} de ${m.slice(0, 4)}`;
async function pgQuente(arg) {
  await carregarResumo();
  app.innerHTML = `<h1>Assunto quente do mês</h1><p class="carregando">Carregando…</p>`;
  const Q = await fetch("dados/atas_quente.json").then(r => r.ok ? r.json() : null).catch(() => null);
  if (!Q || !Q.meses.length) { app.innerHTML = `<h1>Assunto quente do mês</h1><div class="info">Os dados das atas ainda estão sendo preparados.</div>`; return; }
  const nomeV = id => (VER[id] || {}).apelido || "";
  const COMPLETO = 8;  // mês com poucas atas publicadas ainda está incompleto
  let m = Q.meses.some(x => x.m === arg) ? arg : (Q.meses.find(x => x.reunioes >= COMPLETO) || Q.meses[0]).m;
  const fonte = c => (Q.fonte || "").replace("{}", c);
  const ult = Q.meses.slice(0, 12).reverse();
  const termometro = () => {
    const mx = Math.max(...ult.flatMap(x => Object.values(x.todos)), 1);
    const linhas = Q.pautas.filter(p => ult.some(x => (x.todos[p] || 0) >= 2));
    return `<div class="qt-term"><table><thead><tr><th></th>${ult.map(x => `<th><a href="#/quente/${x.m}">${MESES_LONGOS[+x.m.slice(5, 7) - 1].slice(0, 3)}<br>${x.m.slice(2, 4)}</a></th>`).join("")}</tr></thead>
      <tbody>${linhas.map(p => `<tr><th>${esc(p)}</th>${ult.map(x => { const n = x.todos[p] || 0; return `<td${n ? ` style="background:rgba(214,69,40,${(0.12 + 0.88 * n / mx).toFixed(2)})"` : ""}${n / mx > .55 ? ' class="forte"' : ""} title="${esc(p)}, ${nomeMes(x.m)}: ${n} vereadores">${n || ""}</td>`; }).join("")}</tr>`).join("")}</tbody></table></div>`;
  };
  const desenha = () => {
    const M = Q.meses.find(x => x.m === m), i = Q.meses.indexOf(M), ant = Q.meses[i + 1];
    history.replaceState(null, "", "#/quente/" + m);
    app.innerHTML = `
      <h1>Assunto quente do mês</h1>
      <p class="sub">O que mais vereadores levaram às reuniões da Câmara em cada mês, contado nas atas oficiais. Quanto mais vereadores diferentes falam de um assunto, mais quente ele está.</p>
      <label class="sr" for="qt-mes">Mês</label>
      <select id="qt-mes" class="qt-mes">${Q.meses.map(x => `<option value="${x.m}"${x.m === m ? " selected" : ""}>${nomeMes(x.m)} (${x.reunioes} ${x.reunioes === 1 ? "reunião" : "reuniões"})</option>`).join("")}</select>
      ${M.reunioes < COMPLETO ? `<div class="info">Mês ainda incompleto: só ${M.reunioes} ${M.reunioes === 1 ? "reunião tem" : "reuniões têm"} ata publicada pela Câmara até agora. O resultado pode mudar.</div>` : ""}
      ${M.pautas.length ? M.pautas.map((p, k) => {
        const antes = ant ? (ant.todos[p.p] || 0) : null;
        return `<div class="qt-card${k ? "" : " top"}">
          <div class="qt-tit"><span class="qt-pos">${k + 1}º</span><h2>${esc(p.p)}</h2></div>
          <p class="qt-num"><b>${p.vereadores.length} vereadores</b> falaram do assunto em <b>${p.reunioes} de ${M.reunioes}</b> reuniões do mês${antes !== null ? `. Em ${MESES_LONGOS[+ant.m.slice(5, 7) - 1]}: ${antes} ${antes === 1 ? "vereador" : "vereadores"}` : ""}.</p>
          <p class="sub">Quem falou: ${p.vereadores.map(id => `<a href="#/v/${id}">${esc(nomeV(id))}</a>`).join(", ")}</p>
          ${p.ex.map(e => `<div class="ag-item fala"><div class="ag-tx"><small class="sub">${dataBR(e.d)} · ${esc(nomeV(e.v))}</small><p>${esc(e.x)}</p>
            <div class="ag-bt"><a href="${fonte(e.c)}" target="_blank" rel="noopener">Ler a ata completa</a></div></div></div>`).join("")}
        </div>`;
      }).join("") : `<p class="sub">Nenhum assunto acompanhado foi levado por dois ou mais vereadores neste mês.</p>`}
      <h2>Termômetro dos últimos 12 meses</h2>
      <p class="sub">Quantos vereadores falaram de cada assunto em cada mês. Toque no mês para ver os detalhes.</p>
      ${termometro()}
      <p class="sub fonte-linha">Como é feito: o computador lê, nas atas, só os trechos em que os vereadores falam (não conta a leitura de projetos nem as votações) e procura palavras ligadas a cada assunto, como "chuvas", "Defesa Civil" e "famílias atingidas". Acompanhamos ${Q.pautas.length} assuntos que voltam com frequência às reuniões: ${Q.pautas.map(esc).join(", ")}. Um assunto só entra no mês quando pelo menos dois vereadores falaram dele. Mostra do que se falou, não a posição de cada um: para isso, leia as falas, que levam à ata oficial. As atas são um resumo escrito pela Câmara, não uma transcrição palavra por palavra.</p>`;
    document.getElementById("qt-mes").onchange = e => { m = e.target.value; desenha(); window.scrollTo(0, 0); };
  };
  desenha();
}

// ---------- Quem defende o quê ----------
async function pgDefende(arg) {
  await carregarResumo();
  if (!FALAS) { app.innerHTML = `<h1>Quem defende o quê</h1><div class="info">Os dados das atas ainda estão sendo preparados.</div>`; return; }
  const atuais = RESUMO.vereadores.filter(v => !v.fora_da_lista && falasDe(v));
  const todos = {};
  atuais.forEach(v => (falasDe(v).temas || []).forEach(([t, n]) => todos[t] = (todos[t] || 0) + n));
  const ordem = Object.keys(todos).sort((a, b) => todos[b] - todos[a]);
  let tema = ordem.includes(arg) ? arg : "";
  app.innerHTML = `
    <h1>Quem defende o quê</h1>
    <p class="sub">Os assuntos que cada vereador mais levou às reuniões da Câmara desde ${dataBR(FALAS.desde)}, contados nas atas oficiais. Escolha um assunto para ver quem mais falou dele.</p>
    <div class="chips-filtro" id="df-abas"><a href="javascript:void 0" data-t=""${tema ? "" : ' class="on"'}>Todos os vereadores</a>${ordem.map(t => `<a href="javascript:void 0" data-t="${esc(t)}"${t === tema ? ' class="on"' : ""}>${esc(t)}</a>`).join("")}</div>
    <div id="df-lista"></div>
    <p class="sub fonte-linha">${NOTA_TEMAS} Pedidos de rotina e homenagens não entram nos assuntos. O presidente da Câmara conduz as reuniões e quase não aparece falando com o próprio nome. Fonte: <a href="#/atas">atas da Câmara Municipal de Juiz de Fora</a>.</p>`;
  const desenha = () => {
    document.querySelectorAll("#df-abas a").forEach(a => a.classList.toggle("on", a.dataset.t === tema));
    history.replaceState(null, "", "#/defende" + (tema ? "/" + encodeURIComponent(tema) : ""));
    const out = document.getElementById("df-lista");
    if (tema) {
      const L = atuais.filter(v => !ehPresidente(v)).map(v => ({v, n: ((falasDe(v).temas || []).find(x => x[0] === tema) || [])[1] || 0})).filter(l => l.n >= 2).sort((a, b) => b.n - a.n);
      const mx = Math.max(...L.map(l => l.n), 1);
      out.innerHTML = `<p class="sub">Em quantas reuniões cada vereador falou sobre ${esc(tema.toLowerCase())}. Aparecem os vereadores que falaram do assunto em pelo menos 2 reuniões.</p>` + (L.map((l, i) => `
        <a class="rk" href="#/v/${l.v.id}"><span class="rk-pos">${i + 1}º</span>${avatar(l.v)}
          <span class="rk-cx"><span class="rk-nm">${esc(l.v.apelido)}<small>${esc(l.v.partido || "")}</small></span>
          <span class="rk-barra"><i style="width:${100 * l.n / mx}%"></i></span>
          <span class="rk-partes"><span>Ver as falas na página do vereador</span></span></span>
          <span class="rk-nota">${fmt(l.n)}<small>reuniões</small></span></a>`).join("") || `<p class="sub">Nenhum vereador com esse assunto entre os principais.</p>`);
    } else {
      out.innerHTML = atuais.slice().sort((a, b) => a.apelido.localeCompare(b.apelido, "pt-BR")).map(v => {
        const f = falasDe(v), tm = temasFortes(f).slice(0, 3);
        return `<a class="rk df" href="#/v/${v.id}"><span class="rk-pos"></span>${avatar(v)}
          <span class="rk-cx"><span class="rk-nm">${esc(v.apelido)}<small>${esc(v.partido || "")}</small></span>
          <span class="rk-partes">${tm.length ? tm.map(([t, n]) => `<span>${esc(t)}: ${fmt(n)} ${n === 1 ? "reunião" : "reuniões"}</span>`).join("") : `<span>${ehPresidente(v) ? "Presidente: conduz as reuniões" : "Poucas falas registradas"}</span>`}</span></span>
          <span class="rk-nota">${fmt(f.falou)}<small>reuniões com fala</small></span></a>`;
      }).join("");
    }
  };
  document.querySelectorAll("#df-abas a").forEach(a => a.onclick = () => { tema = a.dataset.t; desenha(); });
  desenha();
}

async function pgVereador(id) {
  const v = VER[id];
  if (!v) { app.innerHTML = "<p>Vereador não encontrado.</p>"; return; }
  await carregarPropostas();
  const meus = PROPOSTAS.filter(p => p.au.includes(v.id)).sort(ordenaData);
  const c = v.contagem;
  const sal = v.fora_da_lista ? 0 : subsidioMes(new Date().getFullYear());
  app.innerHTML = `
    <div class="cr-topo grande">${avatar(v)}
      <span class="cx"><h1>${esc(v.apelido)}</h1><span class="partido">${esc(v.nome)}${v.partido ? ", " + esc(v.partido) : ""}</span></span></div>
    ${v.observacao ? `<p class="sub">${esc(v.observacao[0].toUpperCase() + v.observacao.slice(1))}</p>` : ""}
    ${FOTOS.has(v.id) ? `<p class="credito">${esc(CREDITO_FOTO)}</p>` : ""}
    <div class="nums">
      <span><b>${fmt(c.total)}</b>propostas</span>
      ${sal ? `<span><b>R$ ${Math.round(sal).toLocaleString("pt-BR")}</b>salário por mês (<a href="${RESUMO.subsidio.fonte}" target="_blank" rel="noopener">lei</a>)</span>` : ""}
      ${votos24(v) ? `<span><b>${fmt(votos24(v))}</b>votos em 2024</span>` : ""}
    </div>
    ${v.email_gabinete || v.telefone_gabinete ? `<p class="contato">Gabinete: ${v.email_gabinete ? `<a href="mailto:${esc(v.email_gabinete)}">${esc(v.email_gabinete)}</a>` : ""} ${esc(v.telefone_gabinete)}</p>` : ""}
    ${v.ficha ? `<p class="contato"><a href="${esc(v.ficha)}" target="_blank" rel="noopener">Ficha oficial na Câmara</a></p>` : ""}
    ${v.mesa || (v.comissoes || []).length ? `<h2>Cargos na Câmara</h2>
      ${v.mesa ? `<div class="linha"><span class="nm"><b>Mesa Diretora</b> (${esc(RESUMO.cargos ? RESUMO.cargos.mesa_bienio : "")})</span><span class="vl">${esc(v.mesa)}</span></div>` : ""}
      ${(v.comissoes || []).map(cm => `<div class="linha"><span class="nm">${esc(cm.c)}</span><span class="vl papel-${esc(cm.papel)}">${esc(cm.papel[0].toUpperCase() + cm.papel.slice(1))}</span></div>`).join("")}
      ${RESUMO.cargos ? `<p class="sub" style="margin-top:6px">Fonte: <a href="${RESUMO.cargos.fonte_mesa}" target="_blank" rel="noopener">Mesa Diretora</a> e <a href="${RESUMO.cargos.fonte_comissoes}" target="_blank" rel="noopener">comissões ${esc(RESUMO.cargos.comissoes_ano)}</a> no site da Câmara.</p>` : ""}` : ""}
    ${(() => { const e = emendasDe(v); if (!e) return ""; return `<h2>Emendas ao orçamento</h2>
      <p class="sub">Dinheiro do orçamento da Prefeitura que o vereador indicou para obras, serviços ou entidades, desde ${EMENDAS_R.desde}.</p>
      <div class="nums verde"><span><b>${reaisCurto(e.previsto)}</b>indicados em ${fmt(e.n)} emendas</span><span><b>${reaisCurto(e.pago)}</b>já pagos (${Math.round(100 * e.pago / (e.previsto || 1))}%)</span></div>
      <a class="btn-grande prefeitura" href="#/prefeitura/emendas/${encodeURIComponent(e.nome)}">${ic("dinheiro")}<span class="tx">Ver cada emenda e em que etapa está<small>Fonte: Monitor de Emendas da Prefeitura</small></span>›</a>`; })()}
    ${blocoFalas(v)}
    ${blocoGabinete(v)}
    ${blocoEleicao(v)}
    <h2>O que propôs até agora</h2>
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

async function pgRepetidos(filtro0) {
  await Promise.all([carregarRepetidos(), carregarPropostas()]);
  app.innerHTML = `
    <h1>Pedidos que voltam</h1>
    <p class="sub">Quando o mesmo tipo de pedido (por exemplo, iluminação ou buraco) é feito várias vezes para a mesma rua.</p>
    <div class="aviso"><b>Atenção:</b> pedido repetido não prova que a Prefeitura ignorou. O problema pode ter sido resolvido e voltado, o pedido pode ser para trechos diferentes da rua, ou mais de um vereador pode ter pedido a mesma coisa. Abra cada documento para conferir.</div>
    <input type="search" id="q" placeholder="Filtrar por bairro, rua ou tipo de pedido" autocomplete="off" value="${esc(filtro0 || "")}">
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
        return `<div class="rep"><div><span class="q">${r.q} vezes</span> <b>${esc(r.tm)}</b></div>
          <div>${esc(r.r)}${r.b ? ", " + esc(r.b) : ""}</div>
          <div class="pe" style="font-size:14px;color:#555">${r.nv ? `${r.nv} ${r.nv > 1 ? "vereadores pediram" : "vereador pediu"}${periodo(r.d1, r.d2) ? ", " + periodo(r.d1, r.d2) : ""}<br>` : ""}Quando: ${datas}<br>Quem pediu: ${quem}</div>
          ${painelCobrar(r, ps)}
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
      <li>As fotos dos vereadores são as fotos oficiais publicadas pela Câmara Municipal de Juiz de Fora.</li>
    </ul>
    <h2>O que é estimativa</h2>
    <ul>
      <li>A divisão em grupos e a identificação de rua, bairro e tipo de pedido são feitas automaticamente pelo texto oficial. Pode haver erro pontual.</li>
      <li>A data de cada proposta é a primeira data de tramitação registrada no sistema. ${RESUMO.sem_data ? `Ainda faltam as datas de ${fmt(RESUMO.sem_data)} propostas, que o robô busca aos poucos para não sobrecarregar o site da Câmara.` : ""}</li>
    </ul>
    <h2>O que este site ainda não mostra</h2>
    <p>Presença dos vereadores nas reuniões e como cada um votou. A Câmara de Juiz de Fora não publica esses registros de forma que possam ser baixados (as atas aparecem na lista, mas o texto não abre). Sem dado oficial, o site não mostra número nenhum, e falta de registro não é tratada como falta do vereador.</p>
    <h2>Privacidade</h2>
    <p>O site não usa cookies e não pede cadastro. Para saber quantas pessoas visitam cada página, usamos o <a href="https://www.goatcounter.com" target="_blank" rel="noopener">GoatCounter</a>, um contador aberto que não guarda dados pessoais nem identifica quem visita.</p>
    <h2>Achou um erro?</h2>
    <p><a href="mailto:radarjflandia@gmail.com?subject=Erro%20no%20Radar%20JFl%C3%A2ndia" >Avise aqui</a> pelo e-mail radarjflandia@gmail.com. Erros são corrigidos o mais rápido possível. O código do site é aberto e pode ser conferido por qualquer pessoa.</p>`;
}

// ---------- rotas ----------
const SELO_NOVO = `<span class="selo-novo" aria-label="novo em 2026"><b>novo</b><small>2026</small></span>`;
// itens recém-lançados ganham o selo "novo 2026" no menu (tirar daqui depois de algumas semanas)
const NOVOS = new Set(["#/prefeitura/alugueis", "#/imoveis", "#/prefeitura/curiosas", "#/combustivel", "#/obra", "#/quente", "#/defende", "#/atas", "#/prefeitura/chuvas", "#/prefeitura/emprestimos", "#/prefeitura/hospitais", "#/prefeitura/creditos", "#/prefeitura/aditivos"]);
const SUBNAV = {
  camara: [["#/camara", "Vereadores", "pessoas"], ["#/placar", "Ranking", "placar"], ["#/busca", "Meu bairro", "pin"], ["#/obra", "O pedido virou obra?", "predios"], ["#/repetidos", "Pedidos que voltam", "repete"], ["#/agenda", "Agenda", "agenda"], ["#/quente", "Assunto do mês", "alerta"], ["#/defende", "Quem defende o quê", "fala"], ["#/atas", "Atas", "lupa"], ["#/combustivel", "Combustível", "carro"], ["#/imoveis", "Imóveis alugados", "predios"]],
  prefeitura: [["#/prefeitura/alertas", "Sinais de alerta", "alerta"], ["#/prefeitura/chuvas", "Dinheiro das chuvas", "alerta"], ["#/prefeitura/emprestimos", "Empréstimos", "dinheiro"], ["#/prefeitura/hospitais", "Hospitais", "coracao"], ["#/prefeitura/creditos", "Orçamento que muda", "repete"], ["#/prefeitura/aditivos", "Aditivos de contratos", "jornal"], ["#/prefeitura/curiosas", "Coisas curiosas", "lupa"], ["#/prefeitura/alugueis", "Imóveis alugados", "predios"], ["#/prefeitura/lupa", "Na lupa", "lupa"], ["#/prefeitura/impostometro", "Impostômetro", "dinheiro"], ["#/prefeitura/iptu", "Calculadora do IPTU", "dinheiro"], ["#/prefeitura/placar", "Placar fiscal", "balanca"], ["#/prefeitura/comissionados", "Cargos de confiança", "pessoas"], ["#/prefeitura/supersalarios", "Supersalários", "dinheiro"], ["#/prefeitura", "Gastos por secretaria", "predios"], ["#/prefeitura/emendas", "Emendas dos vereadores", "pessoas"], ["#/prefeitura/fornecedores", "Quem recebe", "maleta"], ["#/prefeitura/busca", "Buscar gasto", "lupa"]],
};
const SELO = {
  camara: () => `<div class="placa camara">${ic("camara")}<span class="tx"><span class="tt">Câmara Municipal de Juiz de Fora</span><span class="ds">O que os vereadores apresentam. Fonte: sistema oficial da Câmara.</span></span></div>`,
  prefeitura: () => `<div class="placa prefeitura">${ic("dinheiro")}<span class="tx"><span class="tt">Prefeitura de Juiz de Fora</span><span class="ds">Quanto entra e para onde vai o dinheiro. Fontes: Portal da Transparência e Tesouro Nacional.</span></span></div>`,
};

function pgEscolha() {
  const atuais = RESUMO.vereadores.filter(v => !v.fora_da_lista).sort((x, y) => x.apelido.localeCompare(y.apelido, "pt-BR"));
  const nV = atuais.length;
  app.innerHTML = `
    <section class="hero">
      <svg class="hero-ondas" viewBox="0 0 400 400" aria-hidden="true"><g fill="none" stroke="currentColor"><circle cx="330" cy="200" r="40" stroke-width="10"/><circle cx="330" cy="200" r="95" stroke-width="8"/><circle cx="330" cy="200" r="150" stroke-width="6"/><circle cx="330" cy="200" r="205" stroke-width="4"/></g><circle cx="330" cy="200" r="14" fill="currentColor"/></svg>
      <div class="hero-grid">
      <div class="hero-txt">
      <div class="logo-home" role="img" aria-label="Radar JFlândia">
      <div class="lh-1"><svg class="lh-ic" viewBox="0 0 120 80" aria-hidden="true"><circle cx="60" cy="40" r="11" fill="currentColor"/><path d="M40 18a32 32 0 0 0 0 44M80 18a32 32 0 0 1 0 44M24 6a52 52 0 0 0 0 68M96 6a52 52 0 0 1 0 68" fill="none" stroke="currentColor" stroke-width="9" stroke-linecap="round"/></svg><span>RADAR</span></div>
      <div class="lh-2"><span class="pt">JF</span><span>LÂNDIA</span><span class="lh-bands"><svg class="lh-band" viewBox="0 0 30 21" aria-label="Bandeira do Brasil" role="img"><rect width="30" height="21" fill="#009c3b"/><path d="M15 2.5 27.5 10.5 15 18.5 2.5 10.5z" fill="#ffdf00"/><circle cx="15" cy="10.5" r="4.6" fill="#002776"/></svg><svg class="lh-band" viewBox="0 0 30 21" aria-label="Bandeira de Minas Gerais" role="img"><rect width="30" height="21" fill="#fff" stroke="#c9ccd1" stroke-width=".6"/><path d="M15 4 21.5 16H8.5z" fill="#e8272c"/></svg><svg class="lh-band" viewBox="0 0 30 21" aria-label="Bandeira de Juiz de Fora" role="img"><rect width="30" height="21" fill="#1f4e9c"/><rect y="6.46" width="30" height="1.62" fill="#fff"/><rect y="8.08" width="30" height="4.85" fill="#d52b1e"/><rect y="12.92" width="30" height="1.62" fill="#fff"/><rect y="14.54" width="30" height="6.56" fill="#16924a"/><path d="M15 8.88 16.86 12.12 13.14 12.12z" fill="#fff"/></svg></span></div>
    </div>
      <h1 class="hero-t">Veja o que os vereadores e a prefeita de Juiz de Fora fazem com o <span>seu dinheiro</span></h1>
      <p class="hero-sub">Raio-X de Juiz de Fora-MG. Cada proposta, cada gasto e cada salário, contados todo dia, só com dados oficiais.</p>
      </div>
      <div class="hero-card">
        <p class="hc-t">Comece por aqui</p>
        <div id="hoje-camara"></div>
        <div class="hc-linha">
      <label class="hero-sel"><span class="sr">Escolha um vereador</span>
        <select id="esc-ver"><option value="">Escolha um vereador</option>${atuais.map(v => `<option value="${v.id}">${esc(v.apelido)} (${esc(v.partido || "")})</option>`).join("")}</select></label>
      <form class="hero-busca" id="hero-busca"><label class="sr" for="hb">Pesquisar meu bairro</label><input id="hb" placeholder="Ou digite o seu bairro ou rua" autocomplete="off"><button type="submit">Buscar</button></form>
        </div>
        <div class="hc-atalhos"><a href="#/placar">Ranking</a><a href="#/quente">Assunto do mês</a><a href="#/atas">Atas</a></div>
      </div>
      </div>
    </section>
    <section class="dest" id="destaques" hidden aria-label="Destaques sobre Juiz de Fora"></section>
    <a class="btn-alerta" href="#/prefeitura/alertas">${ic("alerta")}<span class="tx"><b><span id="ba-n">Sinais</span> de alerta nos gastos da Prefeitura</b><small>Compras fatiadas, empresas punidas, sócios que doaram para campanhas e mais. Veja o que merece uma pergunta.</small></span><span class="seta">›</span></a>
    <div class="faixa-nums">
      <a href="#/camara"><b id="fx-sal">${reaisCurto(salarioAcumulado())}</b><span>em salários de vereadores desde a posse</span></a>
      <a href="#/prefeitura/impostometro"><b id="fx-imp">...</b><span>em impostos municipais pagos este ano</span></a>
      <a href="#/prefeitura/emendas"><b>${EMENDAS_R && EMENDAS_R.total ? reaisCurto(EMENDAS_R.total.previsto) : "Emendas"}</b><span>em emendas indicadas pelos vereadores</span></a>
    </div>
    <div id="instalar-app"></div>
    <p class="sec-t">Novidades no Radar</p>
    <div class="novos">
      <a href="#/quente"><span class="nv-ic">${ic("alerta")}</span><b>Assunto quente do mês</b><small>O que mais vereadores levaram às reuniões, mês a mês.</small>${SELO_NOVO}</a>
      <a href="#/defende"><span class="nv-ic">${ic("fala")}</span><b>Quem defende o quê</b><small>Os assuntos que cada vereador mais leva para a tribuna.</small>${SELO_NOVO}</a>
      <a href="#/placar/tribuna"><span class="nv-ic">${ic("placar")}</span><b>Quem mais fala</b><small>Em quantas reuniões cada vereador falou, contado nas atas.</small>${SELO_NOVO}</a>
      <a href="#/obra"><span class="nv-ic">${ic("predios")}</span><b>O pedido virou obra?</b><small>Os pedidos dos vereadores para a sua rua e as obras da Prefeitura.</small>${SELO_NOVO}</a>
      <a href="#/prefeitura/chuvas" class="pref"><span class="nv-ic">${ic("alerta")}</span><b>Dinheiro das chuvas</b><small>Quanto foi reservado e pago desde a emergência de dezembro.</small>${SELO_NOVO}</a>
      <a href="#/prefeitura/creditos" class="pref"><span class="nv-ic">${ic("repete")}</span><b>Orçamento que muda</b><small>De onde saiu e para onde foi o dinheiro mexido por decreto.</small>${SELO_NOVO}</a>
      <a href="#/combustivel"><span class="nv-ic">${ic("carro")}</span><b>Combustível dos vereadores</b><small>Quantos litros o carro de cada vereador abasteceu, mês a mês.</small>${SELO_NOVO}</a>
      <a href="#/rankings"><span class="nv-ic">${ic("placar")}</span><b>JF nos rankings</b><small>IDH, progresso social, saneamento, competitividade e mais.</small>${SELO_NOVO}</a>
    </div>
    <p class="sec-t">Escolha por onde começar</p>
    <div class="escolhas">
      <a class="placa camara" href="#/camara">${ic("camara")}<span class="tx"><span class="tt">Câmara</span><span class="ds">O que cada um dos ${nV} vereadores apresentou, quanto custa cada gabinete e o que foi pedido para o seu bairro.</span><span class="num">${fmt(RESUMO.total)} propostas</span></span><span class="seta">›</span></a>
      <a class="placa prefeitura" href="#/prefeitura">${ic("dinheiro")}<span class="tx"><span class="tt">Prefeitura</span><span class="ds">Para onde vai o dinheiro: quanto cada secretaria gasta, com quem e em quê.</span><span class="num">Gastos por secretaria</span></span><span class="seta">›</span></a>
    </div>
    <p class="sec-t">Ferramentas</p>
    <div class="ferramentas">
    <a class="btn-grande camara" href="#/placar">${ic("placar")}<span class="tx">Ranking dos vereadores<small>Quem apresenta mais, quem fiscaliza mais, o gabinete mais econômico e o mais eficiente</small></span>›</a>
    <a class="btn-grande prefeitura" href="#/prefeitura/placar">${ic("balanca")}<span class="tx">Placar fiscal da Prefeitura<small>Gasta mais do que arrecada? Cumpre os mínimos de saúde e educação?</small></span>›</a>
    <a class="btn-grande" href="#/rankings">${ic("placar")}<span class="tx">Juiz de Fora nos rankings<small>Onde a cidade aparece em IDH, progresso social, saneamento e outros índices</small></span>›</a>
    <a class="btn-grande prefeitura" href="#/prefeitura/busca">${ic("lupa")}<span class="tx">Pesquisar um gasto<small>Empresa, CNPJ ou palavra, como asfalto ou merenda</small></span>›</a>
    </div>
    <div class="info">Câmara e Prefeitura são poderes diferentes. A Câmara (vereadores) faz leis, fiscaliza e pede melhorias. A Prefeitura (prefeita e secretarias) executa os serviços e gasta o orçamento.</div>`;
  botaoInstalar();
  bannerDestaques();
  document.getElementById("esc-ver").onchange = e => { if (e.target.value) location.hash = "#/v/" + e.target.value; };
  document.getElementById("hero-busca").onsubmit = e => { e.preventDefault(); const q = document.getElementById("hb").value.trim(); location.hash = "#/busca" + (q ? "/" + encodeURIComponent(q) : ""); };
  if (window.prefReceitas) prefReceitas().then(R => { const x = R && impostometro(R); const el = document.getElementById("fx-imp"); if (el) el.textContent = x ? reaisCurto(x.total) : "ver"; });
  fetch("dados/prefeitura/alertas.json").then(r => r.ok ? r.json() : null).catch(() => null).then(A => { const el = document.getElementById("ba-n"); if (el && A) el.textContent = fmt(A.alertas.length) + " sinais"; });
}

// ---------- Combustível dos carros dos vereadores (relatórios mensais da Câmara) ----------
async function pgCombustivel(arg) {
  await carregarResumo();
  app.innerHTML = `<h1>Combustível dos vereadores</h1><p class="carregando">Carregando…</p>`;
  const C = await fetch("dados/combustivel.json").then(r => r.ok ? r.json() : null).catch(() => null);
  if (!C || !(C.meses || []).length) { app.innerHTML = `<h1>Combustível dos vereadores</h1><div class="info">Os dados de combustível ainda estão sendo preparados.</div>`; return; }
  const M = C.meses, nomeV = id => (VER[id] || {}).apelido || "";
  const lt = v => v.toLocaleString("pt-BR", {maximumFractionDigits: 0}) + " litros";
  const mesSel = M.some(x => x.m === arg) ? arg : "";
  const pagoTot = M.reduce((s, x) => s + (x.pago || 0), 0), ML = M.filter(x => x.em !== "reais" && x.preco_medio), litTot = M.reduce((s, x) => s + x.litros, 0);
  const precoMed = ML.reduce((s, x) => s + x.pago, 0) / Math.max(1, ML.reduce((s, x) => s + x.litros, 0));
  const desde = M[M.length - 1].m, ate = M[0].m;
  let linhas;
  if (mesSel) {
    const x = M.find(y => y.m === mesSel);
    linhas = x.em === "reais" ? x.por.filter(p => p.id).map(p => ({id: p.id, v: p.reais, rs: true, sub: ""}))
      : x.por.filter(p => p.id).map(p => ({id: p.id, v: p.litros, sub: p.reais ? "cerca de " + reaisBR(p.reais) : ""}));
    linhas.forEach(l => { const t = ((C.por_vereador[l.id] || {}).teto || []).filter(t => t.m === mesSel); l.teto = t.filter(y => y.teto); l.acima = t.filter(y => y.abastecidos && y.abastecidos > y.pagos + 0.5); });
  } else {
    linhas = Object.entries(C.por_vereador).filter(([, p]) => p.meses).map(([id, p]) => ({id: +id, v: p.litros / p.meses, sub: `${lt(p.litros)} em ${p.meses} ${p.meses > 1 ? "meses" : "mês"}${p.reais_est ? `; cerca de ${reaisCurto(p.reais_est)} em ${p.meses_reais} ${p.meses_reais > 1 ? "meses" : "mês"}` : ""}`, teto: (p.teto || []).filter(t => t.teto), acima: (p.teto || []).filter(t => t.abastecidos && t.abastecidos > t.pagos + 0.5)}));
  }
  linhas = linhas.filter(l => VER[l.id]).sort((a, b) => b.v - a.v);
  const mx = Math.max(...linhas.map(l => l.v), 1);
  const xMes = mesSel ? M.find(y => y.m === mesSel) : null;
  app.innerHTML = `
    <h1>Combustível dos vereadores</h1>
    <p class="sub">Cada vereador usa um carro alugado pela Câmara, e a Câmara paga o combustível. Todo mês ela publica quantos litros cada carro abasteceu. Juntamos esses relatórios desde ${nomeMes(desde)}.</p>
    <div class="faixa-nums">
      <div><b>${reaisCurto(pagoTot)}</b><span>pagos em combustível de ${nomeMes(desde)} a ${nomeMes(ate)}</span></div>
      <div><b>${Math.round(litTot).toLocaleString("pt-BR")}</b><span>litros nos meses publicados em litros, contando os carros da administração</span></div>
      <div><b>${reaisBR(precoMed)}</b><span>preço médio do litro pago pela Câmara</span></div>
    </div>
    <label class="hero-sel" style="display:block;margin:14px 0"><span class="sr">Período</span>
      <select id="cb-mes"><option value="">Média mensal, todos os meses</option>${M.map(x => `<option value="${x.m}"${x.m === mesSel ? " selected" : ""}>${nomeMes(x.m)}</option>`).join("")}</select></label>
    <h2>${mesSel ? (xMes.em === "reais" ? "Valor pago em " : "Litros em ") + nomeMes(mesSel) : "Média de litros por mês"}</h2>
    ${linhas.map((l, i) => { const v = VER[l.id]; return `
      <div class="tp-linha">
        <div class="tp-tit"><b>${i + 1}. <a href="#/v/${l.id}">${esc(nomeV(l.id))}</a>${ehPresidente(v) ? ` <small class="sub">(presidente da Câmara)</small>` : ""}</b><span>${l.rs ? reaisBR(l.v) : lt(l.v) + (mesSel ? "" : " por mês")}</span></div>
        <span class="tp-barra"><i style="width:${(100 * l.v / mx).toFixed(1)}%"></i></span>
        ${l.sub ? `<small class="sub">${esc(l.sub)}</small>` : ""}
        ${(l.teto || []).length ? `<span class="cb-teto" title="${esc(l.teto.map(t => nomeMes(t.m)).join(", "))}">${mesSel ? "Bateu o teto" : `Bateu o teto em ${l.teto.length} ${l.teto.length > 1 ? "meses" : "mês"}`}</span>` : ""}
        ${(l.acima || []).length ? `<small class="sub cb-acima">Abasteceu mais do que a Câmara pagou: ${l.acima.map(t => `${nomeMes(t.m)} (${Math.round(t.abastecidos)} litros, a Câmara pagou ${Math.round(t.pagos)})`).join("; ")}.</small>` : ""}
      </div>`; }).join("")}
    <p class="sub" style="margin-top:12px">${xMes ? `<a href="${C.relatorio.replace("{}", xMes.cod)}" target="_blank" rel="noopener">Abrir o relatório oficial de ${nomeMes(mesSel)}</a> · ` : ""}<a href="${C.fonte}" target="_blank" rel="noopener">Página de combustível no Portal da Transparência da Câmara</a></p>
    <div class="info"><b>Teto:</b> a Câmara paga no máximo ${C.teto_litros || 400} litros por carro no mês (de fevereiro a maio de 2025, quando publicava em reais, o limite era ${reaisBR(C.teto_reais || 2000)}). "Bateu o teto" quer dizer que o vereador chegou a esse limite. Quando o relatório mostra mais litros abastecidos do que pagos, a Câmara pagou só até o teto; o relatório não diz quem pagou a diferença.</div>
    ${(C.avisos || []).filter(a => !mesSel || a.m === mesSel).map(a => `<div class="info cb-aviso"><b>Erro no relatório oficial de ${nomeMes(a.m)}:</b> ${esc(a.texto)} <a href="${C.relatorio.replace("{}", (M.find(y => y.m === a.m) || {}).cod)}" target="_blank" rel="noopener">Ver o relatório</a>.</div>`).join("")}
    <div class="info">Como ler: os litros são os que a própria Câmara publica para cada carro. O valor em reais é uma estimativa nossa: litros do vereador vezes o preço médio pago pela Câmara naquele mês. Usar o carro faz parte do mandato (visitar bairros, reuniões, eventos), e cada vereador tem uma rotina e uma área de atuação diferentes, então gastar mais combustível não é, sozinho, sinal de irregularidade. A média por mês considera só os meses em que o carro do vereador aparece no relatório. De fevereiro a maio de 2025 a Câmara publicou o valor em reais em vez dos litros; esses meses entram só no valor em reais. O relatório chamado "janeiro de 2025" soma vários meses de uma vez e por isso ficou de fora. Os carros marcados como "Administração" ficam fora da comparação.</div>`;
  document.getElementById("cb-mes").onchange = e => { location.hash = "#/combustivel" + (e.target.value ? "/" + e.target.value : ""); };
}

// ---------- Imóveis alugados pela Câmara (lista curada; cada valor conferido nos documentos oficiais da Câmara) ----------
// Para atualizar: confira os extratos de contratos e os relatórios de empenhos antes de mudar qualquer valor.
const IMOVEIS_CAMARA = {
  conferido: "2026-11-19",
  relatorio: "https://www.camarajf.mg.gov.br/relatorio.php?cod_relatorio=",
  contratos: "https://www.camarajf.mg.gov.br/transparencia/extratoDeContratos.php",
  imoveis: [
    {nome: "Prédio do INSS: 1º e 2º andares", end: "Rua Marechal Deodoro, 722, Centro", area: "cerca de 800 m²",
     uso: "Centro administrativo da Câmara (setores administrativos)", dono: "Instituto Nacional do Seguro Social (INSS)",
     aluguel: 18470.99, condominio: 12000, vig: "16/07/2025 a 16/01/2028 (30 meses, 3º termo aditivo ao contrato 01/2020)",
     desde: 2015,
     nota: "Alugado desde julho de 2015. O empenho de julho de 2025 citava aluguel mensal de R$ 18.977,07; o de junho de 2026 reserva 12 parcelas de R$ 18.470,99. O condomínio é estimado em R$ 12.000 por mês.",
     docs: [["Empenho de julho de 2025", 21636], ["Empenho de junho de 2026", 23328]]},
    {nome: "Prédio do INSS: térreo e 5º andar", end: "Rua Marechal Deodoro, 722, Centro", area: "",
     uso: "Setores administrativos da Câmara; no térreo funciona o Serviço de Defesa do Consumidor (Sedecon), cuja conta de luz é paga pela Câmara", dono: "Instituto Nacional do Seguro Social (INSS)",
     aluguel: 9788.29, condominio: 5000, vig: "15/09/2026 a 15/03/2029 (30 meses, 3º termo aditivo ao contrato 01/2021)",
     desde: 2021,
     nota: "Alugado desde setembro de 2021. Na renovação de setembro de 2026 os valores caíram: de março a setembro de 2026 a Câmara reservou R$ 97.882,90 de aluguel e R$ 61.600 de condomínio para seis meses (cerca de R$ 16,3 mil e R$ 10,3 mil por mês); no novo período são R$ 9.788,29 de aluguel e R$ 5.000 de condomínio por mês. Os documentos não dizem o motivo da redução.",
     docs: [["Empenho de janeiro de 2026", 22521], ["Empenho de setembro de 2026 (renovação)", 23902]]},
  ],
  outros: [
    {t: "Vagas de estacionamento para os carros dos vereadores", v: "R$ 71.196,00 por 12 meses", q: "Jamaica Veículos Ltda., contrato 1011/2025, de 15/12/2025 a 14/12/2026. A Câmara aluga vagas desde 2012."},
    {t: "Espaço em torre de transmissão para a TV Câmara", v: "R$ 132.090,84 (contrato 1063/2026)", q: "JF Sistema de Comunicação Ltda., contrato de 22/10/2026 a 21/10/2031, para antenas e equipamentos da transmissão."},
  ],
};
function pgImoveis() {
  const I = IMOVEIS_CAMARA;
  const brl = v => "R$ " + v.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const mes = I.imoveis.reduce((s, x) => s + x.aluguel + x.condominio, 0);
  app.innerHTML = `
    <h1>Imóveis alugados pela Câmara</h1>
    <p class="sub">O Plenário e os gabinetes ficam no Palácio Barbosa Lima e no anexo Ignácio Halfeld. Os setores administrativos ficam em quatro andares alugados do INSS, no prédio da Rua Marechal Deodoro, 722. Os valores abaixo foram conferidos nos extratos de contratos e nos relatórios de empenhos publicados pela Câmara (conferido em ${dataBR(I.conferido)}).</p>
    <div class="faixa-nums">
      <div><b>${brl(mes)}</b><span>por mês hoje, somando aluguel e condomínio dos quatro andares</span></div>
      <div><b>${brl(mes * 12)}</b><span>por ano, no valor atual</span></div>
      <div><b>desde 2015</b><span>a Câmara aluga andares no prédio do INSS</span></div>
    </div>
    ${I.imoveis.map(x => `<div class="alerta-card">
      <div class="ac-topo"><span class="ac-tipo">${esc(x.end)}${x.area ? " · " + esc(x.area) : ""}</span><span class="ac-valor">${brl(x.aluguel + x.condominio)}/mês</span></div>
      <b class="ac-nome">${esc(x.nome)}</b>
      <div class="nb-conta">
        <div><small>Aluguel por mês</small><b>${brl(x.aluguel)}</b></div>
        <div><small>Condomínio por mês</small><b>${brl(x.condominio)}</b></div>
        <div><small>Contrato vale até</small><b>${esc(x.vig.split(" (")[0].split(" a ")[1])}</b></div>
      </div>
      <p><b>Uso:</b> ${esc(x.uso)}. <b>Dono:</b> ${esc(x.dono)}.</p>
      <p><small class="sub">Vigência: ${esc(x.vig)}.</small></p>
      <p>${esc(x.nota)}</p>
      <p><small class="sub">Documentos oficiais: ${x.docs.map(([t, c]) => `<a href="${I.relatorio}${c}" target="_blank" rel="noopener">${esc(t)}</a>`).join(" · ")}</small></p>
    </div>`).join("")}
    <h2>Outros aluguéis de espaço</h2>
    ${I.outros.map(o => `<div class="tp-linha"><div class="tp-tit"><b>${esc(o.t)}</b><span>${esc(o.v)}</span></div><small class="sub">${esc(o.q)}</small></div>`).join("")}
    <p class="sub" style="margin-top:12px"><a href="${I.contratos}" target="_blank" rel="noopener">Ver todos os extratos de contratos no Portal da Transparência da Câmara</a></p>
    <div class="info"><b>Como ler:</b> "empenho" é o dinheiro reservado para pagar a despesa; o condomínio é estimado e pode variar. Os empenhos registram o aluguel como dispensa de licitação. Alugar não é irregular: a pergunta que fica é se compensa alugar por tantos anos ou ter um prédio próprio, e por que o valor do térreo e 5º andar caiu na renovação de 2026.</div>`;
}

// ---------- Juiz de Fora nos rankings (lista curada à mão, cada item com a fonte) ----------
// Para atualizar: troque os números e o ano quando sair edição nova. Mostrar pontos fortes e fracos, sem escolher lado.
const RANK_JF = [
  {t: "Progresso social (IPS Brasil)", ano: "2026", pos: "94º", de: "de 5.570 cidades", extra: "10º em Minas Gerais",
   d: "Mede necessidades básicas, bem-estar e oportunidades, com 57 indicadores. Nota 68,95. Em 2025 a cidade era a 107ª do país.",
   fraco: "Ponto fraco: no item Inclusão Social a cidade fica na posição 5.274.", tom: "bom",
   fonte: "IPS Brasil", url: "https://ipsbrasil.org.br/"},
  {t: "Competitividade (CLP)", ano: "2025", pos: "58º", de: "entre cidades com mais de 80 mil habitantes", extra: "4º em Minas Gerais",
   d: "Junta 65 indicadores de economia, serviços públicos e gestão. Subiu 70 posições em relação a 2024. A edição 2026 já saiu e o número de Juiz de Fora será atualizado aqui.",
   fraco: "Ponto fraco: acesso à saúde ficou em 25º, mas qualidade da saúde em 254º.", tom: "bom",
   fonte: "Centro de Liderança Pública, via Tribuna de Minas", url: "https://tribunademinas.com.br/noticias/cidade/17-09-2025/jf-ranking-competitividade-saude.html"},
  {t: "Saneamento (Trata Brasil)", ano: "2026", pos: "58º", de: "entre as 100 maiores cidades", extra: "era 70º na edição anterior",
   d: "Água tratada e coleta de esgoto chegam a praticamente toda a cidade.",
   fraco: "Ponto fraco: só cerca de metade do esgoto coletado é tratado.", tom: "meio",
   fonte: "Instituto Trata Brasil", url: "https://tratabrasil.org.br/ranking-do-saneamento/"},
  {t: "Desenvolvimento (IFDM Firjan)", ano: "2025", pos: "847º", de: "no Brasil", extra: "89º em Minas Gerais",
   d: "Índice da Firjan que soma emprego e renda, educação e saúde.",
   fraco: "Fica atrás de muitas cidades mineiras menores neste índice.", tom: "ruim",
   fonte: "Firjan, via Tribuna de Minas (28/05/2025)", url: "https://www.firjan.com.br/ifdm/"},
  {t: "Desenvolvimento humano (IDHM)", ano: "2010", pos: "0,778", de: "faixa alta (0,700 a 0,799)", extra: "último dado municipal oficial",
   d: "O IDH das cidades usa o Censo. O de 2010 é o último publicado por município; o cálculo com o Censo 2022 ainda não saiu para todas as cidades.",
   fraco: "", tom: "meio",
   fonte: "IBGE Cidades / Atlas Brasil (PNUD)", url: "https://www.ibge.gov.br/cidades-e-estados/mg/3136702.html"},
  {t: "Homicídios (Atlas da Violência)", ano: "2022", pos: "4ª", de: "em Minas Gerais em número de homicídios", extra: "68ª do Brasil",
   d: "88 homicídios registrados em 2022, atrás de Belo Horizonte, Contagem e Betim.",
   fraco: "Atenção: é contagem absoluta, e cidade grande tende a aparecer mais alto. Não é taxa por habitante.", tom: "ruim",
   fonte: "Ipea e Fórum Brasileiro de Segurança Pública, via Tribuna de Minas", url: "https://tribunademinas.com.br/?p=664843"},
];
function pgRankings() {
  const cor = {bom: "rk-bom", meio: "rk-meio", ruim: "rk-ruim"};
  app.innerHTML = `
    <h1>Juiz de Fora nos rankings</h1>
    <p class="sub">Onde a cidade aparece nos principais índices do país. Cada número tem o ano e o link da fonte. Mostramos o lado bom e o lado fraco de cada um.</p>
    <div class="rk-lista">${RANK_JF.map(r => `
      <article class="rk ${cor[r.tom]}">
        <div class="rk-pos"><b>${esc(r.pos)}</b><small>${esc(r.de)}</small></div>
        <div class="rk-tx">
          <h2>${esc(r.t)} <span class="rk-ano">${esc(r.ano)}</span></h2>
          ${r.extra ? `<p class="rk-extra">${esc(r.extra)}</p>` : ""}
          <p>${esc(r.d)}</p>
          ${r.fraco ? `<p class="rk-fraco">${esc(r.fraco)}</p>` : ""}
          <p class="rk-fonte">Fonte: <a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.fonte)}</a></p>
        </div>
      </article>`).join("")}</div>
    <div class="info">Cada ranking usa uma régua diferente, com anos e grupos de cidades diferentes. Por isso as posições não se comparam entre si. Ranking mostra um retrato, não explica sozinho a causa. Viu um número desatualizado? Avise pelo botão do WhatsApp.</div>`;
}

// ---------- Banner da página inicial: "veja o que está acontecendo em Juiz de Fora" ----------
let _destTimer = null;
async function bannerDestaques() {
  const el = document.getElementById("destaques");
  if (!el) return;
  const D = await fetch("dados/destaques.json").then(r => r.ok ? r.json() : null).catch(() => null);
  if (!D || !(D.itens || []).length || !document.body.contains(el)) return;
  const it = D.itens;
  el.innerHTML = `
    <div class="dest-topo"><h2>Veja o que está acontecendo em Juiz de Fora</h2>
      <div class="dest-setas"><button type="button" data-d="-1" aria-label="Destaque anterior">‹</button><button type="button" data-d="1" aria-label="Próximo destaque">›</button></div></div>
    <div class="dest-trilho" id="dest-trilho">${it.map((x, i) => `
      <a class="dest-card ${esc(x.area)}" href="${esc(x.href)}" data-i="${i}">
        <span class="dest-rot"><span class="dest-ic">${ic(x.ic)}</span>${esc(x.rot)}</span>
        <b class="dest-v">${esc(x.v)}</b>
        <span class="dest-d">${esc(x.d)}</span>
        <span class="dest-ver">Ver mais ›</span>
      </a>`).join("")}</div>
    <div class="dest-pontos">${it.map((_, i) => `<button type="button" data-i="${i}" aria-label="Destaque ${i + 1}"></button>`).join("")}</div>`;
  el.hidden = false;
  const tr = document.getElementById("dest-trilho"), cards = [...tr.children], pts = [...el.querySelectorAll(".dest-pontos button")];
  const atual = () => { let m = 0, d = 1e9; cards.forEach((c, i) => { const x = Math.abs(c.offsetLeft - tr.offsetLeft - tr.scrollLeft); if (x < d) { d = x; m = i; } }); return m; };
  const vai = i => { i = (i + cards.length) % cards.length; tr.scrollTo({left: cards[i].offsetLeft - tr.offsetLeft, behavior: "smooth"}); };
  const marca = () => { const a = atual(); pts.forEach((p, i) => p.classList.toggle("on", i === a)); };
  tr.addEventListener("scroll", () => { clearTimeout(tr._t); tr._t = setTimeout(marca, 80); }, {passive: true});
  pts.forEach((p, i) => p.onclick = () => { vai(i); parar(); });
  el.querySelectorAll(".dest-setas button").forEach(b => b.onclick = () => { vai(atual() + +b.dataset.d); parar(); });
  const parar = () => { clearInterval(_destTimer); _destTimer = null; };
  const andar = () => { parar(); if (!matchMedia("(prefers-reduced-motion: reduce)").matches) _destTimer = setInterval(() => { if (!document.body.contains(tr)) return parar(); vai(atual() + 1); }, 5500); };
  ["pointerdown", "mouseenter", "focusin"].forEach(ev => tr.addEventListener(ev, parar));
  tr.addEventListener("mouseleave", andar);
  marca(); andar();
}

async function rota() {
  await carregarResumo();
  const h = location.hash.replace(/^#\/?/, "");
  const partes = h.split("/").map(decodeURIComponent);
  const pag = partes[0], arg = partes.slice(1).join("/");
  const area = pag === "prefeitura" ? "prefeitura" : ["camara", "v", "busca", "repetidos", "grupo", "placar", "agenda", "atas", "defende", "quente", "obra", "combustivel", "imoveis"].includes(pag) ? "camara" : pag === "sobre" ? "sobre" : "";
  document.querySelectorAll("nav.areas a").forEach(a => a.classList.toggle("ativo", a.dataset.area === area));
  const sub = document.getElementById("subnav");
  const atual = "#/" + h;
  sub.className = area;
  sub.innerHTML = (SUBNAV[area] || []).map(([href, t, i]) => `<a href="${href}" class="${atual === href || (atual.startsWith(href + "/") && href !== "#/prefeitura") || (href === "#/prefeitura" && /^#\/prefeitura\/(ano|s)\b/.test(atual)) || (href === "#/camara" && (atual.startsWith("#/v/") || atual.startsWith("#/grupo"))) ? "ativo" : ""}"><span class="sn-ic">${ic(i)}</span><span class="sn-tx">${t}</span>${NOVOS.has(href) ? SELO_NOVO : ""}</a>`).join("");
  document.getElementById("selo").innerHTML = SELO[area] ? SELO[area]() : "";
  const at = sub.querySelector("a.ativo"); if (at) sub.scrollLeft = at.offsetLeft - 16;
  setasSubnav();
  window.scrollTo(0, 0);
  try {
    if (pag === "v") await pgVereador(+arg);
    else if (pag === "busca") await pgBusca(arg);
    else if (pag === "repetidos") await pgRepetidos(arg);
    else if (pag === "grupo") await pgGrupo(arg);
    else if (pag === "placar") pgPlacar(arg);
    else if (pag === "agenda") await pgAgenda();
    else if (pag === "atas") await pgAtas(arg);
    else if (pag === "defende") await pgDefende(arg);
    else if (pag === "quente") await pgQuente(arg);
    else if (pag === "obra") await pgPedidoObra(arg);
    else if (pag === "combustivel") await pgCombustivel(arg);
    else if (pag === "imoveis") pgImoveis();
    else if (pag === "resumo") await pgResumo();
    else if (pag === "rankings") pgRankings();
    else if (pag === "apoie") pgApoie();
    else if (pag === "sobre") { pgSobre(); if (window.sobrePrefeitura) await sobrePrefeitura(); }
    else if (pag === "camara") pgInicio();
    else if (pag === "prefeitura" && window.rotaPrefeitura) await rotaPrefeitura(partes.slice(1));
    else pgEscolha();
    botaoZap(pag, partes);
    if (document.getElementById("hoje-camara")) faixaHoje("hoje-camara");
  } catch (e) {
    app.innerHTML = `<p>Não foi possível carregar os dados agora. Tente de novo em instantes.</p>`;
    console.error(e);
  }
}
// ---------- Agenda: audiências públicas da Câmara ----------
async function pgAgenda() {
  const A = await fetch("dados/agenda.json").then(r => r.ok ? r.json() : null).catch(() => null);
  const DIAS = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];
  const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  const hoje = new Date().toLocaleDateString("sv-SE", {timeZone: "America/Sao_Paulo"});
  const ev = (A && A.eventos) || [];
  const futuros = ev.filter(e => e.data >= hoje), passados = ev.filter(e => e.data < hoje).reverse();
  const gcal = e => {
    const d = e.data.replace(/-/g, ""), h = (e.hora || "09:00").replace(":", "");
    const fim = String(Math.min(23, +h.slice(0, 2) + 3)).padStart(2, "0") + h.slice(2);
    return "https://calendar.google.com/calendar/render?action=TEMPLATE&ctz=America/Sao_Paulo"
      + "&text=" + encodeURIComponent("Audiência pública: " + e.tema.slice(0, 100))
      + "&dates=" + d + "T" + h + "00/" + d + "T" + fim + "00"
      + "&location=" + encodeURIComponent(e.local) + "&details=" + encodeURIComponent(e.tema + "\n\nFonte: " + e.fonte);
  };
  const card = (e, futuro) => {
    const [y, m, d] = e.data.split("-").map(Number), dia = DIAS[new Date(y, m - 1, d).getDay()];
    return `<div class="ag-item${futuro ? "" : " passado"}">
      <div class="ag-data"><b>${d}</b><span>${MESES[m - 1]}</span><small>${dia}</small></div>
      <div class="ag-tx"><small class="sub">${esc(e.tipo)}${e.hora ? " · " + esc(e.hora.replace(":00", "h").replace(":", "h")) : ""} · ${esc(e.local)}</small>
        <p>${esc(e.tema)}</p>
        ${e.autoria ? `<small class="sub">Autoria: ${esc(e.autoria)}${e.requerimento ? ` · Requerimento ${esc(e.requerimento)}` : ""}</small>` : ""}
        ${futuro ? `<div class="ag-bt"><a href="${gcal(e)}" target="_blank" rel="noopener">Adicionar à minha agenda</a></div>` : ""}
      </div></div>`;
  };
  // ----- pauta do plenário (Ordem do Dia) -----
  const PS = (A && A.pautas) || [];
  const proxP = PS.filter(p => p.data >= hoje);
  const diaP = proxP.length ? proxP[0].data : null;
  const doDia = PS.filter(p => p.data === diaP);
  const quando = d => { if (d === hoje) return "Hoje"; const [y, m, dd] = d.split("-").map(Number); return `${DIAS[new Date(y, m - 1, dd).getDay()].replace(/^./, c => c.toUpperCase())}, ${dd} de ${MESES[m - 1]}`; };
  const FASE = {"Veto Total": "A Prefeitura vetou o projeto inteiro. O plenário decide se mantém ou derruba o veto.", "Veto Parcial": "A Prefeitura vetou parte do projeto. O plenário decide se mantém ou derruba o veto."};
  const temasP = [...new Set(doDia.flatMap(p => p.itens.flatMap(i => i.temas)))];
  const itemP = i => `<div class="pt-item" data-temas="${esc(i.temas.join("|"))}">
      <div class="pt-n">${i.n}</div>
      <div class="ag-tx"><small class="sub">${esc(i.fase)} · ${esc(i.proposicao)}${i.temas.length ? " · " + i.temas.map(esc).join(", ") : ""}</small>
        <p>${esc(i.ementa)}</p>
        <small class="sub">Autoria: ${esc(i.autoria)}${i.vista ? " · Já teve pedido de vista, pode ser adiado de novo" : ""}</small>
        ${FASE[i.fase] ? `<small class="sub pt-exp">${FASE[i.fase]}</small>` : ""}</div></div>`;
  const blocoPauta = doDia.length ? `<section class="pauta" id="pauta">
      ${doDia.map(p => { const [y, m, dd] = p.data.split("-").map(Number); return `<div class="pt-topo">
        <div class="ag-data"><b>${dd}</b><span>${MESES[m - 1]}</span><small>${p.data === hoje ? "hoje" : DIAS[new Date(y, m - 1, dd).getDay()]}</small></div>
        <div><h2>${quando(p.data)} no plenário, às ${esc(p.hora.replace(":", "h"))}</h2>
          <p class="sub">${esc(p.nome)}. ${p.itens.length ? `${p.itens.length} ${p.itens.length === 1 ? "item" : "itens"} na Ordem do Dia.` : "A Ordem do Dia ainda não foi publicada."} <a href="${esc(p.url)}" target="_blank" rel="noopener">Ver a pauta oficial</a></p></div></div>`; }).join("")}
      ${temasP.length ? `<div class="chips pt-filtro"><a href="javascript:void 0" data-t="" class="on">Todos</a>${temasP.map(t => `<a href="javascript:void 0" data-t="${esc(t)}">${esc(t)}</a>`).join("")}</div>` : ""}
      ${doDia.flatMap(p => p.itens).map(itemP).join("")}
      <p class="sub">A pauta é anunciada pela Câmara e pode mudar no dia, nos termos do Regimento. Os assuntos (Educação, Saúde etc.) são marcados pelo Radar a partir do texto da ementa.</p>
    </section>` : "";
  app.innerHTML = `
    <h1>Agenda da Câmara</h1>
    ${blocoPauta}
    <p class="sub">Audiências públicas abertas à população, com data, hora e tema. Você pode ir ao plenário ou mandar perguntas pelo WhatsApp da Câmara, <b>(32) 99183-0706</b>, até 30 minutos depois do início. A transmissão é ao vivo pela JFTV (canal 35.1) e pelo YouTube da Câmara.</p>
    <div class="botoes-ag"><a class="btn-ag" href="webcal://jflandia.com.br/agenda.ics">${ic("agenda")} Assinar a agenda no celular</a><a class="btn-ag sec" href="https://calendar.google.com/calendar/r?cid=${encodeURIComponent("webcal://jflandia.com.br/agenda.ics")}" target="_blank" rel="noopener">Assinar no Google Agenda</a></div>
    <h2>Próximas audiências</h2>
    ${futuros.length ? futuros.map(e => card(e, true)).join("") : `<p class="sub">Nenhuma audiência marcada na página oficial da Câmara por enquanto. A Câmara costuma publicar as do mês no início de cada mês; o Radar confere todo dia.</p>`}
    <h2>Reuniões ordinárias</h2>
    <p>${esc((A && A.ordinarias) || "Reuniões ordinárias de segunda a quinta às 17h30 e às sextas às 10h30.")} Veja o <a href="https://www.camarajf.mg.gov.br/www/agenda-de-reunioes" target="_blank" rel="noopener">calendário oficial</a>.</p>
    ${passados.length ? `<h2>Audiências que já aconteceram</h2>${passados.slice(0, 20).map(e => card(e, false)).join("")}<p class="sub">O que foi dito em cada uma está nas <a href="#/atas/tipo=${encodeURIComponent("Audiência pública")}">atas das audiências</a>.</p>` : ""}
    <p class="sub fonte-linha">Fontes: <a href="https://www.camarajf.mg.gov.br/sal/buscarreuniao.php" target="_blank" rel="noopener">Ordem do Dia</a> e <a href="https://www.camarajf.mg.gov.br/www/audiencias-publicas" target="_blank" rel="noopener">página de audiências públicas da Câmara Municipal</a>${A ? `, conferida em ${esc(A.atualizado.split(" ")[0].split("-").reverse().join("/"))}` : ""}. O Radar guarda o histórico a partir de outubro de 2026.</p>`;

  app.querySelectorAll(".pt-filtro a").forEach(a => a.onclick = () => {
    app.querySelectorAll(".pt-filtro a").forEach(b => b.classList.toggle("on", b === a));
    app.querySelectorAll(".pt-item").forEach(it => it.hidden = !!a.dataset.t && !it.dataset.temas.split("|").includes(a.dataset.t));
  });}

// ---------- Atas da Câmara (reuniões e audiências) ----------
async function pgAtas(arg) {
  app.innerHTML = `<h1>Atas da Câmara</h1><p class="carregando">Carregando as atas…</p>`;
  const A = await fetch("dados/atas.json").then(r => r.ok ? r.json() : null).catch(() => null);
  const L = (A && A.atas) || [];
  const fonte = c => (A && A.fonte ? A.fonte : "https://www.camarajf.mg.gov.br/sal/ata.php?cod={}").replace("{}", c);
  const semAc = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const NV = {}; (RESUMO.vereadores || []).forEach(v => NV[v.id] = v.apelido);
  L.forEach(a => a._b = semAc(a.n + " " + a.x + " " + a.t + " " + (a.tm || []).join(" ") + " " + (a.v || []).map(i => NV[i] || "").join(" ")));
  const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  const cont = (k, f) => L.reduce((o, a) => { (f(a) || []).forEach(x => o[x] = (o[x] || 0) + 1); return o; }, {});
  const tipos = cont("t", a => [a.t]), anos = Object.keys(cont("d", a => a.d ? [a.d.slice(0, 4)] : [])).sort().reverse();
  const temas = cont("tm", a => a.tm), vers = cont("v", a => a.v);
  const P = new URLSearchParams(arg || "");
  const opt = (v, t, sel) => `<option value="${esc(v)}"${sel === String(v) ? " selected" : ""}>${esc(t)}</option>`;

  app.innerHTML = `
    <h1>Atas da Câmara</h1>
    <p class="sub">O registro oficial de cada reunião e audiência pública: quem falou, o que foi votado e o que foi cobrado. Cada ata leva ao documento oficial da Câmara.</p>
    ${L.length ? `
    <form class="busca-rapida" id="at-form" onsubmit="event.preventDefault()">
      <label class="sr" for="at-q">Buscar nas atas</label>
      <input type="search" id="at-q" placeholder="Tema, bairro, projeto…" value="${esc(P.get("q") || "")}" autocomplete="off">
    </form>
    <div class="at-sel">
      <select id="at-tipo" aria-label="Tipo de reunião">${opt("", "Todos os tipos", P.get("tipo") || "")}${Object.keys(tipos).sort().map(t => opt(t, `${t} (${fmt(tipos[t])})`, P.get("tipo") || "")).join("")}</select>
      <select id="at-ano" aria-label="Ano">${opt("", "Todos os anos", P.get("ano") || "")}${anos.map(y => opt(y, y, P.get("ano") || "")).join("")}</select>
      <select id="at-v" aria-label="Vereador que falou">${opt("", "Qualquer vereador", P.get("v") || "")}${Object.keys(vers).filter(i => NV[i]).sort((x, y) => NV[x].localeCompare(NV[y], "pt-BR")).map(i => opt(i, `${NV[i]} (${fmt(vers[i])})`, P.get("v") || "")).join("")}</select>
    </div>
    <div class="chips-filtro" id="at-temas"><a href="javascript:void 0" data-t=""${P.get("tema") ? "" : ' class="on"'}>Todos os assuntos</a>${Object.keys(temas).sort().map(t => `<a href="javascript:void 0" data-t="${esc(t)}"${P.get("tema") === t ? ' class="on"' : ""}>${esc(t)} <b>${fmt(temas[t])}</b></a>`).join("")}</div>
    <p class="sub" id="at-n"></p>
    <div id="at-lista"></div>
    <button class="btn-ag sec at-mais" id="at-mais" type="button" hidden>Mostrar mais atas</button>`
    : `<div class="info">As atas ainda estão sendo carregadas pelo robô do Radar. Volte em algumas horas.</div>`}
    <p class="sub fonte-linha">Fonte: atas publicadas pela <a href="https://www.camarajf.mg.gov.br/sal/" target="_blank" rel="noopener">Câmara Municipal de Juiz de Fora</a>${A ? `, conferidas em ${esc(A.atualizado.split(" ")[0].split("-").reverse().join("/"))}` : ""}. A busca olha o título e o começo de cada ata, os assuntos e os vereadores que falaram; para ler tudo, abra o documento oficial. Ata "ainda não aprovada" é a versão provisória, antes da votação em plenário.</p>`;
  if (!L.length) return;

  let mostrar = 30;
  const $ = id => document.getElementById(id);
  const destacar = (t, termos) => {
    let h = esc(t);
    termos.filter(x => x.length > 1).forEach(x => {
      const n = semAc(h); let out = "", i = 0, p;
      while ((p = n.indexOf(x, i)) >= 0) { out += h.slice(i, p) + "<mark>" + h.slice(p, p + x.length) + "</mark>"; i = p + x.length; }
      h = out + h.slice(i);
    });
    return h;
  };
  const desenhar = () => {
    const termos = semAc($("at-q").value).split(/\s+/).filter(Boolean);
    const tipo = $("at-tipo").value, ano = $("at-ano").value, v = $("at-v").value;
    const tema = ($("at-temas").querySelector("a.on") || {}).dataset?.t || "";
    const R = L.filter(a => (!tipo || a.t === tipo) && (!ano || (a.d || "").startsWith(ano)) && (!v || (a.v || []).includes(+v))
      && (!tema || (a.tm || []).includes(tema)) && termos.every(x => a._b.includes(x)));
    $("at-n").textContent = `${fmt(R.length)} de ${fmt(L.length)} atas`;
    $("at-lista").innerHTML = R.slice(0, mostrar).map(a => {
      const [y, m, d] = (a.d || "--").split("-");
      const nomes = (a.v || []).map(i => NV[i]).filter(Boolean);
      return `<div class="ag-item">
        <div class="ag-data">${a.d ? `<b>${+d}</b><span>${MESES[+m - 1]}</span><small>${y}</small>` : "<small>sem data</small>"}</div>
        <div class="ag-tx"><small class="sub">${esc(a.t)}${a.ap ? "" : ' · <span class="at-pend">ata ainda não aprovada</span>'}${(a.tm || []).length ? " · " + a.tm.map(esc).join(", ") : ""}</small>
          <p><b>${esc(a.n)}</b></p>
          <p class="at-x">${destacar(a.x, termos)}${a.x.length >= 300 ? "…" : ""}</p>
          ${nomes.length ? `<small class="sub">Falaram: ${nomes.map(esc).join(", ")}</small>` : ""}
          <div class="ag-bt"><a href="${fonte(a.c)}" target="_blank" rel="noopener">Ler a ata completa (documento oficial)</a></div>
        </div></div>`;
    }).join("") || `<p class="sub">Nenhuma ata com esses filtros.</p>`;
    $("at-mais").hidden = R.length <= mostrar;
    const q = new URLSearchParams();
    [["q", $("at-q").value.trim()], ["tipo", tipo], ["ano", ano], ["v", v], ["tema", tema]].forEach(([k, x]) => x && q.set(k, x));
    history.replaceState(null, "", "#/atas" + (q.toString() ? "/" + q : ""));
  };
  let tempo;
  $("at-q").oninput = () => { clearTimeout(tempo); tempo = setTimeout(() => { mostrar = 30; desenhar(); }, 150); };
  ["at-tipo", "at-ano", "at-v"].forEach(id => $(id).onchange = () => { mostrar = 30; desenhar(); });
  $("at-temas").querySelectorAll("a").forEach(a => a.onclick = () => {
    $("at-temas").querySelectorAll("a").forEach(b => b.classList.toggle("on", b === a)); mostrar = 30; desenhar();
  });
  $("at-mais").onclick = () => { mostrar += 30; desenhar(); };
  desenhar();
}

// ---------- Resumo do dia (para o canal do Radar no WhatsApp) ----------
const CANAL_ZAP = "";  // link do canal do Radar no WhatsApp (whatsapp.com/channel/...), quando existir
async function pgResumo() {
  const j = u => fetch(u).then(r => r.ok ? r.json() : null).catch(() => null);
  const [AG, AL, LU] = await Promise.all([j("dados/agenda.json"), j("dados/prefeitura/alertas.json"), j("dados/prefeitura/lupa.json")]);
  const hoje = new Date().toLocaleDateString("sv-SE", {timeZone: "America/Sao_Paulo"});
  const [y, m, d] = hoje.split("-").map(Number);
  const DS = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"][new Date(y, m - 1, d).getDay()];
  const curto = (t, n) => t.length > n ? t.slice(0, n).replace(/\s+\S*$/, "") + "..." : t;
  const linhas = [`📡 *Radar JFlândia: resumo de ${DS}, ${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}*`, ""];
  // plenário
  const ps = ((AG && AG.pautas) || []).filter(p => p.data >= hoje);
  if (ps.length) {
    const dia = ps[0].data, doDia = ps.filter(p => p.data === dia), itens = doDia.flatMap(p => p.itens);
    const quando = dia === hoje ? "Hoje" : "Próxima reunião, " + dia.split("-").reverse().slice(0, 2).join("/");
    linhas.push(`🏛️ *${quando} no plenário, às ${doDia[0].hora.replace(":", "h")}:* ${itens.length ? itens.length + " itens na pauta." : "pauta ainda não publicada."}`);
    const dest = itens.filter(i => i.temas.length && !i.temas.includes("Homenagens")).slice(0, 4);
    dest.forEach(i => linhas.push(`• ${i.temas[0]}: ${curto(i.ementa, 95)}${/veto/i.test(i.fase) ? " (veto da Prefeitura)" : ""}`));
    linhas.push("Pauta completa: jflandia.com.br/#/agenda", "");
  }
  const futuras = ((AG && AG.eventos) || []).filter(e => e.data >= hoje).slice(0, 2);
  futuras.forEach(e => linhas.push(`🎤 *Audiência pública ${e.data.split("-").reverse().slice(0, 2).join("/")}${e.hora ? " às " + e.hora.replace(":00", "h").replace(":", "h") : ""}:* ${curto(e.tema, 110)}`));
  if (futuras.length) linhas.push("");
  // alertas novos da última semana
  if (AL) {
    const lim = new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10);
    const novos = AL.alertas.filter(a => a.desde && a.desde !== "antes" && a.desde >= lim);
    if (novos.length) {
      linhas.push(`⚠️ *${novos.length} ${novos.length === 1 ? "sinal de alerta novo" : "sinais de alerta novos"} nos gastos da Prefeitura:*`);
      novos.slice(0, 3).forEach(a => linhas.push(`• ${a.nome}: ${(AL.tipos[a.tipo] || a.tipo).toLowerCase()}`));
      linhas.push("Veja: jflandia.com.br/#/prefeitura/alertas", "");
    } else {
      linhas.push(`⚠️ *${AL.alertas.length} sinais de alerta* nos gastos da Prefeitura: jflandia.com.br/#/prefeitura/alertas`, "");
    }
  }
  // um tema da lupa por dia, em rodízio
  if (LU) {
    const ts = LU.temas.filter(t => t.anos[String(y)]);
    if (ts.length) {
      const t = ts[Math.floor(Date.UTC(y, m - 1, d) / 864e5) % ts.length], A = t.anos[String(y)];
      const f = A.fornecedores[0];
      linhas.push(`🔎 *Na lupa, ${t.titulo.toLowerCase()}:* ${reaisCurto(A.p)} pagos pela Prefeitura em ${y} até agora${f ? `. Quem mais recebeu: ${f[1]} (${reaisCurto(f[2])})` : ""}.`, `jflandia.com.br/#/prefeitura/lupa/${t.id}`, "");
    }
  }
  linhas.push("Dados oficiais, atualizados todo dia. 👉 jflandia.com.br");
  const texto = linhas.join("\n");
  app.innerHTML = `<h1>Resumo do dia</h1>
    <p class="sub">O que está acontecendo hoje na Câmara e nos gastos da Prefeitura, num texto pronto para o WhatsApp. Muda sozinho todo dia.</p>
    ${CANAL_ZAP ? `<a class="btn-alerta" href="${CANAL_ZAP}" target="_blank" rel="noopener">${ic("agenda")}<span class="tx"><b>Seguir o canal do Radar no WhatsApp</b><small>Receba o resumo no celular. Ninguém vê o seu número e o Radar não guarda nenhum dado seu.</small></span><span class="seta">›</span></a>` : ""}
    <pre class="resumo-zap">${esc(texto)}</pre>
    <div class="botoes-ag"><button class="btn-ag" id="copiar">Copiar o texto</button><a class="btn-ag sec" href="https://wa.me/?text=${encodeURIComponent(texto)}" target="_blank" rel="noopener">Enviar no WhatsApp</a></div>
    <p class="sub">Os asteriscos viram negrito no WhatsApp.</p>`;
  document.getElementById("copiar").onclick = async e => {
    try { await navigator.clipboard.writeText(texto); e.target.textContent = "Copiado!"; } catch (_) { e.target.textContent = "Selecione o texto e copie"; }
  };
}

// botão flutuante para compartilhar a página atual no WhatsApp
function botaoZap(pag, partes) {
  let b = document.getElementById("zap");
  if (!b) { b = document.createElement("a"); b.id = "zap"; b.target = "_blank"; b.rel = "noopener"; b.setAttribute("aria-label", "Compartilhar esta página no WhatsApp"); document.body.appendChild(b); }
  let url = SITE + (location.hash || "");
  if (pag === "v" && partes[1]) url = SITE + "v/" + partes[1] + "/";
  if (pag === "prefeitura" && partes[1] === "empresa" && partes[3]) url = SITE + "empresa/" + partes[3] + "/";
  const h1 = (app.querySelector("h1") || {}).textContent || "";
  const msg = pag === "v" ? `Veja o que ${h1.trim()} fez na Câmara de Juiz de Fora, com dados oficiais:`
    : pag === "placar" ? "Qual vereador de Juiz de Fora trabalha mais? Monte o seu ranking:"
    : !pag ? "Veja o que fazem com o seu dinheiro em Juiz de Fora, com dados oficiais:"
    : `${h1.trim() || "Radar JFlândia"}: veja no Radar JFlândia, com dados oficiais:`;
  b.href = "https://wa.me/?text=" + encodeURIComponent(msg + "\n" + url);
  b.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.6.8-.8 1-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.6.5-.1 1.5-.6 1.7-1.2s.2-1.1.2-1.2-.2-.2-.4-.3z"/></svg><span>Compartilhar</span>`;
}
window.addEventListener("hashchange", rota);
window.addEventListener("load", () => {
  document.querySelectorAll("[data-ic]").forEach(e => e.outerHTML = ic(e.dataset.ic));
  rota();
});


// ---------- custo do gabinete e eleição de 2024 (perfil do vereador) ----------
const mesBR = k => { const [a, m] = k.split("-"); return `${["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"][+m - 1]}/${a}`; };
const gabDe = v => GAB_R && GAB_R.vereadores[String(v.id)];
const tseDe = v => TSE_R && TSE_R.vereadores[String(v.id)];
const votos24 = v => v.votos_2024 || (tseDe(v) || {}).votos || 0;

function blocoGabinete(v) {
  const g = gabDe(v);
  if (!g) return "";
  const meses = Object.entries(g.meses).sort();
  const max = Math.max(...meses.map(([, x]) => x[1]), 1);
  return `<h2>Custo do gabinete</h2>
    <p class="sub">Quanto a Câmara paga, por mês, à equipe que o vereador escolhe (assessores nomeados por ele). Soma dos salários brutos; não inclui o salário do próprio vereador nem encargos.</p>
    <div class="nums"><span><b>${reaisCurto(g.atual.custo)}</b>em ${mesBR(GAB_R.ultimo_mes)}, com ${fmt(g.atual.n)} ${g.atual.n === 1 ? "pessoa" : "pessoas"}</span>
      <span><b>${reaisCurto(g.media)}</b>por mês, em média</span><span><b>${reaisCurto(g.total)}</b>desde ${esc(GAB_R.desde)}</span></div>
    <div class="mini-barras" role="img" aria-label="Custo do gabinete mês a mês">${meses.map(([k, x]) => `<span title="${mesBR(k)}: ${reais(x[1], false)}, ${x[0]} pessoas" style="height:${Math.max(4, Math.round(100 * x[1] / max))}%"></span>`).join("")}</div>
    ${g.equipe && g.equipe.length ? `<details class="equipe"><summary>${ic("pessoas")}<span><b>Ver a equipe do gabinete</b><small>${fmt(g.equipe.length)} ${g.equipe.length === 1 ? "pessoa" : "pessoas"} em ${mesBR(GAB_R.ultimo_mes)}, com cargo e salário bruto</small></span></summary>
      <table class="tab-equipe"><thead><tr><th>Nome</th><th>Cargo</th><th>Bruto no mês</th></tr></thead><tbody>
      ${g.equipe.map(([n, c, r]) => `<tr><td>${esc(n)}</td><td>${esc(c)}</td><td>${reais(r, false)}</td></tr>`).join("")}</tbody></table></details>` : ""}
    <p class="sub fonte-linha">Fonte: <a href="${esc(GAB_R.fonte_url)}" target="_blank" rel="noopener">remuneração dos servidores, Portal da Transparência da Câmara</a>. Nomes, cargos e salários de servidores são públicos por lei (Lei de Acesso à Informação).</p>`;
}

const ORIGEM = {fundo_eleitoral: "Fundo eleitoral (dinheiro público)", fundo_partidario: "Fundo partidário (dinheiro público)", pessoas_fisicas: "Doações de pessoas", proprios: "Dinheiro do próprio candidato", partido_e_outros_candidatos: "Partido e outros candidatos", outros: "Outros"};
function blocoEleicao(v) {
  const t = tseDe(v);
  if (!t) return "";
  const porVoto = t.votos ? t.gasto / t.votos : 0;
  const ori = Object.entries(t.origem || {}).sort((a, b) => b[1] - a[1]);
  const tot = ori.reduce((s, [, x]) => s + x, 0) || 1;
  const e20 = t.eleicao_2020;
  return `<h2>Eleição de 2024</h2>
    <div class="nums"><span><b>${fmt(t.votos)}</b>votos</span><span><b>${reaisCurto(t.gasto)}</b>gastos na campanha</span>${porVoto ? `<span><b>R$ ${porVoto.toLocaleString("pt-BR", {maximumFractionDigits: 2, minimumFractionDigits: 2})}</b>por voto</span>` : ""}</div>
    ${ori.length ? `<p class="sub">De onde veio o dinheiro da campanha (${reaisCurto(t.receita)}):</p>
      ${ori.map(([k, x]) => `<div class="barra-l"><span class="bl-t">${ORIGEM[k] || k}</span><span class="bl-b"><i style="width:${Math.round(100 * x / tot)}%"></i></span><span class="bl-v">${Math.round(100 * x / tot)}%</span></div>`).join("")}` : ""}
    <p class="sub" style="margin-top:12px">Bens declarados à Justiça Eleitoral: <b>${reaisCurto(t.bens_2024)}</b> em 2024${e20 ? `; em 2020, quando concorreu a ${esc(e20.cargo.toLowerCase())}, declarou <b>${reaisCurto(e20.bens)}</b>` : ""}.</p>
    <p class="sub fonte-linha">Fonte: <a href="${esc(TSE_R.fonte_url)}" target="_blank" rel="noopener">Portal de Dados Abertos do TSE</a> (prestação de contas e bens declarados pelo próprio candidato).</p>`;
}

// ---------- Placar: monte seu ranking ----------
const CRITERIOS = [
  {k: "leis", t: "Propostas de lei", d: "Projetos de lei, de resolução e emendas à Lei Orgânica apresentados.", mais: true, p: 2},
  {k: "pedidos", t: "Pedidos para os bairros", d: "Pedidos de obra e serviço (buraco, luz, capina...).", mais: true, p: 1},
  {k: "cobrancas", t: "Fiscalização", d: "Perguntas e cobranças à Prefeitura, pedidos de informação.", mais: true, p: 2},
  {k: "emendas", t: "Emendas que viraram pagamento", d: "Parte do dinheiro indicado em emendas que a Prefeitura já pagou.", mais: true, p: 1},
  {k: "gabinete", t: "Gabinete econômico", d: "Custo médio mensal da equipe do gabinete. Quanto menor, mais pontos.", mais: false, p: 1},
  {k: "homenagens", t: "Menos homenagens", d: "Moções, títulos e nomes de rua. Quanto menos, mais pontos.", mais: false, p: 0},
  {k: "porvoto", t: "Campanha barata", d: "Gasto de campanha em 2024 dividido pelos votos. Quanto menor, mais pontos.", mais: false, p: 0},
];
function valorCriterio(v, k) {
  const c = v.contagem || {};
  if (k === "emendas") { const e = emendasDe(v); return e && e.previsto ? e.pago / e.previsto : null; }
  if (k === "gabinete") { const g = gabDe(v); return g ? g.media : null; }
  if (k === "porvoto") { const t = tseDe(v); return t && t.votos ? t.gasto / t.votos : null; }
  return c[k] ?? 0;
}
// ---------- Falas nas reuniões (contadas nas atas) ----------
const ehPresidente = v => /^presidente$/i.test(String(v.mesa || "").trim());
const falasDe = v => FALAS && FALAS.vereadores ? FALAS.vereadores[v.id] || null : null;
const NOTA_FALAS = () => `Contamos, nas atas oficiais, as reuniões em que o vereador aparece falando ("o Vereador Fulano comentou, pediu, cobrou..."), desde ${FALAS ? dataBR(FALAS.desde) : ""}. Pedidos de rotina, como licença para sair ou justificar falta, não contam. A conta é feita por computador a partir do texto das atas e pode ter pequenos erros; cada número leva às atas para conferir. Falar muito não é o mesmo que trabalhar bem: a conta não mede a qualidade das falas, o trabalho nas comissões nem o trabalho no gabinete. O presidente conduz as reuniões, e as falas dele como presidente não são registradas com o nome, por isso ele fica fora da comparação.`;

const RANKINGS = [
  {id: "geral", t: "Placar geral", d: "Nota de 0 a 10 que junta propostas de lei, fiscalização, pedidos para os bairros, emendas pagas e gabinete econômico. Propostas de lei e fiscalização valem o dobro."},
  {id: "economico", t: "Gabinete mais econômico", d: "Quem gasta menos, por mês, com a equipe do gabinete (assessores escolhidos pelo vereador). Média mensal desde o início do mandato."},
  {id: "eficiente", t: "Gabinete mais eficiente", d: "Quanto trabalho o vereador apresentou para cada R$ 100 mil gastos com o gabinete. Você escolhe o que conta como trabalho."},
  {id: "leis", t: "Mais propostas de lei", d: "Projetos de lei, de resolução e emendas à Lei Orgânica apresentados desde o início do mandato."},
  {id: "cobrancas", t: "Mais fiscalização", d: "Perguntas e cobranças à Prefeitura e pedidos de informação apresentados desde o início do mandato."},
  {id: "pedidos", t: "Mais pedidos para os bairros", d: "Pedidos de obra e serviço (buraco, luz, capina...) apresentados desde o início do mandato."},
  {id: "emendas", t: "Emendas que viraram pagamento", d: "Parte do dinheiro que o vereador indicou em emendas e que a Prefeitura já pagou."},
  {id: "tribuna", t: "Quem mais fala nas reuniões", d: "Em quantas reuniões da Câmara o vereador falou, do total de reuniões do período em que esteve no mandato. Contado nas atas oficiais."},
  {id: "monte", t: "Monte o seu", d: "Escolha o quanto cada assunto importa para você e veja o seu ranking."},
];
const NIVEIS = ["Não conta", "Pouco", "Importante", "Muito"];
function pgPlacar(arg) {
  const atuais = RESUMO.vereadores.filter(v => !v.fora_da_lista);
  const custom = /^\d(-\d)+$/.test(arg || "");
  let aba = custom ? "monte" : (RANKINGS.some(r => r.id === arg) ? arg : "geral");
  const pesos = {};
  const vindos = (arg || "").split("-").map(Number);
  CRITERIOS.forEach((c, i) => pesos[c.k] = custom && Number.isFinite(vindos[i]) ? Math.max(0, Math.min(3, vindos[i])) : c.p);
  const conta = {leis: true, cobrancas: true, pedidos: true};
  const faixas = {};
  CRITERIOS.forEach(c => {
    const vals = atuais.map(v => valorCriterio(v, c.k)).filter(x => x !== null);
    faixas[c.k] = [Math.min(...vals), Math.max(...vals)];
  });
  const nota = (v, c) => {
    const x = valorCriterio(v, c.k); if (x === null) return null;
    const [a, b] = faixas[c.k]; if (b === a) return 10;
    const n = 10 * (x - a) / (b - a);
    return c.mais ? n : 10 - n;
  };
  const n1 = x => x.toLocaleString("pt-BR", {maximumFractionDigits: 1, minimumFractionDigits: 1});
  const linha = (v, i, barra, valor, det) => `
      <a class="rk" href="#/v/${v.id}"><span class="rk-pos">${i + 1}º</span>${avatar(v)}
        <span class="rk-cx"><span class="rk-nm">${esc(v.apelido)}<small>${esc(v.partido || "")}</small></span>
          <span class="rk-barra"><i style="width:${Math.max(0, Math.min(100, barra))}%"></i></span>
          ${det ? `<span class="rk-partes">${det}</span>` : ""}</span>
        <span class="rk-nota">${valor}</span></a>`;
  app.innerHTML = `
    <h1>Ranking dos vereadores</h1>
    <p class="sub">Escolha o ranking que você quer ver. Todos os vereadores são contados com a mesma regra, a partir de dados oficiais.</p>
    <div class="chips rk-abas" id="rk-abas">${RANKINGS.map(r => `<a href="javascript:void 0" data-a="${r.id}">${r.t}</a>`).join("")}</div>
    <p class="rk-expl" id="rk-expl"></p>
    <div id="rk-ctrl"></div>
    <div id="ranking"></div>
    <div class="info">Quantidade não mede qualidade: um projeto de lei importante vale mais que dez simbólicos. Use o ranking como ponto de partida e abra o perfil de cada vereador para ver o que ele apresentou.</div>
    <div class="acoes-placar"><button id="copiar-placar" class="btn-sec">Copiar o link deste ranking</button><span id="copiado" class="sub"></span></div>
    <p class="sub fonte-linha">Fontes: sistema de proposições da Câmara, Monitor de Emendas da Prefeitura, folha de pagamento da Câmara (Portal da Transparência) e TSE. Vereador sem dado num critério fica de fora daquele ranking ou daquela parte da nota.</p>`;
  const linkAtual = () => location.href.split("#")[0] + "#/placar/" + (aba === "monte" ? CRITERIOS.map(c => pesos[c.k]).join("-") : aba);
  const ctrl = document.getElementById("rk-ctrl"), out = document.getElementById("ranking");
  const desenha = () => {
    const R = RANKINGS.find(r => r.id === aba);
    document.querySelectorAll("#rk-abas a").forEach(a => a.classList.toggle("on", a.dataset.a === aba));
    document.getElementById("rk-expl").textContent = R.d;
    history.replaceState(null, "", "#/placar/" + (aba === "monte" ? CRITERIOS.map(c => pesos[c.k]).join("-") : aba));
    if (aba === "geral" || aba === "monte") {
      const ps = aba === "geral" ? Object.fromEntries(CRITERIOS.map(c => [c.k, c.p])) : pesos;
      ctrl.innerHTML = aba === "monte" ? `<div class="pesos" id="pesos">${CRITERIOS.map(c => `
        <div class="peso"><div class="pz-t"><b>${c.t}</b><small>${c.d}</small></div>
          <div class="pz-b" role="radiogroup" aria-label="Quanto importa: ${c.t}">${[0, 1, 2, 3].map(n => `<button data-k="${c.k}" data-n="${n}" class="${pesos[c.k] === n ? "on" : ""}" aria-pressed="${pesos[c.k] === n}">${NIVEIS[n]}</button>`).join("")}</div></div>`).join("")}</div>
        <p class="sub">Quanto mais importante, mais aquele assunto pesa na nota final.</p>` : "";
      const tot = CRITERIOS.reduce((x, c) => x + ps[c.k], 0);
      const lin = atuais.map(v => {
        let soma = 0, peso = 0; const partes = [];
        CRITERIOS.forEach(c => { const n = nota(v, c); if (ps[c.k] && n !== null) { soma += n * ps[c.k]; peso += ps[c.k]; partes.push([c, n]); } });
        return {v, nota: peso ? soma / peso : null, partes};
      }).sort((a, b) => (b.nota ?? -1) - (a.nota ?? -1));
      out.innerHTML = !tot ? '<p class="sub">Marque pelo menos um assunto como importante.</p>' :
        `<p class="sub">Nota de 0 a 10. Em cada assunto, 10 é o melhor da Câmara e 0 o pior.</p>` +
        lin.map((l, i) => linha(l.v, i, l.nota === null ? 0 : l.nota * 10, l.nota === null ? "sem dados" : n1(l.nota), l.partes.map(([c, n]) => `<span>${c.t}: ${n1(n)}</span>`).join(""))).join("");
      document.querySelectorAll("#pesos button").forEach(b => b.onclick = () => { pesos[b.dataset.k] = +b.dataset.n; desenha(); });
      return;
    }
    ctrl.innerHTML = "";
    let lista;
    if (aba === "economico") {
      lista = atuais.map(v => ({v, x: (gabDe(v) || {}).media})).filter(l => l.x != null).sort((a, b) => a.x - b.x);
      const mx = Math.max(...lista.map(l => l.x));
      out.innerHTML = `<p class="sub">Do mais barato para o mais caro. Soma dos salários brutos da equipe; não inclui o salário do próprio vereador.</p>` +
        lista.map((l, i) => { const g = gabDe(l.v); return linha(l.v, i, 100 * (1 - l.x / mx) + 5, `${reaisCurto(l.x)}<small>por mês</small>`, `<span>Hoje: ${fmt(g.atual.n)} ${g.atual.n === 1 ? "pessoa" : "pessoas"}, ${reaisCurto(g.atual.custo)} no mês</span><span>Total desde ${esc(GAB_R.desde)}: ${reaisCurto(g.total)}</span>`); }).join("");
    } else if (aba === "eficiente") {
      ctrl.innerHTML = `<div class="rk-conta"><span>O que conta como trabalho:</span>${[["leis", "Propostas de lei"], ["cobrancas", "Fiscalização"], ["pedidos", "Pedidos para os bairros"]].map(([k, t]) => `<label><input type="checkbox" data-k="${k}" ${conta[k] ? "checked" : ""}> ${t}</label>`).join("")}</div>`;
      ctrl.querySelectorAll("input").forEach(c => c.onchange = () => { conta[c.dataset.k] = c.checked; desenha(); });
      const ks = Object.keys(conta).filter(k => conta[k]);
      if (!ks.length) { out.innerHTML = '<p class="sub">Marque pelo menos um tipo de trabalho.</p>'; return; }
      lista = atuais.map(v => { const g = gabDe(v), c = v.contagem || {}; const trab = ks.reduce((x, k) => x + (c[k] || 0), 0); return {v, trab, g, x: g && g.total ? trab / g.total * 100000 : null}; })
        .filter(l => l.x != null).sort((a, b) => b.x - a.x);
      const mx = Math.max(...lista.map(l => l.x), 0.0001);
      out.innerHTML = `<p class="sub">Itens apresentados para cada R$ 100 mil gastos com o gabinete desde ${esc(GAB_R.desde)}. ${conta.pedidos ? "Pedidos para os bairros são numerosos e costumam puxar a conta para cima; desmarque para ver só propostas de lei e fiscalização." : ""}</p>` +
        lista.map((l, i) => linha(l.v, i, 100 * l.x / mx, `${n1(l.x)}<small>por R$ 100 mil</small>`, `<span>${fmt(l.trab)} itens apresentados</span><span>Gabinete: ${reaisCurto(l.g.total)} no total</span>`)).join("");
    } else if (aba === "tribuna") {
      if (!FALAS) { out.innerHTML = '<p class="sub">Os dados das atas ainda estão sendo preparados.</p>'; return; }
      const com = atuais.map(v => ({v, f: falasDe(v)})).filter(l => l.f && l.f.reunioes);
      const presid = com.filter(l => ehPresidente(l.v));
      lista = com.filter(l => !ehPresidente(l.v)).map(l => ({...l, x: l.f.falou / l.f.reunioes})).sort((a, b) => b.x - a.x);
      const det = l => `<span>Falou em ${fmt(l.f.falou)} de ${fmt(l.f.reunioes)} reuniões</span>${l.f.reunioes < 60 ? `<span>No mandato de ${dataBR(l.f.de)} a ${dataBR(l.f.ate)}: período curto, compare com cuidado</span>` : ""}`;
      out.innerHTML = `<p class="sub">${NOTA_FALAS()} <a href="#/atas">Ver todas as atas</a>.</p>` +
        lista.map((l, i) => linha(l.v, i, 100 * l.x, `${Math.round(100 * l.x)}%<small>das reuniões</small>`, det(l))).join("") +
        presid.map(l => `<a class="rk" href="#/v/${l.v.id}"><span class="rk-pos"></span>${avatar(l.v)}
          <span class="rk-cx"><span class="rk-nm">${esc(l.v.apelido)}<small>${esc(l.v.partido || "")}</small></span>
          <span class="rk-partes"><span>Presidente da Câmara: conduz as reuniões, por isso fica fora da comparação</span></span></span>
          <span class="rk-nota"><small>presidente</small></span></a>`).join("");
    } else if (aba === "emendas") {
      lista = atuais.map(v => { const e = emendasDe(v); return {v, e, x: e && e.previsto ? e.pago / e.previsto : null}; }).filter(l => l.x != null).sort((a, b) => b.x - a.x);
      out.innerHTML = `<p class="sub">Percentual do valor indicado em emendas que a Prefeitura já pagou. Depende também da Prefeitura, não só do vereador.</p>` +
        lista.map((l, i) => linha(l.v, i, 100 * l.x, `${Math.round(100 * l.x)}%<small>pago</small>`, `<span>Indicado: ${reaisCurto(l.e.previsto)}</span><span>Pago: ${reaisCurto(l.e.pago)}</span>`)).join("");
    } else {
      const k = aba, nome = {leis: ["proposta", "propostas"], cobrancas: ["cobrança", "cobranças"], pedidos: ["pedido", "pedidos"]}[k];
      lista = atuais.map(v => ({v, x: (v.contagem || {})[k] || 0})).sort((a, b) => b.x - a.x);
      const mx = Math.max(...lista.map(l => l.x), 1);
      out.innerHTML = lista.map((l, i) => linha(l.v, i, 100 * l.x / mx, `${fmt(l.x)}<small>${l.x === 1 ? nome[0] : nome[1]}</small>`, "")).join("");
    }
  };
  document.querySelectorAll("#rk-abas a").forEach(a => a.onclick = () => { aba = a.dataset.a; desenha(); a.scrollIntoView({block: "nearest", inline: "center"}); });
  document.getElementById("copiar-placar").onclick = async () => {
    const url = linkAtual();
    try { await navigator.clipboard.writeText(url); document.getElementById("copiado").textContent = "Link copiado."; } catch (e) { document.getElementById("copiado").textContent = url; }
  };
  desenha();
}

// setas do menu de baixo quando as opções não cabem na tela
function setasSubnav() {
  const sub = document.getElementById("subnav"), w = sub.parentElement;
  const esq = w.querySelector(".sn-seta.esq"), dir = w.querySelector(".sn-seta.dir");
  const atualiza = () => {
    const sobra = sub.scrollWidth - sub.clientWidth;
    esq.hidden = !(sobra > 4 && sub.scrollLeft > 4);
    dir.hidden = !(sobra > 4 && sub.scrollLeft < sobra - 4);
  };
  if (!w.dataset.ok) {
    w.dataset.ok = 1;
    esq.onclick = () => sub.scrollBy({left: -sub.clientWidth * 0.7, behavior: "smooth"});
    dir.onclick = () => sub.scrollBy({left: sub.clientWidth * 0.7, behavior: "smooth"});
    sub.addEventListener("scroll", atualiza, {passive: true});
    window.addEventListener("resize", atualiza);
  }
  atualiza();
}


// ---------- Apoie ----------
// Enquanto a campanha no Catarse não estiver pronta, a página só avisa. Quando houver o link, preencher APOIA_SE.
const APOIA_SE = "";
function pgApoie() {
  app.innerHTML = `
    <h1>Apoie o Radar JFlândia</h1>
    <p class="sub">O Radar coleta todo dia os dados oficiais da Câmara e da Prefeitura e mostra de um jeito que qualquer pessoa entende.</p>
    ${APOIA_SE ? `<a class="btn-apoie" href="${APOIA_SE}" target="_blank" rel="noopener">${ic("coracao")}<span class="tx"><b>Apoiar pelo Catarse</b><small>Apoio mensal ou avulso, pelo cartão, Pix ou boleto</small></span><span class="seta">›</span></a>` : '<p>A página de apoio está sendo preparada. Volte em breve.</p>'}
    <h2>Quem não pode apoiar</h2>
    <p>Para o Radar continuar independente, <b>não aceitamos apoio</b> de partidos, candidatos, vereadores, da prefeita, de servidores comissionados nem de empresas e entidades que recebem dinheiro da Prefeitura ou da Câmara. Se um apoio desses chegar, ele é devolvido.</p>`;
}


// ---------- aplicativo (instalar na tela do celular) ----------
let _pedidoInstalar = null;
const jaInstalado = () => matchMedia("(display-mode: standalone)").matches || navigator.standalone;
const ehIphone = () => /iphone|ipad|ipod/i.test(navigator.userAgent);
if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
addEventListener("beforeinstallprompt", e => { e.preventDefault(); _pedidoInstalar = e; botaoInstalar(); });
addEventListener("appinstalled", () => { _pedidoInstalar = null; botaoInstalar(); });
function botaoInstalar() {
  const box = document.getElementById("instalar-app");
  if (!box) return;
  if (jaInstalado() || (!_pedidoInstalar && !ehIphone())) { box.innerHTML = ""; return; }
  box.innerHTML = `<button class="btn-app" id="btn-app" type="button"><img src="icone-192.png" alt="" width="40" height="40"><span class="tx"><b>Instale o app JFlândia</b><small>Ícone na tela do celular, abre direto, sem precisar procurar o site.</small></span><span class="seta">›</span></button><div id="app-ios" class="app-ios" hidden>No iPhone: toque em <b>Compartilhar</b> (o quadrado com a seta para cima, embaixo da tela) e depois em <b>Adicionar à Tela de Início</b>.</div>`;
  document.getElementById("btn-app").onclick = async () => {
    if (_pedidoInstalar) { _pedidoInstalar.prompt(); await _pedidoInstalar.userChoice.catch(() => {}); _pedidoInstalar = null; botaoInstalar(); }
    else document.getElementById("app-ios").hidden = false;
  };
}

// ---------- Pedido x obra: o pedido do vereador virou gasto de obra? ----------
async function pgPedidoObra(arg) {
  app.innerHTML = `<h1>O pedido virou obra?</h1><p class="carregando">Carregando…</p>`;
  const P = await fetch("dados/pedido_obra.json").then(r => r.ok ? r.json() : null).catch(() => null);
  if (!P) { app.innerHTML = `<h1>O pedido virou obra?</h1><div class="info">Os dados ainda estão sendo preparados. Volte mais tarde.</div>`; return; }
  const nomeV = id => (VER[id] || {}).apelido || "";
  const semAc = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const reaisP = v => window.reais ? reais(v) : reaisCurto(v);
  const cartao = (r, aberto) => `<details class="po-card"${aberto ? " open" : ""}><summary>
      <span class="po-rua"><b>${esc(r.r)}</b>${r.b ? `<small> · ${esc(r.b)}</small>` : ""}</span>
      <span class="po-nums"><span class="po-ped">${fmt(r.q)} ${r.q === 1 ? "pedido de obra" : "pedidos de obra"}</span>${r.ng ? `<span class="po-gas">${fmt(r.ng)} ${r.ng === 1 ? "gasto" : "gastos"} de obra · ${reaisP(r.ge)}</span>` : ""}${r.na ? `<span class="po-gas">${fmt(r.na)} no Diário Oficial</span>` : ""}${!r.ng && !r.na ? `<span class="po-sem">nada encontrado</span>` : ""}</span></summary>
      <div class="po-corpo">
        <p class="sub">Pedidos de ${r.au.map(id => `<a href="#/v/${id}">${esc(nomeV(id))}</a>`).filter(x => !/>\s*<\/a>/.test(x)).join(", ") || "vereadores"}${r.d1 ? `, de ${dataBR(r.d1)} a ${dataBR(r.d2)}` : ""}${r.temas.length ? `. Assuntos: ${r.temas.map(esc).join(", ").toLowerCase()}` : ""}.</p>
        ${(r.ped || []).slice(0, 4).map(p => `<div class="po-item"><small class="sub">${p.d ? dataBR(p.d) : p.a} · <a href="${FONTE(p.i)}" target="_blank" rel="noopener">${esc(p.t)} ${esc(p.n)}/${esc(p.a)}</a></small><p>${esc(p.e)}</p></div>`).join("")}
        ${r.g && r.g.length ? `<h3>Gastos de obra da Prefeitura que citam esta rua</h3>
        ${r.g.slice().reverse().map(g => `<div class="po-item obra"><small class="sub">${dataBR(g.d)} · ${esc(g.cred)} · ${esc(g.sec)}</small><p>${esc(g.h)}</p><small><b>${reaisP(g.e)}</b> reservados · ${reaisP(g.p)} pagos · <a href="#/prefeitura/empresa/${g.d.slice(0, 4)}/${g.cnpj}">ver a empresa</a></small></div>`).join("")}
        ${r.depois ? "" : '<p class="sub">Os gastos encontrados são de antes do primeiro pedido.</p>'}` : ""}
        ${r.at && r.at.length ? `<h3>Contratos e licitações de obra no Diário Oficial que citam esta rua</h3>
        ${r.at.map(a => `<div class="po-item obra"><small class="sub">${dataBR(a.d)} · ${esc(a.tipo)}</small><p>${esc(a.x)}</p><small><a href="${P.link_ato}${a.id}" target="_blank" rel="noopener">ver no Diário Oficial</a></small></div>`).join("")}` : ""}
      </div></details>`;
  const desenha = q => {
    const t = semAc(q).trim();
    const filtra = L => t ? L.filter(r => semAc(r.r + " " + r.b).includes(t)) : L;
    const C = filtra(P.com_gasto), S = filtra(P.sem_gasto);
    document.getElementById("po-res").innerHTML = `
      <h2>Ruas com pedido e com obra encontrada</h2>
      <p class="sub">${t ? `${fmt(C.length)} ${C.length === 1 ? "rua" : "ruas"} com “${esc(q)}”.` : `${fmt(P.ruas_com_gasto)} ruas. Começando pelas mais pedidas.`}</p>
      ${C.slice(0, t ? 60 : 25).map((r, i) => cartao(r, t && i === 0)).join("") || '<p class="sub">Nenhuma.</p>'}
      <h2>Ruas muito pedidas sem obra encontrada</h2>
      <p class="sub">Ruas com 3 pedidos ou mais em que o Radar não achou nenhum gasto nem contrato de obra da Prefeitura citando a rua. Isso não prova que nada foi feito: veja o aviso acima.</p>
      ${S.slice(0, t ? 60 : 20).map(r => cartao(r, false)).join("") || '<p class="sub">Nenhuma.</p>'}`;
  };
  app.innerHTML = `
    <h1>O pedido virou obra?</h1>
    <p class="sub">Os vereadores pedem à Prefeitura asfalto, drenagem, iluminação, contenção de encosta e outras obras para ruas da cidade. Aqui o Radar junta esses pedidos com os gastos de obra da Prefeitura e os contratos e licitações de obra publicados no Diário Oficial que citam a mesma rua.</p>
    <div class="faixa-nums">
      <div><b>${fmt(P.pedidos_com_rua)}</b><span>pedidos de obra dos vereadores que citam uma rua</span></div>
      <div><b>${fmt(P.ruas_com_pedido)}</b><span>ruas diferentes</span></div>
      <div><b>${fmt(P.ruas_com_gasto)}</b><span>ruas com gasto ou contrato de obra encontrado</span></div>
    </div>
    <form class="busca-rapida" onsubmit="event.preventDefault()"><label class="sr" for="po-q">Buscar uma rua</label>
      <input type="search" id="po-q" placeholder="Digite a sua rua ou bairro" value="${esc(arg || "")}" autocomplete="off"></form>
    <div class="info"><b>Leia com cuidado:</b> quando o Radar acha um gasto ou contrato, quer dizer que a Prefeitura reservou dinheiro ou contratou uma obra ou serviço que cita aquela rua, não que o pedido foi atendido do jeito que o vereador pediu. E quando não acha, não quer dizer que nada foi feito: muitos serviços, como tapa-buraco, capina e iluminação, são pagos em contratos grandes que não citam a rua, e os arquivos públicos da Prefeitura só trazem ${(P.anos_gastos || []).join(" e ")}.</div>
    <div id="po-res"></div>
    <p class="sub fonte-linha">Fontes: pedidos (indicações e requerimentos) do <a href="${P.fonte_ped}" target="_blank" rel="noopener">sistema da Câmara</a> gastos (empenhos) dos <a href="${P.fonte_gastos}" target="_blank" rel="noopener">arquivos do Portal da Transparência da Prefeitura</a> e contratos e licitações do Diário Oficial do Município. A rua é encontrada por computador no texto de cada pedido e de cada gasto; quando os dois citam bairros diferentes, não são juntados. Atualizado em ${esc(P.atualizado)}.</p>`;
  let tm;
  document.getElementById("po-q").oninput = e => { clearTimeout(tm); tm = setTimeout(() => { desenha(e.target.value); history.replaceState(null, "", "#/obra" + (e.target.value.trim() ? "/" + encodeURIComponent(e.target.value.trim()) : "")); }, 250); };
  desenha(arg || "");
}
