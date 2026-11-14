"use strict";
// Área PREFEITURA: para onde vai o dinheiro (dados do Portal da Transparência da PJF)
const PREF = {resumo: null, empenhos: {}};
const FONTE_PREF = "https://www.pjf.mg.gov.br/transparencia/dados_abertos/arquivos.php";
const NOMES_MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

function reais(v, curto = true) {
  v = v || 0;
  const a = Math.abs(v), s = v < 0 ? "-" : "";
  if (curto && a >= 1e9) return `${s}R$ ${(a / 1e9).toLocaleString("pt-BR", {maximumFractionDigits: 2})} bi`;
  if (curto && a >= 1e6) return `${s}R$ ${(a / 1e6).toLocaleString("pt-BR", {maximumFractionDigits: 1})} mi`;
  if (curto && a >= 1e4) return `${s}R$ ${(a / 1e3).toLocaleString("pt-BR", {maximumFractionDigits: 0})} mil`;
  return `${s}R$ ${a.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
}
const cnpjFmt = c => c && c.length === 14 ? `${c.slice(0, 2)}.${c.slice(2, 5)}.${c.slice(5, 8)}/${c.slice(8, 12)}-${c.slice(12)}` : c;
const fonteLink = (t = "fonte oficial") => `<a href="${FONTE_PREF}" target="_blank" rel="noopener">${t}</a>`;

async function prefResumo() {
  if (!PREF.resumo) PREF.resumo = await fetch("dados/prefeitura/resumo.json").then(r => r.json());
  return PREF.resumo;
}
async function prefEmpenhos(ano) {
  if (!PREF.empenhos[ano]) {
    app.innerHTML = '<p class="carregando">Carregando todos os gastos do ano (pode levar alguns segundos no celular)…</p>';
    const d = await fetch(`dados/prefeitura/empenhos_${ano}.json`).then(r => r.json());
    d.empenhos.forEach(x => x._busca = norm(`${x[6]} ${x[2] >= 0 ? d.credores[x[2]][1] + " " + d.credores[x[2]][0] : ""} ${d.secretarias[x[1]]} ${d.elementos[x[3]]}`));
    PREF.empenhos[ano] = d;
  }
  return PREF.empenhos[ano];
}
function anosDisp(R) { return Object.keys(R.anos).sort().reverse(); }
function seletorAnos(R, ano, base) {
  return `<div class="anos">${anosDisp(R).map(a => `<button class="${a == ano ? "on" : ""}" onclick="location.hash='${base}${a}'">${a}</button>`).join("")}</div>`;
}
const explicacao = `<div class="info"><b>Como ler:</b> <b>empenhado</b> é o dinheiro reservado para uma despesa; <b>liquidado</b> é quando a Prefeitura confere que o serviço ou produto foi entregue; <b>pago</b> é o dinheiro que efetivamente saiu. Os valores incluem anulações e correções feitas pela própria Prefeitura.</div>`;

function itemEmpenho(d, x) {
  const credor = x[2] >= 0 ? `<a href="#/prefeitura/empresa/${d.ano}/${d.credores[x[2]][0]}">${esc(d.credores[x[2]][1])}</a>` : "Pessoa física (nome não exibido)";
  return `<div class="item">
    <div class="topo">${x[0] ? dataBR(x[0]) + " · " : ""}Empenho nº ${esc(x[7])} · ${esc(d.secretarias[x[1]])}</div>
    <div class="txt"><b>${credor}</b>${x[6] ? "<br>" + esc(x[6]) : ""}</div>
    <div class="pe">${esc(d.elementos[x[3]])} · empenhado ${reais(x[4], false)} · pago ${reais(x[5], false)}</div>
  </div>`;
}
function listaEmpenhos(d, itens, alvo) {
  let n = 0;
  const box = document.createElement("div"), btn = document.createElement("button");
  btn.className = "mais";
  const mais = () => {
    box.insertAdjacentHTML("beforeend", itens.slice(n, n + 40).map(x => itemEmpenho(d, x)).join(""));
    n += 40;
    btn.style.display = n < itens.length ? "block" : "none";
    btn.textContent = `Mostrar mais (${fmt(itens.length - n)} restantes)`;
  };
  btn.onclick = mais;
  alvo.append(box, btn);
  mais();
}

async function pgPrefInicio(ano) {
  const R = await prefResumo();
  ano = ano || anosDisp(R)[0];
  const A = R.anos[ano], t = A.total;
  const max = Math.max(...A.secretarias.map(s => s.p), 1);
  app.innerHTML = `
    <h1>Para onde vai o dinheiro da Prefeitura</h1>
    <p class="sub">Quanto cada secretaria e órgão da Prefeitura de Juiz de Fora gastou, segundo os arquivos oficiais de despesas. ${fonteLink("Ver fonte oficial")}${R.fonte_atualizada_em ? ` (atualizada pela Prefeitura em ${esc(R.fonte_atualizada_em)})` : ""}.</p>
    ${seletorAnos(R, ano, "#/prefeitura/ano/")}
    <div class="totais">
      <div><span>Empenhado</span><b>${reais(t.e)}</b></div>
      <div><span>Liquidado</span><b>${reais(t.l)}</b></div>
      <div><span>Pago</span><b class="p-verde">${reais(t.p)}</b></div>
    </div>
    ${explicacao}
    <h2>Quanto cada órgão pagou em ${ano}</h2>
    <p class="sub">${A.secretarias.length} unidades, da que mais pagou para a que menos pagou. Toque para ver em quê e com quem.</p>
    ${A.secretarias.map((s, i) => `<a class="linha" href="#/prefeitura/s/${ano}/${i}"><span class="nm">${esc(s.nome)}<div class="barra-p" style="width:${Math.max(1, Math.round(100 * s.p / max))}%"></div></span><span class="vl">${reais(s.p)} ›</span></a>`).join("")}
    <h2>Pagamentos a pessoas físicas</h2>
    <p>${reais(A.pessoa_fisica.p)} pagos em ${fmt(A.pessoa_fisica.n)} lançamentos a pessoas físicas. A maior parte é folha de pagamento: salários de servidores, aposentadorias, pensões e contratos temporários. <b>Nomes e CPFs não são exibidos neste site.</b></p>
    ${(A.pessoa_fisica.elementos || []).map(e => `<div class="linha"><span class="nm">${esc(e.nome)}</span><span class="vl">${reais(e.p)}</span></div>`).join("")}`;
}

async function pgPrefSecretaria(ano, i) {
  const R = await prefResumo();
  const s = R.anos[ano].secretarias[i];
  if (!s) { app.innerHTML = "<p>Não encontrado.</p>"; return; }
  const maxM = Math.max(...s.meses.map(v => Math.max(v, 0)), 1);
  const maxE = Math.max(...s.elementos.map(e => e.p), 1);
  app.innerHTML = `
    <h1>${esc(s.nome)}</h1>
    <p class="sub">${s.categoria ? esc(s.categoria) + " · " : ""}${ano} · ${fmt(s.n)} lançamentos · ${fonteLink()}</p>
    <div class="totais">
      <div><span>Empenhado</span><b>${reais(s.e)}</b></div>
      <div><span>Liquidado</span><b>${reais(s.l)}</b></div>
      <div><span>Pago</span><b class="p-verde">${reais(s.p)}</b></div>
    </div>
    <h2>Pago por mês</h2>
    <div class="meses">${s.meses.map(v => `<div title="${reais(v, false)}" style="height:${Math.round(100 * Math.max(v, 0) / maxM)}%"></div>`).join("")}</div>
    <div class="meses-r">${NOMES_MES.map(m => `<span>${m}</span>`).join("")}</div>
    <h2>Em que o dinheiro foi gasto</h2>
    ${s.elementos.map(e => `<div class="linha"><span class="nm">${esc(e.nome) || "Não informado"}<div class="barra-p" style="width:${Math.max(1, Math.round(100 * e.p / maxE))}%"></div></span><span class="vl">${reais(e.p)}</span></div>`).join("")}
    <h2>Empresas que mais receberam</h2>
    ${s.fornecedores.length ? s.fornecedores.map(f => `<a class="linha" href="#/prefeitura/empresa/${ano}/${f.cnpj}"><span class="nm">${esc(f.nome)}<br><small class="sub">CNPJ ${cnpjFmt(f.cnpj)} · ${fmt(f.n)} lançamentos</small></span><span class="vl">${reais(f.p)} ›</span></a>`).join("") : '<p class="sub">Nenhuma empresa nesta unidade.</p>'}
    <p class="sub" style="margin-top:14px"><a href="#/prefeitura/busca/${ano}/${encodeURIComponent(s.nome)}">Ver todos os lançamentos desta unidade ›</a></p>`;
}

async function pgPrefFornecedores(ano) {
  const R = await prefResumo();
  ano = ano || anosDisp(R)[0];
  const A = R.anos[ano];
  app.innerHTML = `
    <h1>Empresas que recebem da Prefeitura</h1>
    <p class="sub">As 200 empresas que mais receberam em ${ano}, de um total de ${fmt(A.n_fornecedores)}. ${fonteLink()}</p>
    ${seletorAnos(R, ano, "#/prefeitura/fornecedores/")}
    <input type="search" id="q" placeholder="Filtrar por nome ou CNPJ" autocomplete="off" style="margin-top:10px">
    <div id="res"></div>
    <p class="sub">Para empresas fora desta lista, use a <a href="#/prefeitura/busca/${ano}">busca de gastos</a>.</p>`;
  const inp = document.getElementById("q");
  const mostra = () => {
    const q = norm(inp.value.trim()), qd = inp.value.replace(/\D/g, "");
    const it = A.fornecedores.filter(f => !q || norm(f.nome).includes(q) || (qd.length >= 4 && f.cnpj.includes(qd)));
    document.getElementById("res").innerHTML = it.map((f, k) => `<a class="linha" href="#/prefeitura/empresa/${ano}/${f.cnpj}"><span class="nm">${esc(f.nome)}<br><small class="sub">CNPJ ${cnpjFmt(f.cnpj)} · ${esc(f.secretarias.slice(0, 2).join(", "))}</small></span><span class="vl">${reais(f.p)} ›</span></a>`).join("") || '<p class="sub">Nenhuma empresa encontrada nesta lista.</p>';
  };
  let tm; inp.oninput = () => { clearTimeout(tm); tm = setTimeout(mostra, 200); };
  mostra();
}

async function pgPrefEmpresa(ano, cnpj) {
  const d = await prefEmpenhos(ano);
  const ic = d.credores.findIndex(c => c[0] === cnpj);
  if (ic < 0) { app.innerHTML = "<p>Empresa não encontrada neste ano.</p>"; return; }
  const itens = d.empenhos.filter(x => x[2] === ic).sort((a, b) => (b[0] || "").localeCompare(a[0] || ""));
  const tot = itens.reduce((s, x) => [s[0] + x[4], s[1] + x[5]], [0, 0]);
  const porSec = {};
  itens.forEach(x => porSec[d.secretarias[x[1]]] = (porSec[d.secretarias[x[1]]] || 0) + x[5]);
  app.innerHTML = `
    <h1>${esc(d.credores[ic][1])}</h1>
    <p class="sub">CNPJ ${cnpjFmt(cnpj)} · ${ano} · ${fmt(itens.length)} lançamentos · ${fonteLink()}</p>
    <div class="totais" style="grid-template-columns:1fr 1fr">
      <div><span>Empenhado</span><b>${reais(tot[0])}</b></div>
      <div><span>Pago</span><b class="p-verde">${reais(tot[1])}</b></div>
    </div>
    <h2>Por órgão</h2>
    ${Object.entries(porSec).sort((a, b) => b[1] - a[1]).map(([n, v]) => `<div class="linha"><span class="nm">${esc(n)}</span><span class="vl">${reais(v)}</span></div>`).join("")}
    <h2>Lançamentos</h2>
    <div id="lista"></div>`;
  listaEmpenhos(d, itens, document.getElementById("lista"));
}

async function pgPrefBusca(ano, q0) {
  const R = await prefResumo();
  ano = ano || anosDisp(R)[0];
  const d = await prefEmpenhos(ano);
  app.innerHTML = `
    <h1>Buscar gasto da Prefeitura</h1>
    <p class="sub">Procure por empresa, CNPJ, secretaria ou palavra da descrição (ex.: merenda, asfalto, combustível, show). ${fonteLink()}</p>
    ${seletorAnos(R, ano, "#/prefeitura/busca/")}
    <input type="search" id="q" placeholder="Ex.: asfalto, merenda, nome da empresa" value="${esc(q0 || "")}" autocomplete="off" style="margin-top:10px">
    <div id="res"></div>`;
  const inp = document.getElementById("q");
  const busca = () => {
    const q = norm(inp.value.trim());
    history.replaceState(null, "", `#/prefeitura/busca/${ano}/${encodeURIComponent(inp.value.trim())}`);
    const res = document.getElementById("res");
    if (q.length < 3) { res.innerHTML = '<p class="sub">Digite pelo menos 3 letras.</p>'; return; }
    const termos = q.split(/\s+/);
    const it = d.empenhos.filter(x => termos.every(t => x._busca.includes(t))).sort((a, b) => (b[0] || "").localeCompare(a[0] || ""));
    const tot = it.reduce((s, x) => [s[0] + x[4], s[1] + x[5]], [0, 0]);
    res.innerHTML = `<h2>${fmt(it.length)} lançamentos</h2>${it.length ? `<p class="sub">Somando: empenhado ${reais(tot[0])} · pago ${reais(tot[1])}</p>` : ""}`;
    listaEmpenhos(d, it, res);
  };
  let tm; inp.oninput = () => { clearTimeout(tm); tm = setTimeout(busca, 300); };
  busca();
}

async function rotaPrefeitura(p) {
  const [sub, a, b] = p;
  if (sub === "ano") return pgPrefInicio(a);
  if (sub === "s") return pgPrefSecretaria(a, +b);
  if (sub === "fornecedores") return pgPrefFornecedores(a);
  if (sub === "empresa") return pgPrefEmpresa(a, b);
  if (sub === "busca") return pgPrefBusca(a, b);
  return pgPrefInicio();
}

async function sobrePrefeitura() {
  let R = null;
  try { R = await prefResumo(); } catch (e) { return; }
  app.insertAdjacentHTML("beforeend", `
    <div class="selo prefeitura" style="margin-top:28px">🏢 PREFEITURA</div>
    <p>Os gastos da Prefeitura vêm dos <a href="${FONTE_PREF}" target="_blank" rel="noopener">arquivos oficiais de despesas</a> publicados no Portal da Transparência de Juiz de Fora, que a própria Prefeitura atualiza toda semana${R.fonte_atualizada_em ? ` (última atualização: ${esc(R.fonte_atualizada_em)})` : ""}. Cada linha é um empenho, com o órgão, o credor, os valores e a descrição.</p>
    <ul>
      <li>Os valores são somados exatamente como estão no arquivo, incluindo anulações e correções (que aparecem como valores negativos).</li>
      <li>Pagamentos a pessoas físicas aparecem somados, sem nome, CPF nem descrição.</li>
      <li>Nomes de órgãos e empresas aparecem como estão no arquivo oficial, só com letras maiúsculas e minúsculas e acentos ajustados para facilitar a leitura.</li>
      <li>O site não julga se um gasto é bom ou ruim: mostra o dado oficial para cada pessoa tirar suas conclusões.</li>
    </ul>`);
}
