"use strict";
const FONTE = id => `https://www.camarajf.mg.gov.br/sal/proposicaon.php?num=${id}`;
const BUSCA_CAMARA = "https://www.camarajf.mg.gov.br/sal/buscapropos.php";
const ORDEM = ["pedidos", "cobrancas", "homenagens", "leis", "outros"];
const CURTO = {pedidos: "Pedidos nos bairros", cobrancas: "Perguntas e cobranças", homenagens: "Homenagens", leis: "Propostas de lei", outros: "Outros"};
const TIPOS = {REQ: "Requerimento", IND: "Indicação", PEDIF: "Pedido de Informação", REP: "Representação", MOC: "Moção", PLEI: "Projeto de Lei", PLEIC: "Projeto de Lei Complementar", PELOR: "Emenda à Lei Orgânica", PRES: "Projeto de Resolução", PDL: "Projeto de Decreto Legislativo"};

// ícones simples (traço), usados nos botões
const ICONE = {
  coracao: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
  alerta: '<path d="M12 3 2 20h20zM12 10v4M12 17h.01"/>',
  placar: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  balanca: '<path d="M12 3v18M5 21h14M3 7h18M6 7l-3 7a3 3 0 0 0 6 0zM18 7l-3 7a3 3 0 0 0 6 0z"/>',
  camara: '<path d="M3 21h18M5 21V10M9.5 21V10M14.5 21V10M19 21V10M2 10l10-6 10 6z"/>',
  dinheiro: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h.01M18 12h.01"/>',
  agenda: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  pin: '<path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
  repete: '<path d="M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3"/>',
  lupa: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  pessoas: '<circle cx="9" cy="7" r="4"/><path d="M2 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2M16 3.1a4 4 0 0 1 0 7.8M22 21v-2a4 4 0 0 0-3-3.9"/>',
  predios: '<path d="M3 21h18M5 21V4h9v17M14 9h5v12M8 8h3M8 12h3M8 16h3"/>',
  maleta: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2M2 13h20"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  jornal: '<path d="M4 4h13v16H6a2 2 0 0 1-2-2zM17 8h3v10a2 2 0 0 1-2 2M8 8h5M8 12h5M8 16h3"/>',
};
const ic = (n, cls = "") => `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONE[n] || ""}</svg>`;
const iniciais = n => String(n || "").replace(/^(Dr|Dra|Sargento|Prof|Profa)\.?\s+/i, "").split(/\s+/).filter(p => p.length > 2 || /^[A-ZÀ-Ý]/.test(p)).slice(0, 2).map(p => p[0]).join("").toUpperCase();

let FOTOS = new Set(), CREDITO_FOTO = "", EMENDAS_R = null, GAB_R = null, TSE_R = null;
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
const SUBNAV = {
  camara: [["#/camara", "Vereadores", "pessoas"], ["#/placar", "Placar", "placar"], ["#/busca", "Meu bairro", "pin"], ["#/repetidos", "Pedidos que voltam", "repete"], ["#/agenda", "Agenda", "agenda"]],
  prefeitura: [["#/prefeitura/alertas", "Sinais de alerta", "alerta"], ["#/prefeitura/lupa", "Na lupa", "lupa"], ["#/prefeitura/impostometro", "Impostômetro", "dinheiro"], ["#/prefeitura/placar", "Placar fiscal", "balanca"], ["#/prefeitura/comissionados", "Comissionados", "pessoas"], ["#/prefeitura", "Gastos por secretaria", "predios"], ["#/prefeitura/emendas", "Emendas dos vereadores", "pessoas"], ["#/prefeitura/fornecedores", "Quem recebe", "maleta"], ["#/prefeitura/busca", "Buscar gasto", "lupa"]],
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
      <div class="logo-home" role="img" aria-label="Radar JFlândia">
      <div class="lh-1"><svg class="lh-ic" viewBox="0 0 120 80" aria-hidden="true"><circle cx="60" cy="40" r="11" fill="currentColor"/><path d="M40 18a32 32 0 0 0 0 44M80 18a32 32 0 0 1 0 44M24 6a52 52 0 0 0 0 68M96 6a52 52 0 0 1 0 68" fill="none" stroke="currentColor" stroke-width="9" stroke-linecap="round"/></svg><span>RADAR</span></div>
      <div class="lh-2"><span class="pt">JF</span><span>LÂNDIA</span><span class="lh-bands"><svg class="lh-band" viewBox="0 0 30 21" aria-label="Bandeira do Brasil" role="img"><rect width="30" height="21" fill="#009c3b"/><path d="M15 2.5 27.5 10.5 15 18.5 2.5 10.5z" fill="#ffdf00"/><circle cx="15" cy="10.5" r="4.6" fill="#002776"/></svg><svg class="lh-band" viewBox="0 0 30 21" aria-label="Bandeira de Minas Gerais" role="img"><rect width="30" height="21" fill="#fff" stroke="#c9ccd1" stroke-width=".6"/><path d="M15 4 21.5 16H8.5z" fill="#e8272c"/></svg><svg class="lh-band" viewBox="0 0 30 21" aria-label="Bandeira de Juiz de Fora" role="img"><rect width="30" height="21" fill="#1f4e9c"/><rect y="6.46" width="30" height="1.62" fill="#fff"/><rect y="8.08" width="30" height="4.85" fill="#d52b1e"/><rect y="12.92" width="30" height="1.62" fill="#fff"/><rect y="14.54" width="30" height="6.56" fill="#16924a"/><path d="M15 8.88 16.86 12.12 13.14 12.12z" fill="#fff"/></svg></span></div>
    </div>
      <h1 class="hero-t">Veja o que os vereadores e a prefeita de Juiz de Fora fazem com o <span>seu dinheiro</span></h1>
      <p class="hero-sub">Raio-X de Juiz de Fora-MG. Cada proposta, cada gasto e cada salário, contados todo dia, só com dados oficiais.</p>
      <div id="hoje-camara"></div>
      <label class="hero-sel"><span class="sr">Escolha um vereador</span>
        <select id="esc-ver"><option value="">Escolha um vereador</option>${atuais.map(v => `<option value="${v.id}">${esc(v.apelido)} (${esc(v.partido || "")})</option>`).join("")}</select></label>
      <form class="hero-busca" id="hero-busca"><label class="sr" for="hb">Pesquisar meu bairro</label><input id="hb" placeholder="Ou digite o seu bairro ou rua" autocomplete="off"><button type="submit">Buscar</button></form>
    </section>
    <a class="btn-alerta" href="#/prefeitura/alertas">${ic("alerta")}<span class="tx"><b><span id="ba-n">Sinais</span> de alerta nos gastos da Prefeitura</b><small>Compras fatiadas, empresas punidas, sócios que doaram para campanhas e mais. Veja o que merece uma pergunta.</small></span><span class="seta">›</span></a>
    <div class="faixa-nums">
      <a href="#/camara"><b id="fx-sal">${reaisCurto(salarioAcumulado())}</b><span>em salários de vereadores desde a posse</span></a>
      <a href="#/prefeitura/impostometro"><b id="fx-imp">...</b><span>em impostos municipais pagos este ano</span></a>
      <a href="#/prefeitura/emendas"><b>${EMENDAS_R && EMENDAS_R.total ? reaisCurto(EMENDAS_R.total.previsto) : "Emendas"}</b><span>em emendas indicadas pelos vereadores</span></a>
    </div>
    <div id="instalar-app"></div>
    <div class="escolhas">
      <a class="placa camara" href="#/camara">${ic("camara")}<span class="tx"><span class="tt">Câmara</span><span class="ds">O que cada um dos ${nV} vereadores apresentou, quanto custa cada gabinete e o que foi pedido para o seu bairro.</span><span class="num">${fmt(RESUMO.total)} propostas</span></span><span class="seta">›</span></a>
      <a class="placa prefeitura" href="#/prefeitura">${ic("dinheiro")}<span class="tx"><span class="tt">Prefeitura</span><span class="ds">Para onde vai o dinheiro: quanto cada secretaria gasta, com quem e em quê.</span><span class="num">Gastos por secretaria</span></span><span class="seta">›</span></a>
    </div>
    <a class="btn-grande camara" href="#/placar">${ic("placar")}<span class="tx">Placar dos vereadores<small>Monte o seu ranking com os critérios que importam para você</small></span>›</a>
    <a class="btn-grande prefeitura" href="#/prefeitura/placar">${ic("balanca")}<span class="tx">Placar fiscal da Prefeitura<small>Gasta mais do que arrecada? Cumpre os mínimos de saúde e educação?</small></span>›</a>
    <a class="btn-grande prefeitura" href="#/prefeitura/busca">${ic("lupa")}<span class="tx">Pesquisar um gasto<small>Empresa, CNPJ ou palavra, como asfalto ou merenda</small></span>›</a>
    <div class="info">Câmara e Prefeitura são poderes diferentes. A Câmara (vereadores) faz leis, fiscaliza e pede melhorias. A Prefeitura (prefeita e secretarias) executa os serviços e gasta o orçamento.</div>`;
  botaoInstalar();
  document.getElementById("esc-ver").onchange = e => { if (e.target.value) location.hash = "#/v/" + e.target.value; };
  document.getElementById("hero-busca").onsubmit = e => { e.preventDefault(); const q = document.getElementById("hb").value.trim(); location.hash = "#/busca" + (q ? "/" + encodeURIComponent(q) : ""); };
  if (window.prefReceitas) prefReceitas().then(R => { const x = R && impostometro(R); const el = document.getElementById("fx-imp"); if (el) el.textContent = x ? reaisCurto(x.total) : "ver"; });
  fetch("dados/prefeitura/alertas.json").then(r => r.ok ? r.json() : null).catch(() => null).then(A => { const el = document.getElementById("ba-n"); if (el && A) el.textContent = fmt(A.alertas.length) + " sinais"; });
}

async function rota() {
  await carregarResumo();
  const h = location.hash.replace(/^#\/?/, "");
  const partes = h.split("/").map(decodeURIComponent);
  const pag = partes[0], arg = partes.slice(1).join("/");
  const area = pag === "prefeitura" ? "prefeitura" : ["camara", "v", "busca", "repetidos", "grupo", "placar", "agenda"].includes(pag) ? "camara" : pag === "sobre" ? "sobre" : "";
  document.querySelectorAll("nav.areas a").forEach(a => a.classList.toggle("ativo", a.dataset.area === area));
  const sub = document.getElementById("subnav");
  const atual = "#/" + h;
  sub.className = area;
  sub.innerHTML = (SUBNAV[area] || []).map(([href, t, i]) => `<a href="${href}" class="${atual === href || (atual.startsWith(href + "/") && href !== "#/prefeitura") || (href === "#/prefeitura" && /^#\/prefeitura\/(ano|s)\b/.test(atual)) || (href === "#/camara" && (atual.startsWith("#/v/") || atual.startsWith("#/grupo"))) ? "ativo" : ""}">${ic(i)}${t}</a>`).join("");
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
    ${passados.length ? `<h2>Audiências que já aconteceram</h2>${passados.slice(0, 20).map(e => card(e, false)).join("")}<p class="sub">As atas ficam na <a href="https://www.camarajf.mg.gov.br/sal/buscaratas.php" target="_blank" rel="noopener">busca de atas da Câmara</a>.</p>` : ""}
    <p class="sub fonte-linha">Fontes: <a href="https://www.camarajf.mg.gov.br/sal/buscarreuniao.php" target="_blank" rel="noopener">Ordem do Dia</a> e <a href="https://www.camarajf.mg.gov.br/www/audiencias-publicas" target="_blank" rel="noopener">página de audiências públicas da Câmara Municipal</a>${A ? `, conferida em ${esc(A.atualizado.split(" ")[0].split("-").reverse().join("/"))}` : ""}. O Radar guarda o histórico a partir de outubro de 2026.</p>`;

  app.querySelectorAll(".pt-filtro a").forEach(a => a.onclick = () => {
    app.querySelectorAll(".pt-filtro a").forEach(b => b.classList.toggle("on", b === a));
    app.querySelectorAll(".pt-item").forEach(it => it.hidden = !!a.dataset.t && !it.dataset.temas.split("|").includes(a.dataset.t));
  });}

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
function pgPlacar(arg) {
  const atuais = RESUMO.vereadores.filter(v => !v.fora_da_lista);
  const pesos = {};
  const vindos = (arg || "").split("-").map(Number);
  CRITERIOS.forEach((c, i) => pesos[c.k] = Number.isFinite(vindos[i]) && arg ? Math.max(0, Math.min(3, vindos[i])) : c.p);
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
  app.innerHTML = `
    <h1>Placar dos vereadores: monte o seu</h1>
    <p class="sub">Você escolhe o que pesa mais. Cada critério vira uma nota de 0 a 10 (10 para o melhor da Câmara naquele item) e o placar é a média com os pesos que você escolher. Todos os vereadores são contados com a mesma regra, a partir de dados oficiais.</p>
    <div class="info">Quantidade não mede qualidade: um projeto de lei importante vale mais que dez simbólicos. Use o placar como ponto de partida e abra o perfil de cada vereador para ver o que ele apresentou.</div>
    <div class="pesos" id="pesos">${CRITERIOS.map(c => `
      <div class="peso"><div class="pz-t"><b>${c.t}</b><small>${c.d}</small></div>
        <div class="pz-b" role="radiogroup" aria-label="Peso de ${c.t}">${[0, 1, 2, 3].map(n => `<button data-k="${c.k}" data-n="${n}" class="${pesos[c.k] === n ? "on" : ""}" aria-pressed="${pesos[c.k] === n}">${["Não conta", "Peso 1", "Peso 2", "Peso 3"][n]}</button>`).join("")}</div></div>`).join("")}
    </div>
    <div class="acoes-placar"><button id="copiar-placar" class="btn-sec">Copiar link deste placar</button><span id="copiado" class="sub"></span></div>
    <h2>Resultado</h2>
    <div id="ranking"></div>
    <p class="sub fonte-linha">Fontes: sistema de proposições da Câmara, Monitor de Emendas da Prefeitura, folha de pagamento da Câmara e TSE. Critérios sem dado para um vereador ficam de fora da média dele.</p>`;
  const desenha = () => {
    const tot = CRITERIOS.reduce((s, c) => s + pesos[c.k], 0);
    const linhas = atuais.map(v => {
      let soma = 0, peso = 0; const partes = [];
      CRITERIOS.forEach(c => { const n = nota(v, c); if (pesos[c.k] && n !== null) { soma += n * pesos[c.k]; peso += pesos[c.k]; partes.push([c, n]); } });
      return {v, nota: peso ? soma / peso : null, partes};
    }).sort((a, b) => (b.nota ?? -1) - (a.nota ?? -1));
    document.getElementById("ranking").innerHTML = !tot ? '<p class="sub">Escolha o peso de pelo menos um critério.</p>' : linhas.map((l, i) => `
      <a class="rk" href="#/v/${l.v.id}"><span class="rk-pos">${i + 1}º</span>${avatar(l.v)}
        <span class="rk-cx"><span class="rk-nm">${esc(l.v.apelido)}<small>${esc(l.v.partido || "")}</small></span>
          <span class="rk-barra"><i style="width:${l.nota === null ? 0 : l.nota * 10}%"></i></span>
          <span class="rk-partes">${l.partes.map(([c, n]) => `<span>${c.t}: ${n.toFixed(1).replace(".", ",")}</span>`).join("")}</span></span>
        <span class="rk-nota">${l.nota === null ? "sem dados" : l.nota.toFixed(1).replace(".", ",")}</span></a>`).join("");
  };
  document.querySelectorAll("#pesos button").forEach(b => b.onclick = () => {
    pesos[b.dataset.k] = +b.dataset.n;
    document.querySelectorAll(`#pesos button[data-k="${b.dataset.k}"]`).forEach(x => { x.classList.toggle("on", x === b); x.setAttribute("aria-pressed", x === b); });
    history.replaceState(null, "", "#/placar/" + CRITERIOS.map(c => pesos[c.k]).join("-"));
    desenha();
  });
  document.getElementById("copiar-placar").onclick = async () => {
    const url = location.href.split("#")[0] + "#/placar/" + CRITERIOS.map(c => pesos[c.k]).join("-");
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
