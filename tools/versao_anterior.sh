#!/usr/bin/env bash
# Baixa a última versão publicada do site (artefato github-pages de uma execução
# anterior) para $ANT, procurando a mais recente que tenha os gastos da Prefeitura.
# Assim os passos de "reaproveitar" não dependem do endereço público do site.
set -u
ANT=${ANT:-/tmp/anterior}
mkdir -p "$ANT"
ids=$(gh api "repos/$GITHUB_REPOSITORY/actions/artifacts?name=github-pages&per_page=30" \
  --jq '.artifacts[] | select(.expired|not) | .id')
for id in $ids; do
  rm -rf /tmp/art && mkdir -p /tmp/art
  gh api "repos/$GITHUB_REPOSITORY/actions/artifacts/$id/zip" > /tmp/art/a.zip 2>/dev/null || continue
  (cd /tmp/art && unzip -q -o a.zip && mkdir -p x && tar -xf artifact.tar -C x) 2>/dev/null || continue
  if [ -s /tmp/art/x/dados/prefeitura/empenhos_2026.json ]; then
    rm -rf "$ANT" && mv /tmp/art/x "$ANT"
    echo "versão anterior: artefato $id"
    exit 0
  fi
done
echo "nenhuma versão anterior completa encontrada"
