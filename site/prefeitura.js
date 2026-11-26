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
    <a class="btn-grande prefeitura" href="#/prefeitura/iptu">${ic("dinheiro")}<span class="tx">Calculadora do IPTU<small>Quanto dá o seu IPTU, quanto economiza à vista e para onde vai o dinheiro</small></span>›</a>
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

// ---------- Emendas que pagaram eventos (Diário Oficial x Monitor de Emendas) ----------
let EVENTOS_EM = null;
const ATO_URL = id => `https://www.pjf.mg.gov.br/e_atos/e_atos_vis.php?id=${id}`;
const COR_EV = {musica: "#7b3fb5", gastronomia: "#c0612b", esporte: "#1f7a4d", agro: "#6b7d1f", religioso: "#2f5d9b", carnaval: "#c2307a", diversidade: "#8a4fa0", artes: "#2a7f8f", turismo: "#4a5a70", outros: "#7a828e"};
function nomeProp(p) {
  if (p === "COLETIVA") return {nome: "Emenda coletiva (todos os vereadores)", sub: ""};
  const v = vereadorDoProponente(p);
  return v ? {nome: v.apelido, sub: v.partido || "", v} : {nome: p, sub: "não está na lista atual de vereadores"};
}
async function pgEventosEmendas(prop) {
  if (!EVENTOS_EM) {
    app.innerHTML = '<p class="carregando">Carregando…</p>';
    try { EVENTOS_EM = await fetch("dados/prefeitura/emendas_eventos.json").then(r => r.json()); }
    catch (e) { app.innerHTML = "<h1>Emendas que pagaram eventos</h1><p>Os dados ainda não estão disponíveis. Tente mais tarde.</p>"; return; }
  }
  const D = EVENTOS_EM, C = D.categorias;
  if (prop) prop = decodeURIComponent(prop);
  const filtroCat = prop && prop.startsWith("tipo:") ? prop.slice(5) : "";
  const filtroProp = prop && !filtroCat ? prop : "";
  // por vereador
  const pv = {};
  D.itens.forEach(i => { const x = pv[i.p] = pv[i.p] || {n: 0, v: 0, ne: 0, ve: 0}; x.n++; x.v += i.v; if (!i.misto) { x.ne++; x.ve += i.v; } });
  const lista = Object.entries(pv).map(([p, x]) => ({p, ...x, ...nomeProp(p)})).sort((a, b) => b.v - a.v);
  const comEmenda = new Set(lista.map(x => x.v && x.v.id).filter(Boolean));
  const semEmenda = RESUMO.vereadores.filter(v => !v.fora_da_lista && !comEmenda.has(v.id));
  const maxV = Math.max(...lista.map(x => x.v));
  const cats = Object.entries(D.por_categoria).sort((a, b) => b[1].v - a[1].v);
  const card = i => {
    const n = nomeProp(i.p);
    return `<div class="item">
      <div class="topo"><span class="tag" style="background:${COR_EV[i.cat]}">${esc(C[i.cat])}</span>${dataBR(i.d)} · Emenda ${esc(i.ep)} (${i.ano})</div>
      <div class="txt"><b>${esc(i.ev)}</b></div>
      <div class="pe">Para: ${esc(i.benef)} · <b>${reais(i.v, false)}</b> · Emenda de <a href="#/prefeitura/eventos/${encodeURIComponent(i.p)}">${esc(n.nome)}</a>${n.sub ? ", " + esc(n.sub) : ""}</div>
      ${i.misto ? '<div class="pe sub">O ato junta, no mesmo repasse, evento e compra de material ou custeio. O Diário Oficial não diz quanto foi para cada coisa.</div>' : ""}
      <div class="pe">${i.atos.map((a, k) => `<a href="${ATO_URL(a)}" target="_blank" rel="noopener">${k ? "outro ato" : "Ver no Diário Oficial"} ›</a>`).join(" · ")}</div>
    </div>`;
  };
  let itens = D.itens;
  if (filtroCat) itens = itens.filter(i => i.cat === filtroCat);
  if (filtroProp) itens = itens.filter(i => i.p === filtroProp);
  const np = filtroProp ? nomeProp(filtroProp) : null;
  const tot = itens.reduce((s, i) => s + i.v, 0);
  app.innerHTML = `
    <h1>${np ? `Emendas de ${esc(np.nome)} para eventos` : filtroCat ? `Emendas para eventos: ${esc(C[filtroCat])}` : "Emendas que pagaram eventos"}</h1>
    ${!prop ? `<p class="sub">Parte das emendas dos vereadores vai para associações que fazem festas, shows, torneios, festivais e outros eventos. O dinheiro sai da Prefeitura por termo de colaboração e, por ser emenda individual, sem chamamento público (a lei permite: Lei Federal 13.019/2014, art. 29). Aqui está cada uma dessas emendas publicada no Diário Oficial em 2025 e 2026, com o link para o ato.</p>` : `<p class="sub"><a href="#/prefeitura/eventos">‹ Ver todas</a>${np && np.sub ? " · " + esc(np.sub) : ""}</p>`}
    <div class="nums verde"><span><b>${reaisCurto(tot)}</b>em ${fmt(itens.length)} emendas para eventos</span>${!prop ? `<span><b>${fmt(D.por_ano["2025"].n)}</b>em 2025 (${reaisCurto(D.por_ano["2025"].v)})</span><span><b>${fmt(D.por_ano["2026"].n)}</b>em 2026, até ${esc(D.apurado_em.slice(0, 5))} (${reaisCurto(D.por_ano["2026"].v)})</span>` : ""}</div>
    ${np && np.v ? `<a class="btn-grande prefeitura" href="#/prefeitura/emendas/${encodeURIComponent(filtroProp)}">${ic("dinheiro")}<span class="tx">Ver todas as emendas de ${esc(np.nome)}<small>Fonte: Monitor de Emendas da Prefeitura</small></span>›</a>` : ""}
    ${!prop ? `
    <h2>Que tipo de evento</h2>
    ${cats.map(([k, x]) => `<a class="linha" href="#/prefeitura/eventos/tipo:${k}"><span class="nm"><b><i class="ponto" style="background:${COR_EV[k]}"></i> ${esc(C[k])}</b><small class="sub">${fmt(x.n)} emendas</small></span><span class="vl">${reaisCurto(x.v)} ›</span></a>`).join("")}
    <h2>Por vereador</h2>
    <p class="sub">Do maior para o menor valor. A barra escura é o que foi só para evento; a clara é de repasses que juntam evento e compra de material ou custeio.</p>
    ${lista.map(x => `<a class="linha" href="#/prefeitura/eventos/${encodeURIComponent(x.p)}"><span class="nm"><b>${esc(x.nome)}</b>${x.sub ? `, <small class="sub">${esc(x.sub)}</small>` : ""}
      <span class="barra-ev"><i style="width:${(100 * x.ve / maxV).toFixed(1)}%"></i><i class="cl" style="width:${(100 * (x.v - x.ve) / maxV).toFixed(1)}%"></i></span><small class="sub">${fmt(x.n)} ${x.n > 1 ? "emendas" : "emenda"}${x.n !== x.ne ? ` (${fmt(x.n - x.ne)} com material ou custeio junto)` : ""}</small></span><span class="vl">${reaisCurto(x.v)} ›</span></a>`).join("")}
    ${semEmenda.length ? `<p class="sub">Sem emenda para evento encontrada nos atos de 2025 e 2026: ${semEmenda.map(v => `<a href="#/v/${v.id}">${esc(v.apelido)}</a>`).join(", ")}.</p>` : ""}
    <h2>Todas as emendas</h2>` : ""}
    <input type="search" id="q" placeholder="Filtrar por evento, entidade ou vereador" autocomplete="off">
    <div id="lista"></div>
    <div class="aviso"><b>Como foi feito.</b> Lemos os ${fmt(D.atos_lidos)} atos do Diário Oficial publicados de janeiro de 2025 até ${esc(D.apurado_em)} que citam emenda parlamentar. Entram os repasses cujo ato (ou o objeto da emenda no Monitor de Emendas) fala em evento, festa, festival, show, torneio, campeonato, copa, corrida, carnaval, folia, mostra ou parecidos. O autor de cada emenda vem do Monitor de Emendas da Prefeitura, conferido pelo número da emenda, pelo ano e pelo CNPJ ou valor da entidade. O valor é o do repasse publicado no ato. A data é a da publicação no Diário, não a do evento. A mesma regra vale para todos os vereadores. Ficam fora os repasses que não citam evento, as emendas federais e estaduais e o que ainda não foi publicado. Dar dinheiro para evento por emenda é permitido; esta página mostra para onde foi, sem juízo de valor. Achou um erro? Abra o ato pelo link e <a href="https://github.com/alemantini/radar-jf/issues" target="_blank" rel="noopener">avise aqui</a>.</div>
    <p class="sub fonte-linha">Fontes: <a href="${D.fonte_url}" target="_blank" rel="noopener">Diário Oficial do Município (Atos do Governo)</a> e <a href="#/prefeitura/emendas">Monitor de Emendas da Prefeitura</a>. Apuração de ${esc(D.apurado_em)}.</p>`;
  const alvo = document.getElementById("lista"), inp = document.getElementById("q");
  const mostra = () => {
    const q = norm(inp.value.trim());
    const it = q ? itens.filter(i => norm(`${i.ev} ${i.benef} ${i.p} ${nomeProp(i.p).nome} ${C[i.cat]} ${i.ep}`).includes(q)) : itens;
    alvo.innerHTML = it.map(card).join("") || '<p class="sub">Nada encontrado.</p>';
  };
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
  if (sub === "supersalarios") return pgSupersalarios();
  if (sub === "iptu") return a === "areas" ? pgIptuAreas(b) : pgIptu();
  if (sub === "emendas") return pgEmendas(a);
  if (sub === "eventos") return pgEventosEmendas(a);
  if (sub === "diario") return pgDiario(a, b);
  if (sub === "s") return pgPrefSecretaria(a, +b);
  if (sub === "fornecedores") return pgPrefFornecedores(a);
  if (sub === "empresa") return pgPrefEmpresa(a, b);
  if (sub === "busca") return pgPrefBusca(a, b);
  if (sub === "chuvas") return pgChuvas();
  if (sub === "emprestimos") return pgEmprestimos();
  if (sub === "hospitais") return pgHospitais(a);
  if (sub === "creditos") return pgCreditos(a);
  if (sub === "aditivos") return pgAditivos(a);
  if (sub === "curiosas") return pgCuriosas();
  if (sub === "alugueis") return pgAlugueisPJF();
  if (sub === "combustivel") return pgCombustivelPJF(a);
  if (sub === "previdencia") return pgPrevidencia();
  if (sub === "obras") return pgObrasPrevistas();
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
    <p class="sub">O Radar cruza dados públicos (empenhos da Prefeitura, cadastro de empresas da Receita, doações de campanha do TSE, cadastros de punidos da CGU, lista de cargos de confiança e contratos publicados no Portal Nacional de Contratações Públicas) e aponta situações que merecem uma pergunta.</p>
    <div class="aviso-forte"><b>Sinal não é prova.</b> Cada item abaixo pode ter explicação legal: emergência real, fornecedor único, contrato antigo, hospital conveniado. Ninguém aqui está sendo acusado de nada. Use os sinais para perguntar à Prefeitura, à Câmara ou ao Tribunal de Contas, sempre conferindo nos documentos oficiais.</div>
    <div class="chips-filtro">
      <a href="#/prefeitura/alertas" class="${!tipo ? "on" : ""}">Todos <b>${fmt(A.alertas.length)}</b></a>
      ${Object.entries(A.tipos).filter(([k]) => A.contagem[k]).map(([k, t]) => `<a href="#/prefeitura/alertas/${k}" class="${tipo === k ? "on" : ""}">${t} <b>${fmt(A.contagem[k])}</b></a>`).join("")}
    </div>
    ${lista.map(a => `
      <div class="alerta-card">
        <div class="ac-topo"><span class="ac-tipo">${esc(A.tipos[a.tipo] || a.tipo)}${a.desde && a.desde !== "antes" && (Date.now() - new Date(a.desde + "T12:00:00")) < 8 * 864e5 ? ' <b class="ac-novo">novo</b>' : ""}</span><span class="ac-valor">${reais(a.valor)}</span></div>
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
      <li><b>Cargo de confiança com nome de sócio:</b> o nome completo (três palavras ou mais) de um comissionado ou de um concursado em função de confiança da Prefeitura é igual ao de um sócio ou dirigente de empresa ou entidade que recebe da Prefeitura, segundo a Receita Federal. A lista de servidores não traz CPF, então pode ser outra pessoa com o mesmo nome. Servidor pode ser sócio de empresa, mas não pode contratar com o próprio órgão nem participar da escolha dela.</li>
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
  const TODOS = C.pessoas.map(([nome, cargo, lot, adm, sal, bruto, tipo, origem, fg]) => ({nome, cargo, lot, adm, sal, bruto, tipo: tipo || "c", origem: origem || "", fg: fg || 0}));
  const nC = TODOS.filter(p => p.tipo === "c").length, nF = TODOS.filter(p => p.tipo === "f").length;
  const P = TODOS;
  const nomeSec = s => C.siglas[s] ? `${C.siglas[s]} (${s})` : s;
  const grupos = {};
  P.forEach(p => (grupos[p.lot] = grupos[p.lot] || []).push(p));
  Object.values(grupos).forEach(g => g.sort((a, b) => ORDEM_CARGO(a.cargo) - ORDEM_CARGO(b.cargo) || a.nome.localeCompare(b.nome)));
  const ordem = Object.keys(grupos).sort((a, b) => grupos[b].length - grupos[a].length || a.localeCompare(b));
  const soma = g => g.reduce((t, p) => t + p.bruto, 0);
  const total = soma(P), maior = grupos[ordem[0]].length;
  const contaCargo = re => P.filter(p => re.test(p.cargo)).length;

  app.innerHTML = `
    <h1>Cargos de confiança da Prefeitura</h1>
    <p class="sub">Quem a Prefeitura escolheu para secretarias, subsecretarias, gerências e assessorias, com dados de ${esc(C.competencia)}, separados por secretaria. São dois grupos:</p>
    <ul class="metodo">
      <li><b>Comissionados (${fmt(nC)}):</b> nomeados sem concurso. Saem da Prefeitura quando são exonerados.</li>
      ${nF ? `<li><b>Concursados em função de confiança (${fmt(nF)}):</b> servidores de carreira que assumiram uma chefia. Quando saem da função, voltam ao cargo de origem.</li>` : ""}
    </ul>
    <div class="faixa-nums">
      <div><b>${fmt(nC)}</b><span>comissionados</span></div>
      ${nF ? `<div><b>${fmt(nF)}</b><span>concursados em função de confiança</span></div>` : ""}
      <div><b>${reais(total)}</b><span>custo bruto no mês (os dois grupos)</span></div>
    </div>
    <p class="sub">${fmt(contaCargo(/^SECRETARIO/))} secretários, ${fmt(contaCargo(/^SUBSECRETARIO/))} subsecretários, ${fmt(contaCargo(/^GERENTE/))} gerentes e ${fmt(contaCargo(/^ASSESSOR/))} assessores, somando os dois grupos.</p>
    ${nF ? `<label class="sr" for="ct">Tipo</label><select id="ct"><option value="">Os dois grupos</option><option value="c">Só comissionados (sem concurso)</option><option value="f">Só concursados em função de confiança</option></select>` : ""}
    <label class="sr" for="cq">Buscar por nome ou cargo</label>
    <input type="search" id="cq" placeholder="Buscar por nome ou cargo">
    <label class="sr" for="cs">Secretaria</label>
    <select id="cs" style="margin-top:8px"><option value="">Todas as secretarias</option>${ordem.map(s => `<option value="${esc(s)}" ${s === sigla ? "selected" : ""}>${esc(nomeSec(s))} (${grupos[s].length})</option>`).join("")}</select>
    <div id="clista"></div>
    <h2>Sobre esta lista</h2>
    <ul class="metodo">
      <li><b>De onde vem:</b> Portal da Transparência da Prefeitura, planilha com todos os servidores da administração direta no mês. Entram quem tem vínculo "Comissionado" e quem tem a coluna "Função" preenchida (concursados em função de confiança). Prefeita e vice-prefeito, que são eleitos, não entram.</li>
      <li><b>O que fica de fora:</b> as autarquias e empresas (Cesama, Demlurb, AMAC, Funalfa, Emcasa, JFPrev), que têm folha separada, e servidores que recebem gratificação sem ocupar uma função de chefia listada.</li>
      <li><b>Salário do cargo</b> é o valor fixo. <b>Bruto no mês</b> inclui férias, gratificações e outras verbas daquele mês, por isso pode variar.</li>
      <li>A lista é atualizada à mão, porque o site da Prefeitura bloqueia o robô do Radar. Para conferir ou ver um mês mais novo, use a <a href="${FONTE_SERV}" target="_blank" rel="noopener">pesquisa oficial de servidores</a>.</li>
    </ul>
    <p class="sub fonte-linha">Competência ${esc(C.competencia)}, baixado em ${esc(C.baixado_em.split("-").reverse().join("/"))}. Fonte: ${esc(C.fonte)}.</p>`;

  const desenha = () => {
    const q = $("cq").value.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase().trim();
    const sel = $("cs").value, tp = $("ct") ? $("ct").value : "";
    const secs = ordem.filter(s => !sel || s === sel);
    let html = "";
    secs.forEach(s => {
      const g = grupos[s].filter(p => (!tp || p.tipo === tp) && (!q || p.nome.includes(q) || p.cargo.includes(q) || p.origem.includes(q) || cargoTx(p.cargo).toUpperCase().includes(q)));
      if (!g.length) return;
      const aberto = sel || q || secs.length === 1;
      html += `<details class="equipe"${aberto ? " open" : ""}>
        <summary>${ic("predios")}<span class="tx"><b>${esc(nomeSec(s))}</b><small>${fmt(grupos[s].length)} ${grupos[s].length === 1 ? "pessoa" : "pessoas"}, ${reais(soma(grupos[s]))} no mês</small><span class="mini-barra"><i style="width:${Math.max(3, grupos[s].length / maior * 100)}%"></i></span></span></summary>
        <table class="tab-equipe"><thead><tr><th>Nome e cargo</th><th>Bruto no mês</th></tr></thead><tbody>
        ${g.map(p => `<tr><td>${esc(nomeBonito(p.nome))}<small class="sub" style="display:block">${esc(cargoTx(p.cargo))}${p.tipo === "f" ? ` <b class="tag-conc">concursado</b>, no quadro desde ${esc(p.adm.slice(3))} (cargo de origem: ${esc(p.origem)})` : `, comissionado desde ${esc(p.adm.slice(3))}`}</small></td><td title="Salário do cargo: ${reais(p.sal, false)}">${reais(p.bruto, false)}</td></tr>`).join("")}
        </tbody></table></details>`;
    });
    $("clista").innerHTML = html || '<p class="sub">Ninguém encontrado com essa busca.</p>';
  };
  let tm; $("cq").oninput = () => { clearTimeout(tm); tm = setTimeout(desenha, 200); };
  if ($("ct")) $("ct").onchange = desenha;
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
      <p><b>${vezes >= 1.2 ? `Em ${ano}, dezembro foi ${vezes.toLocaleString("pt-BR", {maximumFractionDigits: 1})} vezes o mês típico.` : vezes >= 0.8 ? `Em ${ano}, dezembro ficou perto de um mês típico: não houve corrida geral.` : `Em ${ano}, não houve corrida geral: dezembro ficou abaixo do mês típico.`}</b>${D.secretarias.length ? " Mas algumas unidades aceleraram, veja abaixo." : ""}</p>
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


// ---------- Supersalários: quem passou do teto constitucional ----------
let SUPER = null;
async function pgSupersalarios() {
  if (!SUPER) SUPER = await fetch("dados/prefeitura/supersalarios.json").then(r => r.ok ? r.json() : null).catch(() => null);
  const S = SUPER;
  if (!S) { app.innerHTML = "<h1>Supersalários</h1><p>Os dados ainda não foram publicados. Volte mais tarde.</p>"; return; }
  const r2 = v => reais(v, false);
  const nomeSec = s => (COMISS && COMISS.siglas && COMISS.siglas[s]) ? `${COMISS.siglas[s]} (${s})` : s;
  if (!COMISS) COMISS = await fetch("dados/prefeitura/comissionados.json").then(r => r.ok ? r.json() : null).catch(() => null);
  const posto = (c, f) => f ? `${cargoTx(f)} (cargo de origem: ${c})` : cargoTx(c);
  app.innerHTML = `
    <h1>Supersalários na Prefeitura</h1>
    <p class="sub">A Constituição proíbe que um servidor da Prefeitura ganhe mais do que a prefeita (art. 37, XI). O Radar conferiu a folha de ${esc(S.competencia)} inteira e mostra quem passou do limite e quem mais recebeu no mês.</p>
    <div class="faixa-nums">
      <div><b>${r2(S.teto)}</b><span>teto: salário da prefeita</span></div>
      <div><b>${r2(S.teto_procurador)}</b><span>teto dos procuradores municipais</span></div>
      <div><b>${fmt(S.servidores)}</b><span>servidores conferidos</span></div>
    </div>
    <p>Neste mês a própria Prefeitura aplicou o <b>abate-teto</b> (o corte do que passa do limite) em <b>${fmt(S.com_retencao)} servidores</b>. Mesmo assim, pela conta do Radar, <b>${fmt(S.acima.length)} ${S.acima.length === 1 ? "servidor ficou" : "servidores ficaram"} acima do teto</b>:</p>
    ${S.acima.map(a => { const [nome, cargo, func, vinc, lot, ce, perm, fg, hon, ret, suj, lim, exc, bruto] = a; return `
      <div class="alerta-card">
        <div class="ac-topo"><span class="ac-tipo">Acima do teto em ${r2(exc)}</span><span class="ac-valor">${r2(suj)}</span></div>
        <b class="ac-nome">${esc(nomeBonito(nome))}</b>
        <small class="sub">${esc(posto(cargo, func))} · ${esc(vinc.toLowerCase())} · ${esc(nomeSec(lot))}</small>
        <p>Pela conta mais conservadora, recebeu pelo menos ${r2(suj)} em parcelas que contam para o teto, contra um limite de ${r2(lim)}. Na planilha aparecem: cargo ${r2(ce)}${perm ? `, verbas permanentes ${r2(perm)}` : ""}${fg ? `, função gratificada ${r2(fg)}` : ""}${hon ? `, honorários ${r2(hon)}` : ""}${ret ? `, e ${r2(ret)} já cortados pelo abate-teto` : ""}. Bruto do mês: ${r2(bruto)}.</p>
      </div>`; }).join("") || '<p class="sub">Ninguém passou do teto pela conta do Radar neste mês.</p>'}
    <p class="sub">Pode haver explicação que a planilha não mostra, como decisão judicial, pagamento atrasado lançado no mês ou regra específica da carreira. É uma pergunta a fazer à Prefeitura, não uma acusação.</p>
    ${S.abate ? `<h2>O abate-teto deste mês</h2>
    <p>A Prefeitura cortou <b>${r2(S.abate.total)}</b> de <b>${fmt(S.abate.n)} servidores</b> que passariam do teto. Cada um recebeu até o limite e o que passou ficou retido. Os cortes foram de ${r2(Math.min(...S.abate.lista.map(x => x[4])))} a ${r2(Math.max(...S.abate.lista.map(x => x[4])))}.</p>
    <table class="tab-equipe"><thead><tr><th>Carreira</th><th>Pessoas</th><th>Total cortado</th><th>Maior corte</th></tr></thead><tbody>
    ${S.abate.grupos.map(([g, n, t, mx]) => `<tr><td>${esc(g)}</td><td>${fmt(n)}</td><td>${r2(t)}</td><td>${r2(mx)}</td></tr>`).join("")}
    </tbody></table>
    <p class="sub">Quase todos os cortes são em carreiras da Educação e da Fazenda. ${S.abate.procuradores ? `Dos ${fmt(S.abate.procuradores)} procuradores municipais, ${S.abate.procuradores_com_corte ? fmt(S.abate.procuradores_com_corte) + " tiveram corte" : "nenhum teve corte"} neste mês. O limite deles é maior (${r2(S.teto_procurador)})${S.acima.some(a => a[1].startsWith("PROCURADOR")) ? ", e mesmo assim há procurador acima dele, como mostrado no começo da página" : ""}.` : ""} "PR B" é como o portal abrevia o cargo; pela sigla e pela lotação na Educação, deve ser professor, mas o portal não explica a abreviação.</p>
    <details class="equipe"><summary>${ic("pessoas")}<span class="tx"><b>Ver os ${fmt(S.abate.n)} cortes, um por um</b><small>Por cargo e lotação. Sem nomes, porque aqui a lei foi cumprida.</small></span></summary>
    <table class="tab-equipe"><thead><tr><th>Cargo e lotação</th><th>Bruto</th><th>Corte</th><th>Líquido</th></tr></thead><tbody>
    ${S.abate.lista.map(([c, f, l, b, ret, liq]) => `<tr><td>${esc(f ? cargoTx(f) + " (cargo de origem: " + c + ")" : c)}<small class="sub" style="display:block">${esc(nomeSec(l))}</small></td><td>${r2(b)}</td><td>${r2(ret)}</td><td>${r2(liq)}</td></tr>`).join("")}
    </tbody></table></details>` : ""}
    <h2>Os 50 maiores salários brutos do mês</h2>
    <p class="sub">O bruto inclui férias, 13º, abono e pagamentos atrasados, que não contam para o teto. Por isso alguém pode aparecer aqui com bruto alto e estar dentro da lei.</p>
    <table class="tab-equipe"><thead><tr><th>Nome e cargo</th><th>Bruto no mês</th></tr></thead><tbody>
    ${S.maiores.map(([nome, cargo, func, vinc, lot, bruto, suj, liq]) => `<tr><td>${esc(nomeBonito(nome))}<small class="sub" style="display:block">${esc(posto(cargo, func))} · ${esc(lot)}. Líquido: ${r2(liq)}</small></td><td>${r2(bruto)}</td></tr>`).join("")}
    </tbody></table>
    <h2>Como a conta é feita</h2>
    <ul class="metodo">
      <li><b>Teto:</b> o salário da prefeita, ${r2(S.teto)}, que vem da mesma planilha. Para procuradores municipais, o STF fixou o limite em 90,25% do salário de ministro do Supremo (${r2(S.stf)}), ou seja, ${r2(S.teto_procurador)}.</li>
      <li><b>Contam para o teto:</b> salário do cargo, verbas permanentes, função gratificada e honorários (o STF reafirmou em 2026 que honorários dos procuradores entram no teto). O valor que a Prefeitura já cortou pelo abate-teto é descontado.</li>
      <li><b>Não contam:</b> 13º, férias, abono de permanência, verbas temporárias e indenizações.</li>
      <li><b>Conta conservadora:</b> na planilha da Prefeitura as parcelas nem sempre somam o bruto. Por isso o Radar usa o menor valor entre a soma das parcelas que contam para o teto e o bruto sem 13º, férias, abono e verbas temporárias. Assim só aparece quem passou do teto pelas duas contas.</li>
      <li>Cada linha da planilha é uma matrícula. Quem tem dois cargos que a lei permite acumular aparece duas vezes, e o teto vale para cada cargo separadamente.</li>
      <li>Ficam de fora as autarquias e empresas (Cesama, Demlurb, AMAC, Funalfa, Emcasa, JFPrev), que têm folha própria. Prefeita e vice não entram na lista.</li>
      <li><b>Como conferir:</b> no Portal da Transparência da Prefeitura, em Servidores, escolha o órgão PJF e a competência, pesquise sem preencher nada e baixe o CSV. A coluna "Retenção por Teto Constitucional" mostra o abate-teto de cada servidor. Qualquer pessoa chega aos mesmos números.</li>
      <li><b>Bruto, líquido e corte:</b> bruto é tudo o que foi pago no mês antes dos descontos; líquido é o que caiu na conta depois de previdência, imposto de renda e abate-teto.</li>
      <li>Os valores são de um mês só. Um mês com férias, 13º ou atrasados pode ficar bem acima dos outros.</li>
      <li><b>Salário de servidor é informação pública por lei (Lei de Acesso à Informação e decisão do STF). O Radar mostra exatamente o que a Prefeitura publica.</b></li>
    </ul>
    <p class="sub fonte-linha">Competência ${esc(S.competencia)}, baixado em ${esc(S.baixado_em.split("-").reverse().join("/"))}. Fonte: ${esc(S.fonte)}. Confira na <a href="${FONTE_SERV}" target="_blank" rel="noopener">pesquisa oficial de servidores</a>.</p>`;
}


// ---------- Calculadora do IPTU 2026 ----------
// Tabelas do "Manual IPTU/TCRS/CIPS 2026" da Secretaria da Fazenda da PJF.
const IPTU_FONTE = "https://www.pjf.mg.gov.br/secretarias/sf/iptu/arquivos/manual-iptu-2026.pdf";
const IPTU_TAB = {
  res: [[71048.98, .005], [142097.92, .006], [284197.94, .007], [1420987.55, .008], [Infinity, .009]],
  nres: [[71048.98, .006], [142097.92, .007], [284197.94, .008], [1420987.55, .009], [Infinity, .010]],
  lote_murado: [[28419.99, .011], [71048.98, .014], [142097.93, .017], [Infinity, .020]],
  lote_aberto: [[28419.99, .015], [71048.98, .020], [142097.93, .025], [Infinity, .030]],
};
const TCRS_REF = {res: 170.49, nres: 341.00};
async function pgIptu() {
  const R = await prefResumo().catch(() => null);
  const REC = await prefReceitas();
  const anoG = R ? anosDisp(R).filter(a => +a < new Date().getFullYear())[0] || anosDisp(R)[0] : null;
  const pct = x => (x * 100).toLocaleString("pt-BR", {maximumFractionDigits: 1}) + "%";
  app.innerHTML = `
    <h1>Calculadora do IPTU 2026</h1>
    <p class="sub">Coloque o valor venal do seu imóvel e veja quanto dá o IPTU pelas regras de 2026, quanto economiza pagando à vista e para onde vai esse dinheiro.</p>
    <div class="calc">
      <label for="iv">Valor venal do imóvel (R$)</label>
      <input id="iv" inputmode="decimal" placeholder="Ex.: 180.000" autocomplete="off">
      <small class="sub">Está no seu carnê do IPTU ou na consulta do IPTU no site da Prefeitura. Não é o preço de venda do imóvel: costuma ser bem menor.</small>
      <label for="it">Tipo de imóvel</label>
      <select id="it">
        <option value="res">Casa ou apartamento (residencial)</option>
        <option value="nres">Loja, sala ou outro uso (não residencial)</option>
        <option value="lote_murado">Lote vago murado ou cercado</option>
        <option value="lote_aberto">Lote vago sem muro nem cerca</option>
      </select>
      <div id="ic-lixo"><label for="ic">Coleta de lixo por semana</label>
      <select id="ic"><option value="0">Não sei ou não quero incluir</option><option value="2">2 vezes</option><option value="3" selected>3 vezes</option><option value="6">6 vezes (todo dia)</option></select></div>
    </div>
    <div id="ires"></div>
    <a class="btn-grande prefeitura" href="#/prefeitura/iptu/areas">${ic("pin")}<span class="tx">Quanto vale o m² do IPTU em cada área da cidade<small>Ranking das 851 áreas, das mais caras às mais baratas, e o aumento barrado em 2026</small></span>›</a>
    <h2>Por que o seu carnê pode vir diferente</h2>
    <ul class="metodo">
      <li><b>Redução para casas pequenas:</b> imóveis residenciais pequenos em algumas regiões da cidade têm redução no IPTU (Lei 12.196/2010). Pelo manual da Prefeitura, ela pode chegar a 80% para casas de até 79 m² nas regiões do grupo D. A calculadora não aplica essa redução, porque ela depende da região e da área do imóvel.</li>
      <li><b>Isenções:</b> há isenções previstas em lei, por exemplo para quem recebe o BPC e tem um único imóvel residencial. Quem tem isenção não paga.</li>
      <li><b>Taxa do lixo (TCRS):</b> valor de referência de 2026 vezes o número de coletas por semana, limitado a 1,5 vez o IPTU. A calculadora usa esse limite.</li>
      <li><b>Iluminação pública (CIPS):</b> para imóvel construído, vem na conta de luz, não no carnê.</li>
      <li><b>Prazos de 2026:</b> o desconto de 10% à vista valia até 02/02/2026. O parcelamento é em até 10 vezes, com a 1ª parcela em 20/03/2026.</li>
    </ul>
    <p class="sub fonte-linha">Fonte: <a href="${IPTU_FONTE}" target="_blank" rel="noopener">Manual IPTU/TCRS/CIPS 2026, Secretaria da Fazenda da Prefeitura</a>. A conta é uma estimativa; o valor oficial é o do carnê.</p>`;
  const ler = t => { const x = String(t || "").replace(/[^\d,\.]/g, ""); if (!x) return 0; const n = x.includes(",") ? x.replace(/\./g, "").replace(",", ".") : (/\.\d{3}($|\.)/.test(x) ? x.replace(/\./g, "") : x); return parseFloat(n) || 0; };
  const calc = () => {
    const vv = ler(document.getElementById("iv").value), tp = document.getElementById("it").value;
    const lote = tp.startsWith("lote");
    document.getElementById("ic-lixo").hidden = lote;
    const out = document.getElementById("ires");
    if (!vv) { out.innerHTML = ""; return; }
    const faixa = IPTU_TAB[tp].find(([lim]) => vv <= lim), aliq = faixa[1];
    const iptu = vv * aliq;
    const col = lote ? 0 : +document.getElementById("ic").value;
    let tcrs = col ? TCRS_REF[tp === "res" ? "res" : "nres"] * col : 0;
    const limitado = tcrs > 1.5 * iptu;
    if (limitado) tcrs = 1.5 * iptu;
    const total = iptu + tcrs;
    let onde = "";
    if (R && anoG) {
      const A = R.anos[anoG], tot = A.total.p || 1;
      const top = [...A.secretarias].sort((a, b) => b.p - a.p).slice(0, 6);
      const resto = tot - top.reduce((x, y) => x + y.p, 0);
      onde = `<h2>Se o seu IPTU fosse dividido como a Prefeitura gastou em ${anoG}</h2>
        <p class="sub">A Prefeitura junta o IPTU com os outros impostos e repasses e gasta tudo junto. Esta divisão mostra a proporção real dos gastos pagos em ${anoG}.</p>
        ${top.map(x => `<div class="linha"><span class="nm">${esc(secNome(x.nome))}<div class="barra-p" style="width:${Math.round(100 * x.p / tot)}%"></div></span><span class="vl">${reais(iptu * x.p / tot, false)}</span></div>`).join("")}
        <div class="linha"><span class="nm">Todas as outras secretarias e órgãos</span><span class="vl">${reais(iptu * resto / tot, false)}</span></div>`;
    }
    const iptuCidade = REC && REC.contas && REC.contas.IPTU ? REC.contas.IPTU.total_12m : 0;
    out.innerHTML = `
      <div class="iptu-res">
        <div class="ir-linha"><span>IPTU (${pct(aliq)} do valor venal)</span><b>${reais(iptu, false)}</b></div>
        ${tcrs ? `<div class="ir-linha"><span>Taxa do lixo (${col} coletas por semana${limitado ? ", limitada a 1,5 vez o IPTU" : ""})</span><b>${reais(tcrs, false)}</b></div>` : ""}
        <div class="ir-linha total"><span>Total no ano</span><b>${reais(total, false)}</b></div>
        <div class="ir-linha"><span>À vista, com 10% de desconto</span><b>${reais(total * .9, false)}</b></div>
        <div class="ir-linha"><span>Em 10 parcelas de</span><b>${reais(total / 10, false)}</b></div>
        <p class="sub">Pagando à vista você economiza ${reais(total * .1, false)}. Em 2026 o desconto valia para quem pagou até 02/02.</p>
      </div>
      ${iptuCidade ? `<p>Somando todos os imóveis, a cidade pagou <b>${reais(iptuCidade)}</b> de IPTU nos últimos 12 meses. Veja no <a href="#/prefeitura/impostometro">Impostômetro</a>.</p>` : ""}
      ${onde}`;
  };
  ["iv", "it", "ic"].forEach(id => { const el = document.getElementById(id); el.oninput = calc; el.onchange = calc; });
  calc();
}


// ---------- Valor do m² do IPTU por área isótima ----------
// Decreto nº 17.618/2025 (revogado em janeiro de 2026): valores propostos para 17 áreas.
const DECRETO_17618 = {RE072: 461.88, RE156: 461.88, RE206: 334.45, RE208: 334.45, RE373: 899.23, RE411: 355.09, RE570: 461.88, RE584: 461.88, RE610: 461.88, RE637: 332.26, RE639: 223.28, RE649: 258.88, RE650: 195.65, RE658: 219.58, RE671: 476.28, RE749: 363.46, RE751: 363.46};
let IPTU_AREAS = null;
async function pgIptuAreas(busca) {
  if (!IPTU_AREAS) IPTU_AREAS = await fetch("dados/prefeitura/iptu_areas.json").then(r => r.ok ? r.json() : null).catch(() => null);
  const D = IPTU_AREAS;
  if (!D) { app.innerHTML = "<h1>Valor do m² do IPTU</h1><p>Os dados ainda não foram publicados. Volte mais tarde.</p>"; return; }
  const A = D.areas, por = Object.fromEntries(A.map(a => [a.cod, a]));
  const vals = A.map(a => a.iptu).sort((x, y) => x - y), med = vals[Math.floor(vals.length / 2)];
  const r2 = v => reais(v, false);
  const GRP = {A: "sem redução", B: "sem redução", C: "redução para casas pequenas", D: "maiores reduções para casas pequenas"};
  const linhaA = (a, i) => `<div class="linha"><span class="nm"><b>${i != null ? i + 1 + "º · " : ""}${esc(a.cod)}</b>${a.descricao ? `<small class="sub" style="display:block">${esc(a.descricao)}</small>` : ""}<small class="sub" style="display:block">Grupo ${esc(a.grupo || "?")}${a.itbi ? ` · ITBI: ${r2(a.itbi)} o m²` : ""}</small></span><span class="vl">${r2(a.iptu)}<small class="sub" style="display:block">o m²</small></span></div>`;
  const dec = Object.entries(DECRETO_17618).map(([c, v]) => ({c, v, a: por[c]})).filter(x => x.a).sort((x, y) => (y.v / y.a.iptu) - (x.v / x.a.iptu));
  app.innerHTML = `
    <h1>Quanto vale o m² do IPTU em Juiz de Fora</h1>
    <p class="sub">A alíquota do IPTU é a mesma na cidade toda: depende só do valor venal e do tipo do imóvel. O que muda de um lugar para outro é o <b>valor do metro quadrado do terreno</b>, fixado em lei para cada "área isótima" (um pedaço da cidade com imóveis parecidos). É isso que faz o IPTU de um bairro ser mais caro que o de outro.</p>
    <div class="faixa-nums">
      <div><b>${fmt(A.length)}</b><span>áreas isótimas</span></div>
      <div><b>${r2(vals[vals.length - 1])}</b><span>o m² mais caro</span></div>
      <div><b>${r2(med)}</b><span>o m² do meio da lista (mediana)</span></div>
      <div><b>${r2(vals[0])}</b><span>o m² mais barato</span></div>
    </div>
    <div class="calc"><label for="ab">Procure a sua área pelo código ou pelo valor do m²</label><input id="ab" placeholder="Ex.: RE239 ou 1.823,11" autocomplete="off" value="${esc(busca || "")}"><small class="sub">O valor do m² do terreno aparece no espelho do IPTU, o detalhamento do cálculo que a Prefeitura disponibiliza. Com ele (ou com o código da área, se constar) você acha a sua área.</small><div id="ar"></div></div>
    <h2>As 20 áreas com o m² mais caro</h2>
    ${A.slice(0, 20).map(linhaA).join("")}
    <h2>As 20 áreas com o m² mais barato</h2>
    ${A.slice(-20).reverse().map(a => linhaA(a)).join("")}
    <h2>O aumento barrado em 2026</h2>
    <p>No fim de 2025, o Decreto nº 17.618 aumentou o valor do m² de 17 áreas, em bairros como Cruzeiro de Santo Antônio, Parque Jardim da Serra, Salvaterra, Aeroporto, Novo Horizonte, Bom Pastor, Boa Vista, São Pedro, Serro Azul, Democrata, Santa Catarina e Recanto dos Lagos. A Justiça suspendeu o decreto em janeiro de 2026 e a Prefeitura o revogou. Compare o valor de 2025 com o que o decreto queria cobrar:</p>
    <table class="tab-equipe"><thead><tr><th>Área</th><th>m² em 2025</th><th>Decreto (2026)</th><th>Aumento sobre 2025 (inclui a inflação do ano)</th></tr></thead><tbody>
    ${dec.map(x => `<tr><td>${esc(x.c)}</td><td>${r2(x.a.iptu)}</td><td>${r2(x.v)}</td><td>${Math.round(100 * (x.v / x.a.iptu - 1))}%</td></tr>`).join("")}
    </tbody></table>
    <h2>Os grupos de redução</h2>
    <p>Cada área pertence a um grupo. Nos grupos C e D, casas pequenas têm redução no IPTU; no grupo D ela pode chegar a 80% para casas de até 79 m².</p>
    ${["A", "B", "C", "D"].map(g => `<div class="linha"><span class="nm">Grupo ${g}<small class="sub" style="display:block">${GRP[g]}</small></span><span class="vl">${fmt(D.grupos[g] || 0)} áreas</span></div>`).join("")}
    <h2>O que falta</h2>
    <ul class="metodo">
      <li><b>Nome dos bairros:</b> a lei traz só o código de cada área, sem dizer a que bairro pertence (só as áreas criadas no ano têm descrição). O Radar pediu à Prefeitura, pela Lei de Acesso à Informação, a relação de áreas e bairros e o IPTU arrecadado por bairro.</li>
      <li><b>Valores de 2026:</b> os valores mostrados são os de 2025 (Lei nº 15.039/2024). Para 2026 a lei manteve as áreas e corrigiu todos os valores pela inflação (IPCA), a mesma correção para todas, então a ordem do ranking não muda.</li>
      <li><b>ITBI:</b> o imposto pago na compra de um imóvel usa outra tabela de m², mostrada junto.</li>
    </ul>
    <p class="sub fonte-linha">Fonte: <a href="${esc(D.fonte)}" target="_blank" rel="noopener">${esc(D.lei)}</a>, Anexos I, IV a IX (<a href="${esc(D.anexo)}" target="_blank" rel="noopener">PDF oficial</a>); <a href="https://www.pjf.mg.gov.br/e_atos/e_atos_vis.php?id=137992" target="_blank" rel="noopener">Decreto nº 17.618/2025</a>.</p>`;
  const ab = document.getElementById("ab"), ar = document.getElementById("ar");
  const procura = () => {
    const q = ab.value.trim().toUpperCase().replace(/\s/g, "");
    if (!q) { ar.innerHTML = ""; return; }
    if (/^[\d.,]+$/.test(q)) {
      const v = parseFloat(q.includes(",") ? q.replace(/\./g, "").replace(",", ".") : q);
      const iguais = A.filter(a => Math.abs(a.iptu - v) < 0.01);
      ar.innerHTML = iguais.length ? `<p class="sub">${fmt(iguais.length)} ${iguais.length === 1 ? "área tem" : "áreas têm"} esse valor de m²:</p>` + iguais.slice(0, 12).map(a => linhaA(a, A.indexOf(a))).join("") : '<p class="sub">Nenhuma área com esse valor exato em 2025. Os valores de 2026 têm a correção da inflação; tente o código da área.</p>';
      return;
    }
    const i = A.findIndex(a => a.cod === q);
    if (i < 0) { const parc = A.filter(a => a.cod.startsWith(q)).slice(0, 8); ar.innerHTML = parc.length ? parc.map(a => linhaA(a, A.indexOf(a))).join("") : '<p class="sub">Código não encontrado. Confira no espelho do IPTU.</p>'; return; }
    const a = A[i];
    ar.innerHTML = `${linhaA(a, i)}<p>É a <b>${i + 1}ª</b> mais cara de ${fmt(A.length)} áreas. O m² dela vale ${a.iptu >= med ? `${(a.iptu / med).toLocaleString("pt-BR", {maximumFractionDigits: 1})} vezes o do meio da lista` : `${Math.round(100 * a.iptu / med)}% do valor do meio da lista`}.${DECRETO_17618[a.cod] ? ` Esta área estava no decreto revogado, que queria levar o m² para ${r2(DECRETO_17618[a.cod])}.` : ""}</p>`;
  };
  ab.oninput = procura;
  procura();
}

// ---------- Temas quentes: chuvas, empréstimos e hospitais ----------
const TEMAS_PREF = {};
async function temaPref(nome) {
  if (!(nome in TEMAS_PREF)) TEMAS_PREF[nome] = await fetch(`dados/prefeitura/${nome}.json`).then(r => r.ok ? r.json() : null).catch(() => null);
  return TEMAS_PREF[nome];
}
const pctTx = (a, b) => b ? `${Math.round(100 * a / b)}%` : "";
const atoLink = (D, a) => `<a href="${D.link_ato}${a.id}" target="_blank" rel="noopener">ver no Diário Oficial</a>`;
const barra2 = (pago, total) => `<span class="tp-barra" title="${pctTx(pago, total)} pago"><i style="width:${total ? Math.min(100, 100 * pago / total) : 0}%"></i></span>`;
const NOTA_EMPENHO = `<b>Empenhado</b> é o dinheiro que a Prefeitura reservou no orçamento para aquela despesa. <b>Pago</b> é o que já saiu do caixa. A diferença inclui obras e serviços que ainda vão ser feitos, então não quer dizer, sozinha, que há atraso.`;
const atasLink = (texto, mes) => `<a href="#/quente${mes ? "/" + mes : ""}">${texto}</a>`;

async function pgChuvas() {
  const D = await temaPref("chuvas");
  if (!D) { app.innerHTML = "<h1>O dinheiro das chuvas</h1><p>Os dados ainda não foram publicados. Volte mais tarde.</p>"; return; }
  const tot = D.categorias.reduce((s, c) => s + c.e, 0), pago = D.categorias.reduce((s, c) => s + c.p, 0);
  const mx = Math.max(...D.meses.map(m => m.e), 1);
  const formaTot = D.forma.reduce((s, f) => s + f.e, 0);
  app.innerHTML = `
    <h1>O dinheiro das chuvas</h1>
    <p class="sub">Quanto a Prefeitura reservou e gastou desde a situação de emergência de dezembro de 2025 e a calamidade de fevereiro de 2026: ajuda às famílias, limpeza, demolições em área de risco e obras de encostas e drenagem.</p>
    <div class="faixa-nums">
      <div><b>${reais(tot)}</b><span>empenhados (reservados) desde ${dataBR(D.desde)}</span></div>
      <div><b>${reais(pago)}</b><span>já pagos (${pctTx(pago, tot)})</span></div>
      <div><b>${reais(D.creditos_extraordinarios.total)}</b><span>em ${fmt(D.creditos_extraordinarios.n)} créditos extraordinários abertos por decreto desde dezembro de 2025</span></div>
    </div>
    <p class="sub">${NOTA_EMPENHO}</p>
    <h2>Em que o dinheiro foi usado</h2>
    ${D.categorias.map(c => `<div class="tp-linha"><div class="tp-tit"><b>${esc(c.nome)}</b><span>${reais(c.e)} empenhados · ${reais(c.p)} pagos · ${fmt(c.n)} empenhos</span></div>${barra2(c.p, c.e)}</div>`).join("")}
    ${(D.secretarias || []).length ? `<details class="tp-det"><summary>Por órgão da Prefeitura</summary>${D.secretarias.map(s => `<div class="linha"><span class="nm">${esc(secNome(s.nome))}</span><span class="vl">${reais(s.e)}<small class="sub"> · pago ${reais(s.p)}</small></span></div>`).join("")}</details>` : ""}
    ${D.pessoas_fisicas.n ? `<p class="sub">Inclui ${reais(D.pessoas_fisicas.e)} em auxílios pagos diretamente a pessoas (como o Auxílio Calamidade JF), mostrados só somados, sem nomes.</p>` : ""}
    <h2>Mês a mês</h2>
    <p class="sub">Pelo mês em que a despesa foi empenhada. A barra clara é o empenhado; a escura, o que desses empenhos já foi pago.</p>
    <div class="tp-meses">${D.meses.map(m => `<div class="tp-mes"><span class="tp-col" title="${reais(m.e)} empenhados, ${reais(m.p)} pagos"><i class="e" style="height:${100 * m.e / mx}%"></i><i class="p" style="height:${100 * m.p / mx}%"></i></span><small>${NOMES_MES[+m.m.slice(5) - 1]}<br>${m.m.slice(2, 4)}</small></div>`).join("")}</div>
    <h2>Como as empresas foram contratadas</h2>
    <p class="sub">Segundo o texto de cada empenho. Em calamidade, a lei permite contratar sem licitação para agir rápido, mas a contratação continua tendo de ser justificada e publicada.</p>
    ${D.forma.map(f => `<div class="tp-linha"><div class="tp-tit"><b>${esc(f.nome)}</b><span>${reais(f.e)} · ${fmt(f.n)} empenhos (${pctTx(f.e, formaTot)})</span></div>${barra2(f.e, formaTot)}</div>`).join("")}
    <h2>Empresas que mais receberam reservas</h2>
    <p class="sub">${fmt(D.n_fornecedores)} empresas no total. Toque para ver todos os gastos da empresa com a Prefeitura.</p>
    <table class="tab-equipe tp-tab"><thead><tr><th>Empresa</th><th>Empenhado</th><th>Pago</th></tr></thead><tbody>
      ${D.fornecedores.slice(0, 20).map(f => `<tr><td><a href="#/prefeitura/empresa/${D.dados_ate.slice(0, 4)}/${f.cnpj}">${esc(f.nome)}</a><small class="sub"> ${esc(f.cats.join(" e ").toLowerCase())}</small></td><td>${reais(f.e)}</td><td>${reais(f.p)}</td></tr>`).join("")}
    </tbody></table>
    <h2>As maiores despesas, uma a uma</h2>
    <div id="ch-itens"></div><button class="btn-ag sec at-mais" id="ch-mais" type="button">Mostrar mais</button>
    <h2>Linha do tempo no Diário Oficial</h2>
    ${D.marcos.filter(a => !/^ERRATA/i.test(a.x)).map(a => `<div class="ag-item fala"><div class="ag-tx"><small class="sub">${dataBR(a.d)} · ${esc(a.tipo)}</small><p>${esc(a.x)}</p><div class="ag-bt">${atoLink(D, a)}</div></div></div>`).join("")}
    <details class="tp-det"><summary>Os ${fmt(D.creditos_extraordinarios.n)} créditos extraordinários (${reais(D.creditos_extraordinarios.total)})</summary>
      <p class="sub">Crédito extraordinário é dinheiro que a prefeita coloca no orçamento por decreto, sem passar antes pela Câmara, permitido só para despesas urgentes e imprevisíveis, como uma calamidade.</p>
      ${D.creditos_extraordinarios.atos.map(a => `<div class="linha"><span class="nm">${dataBR(a.d)} · ${esc(a.x.split(" - ")[0].split(". ")[0])} ${atoLink(D, a)}</span><span class="vl">${a.v ? reais(a.v) : ""}</span></div>`).join("")}
    </details>
    <p>O que os vereadores disseram sobre as chuvas: ${atasLink("veja o Assunto do mês", "2026-03")}.</p>
    <p class="sub fonte-linha">Fontes: arquivos de despesas do ${fonteLink("Portal da Transparência da Prefeitura")} (dados até ${dataBR(D.dados_ate)}) e Diário Oficial do Município. Entram as despesas desde ${dataBR(D.desde)} do Fundo Municipal de Calamidade Pública e as que citam a calamidade, as chuvas, famílias desabrigadas ou áreas de risco no texto do empenho, além das obras de encostas e drenagem da Secretaria de Obras. A separação é feita por computador a partir desses textos e pode deixar de fora alguma despesa que não cite o motivo. Mostra o que foi reservado e pago, não se a obra ou o serviço foi bem feito: isso merece uma pergunta à Prefeitura.</p>`;
  let n = 0;
  const box = document.getElementById("ch-itens"), btn = document.getElementById("ch-mais");
  const mais = () => {
    box.insertAdjacentHTML("beforeend", D.itens.slice(n, n + 15).map(i => `<div class="alerta-card"><div class="ac-topo"><span class="ac-tipo">${esc(i.cat)} · ${dataBR(i.d)}</span><span class="ac-valor">${reais(i.e)}</span></div>
      <b class="ac-nome"><a href="#/prefeitura/empresa/${i.d.slice(0, 4)}/${i.cnpj}">${esc(i.cred)}</a></b><small class="sub">${esc(secNome(i.sec))} · pago até agora: ${reais(i.p)}${numEmp(i.num) ? " · empenho " + esc(numEmp(i.num)) : ""}</small>
      <p>${esc(i.h)}</p></div>`).join(""));
    n += 15; btn.style.display = n < D.itens.length ? "block" : "none";
  };
  btn.onclick = mais; mais();
}

async function pgEmprestimos() {
  const D = await temaPref("emprestimos");
  if (!D) { app.innerHTML = "<h1>Empréstimos da Prefeitura</h1><p>Os dados ainda não foram publicados. Volte mais tarde.</p>"; return; }
  const L = D.limite || {}, DV = D.divida || {};
  const bancos = r => /caixa|banco|bndes|bdmg|desenvolvimento/i.test(r.credor);
  const anoAtual = Object.keys(D.servico || {}).sort().pop();
  const tabServ = ano => {
    const linhas = (D.servico[ano] || []).filter(r => r.juros_p + r.amort_p > 0 || r.juros_e + r.amort_e > 0);
    const grupo = (tit, ls) => ls.length ? `<tr class="tp-grupo"><td colspan="3">${tit}</td></tr>` + ls.map(r => `<tr><td>${esc(r.credor === "Outros" ? "Credor não identificado no arquivo" : r.credor)}</td><td>${reais(r.juros_p)}</td><td>${reais(r.amort_p)}</td></tr>`).join("") : "";
    return `<table class="tab-equipe tp-tab"><thead><tr><th>A quem</th><th>Juros pagos</th><th>Amortização paga</th></tr></thead><tbody>
      ${grupo("Bancos (empréstimos)", linhas.filter(bancos))}${grupo("Parcelamentos e outras dívidas", linhas.filter(r => !bancos(r)))}</tbody></table>`;
  };
  const bancosAno = ano => (D.servico[ano] || []).filter(bancos).reduce((s, r) => s + r.juros_p + r.amort_p, 0);
  app.innerHTML = `
    <h1>Empréstimos da Prefeitura</h1>
    <p class="sub">Quanto a Prefeitura pegou emprestado, quanto a Câmara autorizou, quanto custa pagar e se está dentro do limite da lei.</p>
    <div class="faixa-nums">
      ${D.entradas.map(e => `<div><b>${reais(e.recebido)}</b><span>de empréstimos entraram em ${e.ano}${e.ate_mes < 12 ? ` (até ${NOMES_MES[e.ate_mes - 1]})` : ""}, de ${reais(e.previsto)} previstos no orçamento</span></div>`).join("")}
      ${anoAtual ? `<div><b>${reais(bancosAno(anoAtual))}</b><span>pagos aos bancos em ${anoAtual} (juros e amortização)</span></div>` : ""}
    </div>
    ${L.pct != null ? `<h2>Está dentro do limite?</h2>
    <div class="tp-linha"><div class="tp-tit"><b>${String(L.pct).replace(".", ",")}% da receita corrente líquida</b><span>em empréstimos contratados em ${L.ano} (até o ${L.quadrimestre}º quadrimestre). O limite do Senado é ${L.limite_pct}% por ano.</span></div>${barra2(L.pct, L.limite_pct)}</div>
    <p class="sub">Receita corrente líquida (RCL) é, de forma simples, quanto a Prefeitura arrecada para o dia a dia em 12 meses: ${reais(L.rcl)}.</p>` : ""}
    ${DV.dc != null ? `<p>A dívida consolidada da Prefeitura era de <b>${reais(DV.dc)}</b> no ${DV.quadrimestre}º quadrimestre de ${DV.ano}. Descontado o dinheiro em caixa, a dívida líquida ficou em <b>${reais(DV.dcl)}</b>${DV.dcl_pct != null ? ` (${String(DV.dcl_pct).replace(".", ",")}% da RCL; o limite legal para municípios é 120%)` : ""}.</p>` : ""}
    <h2>O que a Câmara autorizou</h2>
    <p class="sub">Todo empréstimo precisa de uma lei aprovada pela Câmara. Depois, um decreto define o valor e o banco, e o contrato é publicado. Os vereadores discutiram esses projetos nas reuniões: ${atasLink("veja o Assunto do mês", "2026-07")}.</p>
    ${D.leis.concat(D.contratos).sort((a, b) => a.d < b.d ? 1 : -1).map(a => `<div class="ag-item fala"><div class="ag-tx"><small class="sub">${dataBR(a.d)} · ${esc(a.tipo)}${a.v ? " · " + reais(a.v) : ""}</small><p>${esc(a.x)}</p><div class="ag-bt">${atoLink(D, a)}</div></div></div>`).join("")}
    <h2>Quanto custa pagar</h2>
    ${Object.keys(D.servico).sort().reverse().map(ano => `<h3>${ano}${ano === anoAtual ? " (até agora)" : ""}</h3>${tabServ(ano)}`).join("")}
    <p class="sub">Amortização é a parte que abate o valor emprestado; juros são o custo do empréstimo. Parcelamentos são dívidas antigas negociadas, como as com o fundo de previdência dos servidores (JF Previdência) e com a Receita Federal.</p>
    <p class="sub fonte-linha">Fontes: Tesouro Nacional (Siconfi), Relatório Resumido da Execução Orçamentária, Anexo 1, e Relatório de Gestão Fiscal, Anexos 2 e 4, enviados pela própria Prefeitura; Diário Oficial do Município; arquivos de despesas do ${fonteLink("Portal da Transparência")} (dados até ${dataBR(D.dados_ate)}). O Radar não consegue ligar cada real emprestado a cada obra, porque os arquivos públicos não trazem a fonte do dinheiro de cada despesa.</p>`;
}

async function pgHospitais(ano) {
  const D = await temaPref("hospitais");
  if (!D) { app.innerHTML = "<h1>Hospitais</h1><p>Os dados ainda não foram publicados. Volte mais tarde.</p>"; return; }
  const anos = Object.keys(D.anos).sort();
  ano = anos.includes(ano) ? ano : anos[anos.length - 1];
  const L = D.anos[ano], te = L.reduce((s, h) => s + h.e, 0), tp = L.reduce((s, h) => s + h.p, 0);
  const temL = L.some(h => h.l != null);
  app.innerHTML = `
    <h1>Quanto a Prefeitura paga aos hospitais</h1>
    <p class="sub">Os hospitais que atendem pelo SUS em Juiz de Fora recebem da Prefeitura pelo serviço prestado, com dinheiro do Ministério da Saúde, do Estado e do próprio Município.</p>
    <div class="anos">${anos.map(a => `<button class="${a === ano ? "on" : ""}" onclick="location.hash='#/prefeitura/hospitais/${a}'">${a}</button>`).join("")}</div>
    <div class="faixa-nums">
      <div><b>${reais(te)}</b><span>empenhados para ${fmt(L.length)} hospitais em ${ano}</span></div>
      <div><b>${reais(tp)}</b><span>já pagos (${pctTx(tp, te)})</span></div>
      <div><b>${reais(Math.max(0, te - tp))}</b><span>reservados e ainda não pagos</span></div>
    </div>
    <p class="sub">${NOTA_EMPENHO}${ano === anos[anos.length - 1] ? " O ano ainda não terminou, e parte do valor reservado é para meses que ainda vão chegar." : ""}${temL ? " Quando a Prefeitura informa, mostramos também o valor já liquidado (serviço prestado e conferido) que ainda não foi pago: esse é o sinal de conta em aberto." : ""}</p>
    ${L.map(h => `<div class="tp-linha"><div class="tp-tit"><b><a href="#/prefeitura/empresa/${ano}/${h.cnpj}">${esc(h.nome)}</a></b>
      <span>${reais(h.e)} empenhados · ${reais(h.p)} pagos (${pctTx(h.p, h.e)})${h.l != null && h.l - h.p > 1 ? ` · <b>${reais(h.l - h.p)} liquidados e não pagos</b>` : ""}</span></div>${barra2(h.p, h.e)}</div>`).join("")}
    <p class="sub">Às vezes o pago passa do empenhado no ano: são contas de anos anteriores pagas agora.</p>
    ${D.convenios.length ? `<h2>Contratos e convênios publicados</h2>
    <p class="sub">Os mais recentes no Diário Oficial envolvendo hospitais.</p>
    ${D.convenios.slice(0, 12).map(a => `<div class="ag-item fala"><div class="ag-tx"><small class="sub">${dataBR(a.d)} · ${esc(a.tipo)}</small><p>${esc(a.x)}</p><div class="ag-bt">${atoLink(D, a)}</div></div></div>`).join("")}` : ""}
    <p>Hospitais e o plano de saúde dos servidores estão entre os assuntos que mais voltam às reuniões da Câmara: ${atasLink("veja o Assunto do mês", "")}.</p>
    <p class="sub fonte-linha">Fontes: arquivos de despesas do ${fonteLink("Portal da Transparência da Prefeitura")} (dados até ${dataBR(D.dados_ate)}), despesas da área da Saúde com hospitais, santas casas, maternidades e institutos de tratamento; e Diário Oficial do Município. Um mesmo hospital pode aparecer duas vezes quando tem mais de um CNPJ.</p>`;
}

async function pgCreditos(ano) {
  const D = await temaPref("creditos");
  if (!D || !Object.keys(D.anos || {}).length) { app.innerHTML = "<h1>Orçamento que muda de lugar</h1><p>Os dados ainda não foram publicados. Volte mais tarde.</p>"; return; }
  const anos = Object.keys(D.anos).sort();
  ano = anos.includes(ano) ? ano : anos[anos.length - 1];
  const A = D.anos[ano], O = (D.orcamento || []).find(o => String(o.ano) === ano);
  const mx = Math.max(...A.meses.map(m => m[1]), 1);
  const comDest = A.conferidos > 0 && A.conferidos >= 0.5 * A.n;  // só mostra o "de onde/para onde" com a maioria dos decretos conferida
  const saldo = (A.orgaos || []).map(o => ({...o, s: o.ganhou - o.perdeu})).filter(o => Math.abs(o.s) > 1);
  const ganhou = saldo.filter(o => o.s > 0).sort((a, b) => b.s - a.s).slice(0, 10), perdeu = saldo.filter(o => o.s < 0).sort((a, b) => a.s - b.s).slice(0, 10);
  const mxS = Math.max(...saldo.map(o => Math.abs(o.s)), 1);
  const linhaS = o => `<div class="tp-linha"><div class="tp-tit"><b>${esc(o.orgao)}</b><span>${o.s > 0 ? "+" : "−"}${reais(Math.abs(o.s))}</span></div><span class="tp-barra${o.s < 0 ? " neg" : ""}"><i style="width:${100 * Math.abs(o.s) / mxS}%"></i></span></div>`;
  const tipoTx = {suplementar: "créditos suplementares", extraordinario: "créditos extraordinários", especial: "créditos especiais"};
  app.innerHTML = `
    <h1>Orçamento que muda de lugar</h1>
    <p class="sub">O orçamento é aprovado pela Câmara no fim do ano anterior, mas muda durante o ano. Por decreto, a prefeita coloca dinheiro em uma área e, quase sempre, tira de outra. A Lei do Orçamento já autoriza parte dessas mudanças; elas são legais, mas mostram como as prioridades mudam no caminho.</p>
    <div class="anos">${anos.map(a => `<button class="${a === ano ? "on" : ""}" onclick="location.hash='#/prefeitura/creditos/${a}'">${a}</button>`).join("")}</div>
    <div class="faixa-nums">
      <div><b>${reais(A.valor)}</b><span>mexidos por ${fmt(A.n)} decretos em ${ano}</span></div>
      ${O && O.total && O.total.ini ? `<div><b>${reais(O.total.ini)}</b><span>orçamento aprovado no início do ano</span></div>
      <div><b>${reais(O.total.atu)}</b><span>orçamento atualizado até ${NOMES_MES[O.ate_mes - 1]} (${O.total.atu >= O.total.ini ? "+" : "−"}${reais(Math.abs(O.total.atu - O.total.ini))})</span></div>` : ""}
    </div>
    <p class="sub">Os ${reais(A.valor)} somam tudo o que os decretos colocaram em alguma área. Como quase sempre o mesmo valor sai de outra área, o tamanho do orçamento muda bem menos: a diferença entre o aprovado e o atualizado é o que realmente entrou a mais.</p>
    <p>${Object.entries(A.por_tipo).map(([t, [n, v]]) => `<b>${fmt(n)}</b> ${tipoTx[t] || t} (${reais(v)})`).join(" · ")}</p>
    <p class="sub">Crédito suplementar reforça uma despesa que já existe no orçamento; crédito especial cria uma despesa nova (precisa de lei); crédito extraordinário é para urgência, como a calamidade das chuvas (veja ${`<a href="#/prefeitura/chuvas">o dinheiro das chuvas</a>`}).</p>
    ${O && O.areas && O.areas.length ? `<h2>Quais áreas ganharam e quais perderam</h2>
    <p class="sub">Orçamento aprovado x atualizado por área, segundo o relatório que a própria Prefeitura envia ao Tesouro Nacional (até ${NOMES_MES[O.ate_mes - 1]} de ${O.ano}).</p>
    <table class="tab-equipe tp-tab"><thead><tr><th>Área</th><th>Aprovado</th><th>Atualizado</th><th>Mudou</th></tr></thead><tbody>
      ${O.areas.filter(a => Math.abs(a.atu - a.ini) > 1).slice(0, 18).map(a => { const d = a.atu - a.ini; return `<tr><td>${esc(a.area)}</td><td>${reais(a.ini)}</td><td>${reais(a.atu)}</td><td class="${d >= 0 ? "pos" : "neg"}">${d >= 0 ? "+" : "−"}${reais(Math.abs(d))}${a.ini ? ` <small>(${d >= 0 ? "+" : "−"}${Math.round(Math.abs(100 * d / a.ini))}%)</small>` : ""}</td></tr>`; }).join("")}
    </tbody></table>` : ""}
    ${comDest ? `<h2>De onde saiu o dinheiro</h2>
    ${A.fontes.map(([f, v]) => `<div class="tp-linha"><div class="tp-tit"><b>${esc(f)}</b><span>${reais(v)}</span></div>${barra2(v, A.valor)}</div>`).join("")}
    <h2>Órgãos que mais receberam</h2><p class="sub">Saldo: o que o órgão recebeu menos o que perdeu nos decretos.</p>${ganhou.map(linhaS).join("") || '<p class="sub">Nenhum.</p>'}
    <h2>Órgãos que mais perderam</h2>${perdeu.map(linhaS).join("") || '<p class="sub">Nenhum.</p>'}
    <p class="sub">Baseado em ${fmt(A.conferidos)} de ${fmt(A.n)} decretos de ${ano}, os que o Radar já leu por inteiro e cujas contas batem com o valor do decreto. A fonte do dinheiro vem de ${fmt(A.lidos)} decretos lidos.</p>` :
    `<div class="info">O Radar está lendo o texto completo de cada decreto (${fmt(A.lidos || 0)} de ${fmt(A.n)} de ${ano} lidos até agora) para mostrar de onde o dinheiro saiu e para qual órgão foi. Essa parte aparece aqui quando a maioria estiver conferida.</div>`}
    <h2>Mês a mês</h2>
    <div class="tp-meses">${A.meses.map(([m, v]) => `<div class="tp-mes"><span class="tp-col" title="${reais(v)}"><i class="p" style="height:${100 * v / mx}%;left:15%;right:15%"></i></span><small>${NOMES_MES[+m - 1]}</small></div>`).join("")}</div>
    <h2>Os maiores decretos</h2>
    ${D.maiores.filter(x => x.d.startsWith(ano)).slice(0, 15).map(x => `<div class="alerta-card"><div class="ac-topo"><span class="ac-tipo">Decreto ${esc(x.num || "")} · ${dataBR(x.d)} · ${esc({suplementar: "crédito suplementar", extraordinario: "crédito extraordinário", especial: "crédito especial"}[x.tipo] || x.tipo)}</span><span class="ac-valor">${reais(x.v)}</span></div>
      ${x.para.length ? `<p><b>Para:</b> ${x.para.map(([n, v]) => `${esc(n)} (${reais(v)})`).join("; ")}</p>` : ""}
      ${x.de.length ? `<p><b>De:</b> ${x.de.map(([n, v]) => `${esc(n)} (${reais(v)})`).join("; ")}</p>` : ""}
      ${x.fontes && x.fontes.length ? `<small class="sub">Fonte do dinheiro: ${esc(x.fontes.join(", ").toLowerCase())}</small>` : ""}
      <div class="ag-bt"><a href="${D.link_ato}${x.id}" target="_blank" rel="noopener">ver no Diário Oficial</a></div></div>`).join("")}
    <p class="sub fonte-linha">Fontes: decretos publicados no Diário Oficial do Município (${fmt(D.decretos_lidos)} de ${fmt(D.decretos_total)} já lidos por inteiro) e Tesouro Nacional (Siconfi), Relatório Resumido da Execução Orçamentária, Anexo 2. Atualizado em ${esc(D.atualizado)}.</p>`;
}

async function pgAditivos(aba) {
  const D = await temaPref("aditivos");
  if (!D || !D.n) { app.innerHTML = "<h1>Aditivos de contratos</h1><p>Os dados ainda não foram publicados. Volte mais tarde.</p>"; return; }
  aba = ["muitos", "antigos", "quantidade"].includes(aba) ? aba : "muitos";
  const totTipos = D.tipos.reduce((s, [, n]) => s + n, 0);
  const anoAtual = new Date().getFullYear();
  const cartaoC = c => `<div class="alerta-card"><div class="ac-topo"><span class="ac-tipo">Contrato ${esc(c.contrato)} · assinado em ${c.ano} · ${esc(c.orgao)}</span><span class="ac-valor">${fmt(c.aditivos_total)}º aditivo</span></div>
    <b class="ac-nome">${esc(c.empresa || "Contratado não identificado no resumo")}</b>
    <small class="sub">${anoAtual - c.ano >= 2 ? `Contrato com ${anoAtual - c.ano} anos. ` : ""}Tipos de aditivo publicados desde ${dataBR(D.desde)}: ${c.tipos.map(t => t.toLowerCase()).join(", ")}.</small>
    ${c.atos.slice().reverse().slice(0, 3).map(a => `<p><small class="sub">${dataBR(a.d)}${a.seq ? ` · ${a.seq}º aditivo` : ""}${a.valor ? ` · ${reais(a.valor)}` : ""}</small><br>${esc(a.objeto || "")} <a href="${D.link_ato}${a.id}" target="_blank" rel="noopener">ver no Diário Oficial</a></p>`).join("")}</div>`;
  const abas = [["muitos", "Mais aditivos"], ["antigos", "Contratos mais antigos"], ["quantidade", "Acréscimos e supressões"]];
  app.innerHTML = `
    <h1>Aditivos de contratos</h1>
    <p class="sub">Depois de assinado, um contrato pode ser mudado por termos aditivos: prorrogar o prazo, reajustar o preço, aumentar ou diminuir a quantidade. Prorrogar serviços contínuos e aluguéis e reajustar pela inflação são permitidos. Acréscimos acima de 25% do valor (50% em reforma) são proibidos por lei, e contratos que se renovam por muitos anos merecem uma pergunta: não seria a hora de uma nova licitação?</p>
    <div class="faixa-nums">
      <div><b>${fmt(D.n)}</b><span>termos aditivos publicados desde ${dataBR(D.desde)}</span></div>
      <div><b>${fmt(D.n_contratos)}</b><span>contratos diferentes</span></div>
      <div><b>${fmt((D.tipos.find(t => t[0].startsWith("Acréscimo")) || [0, 0])[1])}</b><span>mudaram a quantidade contratada</span></div>
    </div>
    <h2>Que tipo de mudança</h2>
    ${D.tipos.map(([t, n]) => `<div class="tp-linha"><div class="tp-tit"><b>${esc(t)}</b><span>${fmt(n)} aditivos</span></div>${barra2(n, totTipos)}</div>`).join("")}
    <p class="sub">Um mesmo aditivo pode ter mais de um tipo, como prorrogação com reajuste.</p>
    <div class="chips lupa-abas">${abas.map(([k, t]) => `<a href="#/prefeitura/aditivos/${k}" class="${k === aba ? "on" : ""}">${t}</a>`).join("")}</div>
    ${aba === "muitos" ? `<p class="sub">Contratos com o maior número de aditivos (o número vem do próprio extrato: “/14” quer dizer 14º aditivo). Muitos são aluguéis de imóveis renovados ano a ano.</p>${D.mais_aditivados.map(cartaoC).join("")}` : ""}
    ${aba === "antigos" ? `<p class="sub">Contratos assinados há 5 anos ou mais que continuam recebendo aditivos.</p>${D.mais_antigos.map(cartaoC).join("")}` : ""}
    ${aba === "quantidade" ? `<p class="sub">Aditivos que aumentaram ou diminuíram a quantidade contratada. O percentual, quando informado, está no texto.</p>
      ${D.quantitativos.map(q => `<div class="alerta-card"><div class="ac-topo"><span class="ac-tipo">${dataBR(q.d)} · contrato ${esc(q.contrato)}${q.seq ? ` · ${q.seq}º aditivo` : ""} · ${esc(q.orgao)}</span><span class="ac-valor">${q.valor ? reais(q.valor) : ""}</span></div>
        <b class="ac-nome">${esc(q.empresa || "Contratado não identificado no resumo")}</b><p>${esc(q.objeto)}</p><div class="ag-bt"><a href="${D.link_ato}${q.id}" target="_blank" rel="noopener">ver no Diário Oficial</a></div></div>`).join("")}` : ""}
    ${D.por_empresa.length ? `<h2>Quem mais recebeu aditivos</h2>${D.por_empresa.slice(0, 12).map(([e, n]) => `<div class="linha"><span class="nm">${esc(e)}</span><span class="vl">${fmt(n)}</span></div>`).join("")}` : ""}
    <p class="sub fonte-linha">Fonte: extratos de termos aditivos publicados no Diário Oficial do Município de ${dataBR(D.desde)} a ${dataBR(D.ate)}. O Radar lê o resumo de cada extrato; o valor nem sempre aparece no resumo. Quem aluga imóvel para a Prefeitura como pessoa física aparece sem nome. Um aditivo é legal na maioria dos casos: a página mostra o que merece uma pergunta, não acusa ninguém.</p>`;
}


// ---------- Combustível da Prefeitura (scripts/prefeitura_combustivel.py, a partir dos empenhos oficiais) ----------
async function pgCombustivelPJF(anoArg) {
  const C = await fetch("dados/prefeitura/combustivel.json").then(r => r.ok ? r.json() : null).catch(() => null);
  if (!C || !C.anos) { app.innerHTML = `<h1>Combustível da Prefeitura</h1><p class="sub">Os dados não carregaram. Tente de novo em instantes.</p>`; return; }
  const anos = Object.keys(C.anos).sort().reverse();
  const ano = anos.includes(anoArg) ? anoArg : anos[0];
  const A = C.anos[ano];
  const brl = v => "R$ " + v.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const anoAtual = ano === String(new Date().getFullYear());
  const diesel = A.tipos.filter(t => t[0] === "diesel").reduce((s, t) => s + t[2], 0);
  const demlurb = (A.secretarias.find(x => /Limpeza Urbana/.test(x[0])) || [0, 0, 0])[2];
  const barras = (lista, iv, rot, sub) => { const mx = Math.max(...lista.map(x => Math.max(x[iv], 0)), 1); return lista.map(x => `
      <div class="tp-linha">
        <div class="tp-tit"><b>${rot(x)}</b><span>${brl(x[iv])}</span></div>
        <span class="tp-barra"><i style="width:${(100 * Math.max(x[iv], 0) / mx).toFixed(1)}%"></i></span>
        ${sub ? `<small class="sub">${sub(x)}</small>` : ""}
      </div>`).join(""); };
  app.innerHTML = `
    <h1>Combustível da Prefeitura</h1>
    <p class="sub">Quanto a Prefeitura de Juiz de Fora gasta comprando gasolina, etanol e diesel para os próprios carros, caminhões e máquinas, quem vende e para qual secretaria. Juntamos todos os empenhos de combustível dos arquivos oficiais de despesas.</p>
    <div class="filtros">${anos.map(a => `<a class="${a === ano ? "on" : ""}" href="#/prefeitura/combustivel/${a}">${a}${a === String(new Date().getFullYear()) ? " (até agora)" : ""}</a>`).join("")}</div>
    <div class="faixa-nums">
      <div><b>${reaisCurto(A.pago)}</b><span>pagos em combustível em ${ano}${anoAtual ? `, até ${dataBR(A.ate)}` : ""}</span></div>
      <div><b>${reaisCurto(A.empenhado)}</b><span>reservados (empenhados) para combustível em ${ano}</span></div>
      <div><b>${A.pago ? Math.round(100 * diesel / A.pago) : 0}%</b><span>do valor pago foi diesel${demlurb ? `; ${reaisCurto(demlurb)} só no Demlurb (Departamento Municipal de Limpeza Urbana)` : ""}</span></div>
    </div>
    <h2>Por tipo de combustível</h2>
    ${barras(A.tipos, 2, x => esc(x[0][0].toUpperCase() + x[0].slice(1)), x => `reservado: ${brl(x[1])}`)}
    <h2>Por secretaria</h2>
    ${barras(A.secretarias, 2, x => esc(x[0]), x => `reservado: ${brl(x[1])} · ${x[3]} ${x[3] > 1 ? "empenhos" : "empenho"}`)}
    <h2>Quem vende</h2>
    ${barras(A.fornecedores, 3, x => `<a href="#/prefeitura/empresa/${ano}/${esc(x[0])}">${esc(x[1])}</a>`, x => `CNPJ ${esc(x[0])} · reservado: ${brl(x[2])} · ${x[4]} ${x[4] > 1 ? "empenhos" : "empenho"}`)}
    <h2>Os maiores empenhos de ${ano}</h2>
    ${A.maiores.slice(0, 15).map(m => `
      <div class="tp-linha">
        <div class="tp-tit"><b>${esc(m[3])}</b><span>${brl(m[5])} pagos</span></div>
        <small class="sub">${esc(m[1])} · ${esc(m[7])}${m[8] ? " (o empenho inclui também lubrificante)" : ""} · empenho ${esc(m[6])} de ${dataBR(m[0])} · reservado: ${brl(m[4])} · <a href="#/prefeitura/busca/${ano}/${esc(m[6])}">conferir na busca</a></small>
      </div>`).join("")}
    <div class="info"><b>Como ler:</b> "reservado" (empenhado) é o dinheiro separado no orçamento para a compra; "pago" é o que já saiu do caixa. Os números são somados exatamente como estão no arquivo oficial, com reforços e anulações. Em alguns empenhos o pago aparece maior que o reservado no mesmo ano; é assim que o arquivo da Prefeitura registra, por isso mostramos os dois números. Entram as compras de combustível em distribuidoras e postos e o serviço de cartão de abastecimento da frota (empresa que gerencia os abastecimentos). <b>Não entram</b> os contratos de aluguel de carros, ônibus e caminhões nem os serviços de transporte contratados (como o transporte escolar), mesmo quando o combustível está incluído no preço. Por isso este número não é o custo total da frota. ${A.com_lubrificante ? `Em ${A.com_lubrificante} ${A.com_lubrificante > 1 ? "empenhos" : "empenho"} a distribuidora também vendeu lubrificante, e o arquivo não separa os valores.` : ""} Gastar mais combustível não é, sozinho, sinal de problema: o tamanho da frota e o tipo de serviço de cada secretaria são diferentes. Para conferir qualquer número, use o link "conferir na busca" ou procure o número do empenho no Portal da Transparência.</div>
    <p class="sub fonte-linha">Também dá para ver o <a href="#/combustivel">combustível dos vereadores</a>. Fonte: <a href="${FONTE_PREF}" target="_blank" rel="noopener">arquivos de despesas do Portal da Transparência de Juiz de Fora</a> (dados até ${dataBR(A.ate)}). Atualizado em ${esc(C.atualizado)}.</p>`;
}

// ---------- Coisas curiosas (lista curada à mão; cada número conferido nos empenhos do Portal da Transparência) ----------
// Para atualizar: confira os empenhos de novo antes de mudar qualquer valor.
const CURIOSAS = {
  dados_ate: "2026-11-06",
  itens: [
    {t: "Vigilância eletrônica do prédio do novo HPS, sem licitação", v: "valor não publicado", ic: "alerta",
     d: "A Prefeitura contratou sem licitação, por emergência (art. 75, inciso VIII, da Lei 14.133/2021), segurança eletrônica para a área do novo Hospital de Pronto Socorro, o antigo Hospital Regional: câmeras termográficas, videomonitoramento inteligente, central de monitoramento 24 horas e integração com a Guarda Municipal. O ato foi firmado em 12/11/2026 e publicado no Diário Oficial em 14/11. A vigilância do prédio era feita pelo Estado, que encerrou o contrato da empresa de segurança em setembro, segundo a Tribuna de Minas.",
     q: "Qual é o valor e o prazo do contrato? O ato publicado não informa. Se o Estado saiu em setembro, por que a contratação só saiu em novembro, e por emergência?",
     emp: "Dispensa 105/2026, processo eletrônico 9.918/2026", org: "Secretaria de Saúde", forn: "Torre Segurança Eletrônica e Monitoramento Ltda.",
     link: ["https://www.pjf.mg.gov.br/e_atos/e_atos_vis.php?id=147915", "ver o ato no Diário Oficial ›"]},
    {t: "Bonés para os agentes de trânsito", v: "R$ 134.277,80", ic: "pessoas",
     d: "Um único empenho de março de 2026, já pago, com a descrição \"boné branco (agentes)\". Em agosto há mais R$ 458 em bonés pretos para os técnicos.",
     q: "A descrição publicada fala só em bonés. Quantos foram comprados e por qual preço? O empenho inclui outras peças de uniforme?",
     emp: "2026NE00089, de 06/03/2026", org: "Secretaria de Transporte e Trânsito", forn: "Suporte Ind. e Com. de Artigos Militares Ltda.", busca: ["2026", "Suporte Ind e com de Art Militares"]},
    {t: "Kits lanche para os servidores do Demlurb", v: "R$ 3,77 milhões pagos", ic: "predios",
     d: "Pagos de janeiro de 2025 até novembro de 2026: R$ 1,94 milhão em 2025 e R$ 1,83 milhão em 2026. Parte disso, cerca de R$ 1,1 milhão, é de lanches de anos anteriores que só foram pagos depois (\"despesa de exercício anterior\"). Há ainda R$ 8,4 mil em lanches durante a calamidade das chuvas.",
     q: "Quantos kits são entregues por mês e a que preço? O serviço foi contratado por pregão eletrônico de 2023.",
     emp: "13 empenhos em 2025 e 2026 (por exemplo, 2025NE00058 e 2026NE00014)", org: "Demlurb", forn: "Padre Café Restaurante Ltda. ME", busca: ["2026", "Padre Cafe Restaurante"]},
    {t: "Fantasia do Zé Gotinha", v: "R$ 5.000,00", ic: "coracao",
     d: "Empenho de outubro de 2026 para uma fantasia do Zé Gotinha, o personagem das campanhas de vacinação, feita de espuma, fibra de vidro e lycra. Ainda não foi paga.",
     q: "Curiosidade pequena, mas mostra que até uma fantasia aparece nos gastos públicos.",
     emp: "2026NE04707, de 20/10/2026", org: "Secretaria de Saúde", forn: "Criativa Produtos Ltda.", busca: ["2026", "Criativa Produtos"]},
    {t: "Drones contra a dengue", v: "R$ 587 mil reservados", ic: "alerta",
     d: "Seis empenhos em 2026 para mapear focos do mosquito e aplicar larvicida com drones. Já foram pagos R$ 342 mil, incluindo R$ 149 mil de serviços de 2025. O contrato começou em agosto de 2025.",
     q: "Quantas áreas foram mapeadas e qual foi o resultado no número de casos?",
     emp: "6 empenhos em 2026 (por exemplo, 2026NE00712 e 2026NE04027)", org: "Secretaria de Saúde", forn: "Andrones Soluções Aéreas Ltda.", busca: ["2026", "Andrones Solucoes Aereas"]},
  ],
};
function pgCuriosas() {
  app.innerHTML = `
    <h1>Coisas curiosas</h1>
    <p class="sub">Gastos e contratações da Prefeitura que chamam a atenção. Não são irregularidades: são curiosidades que mostram como o dinheiro é usado no dia a dia. Cada informação foi conferida nos empenhos do Portal da Transparência (dados até ${dataBR(CURIOSAS.dados_ate)}) ou no Diário Oficial.</p>
    ${CURIOSAS.itens.map(x => `<div class="alerta-card">
      <div class="ac-topo"><span class="ac-tipo">${ic(x.ic)} ${esc(x.org)}</span><span class="ac-valor">${esc(x.v)}</span></div>
      <b class="ac-nome">${esc(x.t)}</b>
      <p>${esc(x.d)}</p>
      <p class="cu-perg"><b>Vale perguntar:</b> ${esc(x.q)}</p>
      <p><small class="sub">${x.link ? "Documento" : "Empenho"}: ${esc(x.emp)} · ${x.link ? "Contratada" : "Fornecedor"}: ${esc(x.forn)} · ${x.link ? `<a href="${esc(x.link[0])}" target="_blank" rel="noopener">${esc(x.link[1])}</a>` : `<a href="#/prefeitura/busca/${x.busca[0]}/${encodeURIComponent(x.busca[1])}">ver os lançamentos na busca de gastos ›</a>`}</small></p>
    </div>`).join("")}
    <div class="info">"Reservado" (empenhado) é o dinheiro separado para a despesa; "pago" é o que já saiu do caixa. Viu algo curioso nos gastos? Mande pelo botão do WhatsApp que a gente confere e pode entrar aqui.</div>`;
}

// ---------- Imóveis alugados pela Prefeitura (lista curada; valores conferidos nos empenhos do Portal da Transparência) ----------
// pago = pago em 2026 até a data dos dados, nos empenhos de aluguel daquele locador. Para atualizar, conferir de novo.
const ALUGUEIS_PJF = {
  dados_ate: "2026-11-06",
  hps: {mensal: 217460.73, mensal_antes: 208810.14, pago_2026: 1896592.44, atrasado_2025: 626430.42, locador: "Cotresa S/A", doc: "21.557.889/0001-82"},
  lista: [
    ["Esdeva (Associação Propagadora Esdeva)", "Av. Barão do Rio Branco, 3.520, Passos", "Secretaria de Turismo (endereço que a própria secretaria usa nos editais; o valor inclui parcelas de 2025 pagas em 2026)", 480000.00],
    ["Instituto Educacional Allan Kardec", "Rua Almirante Barroso, 155, Paineiras", "Escola Municipal Nilo Camilo Ayupe", 249329.22],
    ["Ribeiro & Arrabal Negócios Imobiliários", "dois imóveis", "CRAS Sul (Ipiranga) e Centro POP, para a população em situação de rua", 235304.92],
    ["Pattaya Gestão Imobiliária", "Rua Marechal Deodoro, 230, salas", "Plano de saúde dos servidores (PAS) e Cursos Populares para Concursos (CPC)", 180609.45],
    ["Aldeias Infantis SOS Brasil", "Av. Juiz de Fora, 667, Grama", "Escola Municipal Georg Rodenbach", 176096.50],
    ["Asa Gestão Patrimonial", "Rua Espírito Santo, 521, Centro", "Escolas Santa Catarina Labouré e Murilo Mendes, depois que a Defesa Civil interditou os prédios", 164000.00],
    ["Pirâmide Imobiliária", "Av. Brasil, 560, Centro", "Arquivo Histórico da Prefeitura e outros setores (inclui R$ 137,6 mil do aluguel de setembro a dezembro de 2025, pago em 2026, e IPTU)", 254209.54],
    ["Universal Imóveis", "dois imóveis, um na Rua Marechal Floriano Peixoto, 768/778", "CREAS Norte e CAPS II Leste", 112400.00],
    ["Dex Participações", "Costa Carvalho", "CRAS Sudeste", 101379.05],
    ["Dinda e Netos Sociedade Imobiliária", "Rua Gilberto de Alencar, 26, Centro", "CAPS III AD (álcool e drogas)", 95200.00],
    ["Farias Empresarial", "Rua Marechal Deodoro, 57, 2º e 3º andares", "Escola Municipal Adenilde Petrina Bispo (Santa Cândida)", 88220.00],
    ["Conselho Central Diocesano (SSVP)", "Rua Paulo Garcia, 627, Benfica", "Escola Municipal Maria das Dores Lizardo", 78146.40],
    ["B2M Participações", "Rua Carlos Chagas, 57, São Mateus", "CAPS IJ (atendimento psicossocial infantojuvenil)", 73728.00],
    ["S Caetano Construtora", "Rua Dom Pedro II, 222, Mariano Procópio", "CAEE Centro (atendimento educacional especializado)", 64838.87],
    ["Cap Participações", "Linhares", "CRAS Leste", 56640.00],
    ["Líder Negócios Imobiliários", "Av. Presidente Itamar Franco, 982, Centro", "Farmácia Central (abastecimento de medicamentos)", 56600.35],
    ["Martins Oliveira Imobiliária", "Rua Marília, 303, Benfica", "Casa de Leitura Delfina Fonseca Lima", 38414.85],
    ["Almar Imóveis", "Rua Porto das Flores, 276, Santa Luzia", "Secretaria de Desenvolvimento Urbano (Sedupp)", 32320.72],
    ["Fábrica de Tecidos São João Evangelista", "Rua Coronel Assis, 15, Floresta", "Escola Municipal Carolina de Assis", 31726.26],
    ["Igreja Batista do Ipiranga", "Rua Capitão Antônio Carias, 36, Ipiranga", "Anexo da Escola Municipal Jardim de Alá", 28574.70],
    ["Mitra Arquidiocesana de Juiz de Fora", "Rua Raulina Magalhães, 40, Grajaú", "Escola Municipal Antônio Faustino", 27166.67],
    ["Centauro Administração de Imóveis", "Rua Abílio Gomes, 33, Francisco Bernardino", "Regional Nordeste de fiscalização da Sedupp", 26408.82],
    ["DDJ Participações", "Linhares", "CRAS Leste (parcelas de 2025 pagas em 2026)", 21328.00],
    ["Instituto Jesus", "Rua Inácio Gama, 813, Nossa Senhora de Lourdes", "UBS do bairro de Lourdes", 17618.65],
    ["R. A. Arbex Gestão Imobiliária", "Av. Sete de Setembro, 768, Costa Carvalho", "Secretaria de Segurança Pública", 11269.54],
    ["HGD Empreendimentos Imobiliários", "Av. Barão do Rio Branco, 2.390, salas 1801 a 1808", "JFPREV (previdência dos servidores)", 10000.00],
    ["Construtora Vankur", "Rua José Lourenço Kelmer, 1.300, sala 203, São Pedro", "Sedupp", 6000.00],
    ["Big Ben Administração de Imóveis", "Av. Presidente Itamar Franco, 996, Centro", "Procon (Agência de Proteção e Defesa do Consumidor)", 3000.00],
  ],
};
function pgAlugueisPJF() {
  const A = ALUGUEIS_PJF, H = A.hps;
  const brl = v => "R$ " + v.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const tot = A.lista.reduce((s, x) => s + x[3], 0) + H.pago_2026 + H.atrasado_2025;
  const mx = Math.max(...A.lista.map(x => x[3]));
  app.innerHTML = `
    <h1>Imóveis alugados pela Prefeitura</h1>
    <p class="sub">Prédios e salas que a Prefeitura aluga para escolas, postos de saúde, CRAS, CAPS e secretarias, com o valor pago em 2026 (até ${dataBR(A.dados_ate)}). Cada valor foi conferido nos empenhos do Portal da Transparência. Não inclui o aluguel social pago às famílias.</p>
    <div class="faixa-nums">
      <div><b>${reaisCurto(tot)}</b><span>pagos em aluguel de imóveis em 2026 nos imóveis desta lista</span></div>
      <div><b>${A.lista.length + 1}</b><span>locadores diferentes</span></div>
      <div><b>${brl(H.mensal)}</b><span>é o aluguel de um único prédio: o do HPS</span></div>
    </div>
    <div class="alerta-card">
      <div class="ac-topo"><span class="ac-tipo">Secretaria de Saúde · dispensa de licitação 125/2022</span><span class="ac-valor">${brl(H.mensal)}/mês</span></div>
      <b class="ac-nome">Hospital de Pronto Socorro (HPS) Dr. Mozart Geraldo Teixeira</b>
      <p>O prédio onde funcionam o HPS e o Departamento de Internação Domiciliar é alugado da empresa ${esc(H.locador)} (CNPJ ${esc(H.doc)}). Desde agosto de 2026, com o reajuste feito na prorrogação do contrato, o aluguel é de ${brl(H.mensal)} por mês (antes eram ${brl(H.mensal_antes)}), cerca de ${reaisCurto(H.mensal * 12)} por ano. É, de longe, o maior aluguel da Prefeitura.</p>
      <div class="nb-conta">
        <div><small>Aluguéis de 2026 já pagos</small><b>${brl(H.pago_2026)}</b></div>
        <div><small>Três parcelas de 2025 pagas só em 2026</small><b>${brl(H.atrasado_2025)}</b></div>
        <div><small>Total pago em 2026</small><b>${brl(H.pago_2026 + H.atrasado_2025)}</b></div>
      </div>
      <p class="cu-perg"><b>Vale perguntar:</b> há quantos anos o HPS funciona em prédio alugado? Quanto custaria ter um prédio próprio? Por que parcelas de 2025 só foram pagas em 2026?</p>
      <p><small class="sub"><a href="#/prefeitura/busca/2026/Cotresa">Ver os pagamentos à Cotresa na busca de gastos ›</a></small></p>
    </div>
    <h2>Os outros imóveis alugados</h2>
    ${A.lista.slice().sort((a, b) => b[3] - a[3]).map(([loc, end, uso, v]) => `
      <div class="tp-linha">
        <div class="tp-tit"><b>${esc(uso)}</b><span>${brl(v)}</span></div>
        <span class="tp-barra"><i style="width:${(100 * v / mx).toFixed(1)}%"></i></span>
        <small class="sub">${esc(end)} · locador: <a href="#/prefeitura/busca/2026/${encodeURIComponent(loc.split(" (")[0])}">${esc(loc)}</a></small>
      </div>`).join("")}
    <div class="info"><b>Lei da placa:</b> desde setembro de 2026, uma lei municipal proposta pela vereadora Roberta Lopes e sancionada pela prefeita obriga os imóveis alugados pela Prefeitura a exibir na entrada o valor mensal do aluguel, o dono ou a imobiliária, a vigência do contrato e o que funciona no local. <a href="https://www.acessa.com/cidade/2026/09/340757-juiz-de-fora-passa-a-exigir-valor-da-locacao-na-porta-de-predios-publicos.html" target="_blank" rel="noopener">Notícia no Acessa.com</a>. Passou por um desses prédios? Veja se a placa está lá.</div>
    <div class="info"><b>Como ler:</b> os valores são o que foi pago em 2026 até ${dataBR(A.dados_ate)}, e alguns incluem parcelas atrasadas de 2025. Alugar imóvel para serviço público é permitido e muitas vezes necessário, como quando a Defesa Civil interdita uma escola. Alguns empenhos de aluguel aparecem no Portal sem o nome do locador e ficaram fora desta lista. Desde 18/11/2026 o site da Prefeitura recusa o acesso do nosso robô, por isso os dados param em ${dataBR(A.dados_ate)}.</div>`;
}

// ---------- Previdência dos servidores (JFPREV): multas, juros e parcelamentos (conferido nos empenhos) ----------
const PREV_JF = {
  dados_ate: "2026-11-06",
  memorando: {multa: 6163166.22, juros: 4889345.97},
  atraso26: [
    {t: "Multa pelo atraso no repasse do Imposto de Renda de setembro a dezembro e do 13º de 2025", v: 1812652.48, emp: "2026NE00717"},
    {t: "Correção pelo mesmo atraso", v: 184901.72, emp: "2026NE00718"},
    {t: "Multa pelo atraso no repasse do Imposto de Renda de junho de 2026", v: 196429.57, emp: "2026NE01042"},
  ],
  parcel: {p2025: 18181910.60, p2026: 43493784.90},
};
function pgPrevidencia() {
  const P = PREV_JF, brl = v => "R$ " + v.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const mem = P.memorando.multa + P.memorando.juros, a26 = P.atraso26.reduce((s, x) => s + x.v, 0);
  app.innerHTML = `
    <h1>A conta da previdência dos servidores</h1>
    <p class="sub">O JFPREV é o instituto que paga as aposentadorias e pensões dos servidores municipais. A Prefeitura precisa repassar a ele, todo mês, a sua contribuição e o Imposto de Renda descontado dos aposentados. Quando o repasse atrasa ou fica abaixo do devido, vêm multa, juros e parcelamento. Todos os números abaixo foram conferidos nas notas de empenho do Portal da Transparência (dados até ${dataBR(P.dados_ate)}).</p>
    <div class="faixa-nums">
      <div><b>${reaisCurto(mem + a26)}</b><span>pagos ao JFPREV só em multas, juros e correção desde 2025</span></div>
      <div><b>${reaisCurto(P.parcel.p2025 + P.parcel.p2026)}</b><span>pagos em parcelas de dívidas antigas com o JFPREV em 2025 e 2026</span></div>
      <div><b>R$ 135 milhões</b><span>em débitos parcelados em 60 meses no fim de 2025</span></div>
    </div>
    <div class="alerta-card">
      <div class="ac-topo"><span class="ac-tipo">${ic("alerta")} Secretaria de Recursos Humanos · março de 2025</span><span class="ac-valor">${brl(mem)}</span></div>
      <b class="ac-nome">Multas e juros pagos ao JFPREV em 2025</b>
      <p>Quatro empenhos de março de 2025, citando o Memorando 3180/2025, foram feitos "para pagamento de multa" e "para pagamento de juros" ao JFPREV. Todos já foram pagos.</p>
      <div class="nb-conta">
        <div><small>Multas (2025NE00125 e 2025NE00128)</small><b>${brl(P.memorando.multa)}</b></div>
        <div><small>Juros (2025NE00126 e 2025NE00129)</small><b>${brl(P.memorando.juros)}</b></div>
        <div><small>Total</small><b>${brl(mem)}</b></div>
      </div>
      <p class="cu-perg"><b>Vale perguntar:</b> as notas não dizem a que se referem as multas. De quais meses eram os repasses e por que atrasaram? O que diz o Memorando 3180/2025?</p>
      <p><small class="sub"><a href="#/prefeitura/busca/2025/Juiz%20de%20Fora%20Previdencia">Ver os lançamentos de 2025 na busca de gastos ›</a></small></p>
    </div>
    <div class="alerta-card">
      <div class="ac-topo"><span class="ac-tipo">${ic("alerta")} Secretaria da Fazenda · 2026</span><span class="ac-valor">${brl(a26)}</span></div>
      <b class="ac-nome">Em 2026, multas com o motivo escrito: atraso</b>
      <p>Nestas notas a própria Prefeitura escreveu o motivo: atraso no repasse do Imposto de Renda retido dos aposentados e pensionistas, que pertence ao JFPREV.</p>
      ${P.atraso26.map(x => `<div class="tp-linha"><div class="tp-tit"><b>${esc(x.t)}</b><span>${brl(x.v)}</span></div><small class="sub">Empenho ${esc(x.emp)}, já pago</small></div>`).join("")}
      <p class="cu-perg"><b>Vale perguntar:</b> mesmo depois do parcelamento de dezembro de 2025, o repasse de junho de 2026 também atrasou. Os repasses de 2026 estão em dia agora?</p>
      <p><small class="sub"><a href="#/prefeitura/busca/2026/Juiz%20de%20Fora%20Previdencia">Ver os lançamentos de 2026 na busca de gastos ›</a></small></p>
    </div>
    <h2>Os parcelamentos</h2>
    <p>A Prefeitura já pagava um parcelamento antigo de débitos com o JFPREV, que as próprias notas explicam como "devido a repasses de recursos insuficientes": a parcela principal é de ${brl(1637079.23)} por mês, mais juros e correção. Em dezembro de 2025 a Câmara aprovou um novo parcelamento, ratificado pela Lei 15.267/2025, com quatro termos (0862, 0865, 0866 e 0867/2025).</p>
    <div class="nb-conta">
      <div><small>Pago em parcelamentos em 2025</small><b>${brl(P.parcel.p2025)}</b></div>
      <div><small>Pago em parcelamentos em 2026 (até ${dataBR(P.dados_ate)})</small><b>${brl(P.parcel.p2026)}</b></div>
    </div>
    <p>Segundo o diretor-presidente do JFPREV, em entrevista à Tribuna de Minas, o novo parcelamento soma cerca de R$ 135 milhões, em 60 parcelas de cerca de R$ 2,25 milhões corrigidas pelo IPCA mais juros. Entram nele a contribuição suplementar de maio a agosto de 2025 (R$ 61 milhões), o aporte para o déficit de junho a agosto de 2025 (R$ 12,4 milhões), o Imposto de Renda dos aposentados não repassado de junho a dezembro de 2024 e de maio a agosto de 2025 (R$ 52,7 milhões) e repasses de 2022 e 2023 previstos na Lei da Transação (R$ 8,8 milhões). <a href="https://tribunademinas.com.br/noticias/politica/12-12-2025/jfprev-explica-deficit-atuarial-e-debitos-que-serao-parcelados-pela-prefeitura.html" target="_blank" rel="noopener">Matéria da Tribuna de Minas</a>.</p>
    <div class="info"><b>Na Câmara:</b> em outubro de 2025 o plenário aprovou o Pedido de Informação 309/2025, que pede à Prefeitura os empenhos e pagamentos das contribuições ao JFPREV de 2022 a 2025, mês a mês e por secretaria, citando atrasos sobretudo na Educação e na Saúde. <a href="https://www.camarajf.mg.gov.br/sal/mostrapfs.php?n=153758" target="_blank" rel="noopener">Ver o pedido</a>.</div>
    <div class="info"><b>Como ler:</b> multa, juros e correção são dinheiro público que sai da Prefeitura e entra no próprio instituto de previdência do Município; não é dinheiro que some, mas é dinheiro que poderia ir para outras áreas se os repasses estivessem em dia. Os parcelamentos pagam dívidas reconhecidas e são legais. A Prefeitura pode explicar cada caso. Desde 18/11/2026 o site da Prefeitura recusa o acesso do nosso robô, por isso os dados param em ${dataBR(P.dados_ate)}.</div>`;
}

// ---------- Investimentos: previsto x feito (Siconfi, RREO Anexo 1, linha Investimentos) ----------
const OBRAS_PREV = {
  anos: [
    {ano: "2024", ini: 235.06, atu: 419.07, emp: 272.85, liq: 247.26, pago: 243.64, obs: "ano fechado"},
    {ano: "2025", ini: 408.02, atu: 590.73, emp: 301.76, liq: 283.49, pago: 278.87, obs: "ano fechado"},
    {ano: "2026", ini: 734.15, atu: 784.39, emp: 419.21, liq: 159.57, pago: 155.92, obs: "só até agosto"},
  ],
};
function pgObrasPrevistas() {
  const M = v => "R$ " + v.toLocaleString("pt-BR", {minimumFractionDigits: 1, maximumFractionDigits: 1}) + " mi";
  const pc = (a, b) => Math.round(100 * a / b) + "%";
  const A = OBRAS_PREV.anos, a25 = A[1];
  app.innerHTML = `
    <h1>Obras e investimentos: previsto x feito</h1>
    <p class="sub">"Investimentos" é a parte do orçamento para obras, reformas, compra de equipamentos e veículos. Comparamos o que a Prefeitura previu no orçamento com o que de fato foi feito, pelos relatórios oficiais que ela mesma envia ao Tesouro Nacional (Siconfi, Relatório Resumido da Execução Orçamentária).</p>
    <div class="faixa-nums">
      <div><b>${pc(a25.liq, a25.atu)}</b><span>do orçamento de investimentos de 2025 virou obra ou compra entregue (liquidada)</span></div>
      <div><b>${M(a25.atu - a25.liq)}</b><span>previstos para investimentos em 2025 que não foram executados no ano</span></div>
      <div><b>${M(A[2].ini)}</b><span>previstos para 2026, quase o dobro de 2025</span></div>
    </div>
    ${A.map(x => `<div class="alerta-card">
      <div class="ac-topo"><span class="ac-tipo">${x.ano} · ${x.obs}</span><span class="ac-valor">${pc(x.liq, x.atu)} feito</span></div>
      <div class="tp-linha"><div class="tp-tit"><b>Previsto (orçamento atualizado)</b><span>${M(x.atu)}</span></div><span class="tp-barra"><i style="width:100%"></i></span></div>
      <div class="tp-linha"><div class="tp-tit"><b>Contratado (empenhado)</b><span>${M(x.emp)}</span></div><span class="tp-barra"><i style="width:${(100 * x.emp / x.atu).toFixed(1)}%"></i></span></div>
      <div class="tp-linha"><div class="tp-tit"><b>Entregue (liquidado)</b><span>${M(x.liq)}</span></div><span class="tp-barra"><i style="width:${(100 * x.liq / x.atu).toFixed(1)}%"></i></span></div>
      <small class="sub">Orçamento aprovado no início do ano: ${M(x.ini)} · pago: ${M(x.pago)}</small>
    </div>`).join("")}
    <p class="cu-perg"><b>Vale perguntar:</b> quais obras previstas em 2025 ficaram para depois? Com só ${pc(A[2].liq, A[2].atu)} entregue até agosto, o orçamento de ${M(A[2].ini)} para 2026 é realista?</p>
    <div class="info"><b>Como ler:</b> o orçamento costuma crescer durante o ano com créditos adicionais, e o que não é feito em um ano pode virar "resto a pagar" no seguinte; no fim de 2025 o saldo total de restos a pagar da Prefeitura (todas as despesas) era de R$ 40,6 milhões. Obra que atrasa nem sempre é culpa da Prefeitura: há licitações que fracassam, chuvas e recursos de convênio que demoram. 2026 tem só até agosto (o relatório de setembro e outubro ainda não foi publicado). Fonte: <a href="https://siconfi.tesouro.gov.br/" target="_blank" rel="noopener">Siconfi, Tesouro Nacional</a>, RREO, Anexo 1, linha Investimentos.</div>`;
}
