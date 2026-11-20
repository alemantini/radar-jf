import requests, json, unicodedata, re
def sa(s): return unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()
C="18338178000102"; API="https://pncp.gov.br/api"
for mod in (8,9,6):
  for p in range(1,6):
    r=requests.get(f"{API}/consulta/v1/contratacoes/publicacao",params=dict(dataInicial="20260901",dataFinal="20261120",codigoModalidadeContratacao=mod,cnpj=C,pagina=p,tamanhoPagina=50),timeout=90)
    if r.status_code!=200: print("st",mod,p,r.status_code); break
    d=r.json(); 
    for c in d.get("data",[]):
        t=sa(c.get("objetoCompra"))
        if re.search(r"hps|pronto socorro|seguranca eletronica|vigilancia",t):
            print("@",json.dumps({k:c.get(k) for k in ["numeroCompra","anoCompra","sequencialCompra","processo","objetoCompra","valorTotalEstimado","valorTotalHomologado","dataPublicacaoPncp","dataAberturaProposta","amparoLegal","modalidadeNome","situacaoCompraNome","informacaoComplementar","linkSistemaOrigem"]},ensure_ascii=False))
            it=requests.get(f"{API}/pncp/v1/orgaos/{C}/compras/{c['anoCompra']}/{c['sequencialCompra']}/itens",params=dict(pagina=1,tamanhoPagina=50),timeout=90).json()
            for i in it or []:
                print("  item",i.get("numeroItem"),i.get("descricao","")[:400],"| qtd",i.get("quantidade"),i.get("unidadeMedida"),"| unit",i.get("valorUnitarioEstimado"),"| total",i.get("valorTotal"))
                try:
                    res=requests.get(f"{API}/pncp/v1/orgaos/{C}/compras/{c['anoCompra']}/{c['sequencialCompra']}/itens/{i['numeroItem']}/resultados",timeout=90).json()
                    for x in res or []: print("   res",x.get("niFornecedor"),x.get("nomeRazaoSocialFornecedor"),x.get("valorUnitarioHomologado"),x.get("valorTotalHomologado"),x.get("dataResultado"))
                except Exception as e: print("   res erro",e)
            arqs=requests.get(f"{API}/pncp/v1/orgaos/{C}/compras/{c['anoCompra']}/{c['sequencialCompra']}/arquivos",timeout=90).json()
            for a in arqs or []: print("   arq",a.get("titulo"),a.get("url"))
    if not d.get("paginasRestantes"): break
for p in range(1,4):
    r=requests.get(f"{API}/consulta/v1/contratos",params=dict(dataInicial="20261001",dataFinal="20261120",cnpjOrgao=C,pagina=p,tamanhoPagina=100),timeout=90)
    if r.status_code!=200: print("ct",r.status_code); break
    d=r.json()
    for k in d.get("data",[]):
        if re.search(r"hps|pronto socorro|seguranca eletronica",sa(k.get("objetoContrato"))):
            print("CT",json.dumps({x:k.get(x) for x in ["numeroContratoEmpenho","niFornecedor","nomeRazaoSocialFornecedor","objetoContrato","valorInicial","valorGlobal","valorParcela","numeroParcelas","dataAssinatura","dataVigenciaInicio","dataVigenciaFim","processo"]},ensure_ascii=False))
    if not d.get("paginasRestantes"): break
