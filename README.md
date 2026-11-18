# Radar JF

O que cada vereador de Juiz de Fora apresentou na Câmara Municipal, só com dados oficiais e link para cada documento.

- Fonte: sistema iS@l da Câmara Municipal de Juiz de Fora (https://www.camarajf.mg.gov.br/sal/).
- Um robô (GitHub Actions) coleta tudo de novo toda madrugada. Se a coleta vier incompleta ou estranha, o site não é republicado e continua com a última versão boa.
- O robô se identifica e coleta devagar, para não pesar no servidor da Câmara.

## Como funciona

1. `scripts/coletar.py` baixa proposições (por ano e tipo), a lista de vereadores e a data de cada proposição (aos poucos, com cache em `data/cache/datas.json`).
2. `scripts/processar.py` classifica as propostas em grupos com a mesma regra para todos, identifica rua, bairro e tipo de pedido, e cruza pedidos repetidos.
3. `scripts/camara_atas.py` baixa e lê as atas das reuniões e audiências públicas (workflow "Atas da Câmara", todo dia; texto completo guardado em `data/cache/atas/`, um arquivo por ano). A carga completa é feita uma vez pelo botão "Run workflow" com início 1 e fim 6000.
4. `site/` é o site estático publicado no GitHub Pages.

## Correções

Achou um erro? Abra uma issue neste repositório.
