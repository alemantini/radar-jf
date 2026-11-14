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
    ${A.secretarias.map((s, i) => `<a class="linha" href="#/prefeitura/s/${ano}/${i}"><span class="nm">${esc(s.nome)}<div class="barra-p" style="width:${Math.max(1, Math.round(100 * s.p / max))}%"></div></span><span class="vl">${reais(s.p)} ›</span></a>`).join("")}
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
    document.getElementById("res").innerHTML = it.map((f, k) => `<a class="linha" href="#/prefeitura/empresa/${ano}/${f.cnpj}"><span class="nm">${esc(f.nome)}<br><small class="sub">CNPJ ${cnpjFmt(f.cnpj)} · ${esc(f.secretarias.slice(0, 2).join(", "))}</small></span><span class="vl">${reais(f.p)} ›</span></a>`).join("") || '<p class="sub">Ninguém encontrado nesta lista.</p>';
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
