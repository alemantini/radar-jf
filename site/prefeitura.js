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
const secNome = n => /^#?n\/?a$/i.test(String(n || "").trim()) ? "Unidade não informada pela Prefeitura" : String(n || "").replace(/\bMuncipal\b/g, "Municipal");
const numEmp = n => /^\d{4}[A-Z]{0,2}$/i.test(String(n || "").trim()) ? "" : String(n || "").trim();
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
    <div class="topo">${x[0] ? dataBR(x[0]) + " · " : ""}${numEmp(x[7]) ? `Empenho nº ${esc(numEmp(x[7]))} · ` : ""}${esc(secNome(d.secretarias[x[1]]))}</div>
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


// ---------- Impostômetro (Siconfi / Tesouro Nacional) ----------
let RECEITAS = null, _relogioImp = null;
async function prefReceitas() {
  if (!RECEITAS) RECEITAS = await fetch("dados/prefeitura/receitas.json").then(r => r.ok ? r.json() : null).catch(() => null);
  return RECEITAS;
}
const NOME_MES_LONGO = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
const mesLongo = am => `${NOME_MES_LONGO[+am.slice(5, 7) - 1]} de ${am.slice(0, 4)}`;
function impostosAno(R, conta, ano) {
  const c = R.contas[conta]; if (!c) return 0;
  return Object.entries(c.meses).filter(([m]) => m.startsWith(String(ano))).reduce((s, [, v]) => s + v, 0);
}
function impostometro(R, agora = new Date()) {
  const conta = "Impostos, Taxas e Contribuições de Melhoria";
  const c = R.contas[conta]; if (!c) return null;
  const ano = agora.getFullYear();
  const oficial = impostosAno(R, conta, ano);
  const porSeg = (c.total_12m || 0) / 365 / 86400;
  const [ua, um] = R.ultimo_mes.split("-").map(Number);
  // estimativa a partir do dia seguinte ao último mês informado (ou de 1º de janeiro, se for de outro ano)
  const inicio = ua === ano ? new Date(ua, um, 1) : new Date(ano, 0, 1);
  const seg = Math.max(0, (agora - inicio) / 1000);
  return {oficial: ua === ano ? oficial : 0, estimado: seg * porSeg, total: (ua === ano ? oficial : 0) + seg * porSeg, porSeg, ano};
}
function blocoImpostometro(R, grande = true) {
  const x = impostometro(R); if (!x) return "";
  return `<div class="placa prefeitura contador impostometro">
    <span class="tx"><span class="ds">Impostômetro de Juiz de Fora: impostos e taxas municipais pagos em ${x.ano}</span>
    <span class="tt num" id="imp-valor">${reais(x.total, false)}</span>
    <span class="ds">IPTU, ISS, ITBI e taxas da Prefeitura. Até ${mesLongo(R.ultimo_mes)}: valor oficial informado ao Tesouro Nacional. Depois disso: estimativa pela média dos últimos 12 meses, cerca de ${reais(x.porSeg * 86400)} por dia.</span></span></div>`;
}
function ligarRelogioImp(R) {
  clearInterval(_relogioImp);
  const el = document.getElementById("imp-valor"); if (!el) return;
  const passo = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 60000 : 1000;
  _relogioImp = setInterval(() => { if (!document.body.contains(el)) return clearInterval(_relogioImp); el.textContent = reais(impostometro(R).total, false); }, passo);
}

async function pgImpostometro() {
  const R = await prefReceitas();
  if (!R) { app.innerHTML = "<h1>Impostômetro</h1><p>Os dados de arrecadação ainda não foram coletados. Tente mais tarde.</p>"; return; }
  const ano = new Date().getFullYear();
  const C = R.contas, imp = C["Impostos, Taxas e Contribuições de Melhoria"], rc = C["RECEITAS CORRENTES (I)"];
  const partes = ["IPTU", "ISS", "ITBI", "Outros Impostos, Taxas e Contribuições de Melhoria"].filter(k => C[k]);
  const meses = Object.entries(imp.meses);
  const maxM = Math.max(...meses.map(([, v]) => v), 1);
  const pop = R.populacao;
  app.innerHTML = `
    <h1>Impostômetro de Juiz de Fora</h1>
    <p class="sub">Quanto os moradores e as empresas de Juiz de Fora pagam em impostos e taxas para a Prefeitura. Dados oficiais que a própria Prefeitura informa ao Tesouro Nacional a cada dois meses.</p>
    ${blocoImpostometro(R)}
    <h2>De onde vem: últimos 12 meses</h2>
    <p class="sub">Até ${mesLongo(R.ultimo_mes)}.</p>
    ${partes.map(k => `<div class="linha"><span class="nm">${esc(C[k].nome)}<div class="barra-p" style="width:${Math.round(100 * (C[k].total_12m || 0) / (imp.total_12m || 1))}%"></div></span><span class="vl">${reais(C[k].total_12m)}</span></div>`).join("")}
    <div class="linha"><span class="nm"><b>Total de impostos e taxas municipais</b></span><span class="vl">${reais(imp.total_12m)}</span></div>
    ${pop ? `<div class="nums verde"><span><b>${reais((imp.total_12m || 0) / pop)}</b>por morador, em 12 meses</span><span><b>${fmt(pop)}</b>moradores (estimativa usada pelo Tesouro)</span></div>` : ""}
    <h2>Mês a mês</h2>
    <div class="meses">${meses.map(([m, v]) => `<div title="${mesLongo(m)}: ${reais(v, false)}" style="height:${Math.round(100 * v / maxM)}%"></div>`).join("")}</div>
    <div class="meses-r">${meses.map(([m]) => `<span>${NOMES_MES[+m.slice(5, 7) - 1]}</span>`).join("")}</div>
    <p class="sub">IPTU costuma pesar no começo do ano, quando vence a cota única.</p>
    ${rc ? `<h2>E o resto do dinheiro?</h2>
    <p>Impostos e taxas municipais são só uma parte. Somando os repasses da União e do Estado (como FPM, ICMS, IPVA e verbas do SUS e da educação) e outras receitas, a Prefeitura recebeu <b>${reais(rc.total_12m)}</b> em receitas correntes nos últimos 12 meses. Os impostos e taxas municipais foram ${Math.round(100 * (imp.total_12m || 0) / (rc.total_12m || 1))}% disso.</p>
    ${["Cota-Parte do FPM", "Cota-Parte do ICMS", "Cota-Parte do IPVA"].filter(k => C[k]).map(k => `<div class="linha"><span class="nm">${esc(C[k].nome)}</span><span class="vl">${reais(C[k].total_12m)}</span></div>`).join("")}` : ""}
    <div class="info">Diferente do impostômetro de São Paulo, que soma todos os impostos do país (federais, estaduais e municipais), este mostra só o que é arrecadado pela Prefeitura de Juiz de Fora. O número que sobe em tempo real depois do último mês informado é uma estimativa; o valor oficial é atualizado quando a Prefeitura envia o próximo relatório ao Tesouro.</div>
    <p class="sub">Fonte: ${esc(R.fonte)}. <a href="${R.fonte_url}" target="_blank" rel="noopener">Ver os dados oficiais</a> · coletado em ${esc(R.coletado_em)}.</p>
    <a class="btn-grande prefeitura" href="#/prefeitura">${ic("predios")}<span class="tx">Para onde vai esse dinheiro<small>Gastos por secretaria</small></span>›</a>`;
  ligarRelogioImp(R);
}

async function pgPrefInicio(ano) {
  const R = await prefResumo();
  ano = ano || anosDisp(R)[0];
  const A = R.anos[ano], t = A.total;
  const max = Math.max(...A.secretarias.map(s => s.p), 1);
  const REC = await prefReceitas();
  app.innerHTML = `
    <a class="btn-grande prefeitura" href="#/prefeitura/lupa">${ic("lupa")}<span class="tx">Gastos na lupa<small>Carros e combustível, viagens, publicidade, shows e a corrida de dezembro</small></span>›</a>
    <a class="btn-alerta" href="#/prefeitura/alertas">${ic("alerta")}<span class="tx"><b>Sinais de alerta nos gastos</b><small>Compras fatiadas, empresas punidas, sócios que doaram para campanhas e mais.</small></span><span class="seta">›</span></a>
    ${REC ? blocoImpostometro(REC) + `<a class="btn-grande prefeitura" href="#/prefeitura/impostometro">${ic("dinheiro")}<span class="tx">Ver o impostômetro completo<small>IPTU, ISS, ITBI, por morador e mês a mês</small></span>›</a>` : ""}
    <h1>Para onde vai o dinheiro da Prefeitura</h1>
    <p class="sub">Quanto cada secretaria e órgão da Prefeitura de Juiz de Fora gastou, segundo os arquivos oficiais de despesas. ${fonteLink("Ver fonte oficial")}${R.fonte_atualizada_em ? ` (atualizada pela Prefeitura em ${esc(R.fonte_atualizada_em)})` : ""}.</p>
    ${seletorAnos(R, ano, "#/prefeitura/ano/")}
    <div class="totais">
      <div><span>Empenhado</span><b>${reais(t.e)}</b></div>
      <div><span>Liquidado</span><b>${reais(t.l)}</b></div>
      <div><span>Pago</span><b class="p-verde">${reais(t.p)}</b></div>
    </div>
    <a class="btn-grande prefeitura" href="#/prefeitura/fornecedores/${ano}">${ic("maleta")}<span class="tx">Quem recebe da Prefeitura<small>Empresas e entidades que mais receberam</small></span>›</a>
    <a class="btn-grande prefeitura" href="#/prefeitura/busca/${ano}">${ic("lupa")}<span class="tx">Pesquisar um gasto<small>Asfalto, merenda, combustível, nome da empresa</small></span>›</a>
    ${explicacao}
    <h2>Quanto cada órgão pagou em ${ano}</h2>
    <p class="sub">${A.secretarias.length} unidades, da que mais pagou para a que menos pagou. Toque para ver em quê e com quem.</p>
    ${A.secretarias.map((s, i) => `<a class="linha" href="#/prefeitura/s/${ano}/${i}"><span class="nm">${esc(secNome(s.nome))}<div class="barra-p" style="width:${Math.max(1, Math.round(100 * s.p / max))}%"></div></span><span class="vl">${reais(s.p)} ›</span></a>`).join("")}
    <h2>Pagamentos a pessoas físicas</h2>
    <p>${reais(A.pessoa_fisica.p)} pagos em ${fmt(A.pessoa_fisica.n)} lançamentos a pessoas físicas. A maior parte é folha de pagamento: salários de servidores, aposentadorias, pensões e contratos temporários. <b>Nomes e CPFs não são exibidos neste site.</b></p>
    ${(A.pessoa_fisica.elementos || []).map(e => `<div class="linha"><span class="nm">${esc(e.nome)}</span><span class="vl">${reais(e.p)}</span></div>`).join("")}`;
  if (REC) ligarRelogioImp(REC);
}

async function pgPrefSecretaria(ano, i) {
  const R = await prefResumo();
  const s = R.anos[ano].secretarias[i];
  if (!s) { app.innerHTML = "<p>Não encontrado.</p>"; return; }
  const maxM = Math.max(...s.meses.map(v => Math.max(v, 0)), 1);
  const maxE = Math.max(...s.elementos.map(e => e.p), 1);
  app.innerHTML = `
    <h1>${esc(secNome(s.nome))}</h1>
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
    <h2>Empresas e entidades que mais receberam</h2>
    ${s.fornecedores.length ? s.fornecedores.map(f => `<a class="linha" href="#/prefeitura/empresa/${ano}/${f.cnpj}"><span class="nm">${esc(f.nome)}<br><small class="sub">CNPJ ${cnpjFmt(f.cnpj)} · ${fmt(f.n)} lançamentos</small></span><span class="vl">${reais(f.p)} ›</span></a>`).join("") : '<p class="sub">Nenhuma empresa ou entidade nesta unidade.</p>'}
    <p class="sub" style="margin-top:14px"><a href="#/prefeitura/busca/${ano}/${encodeURIComponent(s.nome)}">Ver todos os lançamentos desta unidade ›</a></p>`;
}

async function pgPrefFornecedores(ano) {
  const R = await prefResumo();
  ano = ano || anosDisp(R)[0];
  const A = R.anos[ano];
  app.innerHTML = `
    <h1>Quem recebe da Prefeitura</h1>
    <p class="sub">As 200 empresas e entidades (com CNPJ) que mais receberam em ${ano}, de um total de ${fmt(A.n_fornecedores)}. Inclui hospitais, associações, fundações e órgãos públicos. ${fonteLink()}</p>
    ${seletorAnos(R, ano, "#/prefeitura/fornecedores/")}
    <input type="search" id="q" placeholder="Filtrar por nome ou CNPJ" autocomplete="off" style="margin-top:10px">
    <div id="res"></div>
    <p class="sub">Para quem está fora desta lista, use a <a href="#/prefeitura/busca/${ano}">busca de gastos</a>.</p>`;
  const inp = document.getElementById("q");
  const mostra = () => {
    const q = norm(inp.value.trim()), qd = inp.value.replace(/\D/g, "");
    const it = A.fornecedores.filter(f => !q || norm(f.nome).includes(q) || (qd.length >= 4 && f.cnpj.includes(qd)));
    document.getElementById("res").innerHTML = it.map((f, k) => `<a class="linha" href="#/prefeitura/empresa/${ano}/${f.cnpj}"><span class="nm">${esc(f.nome)}<br><small class="sub">CNPJ ${cnpjFmt(f.cnpj)} · ${esc(f.secretarias.slice(0, 2).map(secNome).join(", "))}</small></span><span class="vl">${reais(f.p)} ›</span></a>`).join("") || '<p class="sub">Ninguém encontrado nesta lista.</p>';
  };
  let tm; inp.oninput = () => { clearTimeout(tm); tm = setTimeout(mostra, 200); };
  mostra();
}

async function pgPrefEmpresa(ano, cnpj) {
  const d = await prefEmpenhos(ano);
  const ic = d.credores.findIndex(c => c[0] === cnpj);
  if (ic < 0) { app.innerHTML = "<p>Não encontrado neste ano.</p>"; return; }
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


// ---------- Emendas dos vereadores (Monitor de Emendas da Prefeitura) ----------
let EMENDAS = null;
const ETAPA_COR = {"Executada": "#0f6b4b", "Pagamento": "#3d8b5f", "Em execução": "#12407a", "Em análise": "#7a828e", "Inapta": "#b42318", "Não informado": "#c9ced6"};
const ETAPA_DESC = {
  "Executada": "obra, compra ou repasse concluído",
  "Pagamento": "em liquidação ou pagamento",
  "Em execução": "em licitação, contratação ou execução",
  "Em análise": "em análise técnica ou plano de trabalho",
  "Inapta": "considerada inviável pela análise técnica",
  "Não informado": "sem etapa informada",
};
function barraEtapas(et, total) {
  return `<div class="etapas">${Object.keys(ETAPA_COR).filter(k => et[k]).map(k => `<i style="width:${100 * et[k] / total}%;background:${ETAPA_COR[k]}" title="${k}: ${et[k]}"></i>`).join("")}</div>`;
}
function legendaEtapas(et) {
  return `<div class="leg-etapas">${Object.keys(ETAPA_COR).filter(k => et[k]).map(k => `<span><i style="background:${ETAPA_COR[k]}"></i>${k} (${fmt(et[k])}): ${ETAPA_DESC[k]}</span>`).join("")}</div>`;
}
function vereadorDoProponente(p) {
  const n = norm(p);
  return RESUMO.vereadores.find(v => norm(v.nome) === n) || RESUMO.vereadores.find(v => norm(v.nome).includes(n) || n.includes(norm(v.nome)));
}
async function pgEmendas(prop) {
  const R = EMENDAS_R;
  if (!R) { app.innerHTML = "<h1>Emendas dos vereadores</h1><p>Os dados de emendas ainda não foram coletados. Tente mais tarde.</p>"; return; }
  if (prop) return pgEmendasDe(prop);
  const lista = Object.entries(R.proponentes).map(([p, x]) => ({p, ...x, v: vereadorDoProponente(p)}))
    .sort((a, b) => norm(a.v ? a.v.apelido : a.p).localeCompare(norm(b.v ? b.v.apelido : b.p)));
  const T = R.total;
  app.innerHTML = `
    <h1>Emendas dos vereadores</h1>
    <p class="sub">Todo ano, cada vereador indica para onde vai uma parte do orçamento da Prefeitura: uma obra, um serviço ou uma entidade do bairro. São as emendas impositivas: a Prefeitura é obrigada a executar, salvo se a análise técnica considerar inviável. Aqui está o que foi indicado desde ${R.desde} e em que etapa cada emenda está.</p>
    <div class="nums verde"><span><b>${reaisCurto(T.previsto)}</b>indicados em ${fmt(T.n)} emendas</span><span><b>${reaisCurto(T.pago)}</b>já pagos (${Math.round(100 * T.pago / (T.previsto || 1))}%)</span></div>
    <h2>Em que etapa estão</h2>
    ${barraEtapas(R.etapas, T.n)}${legendaEtapas(R.etapas)}
    <h2>Por vereador</h2>
    <p class="sub">Em ordem alfabética. Toque para ver cada emenda.</p>
    ${lista.map(x => `<a class="linha" href="#/prefeitura/emendas/${encodeURIComponent(x.p)}"><span class="nm"><b>${esc(x.v ? x.v.apelido : x.p)}</b>${x.v && x.v.partido ? `, ${esc(x.v.partido)}` : (x.v ? "" : " <small class='sub'>(não está na lista atual de vereadores)</small>")}
      ${barraEtapas(x.etapas, x.n)}<small class="sub">${fmt(x.n)} emendas · ${reaisCurto(x.pago)} pagos de ${reaisCurto(x.previsto)}</small></span><span class="vl">${reaisCurto(x.previsto)} ›</span></a>`).join("")}
    <p class="sub" style="margin-top:12px">Fonte: <a href="${R.fonte_url}" target="_blank" rel="noopener">${esc(R.fonte)}</a>${R.atualizado_fonte ? `, atualizado pela Prefeitura em ${esc(R.atualizado_fonte)}` : ""}. Os valores e etapas são os do painel oficial.</p>`;
}
async function pgEmendasDe(prop) {
  const R = EMENDAS_R, x = R.proponentes[prop];
  if (!x) { app.innerHTML = "<p>Não encontrado.</p>"; return; }
  if (!EMENDAS) { app.innerHTML = '<p class="carregando">Carregando as emendas…</p>'; EMENDAS = await fetch("dados/prefeitura/emendas.json").then(r => r.json()); }
  const v = vereadorDoProponente(prop);
  const itens = EMENDAS.filter(e => e.p === prop).sort((a, b) => b.ano - a.ano || b.prev - a.prev);
  app.innerHTML = `
    <h1>Emendas de ${esc(v ? v.apelido : prop)}</h1>
    <p class="sub">${esc(prop)}${v && v.partido ? ", " + esc(v.partido) : ""}. Desde ${R.desde}.</p>
    <div class="nums verde"><span><b>${reaisCurto(x.previsto)}</b>indicados em ${fmt(x.n)} emendas</span><span><b>${reaisCurto(x.pago)}</b>já pagos (${Math.round(100 * x.pago / (x.previsto || 1))}%)</span></div>
    ${barraEtapas(x.etapas, x.n)}${legendaEtapas(x.etapas)}
    ${v ? `<a class="btn-grande camara" href="#/v/${v.id}">${ic("camara")}<span class="tx">Ver o que ${esc(v.apelido)} propôs na Câmara</span>›</a>` : ""}
    <input type="search" id="q" placeholder="Filtrar por bairro, entidade, objeto ou etapa" autocomplete="off">
    <div id="lista"></div>`;
  const alvo = document.getElementById("lista"), inp = document.getElementById("q");
  const card = e => `<div class="item">
      <div class="topo"><span class="tag" style="background:${ETAPA_COR[e.et] || "#7a828e"}">${esc(e.et)}</span>${e.ano} · Emenda ${esc(e.id)} · ${esc(e.sit)}</div>
      <div class="txt">${esc(e.obj) || "Objeto não informado"}</div>
      <div class="pe">${e.benef ? "Para: " + esc(e.benef) + " · " : ""}${e.local ? esc(e.local) + " · " : ""}indicado ${reais(e.prev, false)} · pago ${reais(e.pago, false)}</div>
      ${/^execut/i.test(e.sit) && !e.pago ? '<div class="pe sub">A planilha oficial marca como executada, mas não registra empenho nem pagamento. A informação está incompleta na fonte.</div>' : ""}
    </div>`;
  const mostra = () => { const q = norm(inp.value.trim()); const it = q ? itens.filter(e => norm(`${e.obj} ${e.benef} ${e.local} ${e.ug} ${e.sit} ${e.et} ${e.funcao}`).includes(q)) : itens; alvo.innerHTML = it.map(card).join("") || '<p class="sub">Nada encontrado.</p>'; };
  let tm; inp.oninput = () => { clearTimeout(tm); tm = setTimeout(mostra, 250); };
  mostra();
}


// ---------- Diário Oficial pesquisável ----------
const DIARIO = {resumo: null, anos: {}};
const ATALHOS = [
  ["Dispensas de licitação", {tipo: "Contratação Direta"}],
  ["Nomeações", {tipo: "Ato de Nomeação"}],
  ["Exonerações", {tipo: "Ato de Exoneração"}],
  ["Contratos", {tipo: "Extrato de Contrato"}],
  ["Decretos", {tipo: "Decreto"}],
  ["Leis", {tipo: "Lei"}],
];
async function pgDiario(ano0, q0) {
  if (!DIARIO.resumo) DIARIO.resumo = await fetch("dados/prefeitura/atos_resumo.json").then(r => r.ok ? r.json() : null).catch(() => null);
  const R = DIARIO.resumo;
  if (!R) { app.innerHTML = "<h1>Diário Oficial</h1><p>Os atos ainda estão sendo coletados. Volte mais tarde.</p>"; return; }
  const ano = ano0 && R.anos.includes(ano0) ? ano0 : R.anos[R.anos.length - 1];
  if (!DIARIO.anos[ano]) { app.innerHTML = '<p class="carregando">Carregando os atos do ano…</p>'; DIARIO.anos[ano] = await fetch(`dados/prefeitura/atos_${ano}.json`).then(r => r.json()); DIARIO.anos[ano].atos.forEach(a => a._b = norm(a[4] + " " + DIARIO.anos[ano].orgaos[a[3]])); }
  const D = DIARIO.anos[ano];
  const grupos = Object.keys(R.grupos);
  const orgaos = R.orgaos.map(o => o[0]);
  app.innerHTML = `
    <h1>Diário Oficial da Prefeitura</h1>
    <p class="sub">Tudo o que a Prefeitura publicou no Diário Oficial desde janeiro de 2025: ${fmt(R.total)} atos, até ${dataBR(R.ate)}. Pesquise por empresa, bairro, obra, nome de cargo ou número de processo.</p>
    ${seletorAnosLista(R.anos, ano)}
    <input type="search" id="q" placeholder="Ex.: dispensa, asfalto, nome da empresa, Saúde" value="${esc(q0 || "")}" autocomplete="off">
    <div class="chips" id="atalhos">${ATALHOS.map(([t], i) => `<a href="#" data-i="${i}">${t}</a>`).join("")}</div>
    <div class="filtros-linha">
      <label>Tipo<select id="fg"><option value="">Todos os tipos</option>${grupos.map(g => `<option>${esc(g)}</option>`).join("")}</select></label>
      <label>Órgão<select id="fo"><option value="">Todos os órgãos</option>${orgaos.map(o => `<option>${esc(o)}</option>`).join("")}</select></label>
      <label>Mês<select id="fm"><option value="">Ano inteiro</option>${NOME_MES_LONGO.map((m, i) => `<option value="${String(i + 1).padStart(2, "0")}">${m}</option>`).join("")}</select></label>
    </div>
    <div id="res"></div>
    <p class="sub">Fonte: <a href="${R.fonte_url}" target="_blank" rel="noopener">${esc(R.fonte)}</a>. O órgão é identificado pelo texto do ato e pode faltar em alguns. Atos sobre situações pessoais de servidores e contribuintes (aposentadoria, pensão, processos disciplinares, decisões fiscais) aparecem sem o texto; o link leva ao ato oficial.</p>`;
  const $ = id => document.getElementById(id);
  let tipoFixo = "";
  const semTexto = new Set(R.tipos_sem_texto);
  const card = a => {
    const tipo = D.tipos[a[2]], org = D.orgaos[a[3]];
    return `<div class="item"><div class="topo"><span class="tag g-leis">${esc(tipo)}</span>${dataBR(a[1])}${org ? " · " + esc(org) : ""}</div>
      <div class="txt">${a[4] ? esc(a[4]) : '<span class="sub">Texto não exibido neste site (situação pessoal).</span>'}</div>
      <div class="pe"><a href="${R.link_ato}${a[0]}" target="_blank" rel="noopener">Ver o ato oficial</a></div></div>`;
  };
  const busca = () => {
    const q = norm($("q").value.trim()), g = $("fg").value, o = $("fo").value, m = $("fm").value;
    history.replaceState(null, "", `#/prefeitura/diario/${ano}/${encodeURIComponent($("q").value.trim())}`);
    const termos = q ? q.split(/\s+/) : [];
    const it = D.atos.filter(a => (!tipoFixo || D.tipos[a[2]] === tipoFixo) && (!g || R.tipo_grupo[D.tipos[a[2]]] === g) && (!o || D.orgaos[a[3]] === o)
      && (!m || a[1].slice(5, 7) === m) && termos.every(t => a._b.includes(t)));
    const res = $("res");
    res.innerHTML = `<h2>${fmt(it.length)} atos${tipoFixo ? ": " + esc(tipoFixo) : ""}</h2>${tipoFixo ? '<p><a href="#" id="limpa">Mostrar todos os tipos</a></p>' : ""}`;
    if ($("limpa")) $("limpa").onclick = e => { e.preventDefault(); tipoFixo = ""; busca(); };
    let n = 0; const box = document.createElement("div"), btn = document.createElement("button"); btn.className = "mais";
    const mais = () => { box.insertAdjacentHTML("beforeend", it.slice(n, n + 40).map(card).join("")); n += 40; btn.style.display = n < it.length ? "block" : "none"; btn.textContent = `Mostrar mais (${fmt(it.length - n)} restantes)`; };
    btn.onclick = mais; res.append(box, btn); mais();
  };
  $("atalhos").querySelectorAll("a").forEach(a => a.onclick = e => { e.preventDefault(); tipoFixo = ATALHOS[+a.dataset.i][1].tipo; $("fg").value = ""; busca(); });
  let tm; $("q").oninput = () => { clearTimeout(tm); tm = setTimeout(busca, 300); };
  ["fg", "fo", "fm"].forEach(id => $(id).onchange = busca);
  busca();
}
function seletorAnosLista(anos, ano) {
  return `<div class="anos">${[...anos].reverse().map(a => `<button class="${a == ano ? "on" : ""}" onclick="location.hash='#/prefeitura/diario/${a}'">${a}</button>`).join("")}</div>`;
}

async function rotaPrefeitura(p) {
  const [sub, a, b] = p;
  if (sub === "ano") return pgPrefInicio(a);
  if (sub === "impostometro") return pgImpostometro();
  if (sub === "placar") return pgPlacarFiscal(a);
  if (sub === "alertas") return pgAlertas(a);
  if (sub === "comissionados") return pgComissionados(a);
  if (sub === "lupa") return pgLupa(a, b);
  if (sub === "emendas") return pgEmendas(a);
  if (sub === "diario") return pgDiario(a, b);
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
    <div class="placa prefeitura" style="margin-top:28px">${ic("dinheiro")}<span class="tx"><span class="tt">Prefeitura</span></span></div>
    <p>Os gastos da Prefeitura vêm dos <a href="${FONTE_PREF}" target="_blank" rel="noopener">arquivos oficiais de despesas</a> publicados no Portal da Transparência de Juiz de Fora, que a própria Prefeitura atualiza toda semana${R.fonte_atualizada_em ? ` (última atualização: ${esc(R.fonte_atualizada_em)})` : ""}. Cada linha é um empenho, com o órgão, o credor, os valores e a descrição.</p>
    <ul>
      <li>Os valores são somados exatamente como estão no arquivo, incluindo anulações e correções (que aparecem como valores negativos).</li>
      <li>Pagamentos a pessoas físicas aparecem somados, sem nome, CPF nem descrição.</li>
      <li>Nomes de órgãos e empresas aparecem como estão no arquivo oficial, só com letras maiúsculas e minúsculas e acentos ajustados para facilitar a leitura.</li>
      <li>O site não julga se um gasto é bom ou ruim: mostra o dado oficial para cada pessoa tirar suas conclusões.</li>
    </ul>`);
}


// ---------- Placar fiscal: Lei de Responsabilidade Fiscal, mínimos e comparação com outras cidades ----------
let INDICES = null;
const pct = x => (x ?? 0).toLocaleString("pt-BR", {maximumFractionDigits: 1}) + "%";
const MEDIDAS = [
  ["Saúde", "Saúde", "f"], ["Educação", "Educação", "f"], ["Assistência Social", "Assistência social", "f"],
  ["Urbanismo", "Urbanismo (ruas, praças, obras)", "f"], ["Transporte", "Transporte", "f"], ["Segurança Pública", "Segurança pública", "f"],
  ["Saneamento", "Saneamento", "f"], ["Cultura", "Cultura", "f"], ["Desporto e Lazer", "Esporte e lazer", "f"],
  ["Legislativa", "Câmara Municipal", "f"], ["Administração", "Administração (máquina pública)", "f"],
  ["iptu", "IPTU arrecadado", "r"], ["iss", "ISS arrecadado", "r"], ["impostos", "Impostos e taxas municipais", "r"], ["rcl", "Receita corrente líquida", "r"],
];
async function pgPlacarFiscal(medida0) {
  if (!INDICES) INDICES = await fetch("dados/prefeitura/indices.json").then(r => r.ok ? r.json() : null).catch(() => null);
  const I = INDICES;
  if (!I) { app.innerHTML = "<h1>Placar fiscal</h1><p>Os dados ainda estão sendo coletados. Volte mais tarde.</p>"; return; }
  const P = I.pessoal, M = I.minimos;
  const medida = MEDIDAS.find(m => m[0] === medida0) || MEDIDAS[0];
  let estado = "", cor = "verde";
  if (P) {
    if (P.pct >= P.limite) { estado = "Acima do limite da lei"; cor = "vermelho"; }
    else if (P.pct >= P.prudencial) { estado = "Acima do limite prudencial"; cor = "vermelho"; }
    else if (P.pct >= P.alerta) { estado = "Em alerta"; cor = "amarelo"; }
    else estado = "Dentro do limite";
  }
  const escala = 60;
  const minimo = (t, x, nota) => x && x.aplicado != null ? `
    <div class="min-linha"><div class="ml-t"><b>${t}</b><small>${nota}</small></div>
      <div class="ml-b"><i class="${x.aplicado >= x.minimo ? "ok" : "falta"}" style="width:${Math.min(100, x.aplicado)}%"></i><em style="left:${x.minimo}%" title="mínimo"></em></div>
      <div class="ml-v"><b>${pct(x.aplicado)}</b><small>mínimo ${pct(x.minimo)}</small></div></div>` : "";
  const cid = (I.cidades || []).map(c => {
    const v = medida[2] === "f" ? (c.funcoes || {})[medida[0]] : c[medida[0]];
    return {...c, pc: v != null && c.pop ? v / c.pop : null};
  }).filter(c => c.pc != null).sort((a, b) => b.pc - a.pc);
  const maxpc = Math.max(...cid.map(c => c.pc), 1);
  const posJF = cid.findIndex(c => c.cod === 3136702) + 1;
  app.innerHTML = `
    <h1>Placar fiscal da Prefeitura</h1>
    <p class="sub">As contas que a própria Prefeitura entrega ao Tesouro Nacional, comparadas com o que a lei exige e com outras cidades grandes de Minas.</p>
    ${P ? `<h2>Gasto com pessoal</h2>
      <p class="sub">A Lei de Responsabilidade Fiscal limita o gasto com servidores da Prefeitura a 54% da receita corrente líquida. Situação em ${P.quadrimestre}º quadrimestre de ${P.ano}:</p>
      <div class="lrf ${cor}"><div class="lrf-n"><b>${pct(P.pct)}</b><span>${estado}</span></div>
        <div class="lrf-b"><i style="width:${100 * P.pct / escala}%"></i>
          <em style="left:${100 * P.alerta / escala}%"></em><em style="left:${100 * P.prudencial / escala}%"></em><em class="lim" style="left:${100 * P.limite / escala}%"></em></div>
        <p class="lrf-leg">Traços: alerta ${pct(P.alerta)}, prudencial ${pct(P.prudencial)} e <b>limite da lei ${pct(P.limite)}</b>.</p>
        <p class="sub">${reais(P.despesa)} com pessoal nos últimos 12 meses, de uma receita corrente líquida de ${reais(P.rcl)}.</p></div>` : ""}
    ${I.balanco && I.balanco.relacao_12m ? (() => { const B = I.balanco, r = B.relacao_12m, ano_r = 100 * B.dc_liquidado / B.rc_realizado, pctAno = 100 * B.receita_realizada / B.receita_prevista_ano, pctTempo = 100 * B.bimestre / 6;
      const c = r > 95 ? "vermelho" : r > 85 ? "amarelo" : "verde";
      return `<h2>Gasta mais do que arrecada?</h2>
      <p class="sub">A Constituição (art. 167-A) compara as despesas correntes (salários, custeio, contas do dia a dia) com as receitas correntes. Quando passa de 95% em 12 meses, a prefeitura fica perto de gastar tudo o que entra e pode adotar medidas de ajuste, como suspender reajustes e concursos.</p>
      <div class="lrf ${c}"><div class="lrf-n"><b>${pct(r)}</b><span>${r > 95 ? "Acima de 95%" : r > 85 ? "Perto do limite de 95%" : "Folga confortável"}</span></div>
        <div class="lrf-b"><i style="width:${Math.min(100, r)}%"></i><em class="lim" style="left:95%"></em></div>
        <p class="lrf-leg">Traço vermelho: 95%. Últimos 12 meses até o ${B.bimestre}º bimestre de ${B.ano}: despesas correntes de ${reais(B.dc_12m)} para receitas correntes de ${reais(B.rc_12m)}.</p>
        <p class="sub">Só em ${B.ano}, até o ${B.bimestre}º bimestre, a relação está em <b>${pct(ano_r)}</b>: ${reais(B.dc_liquidado)} em despesas correntes para ${reais(B.rc_realizado)} em receitas correntes.</p></div>
      <div class="min-linha"><div class="ml-t"><b>Arrecadação do ano</b><small>Arrecadado até o ${B.bimestre}º bimestre, de ${reais(B.receita_prevista_ano)} previstos no orçamento de ${B.ano}</small></div>
        <div class="ml-b"><i class="${pctAno >= pctTempo - 3 ? "ok" : "falta"}" style="width:${Math.min(100, pctAno)}%"></i><em style="left:${pctTempo}%" title="parte do ano que já passou"></em></div>
        <div class="ml-v"><b>${pct(pctAno)}</b><small>${pct(pctTempo)} do ano já passou</small></div></div>`; })() : ""}
    ${M ? `<h2>Mínimos da Constituição</h2>
      <p class="sub">Percentual aplicado até o ${M.bimestre}º bimestre de ${M.ano}. A marca escura é o mínimo exigido; o ano só fecha em dezembro.</p>
      ${minimo("Educação", M.educacao, "Parte da receita de impostos aplicada no ensino")}
      ${minimo("Saúde", M.saude, "Parte da receita de impostos aplicada na saúde")}
      ${minimo("Fundeb", M.fundeb, "Parte do Fundeb usada para pagar os profissionais da educação")}` : ""}
    ${cid.length ? `<h2>Juiz de Fora e outras cidades mineiras</h2>
      <p class="sub">Valor por habitante em ${I.ano_comparacao}, nas ${cid.length} maiores cidades de Minas que entregaram os dados. Escolha o que comparar:</p>
      <div class="filtros-linha"><select id="medida" aria-label="O que comparar">${MEDIDAS.map(m => `<option value="${m[0]}" ${m === medida ? "selected" : ""}>${m[2] === "f" ? "Gasto: " : "Receita: "}${m[1]}</option>`).join("")}</select></div>
      ${posJF ? `<p class="destaque-cidade">Juiz de Fora fica em <b>${posJF}º lugar</b> de ${cid.length} em ${medida[1].toLowerCase()} por habitante.</p>` : ""}
      ${cid.map((c, i) => `<div class="barra-l ${c.cod === 3136702 ? "jf" : ""}"><span class="bl-t">${i + 1}º ${esc(c.nome)}</span><span class="bl-b"><i style="width:${Math.round(100 * c.pc / maxpc)}%"></i></span><span class="bl-v">R$ ${Math.round(c.pc).toLocaleString("pt-BR")}</span></div>`).join("")}
      <p class="sub" style="margin-top:8px">Gasto = despesa liquidada no ano pela função de governo. Gastar mais não quer dizer gastar melhor; a comparação serve para fazer perguntas.</p>` : ""}
    <p class="sub fonte-linha">Fonte: <a href="${esc(I.fonte_url)}" target="_blank" rel="noopener">Siconfi, Tesouro Nacional</a> (Relatório de Gestão Fiscal e Relatório Resumido da Execução Orçamentária enviados por cada prefeitura). Coletado em ${esc(I.coletado_em)}.</p>`;
  const sel = document.getElementById("medida");
  if (sel) sel.onchange = () => { location.hash = "#/prefeitura/placar/" + encodeURIComponent(sel.value); };
}


// ---------- Sinais de alerta ----------
let ALERTAS = null;
async function pgAlertas(tipo) {
  if (!ALERTAS) ALERTAS = await fetch("dados/prefeitura/alertas.json").then(r => r.ok ? r.json() : null).catch(() => null);
  const A = ALERTAS;
  if (!A) { app.innerHTML = "<h1>Sinais de alerta</h1><p>A análise ainda está sendo feita. Volte mais tarde.</p>"; return; }
  const lista = A.alertas.filter(a => !tipo || a.tipo === tipo);
  const anoEmp = Math.max(...A.anos);
  app.innerHTML = `
    <h1>Sinais de alerta nos gastos</h1>
    <p class="sub">O Radar cruza dados públicos (empenhos da Prefeitura, cadastro de empresas da Receita, doações de campanha do TSE, cadastros de punidos da CGU, lista de comissionados e contratos publicados no Portal Nacional de Contratações Públicas) e aponta situações que merecem uma pergunta.</p>
    <div class="aviso-forte"><b>Sinal não é prova.</b> Cada item abaixo pode ter explicação legal: emergência real, fornecedor único, contrato antigo, hospital conveniado. Ninguém aqui está sendo acusado de nada. Use os sinais para perguntar à Prefeitura, à Câmara ou ao Tribunal de Contas, sempre conferindo nos documentos oficiais.</div>
    <div class="chips-filtro">
      <a href="#/prefeitura/alertas" class="${!tipo ? "on" : ""}">Todos <b>${fmt(A.alertas.length)}</b></a>
      ${Object.entries(A.tipos).filter(([k]) => A.contagem[k]).map(([k, t]) => `<a href="#/prefeitura/alertas/${k}" class="${tipo === k ? "on" : ""}">${t} <b>${fmt(A.contagem[k])}</b></a>`).join("")}
    </div>
    ${lista.map(a => `
      <div class="alerta-card">
        <div class="ac-topo"><span class="ac-tipo">${esc(A.tipos[a.tipo] || a.tipo)}</span><span class="ac-valor">${reais(a.valor)}</span></div>
        <a class="ac-nome" href="#/prefeitura/empresa/${anoEmp}/${a.cnpj}">${esc(a.nome || "Empresa")}</a>
        <small class="sub">CNPJ ${cnpjFmt(a.cnpj)}${a.secretaria ? ` · ${esc(secNome(a.secretaria))}` : ""}</small>
        <p>${esc(a.detalhe)}</p>
        ${a.refs.length ? `<small class="sub">Empenhos: ${a.refs.map(esc).join(", ")}</small>` : ""}
        ${a.link ? `<small class="sub"><a href="${esc(a.link)}" target="_blank" rel="noopener">Ver no Portal Nacional de Contratações Públicas</a></small>` : ""}
      </div>`).join("") || '<p class="sub">Nenhum sinal deste tipo.</p>'}
    <h2>Como cada sinal é calculado</h2>
    <ul class="metodo">
      <li><b>Possível fracionamento:</b> só para empresas (associações e órgãos públicos recebem repasses parcelados). 4 ou mais empenhos de compras, serviços, equipamentos ou obras no mesmo ano, para o mesmo fornecedor, na mesma secretaria e no mesmo tipo de despesa, cada um abaixo do limite de dispensa (em 2026, R$ 65.492,11 para compras e R$ 130.984,20 para obras), que somados passam de uma vez e meia o limite, sem citar licitação, ata ou contrato no histórico.</li>
      <li><b>Muita contratação sem licitação:</b> pelo menos 3 empenhos que citam dispensa, inexigibilidade ou emergência, somando R$ 500 mil ou mais.</li>
      <li><b>Emergência que se repete:</b> empenhos citando emergência em 4 meses diferentes ou mais.</li>
      <li><b>Fornecedor concentra pagamentos:</b> uma empresa ou entidade privada recebe 40% ou mais do que a secretaria pagou a empresas e entidades no ano (secretarias com mais de R$ 2 milhões; órgãos públicos como a JFPrev ficam de fora).</li>
      <li><b>Empresa recém-aberta:</b> matriz aberta menos de um ano antes do primeiro empenho, com R$ 100 mil ou mais. Consórcios formados para uma obra e órgãos públicos ficam de fora.</li>
      <li><b>Cadastro irregular:</b> CNPJ que não está "ativo" na Receita Federal.</li>
      <li><b>Capital social pequeno:</b> empresa com capital menor que 2% do que recebeu (acima de R$ 1 milhão).</li>
      <li><b>Sócio doador de campanha:</b> só para empresas (em associações e órgãos públicos, o cadastro lista dirigentes, não sócios). Sócio da empresa com o mesmo nome e os mesmos 6 dígitos do meio do CPF de um doador da eleição de 2024 em Juiz de Fora. O site não mostra o nome do sócio.</li>
      <li><b>Empresa inidônea ou proibida:</b> CNPJ no CEIS ou no CNEP (cadastros de punidos da Controladoria-Geral da União) com sanção que vale para toda a administração pública (inidoneidade ou proibição de contratar com o poder público), vigente enquanto recebia da Prefeitura.</li>
      <li><b>Punida por outro órgão:</b> sanções de impedimento ou suspensão aplicadas por outro órgão, vigentes no período. Em regra elas valem só para quem as aplicou, então não impedem o contrato com a Prefeitura; o sinal mostra histórico de problemas.</li>
      <li><b>Comissionado com nome de sócio:</b> o nome completo (três palavras ou mais) de um cargo comissionado da Prefeitura é igual ao de um sócio ou dirigente de empresa ou entidade que recebe da Prefeitura, segundo a Receita Federal. A lista de comissionados não traz CPF, então pode ser outra pessoa com o mesmo nome. Servidor pode ser sócio de empresa, mas não pode contratar com o próprio órgão nem participar da escolha dela.</li>
      <li><b>Atividade não combina com o pagamento:</b> R$ 100 mil ou mais em empenhos de um tipo de serviço (mão de obra, obras, medicamentos, combustível, alimentos, transporte, informática ou cuidado de animais) para empresa ou entidade cuja atividade principal e secundárias na Receita não são desse ramo.</li>
      <li><b>Contrato cresceu muito:</b> contrato publicado pela Prefeitura no Portal Nacional de Contratações Públicas cujo valor global passou 25% do valor inicial (e pelo menos R$ 100 mil a mais). A lei limita acréscimos a 25% (50% em reforma), mas prorrogar serviço contínuo é permitido: confira os termos aditivos.</li>
      <li><b>Licitação acima do orçado:</b> pregão ou concorrência de R$ 500 mil ou mais homologado por valor maior que o estimado pela própria Prefeitura.</li>
      <li><b>Licitação sem desconto:</b> pregão ou concorrência de R$ 1 milhão ou mais homologado com desconto menor que 1% sobre o orçado, o que costuma indicar pouca disputa. Aparece a empresa que mais ganhou itens da licitação.</li>
      <li><b>Sócio em comum com outro fornecedor:</b> duas empresas diferentes (não filiais) com pelo menos um sócio igual no cadastro da Receita (mesmo nome e mesmos dígitos do CPF), do mesmo ramo segundo a Receita, as duas pagas pela mesma secretaria, com R$ 50 mil ou mais cada. Hospitais, clínicas e laboratórios credenciados ao SUS ficam de fora, porque não disputam preço entre si. Não é ilegal, mas se as duas disputaram a mesma licitação a concorrência pode ter sido de fachada.</li>
      <li><b>Mesmo endereço de outro fornecedor:</b> empresas diferentes, sem sócio em comum, do mesmo ramo, registradas na Receita no mesmo CEP, número e complemento, pagas pela mesma secretaria. Pode ser um prédio comercial ou um escritório de contabilidade; vale conferir se disputaram a mesma compra.</li>
    </ul>
    <p class="sub fonte-linha">Atualizado em ${esc(A.coletado_em)}. Fontes: ${A.fontes.map(esc).join("; ")}. Os gastos da Prefeitura estão na última versão que o Radar conseguiu baixar. Achou um sinal errado? <a href="mailto:radarjflandia@gmail.com?subject=Sinal%20de%20alerta%20errado">Avise pelo e-mail radarjflandia@gmail.com</a> que a gente corrige.</p>`;
}


// ---------- Cargos comissionados (lista pronta) ----------
let COMISS = null;
const FONTE_SERV = "https://www.pjf.mg.gov.br/transparencia/servidores/pesquisar.php?orgao_pesq=PJF";
const MINUSC = new Set(["de", "da", "do", "das", "dos", "e", "d"]);
const nomeBonito = n => n.toLowerCase().split(" ").map((w, i) => i && MINUSC.has(w) ? w : w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
const CARGO_TX = {SECRETARIO: "Secretário(a)", "SECRETARIO ADJUNTO": "Secretário(a) adjunto(a)", "SECRETARIO EXECUTIVO": "Secretário(a) executivo(a)", SUBSECRETARIO: "Subsecretário(a)", GERENTE: "Gerente"};
const cargoTx = c => CARGO_TX[c] || c.replace(/^ASSESSOR/, "Assessor(a)");
const ORDEM_CARGO = c => c === "SECRETARIO" ? 0 : c.startsWith("SECRETARIO") ? 1 : c === "SUBSECRETARIO" ? 2 : c === "GERENTE" ? 3 : 10 - ({VI: 6, V: 5, IV: 4, III: 3, II: 2, I: 1}[c.split(" ")[1]] || 0);

async function pgComissionados(sigla) {
  const $ = id => document.getElementById(id);
  if (!COMISS) COMISS = await fetch("dados/prefeitura/comissionados.json").then(r => r.ok ? r.json() : null).catch(() => null);
  const C = COMISS;
  if (!C) { app.innerHTML = "<h1>Cargos comissionados</h1><p>A lista ainda não foi publicada. Volte mais tarde.</p>"; return; }
  const P = C.pessoas.map(([nome, cargo, lot, adm, sal, bruto]) => ({nome, cargo, lot, adm, sal, bruto}));
  const nomeSec = s => C.siglas[s] ? `${C.siglas[s]} (${s})` : s;
  const grupos = {};
  P.forEach(p => (grupos[p.lot] = grupos[p.lot] || []).push(p));
  Object.values(grupos).forEach(g => g.sort((a, b) => ORDEM_CARGO(a.cargo) - ORDEM_CARGO(b.cargo) || a.nome.localeCompare(b.nome)));
  const ordem = Object.keys(grupos).sort((a, b) => grupos[b].length - grupos[a].length || a.localeCompare(b));
  const soma = g => g.reduce((t, p) => t + p.bruto, 0);
  const total = soma(P), maior = grupos[ordem[0]].length;
  const contaCargo = re => P.filter(p => re.test(p.cargo)).length;

  app.innerHTML = `
    <h1>Cargos comissionados da Prefeitura</h1>
    <p class="sub">Quem foi nomeado sem concurso para cargos de confiança: secretários, subsecretários, gerentes e assessores. Lista pronta, com dados de ${esc(C.competencia)}, separada por secretaria.</p>
    <div class="faixa-nums">
      <div><b>${fmt(P.length)}</b><span>comissionados</span></div>
      <div><b>${reais(total)}</b><span>custo bruto no mês</span></div>
      <div><b>${reais(total * 13.33)}</b><span>estimativa por ano (com 13º e férias)</span></div>
    </div>
    <p class="sub">${fmt(contaCargo(/^SECRETARIO/))} secretários, ${fmt(contaCargo(/^SUBSECRETARIO/))} subsecretários, ${fmt(contaCargo(/^GERENTE/))} gerentes e ${fmt(contaCargo(/^ASSESSOR/))} assessores.</p>
    <label class="sr" for="cq">Buscar por nome ou cargo</label>
    <input type="search" id="cq" placeholder="Buscar por nome ou cargo">
    <label class="sr" for="cs">Secretaria</label>
    <select id="cs" style="margin-top:8px"><option value="">Todas as secretarias</option>${ordem.map(s => `<option value="${esc(s)}" ${s === sigla ? "selected" : ""}>${esc(nomeSec(s))} (${grupos[s].length})</option>`).join("")}</select>
    <div id="clista"></div>
    <h2>Sobre esta lista</h2>
    <ul class="metodo">
      <li><b>De onde vem:</b> Portal da Transparência da Prefeitura, servidores da administração direta com vínculo "Comissionado". O Radar baixou as planilhas por cargo (secretário, subsecretário, gerente, assessor e coordenador) e juntou tudo aqui.</li>
      <li><b>O que pode faltar:</b> comissionados com outro nome de cargo, e os das autarquias e empresas (Cesama, Demlurb, AMAC, Funalfa, Emcasa, JFPrev), que têm folha separada. Servidores concursados que recebem gratificação por chefia não entram, porque o vínculo deles é efetivo.</li>
      <li><b>Salário do cargo</b> é o valor fixo. <b>Bruto no mês</b> inclui férias, gratificações e outras verbas daquele mês, por isso pode variar.</li>
      <li>A lista é atualizada à mão, porque o site da Prefeitura bloqueia o robô do Radar. Para conferir ou ver um mês mais novo, use a <a href="${FONTE_SERV}" target="_blank" rel="noopener">pesquisa oficial de servidores</a>.</li>
    </ul>
    <p class="sub fonte-linha">Competência ${esc(C.competencia)}, baixado em ${esc(C.baixado_em.split("-").reverse().join("/"))}. Fonte: ${esc(C.fonte)}.</p>`;

  const desenha = () => {
    const q = $("cq").value.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase().trim();
    const sel = $("cs").value;
    const secs = ordem.filter(s => !sel || s === sel);
    let html = "";
    secs.forEach(s => {
      const g = grupos[s].filter(p => !q || p.nome.includes(q) || p.cargo.includes(q) || cargoTx(p.cargo).toUpperCase().includes(q));
      if (!g.length) return;
      const aberto = sel || q || secs.length === 1;
      html += `<details class="equipe"${aberto ? " open" : ""}>
        <summary>${ic("predios")}<span class="tx"><b>${esc(nomeSec(s))}</b><small>${fmt(grupos[s].length)} comissionados, ${reais(soma(grupos[s]))} no mês</small><span class="mini-barra"><i style="width:${Math.max(3, grupos[s].length / maior * 100)}%"></i></span></span></summary>
        <table class="tab-equipe"><thead><tr><th>Nome e cargo</th><th>Bruto no mês</th></tr></thead><tbody>
        ${g.map(p => `<tr><td>${esc(nomeBonito(p.nome))}<small class="sub" style="display:block">${esc(cargoTx(p.cargo))}, desde ${esc(p.adm.slice(3))}</small></td><td title="Salário do cargo: ${reais(p.sal, false)}">${reais(p.bruto, false)}</td></tr>`).join("")}
        </tbody></table></details>`;
    });
    $("clista").innerHTML = html || '<p class="sub">Ninguém encontrado com essa busca.</p>';
  };
  let tm; $("cq").oninput = () => { clearTimeout(tm); tm = setTimeout(desenha, 200); };
  $("cs").onchange = () => { history.replaceState(null, "", "#/prefeitura/comissionados" + ($("cs").value ? "/" + $("cs").value : "")); desenha(); };
  desenha();
}


// ---------- Na lupa: veículos, viagens, publicidade, eventos e corrida de dezembro ----------
let LUPA = null;
async function pgLupa(tema, ano) {
  if (!LUPA) LUPA = await fetch("dados/prefeitura/lupa.json").then(r => r.ok ? r.json() : null).catch(() => null);
  const L = LUPA;
  if (!L) { app.innerHTML = "<h1>Gastos na lupa</h1><p>Os dados ainda não foram publicados. Volte mais tarde.</p>"; return; }
  const temas = L.temas.filter(t => Object.keys(t.anos).length);
  const ids = temas.map(t => t.id).concat(Object.keys(L.dezembro || {}).length ? ["dezembro"] : []);
  tema = ids.includes(tema) ? tema : ids[0];
  const nomeT = id => id === "dezembro" ? "Corrida de dezembro" : (temas.find(t => t.id === id) || {}).titulo;
  const abas = `<div class="chips lupa-abas">${ids.map(id => `<a href="#/prefeitura/lupa/${id}" class="${id === tema ? "on" : ""}">${esc(nomeT(id))}</a>`).join("")}</div>`;
  const barrasMes = (meses, destaque) => { const mx = Math.max(...meses, 1); return `<div class="mini-barras lupa-meses" role="img" aria-label="Valor mês a mês">${meses.map((v, i) => `<span class="${i === destaque ? "dest" : ""}" title="${NOMES_MES[i]}: ${reais(v, false)}" style="height:${Math.max(2, Math.round(100 * v / mx))}%"></span>`).join("")}</div><div class="lupa-rot">${NOMES_MES.map(m => `<span>${m}</span>`).join("")}</div>`; };
  const barraL = (lista, fmtNome) => { const mx = Math.max(...lista.map(x => x[1]), 1); return lista.map(x => `<div class="barra-l"><span class="bl-t">${fmtNome(x)}</span><span class="bl-b"><i style="width:${Math.max(1, Math.round(100 * x[1] / mx))}%"></i></span><span class="bl-v">${reais(x[1])}</span></div>`).join(""); };
  let corpo = "";
  if (tema === "dezembro") {
    const anosD = Object.keys(L.dezembro).sort();
    ano = anosD.includes(ano) ? ano : anosD[anosD.length - 1];
    const D = L.dezembro[ano];
    const vezes = D.mediana ? D.dez / D.mediana : 0;
    corpo = `${anosD.length > 1 ? `<div class="anos">${anosD.map(a => `<button class="${a === ano ? "on" : ""}" onclick="location.hash='#/prefeitura/lupa/dezembro/${a}'">${a}</button>`).join("")}</div>` : ""}
      <p class="sub">No fim do ano muitos órgãos correm para empenhar (reservar) o dinheiro que sobrou do orçamento. Gasto apressado costuma ter menos planejamento e menos concorrência. Aqui ficam de fora salários, aposentadorias, 13º, encargos e dívida, que sempre sobem em dezembro.</p>
      <div class="nums"><span><b>${reais(D.dez)}</b>empenhados em dezembro de ${ano}</span><span><b>${reais(D.mediana)}</b>num mês típico (mediana de fevereiro a novembro)</span>${vezes >= 1.2 ? `<span><b>${vezes.toLocaleString("pt-BR", {maximumFractionDigits: 1})} vezes</b>o mês típico</span>` : ""}</div>
      ${barrasMes(D.meses, 11)}
      <p class="sub">Janeiro costuma ser alto porque muitos contratos são empenhados para o ano inteiro logo no começo.</p>
      ${D.secretarias.length ? `<h2>Unidades que mais aceleraram em dezembro</h2><p class="sub">Empenharam em dezembro pelo menos R$ 1 milhão e mais de duas vezes e meia o próprio mês típico.</p>
        ${D.secretarias.map(([s, dez, base]) => `<div class="linha lupa-dez"><span class="nm">${esc(secNome(s))}<br><small class="sub">Mês típico: ${reais(base)}${base ? `. Dezembro foi ${(dez / base).toLocaleString("pt-BR", {maximumFractionDigits: 0})} vezes maior` : ""}</small></span><span class="vl">${reais(dez)}</span></div>`).join("")}` : `<p class="sub">Nenhuma unidade passou do critério neste ano.</p>`}
      <p class="sub">Para ver o que foi empenhado, use a <a href="#/prefeitura/busca/${ano}">busca de gastos</a> e procure pelo nome da secretaria.</p>`;
  } else {
    const T = temas.find(t => t.id === tema);
    const anosT = Object.keys(T.anos).sort();
    ano = anosT.includes(ano) ? ano : anosT[anosT.length - 1];
    const A = T.anos[ano];
    const atual = ano === String(new Date().getFullYear());
    const ant = T.anos[String(+ano - 1)];
    corpo = `${anosT.length > 1 ? `<div class="anos">${anosT.map(a => `<button class="${a === ano ? "on" : ""}" onclick="location.hash='#/prefeitura/lupa/${tema}/${a}'">${a}</button>`).join("")}</div>` : ""}
      <p class="sub">${esc(T.texto)}</p>
      <div class="nums"><span><b>${reais(A.p)}</b>pagos em ${ano}${atual ? " até agora" : ""}</span><span><b>${reais(A.e)}</b>empenhados (reservados)</span><span><b>${fmt(A.n)}</b>lançamentos</span></div>
      ${ant && atual ? `<p class="sub">Em ${+ano - 1}, o ano inteiro somou ${reais(ant.p)} pagos.</p>` : ""}
      ${barrasMes(A.meses, -1)}
      ${A.secretarias.length ? `<h2>Quem gasta</h2>${barraL(A.secretarias, x => esc(secNome(x[0])))}` : ""}
      ${A.fornecedores.length ? `<h2>Quem recebe</h2>${A.fornecedores.map(([c, n, v, k]) => `<a class="linha" href="#/prefeitura/empresa/${ano}/${c}"><span class="nm">${esc(n)}<br><small class="sub">CNPJ ${cnpjFmt(c)} · ${fmt(k)} lançamentos</small></span><span class="vl">${reais(v)} ›</span></a>`).join("")}` : ""}
      ${A.pf ? `<p class="sub">Inclui ${reais(A.pf)} pagos a pessoas físicas (por exemplo diárias de servidores), mostrados só no total, sem nomes.</p>` : ""}
      ${A.maiores.length ? `<h2>Maiores lançamentos</h2>${A.maiores.map(([d, s, c, n, v, h, num]) => `<div class="lanc"><div class="lanc-top"><a href="#/prefeitura/empresa/${ano}/${c}">${esc(n)}</a><b>${reais(v, false)}</b></div><small class="sub">${d ? d.split("-").reverse().join("/") : ""} · ${esc(secNome(s))}${numEmp(num) ? " · empenho " + esc(numEmp(num)) : ""}</small>${h ? `<p>${esc(h)}</p>` : ""}</div>`).join("")}` : ""}
      <p class="sub">Separados pelo Radar a partir do tipo de despesa, do texto do empenho e do ramo da empresa. Um lançamento pode ter ficado de fora ou entrado por engano; confira sempre o texto. <a href="#/prefeitura/busca/${ano}">Buscar outros gastos</a>.</p>`;
  }
  app.innerHTML = `<h1>Gastos na lupa</h1>
    <p class="sub">Os gastos da Prefeitura que mais chamam atenção, separados por assunto, com quem gasta, quem recebe e os maiores valores.</p>
    ${abas}<h2 class="lupa-tit">${esc(nomeT(tema))}</h2>${corpo}
    <p class="sub fonte-linha">Fonte: empenhos do ${fonteLink("Portal da Transparência da Prefeitura")}. Atualizado em ${esc(L.atualizado)}.</p>`;
}
