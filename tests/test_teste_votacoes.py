import sys, pathlib, pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from teste_votacoes import montar

EXEC = {
    "projetos": [{"msg": "4.711/2025", "titulo": "t", "votos": [
        {"data": "2025-05-01", "ata": 1, "disc": "1ª discussão", "res": "aprovado", "contra": [13], "abst": [], "texto": ""},
        {"data": "2025-05-02", "ata": 2, "disc": "2ª discussão", "res": "aprovado", "contra": [13, 42], "abst": [7], "texto": ""}]}],
    "vetos": [{"data": "2025-06-01", "ata": 3, "projeto": "PL 65/2025", "res": "mantido", "derrubar": [44], "manter": [25], "texto": ""}],
}

def p(**k):
    base = {"id": "x", "pergunta": "?", "explica": "e", "disc": None, "sim_e": "aprovar"}
    base.update(k); return base

def test_executivo_contra_vai_para_nao():
    r = montar([p(fonte="executivo", ref="4.711/2025")], EXEC)["perguntas"][0]
    assert r["nao"] == [13, 42] and r["sim"] == [] and r["so_contra_nomeado"] is True and r["ata"] == 2

def test_disc_escolhida():
    r = montar([p(fonte="executivo", ref="4.711/2025", disc="1ª discussão")], EXEC)["perguntas"][0]
    assert r["nao"] == [13] and r["ata"] == 1

def test_veto_derrubar_vai_para_sim():
    r = montar([p(fonte="veto", ref="PL 65/2025", sim_e="derrubar")], EXEC)["perguntas"][0]
    assert r["sim"] == [44] and r["nao"] == [25] and r["so_contra_nomeado"] is False

def test_manual_usa_listas():
    r = montar([p(fonte="manual", ref="PL 195/2025", sim=[44], nao=[25,4], data="2026-11-19", resultado="rejeitado")], EXEC)["perguntas"][0]
    assert r["sim"] == [44] and r["nao"] == [4, 25] and r["ata"] is None

def test_ref_inexistente_falha():
    with pytest.raises(SystemExit) as e:
        montar([p(id="zz", fonte="executivo", ref="9.999/2025")], EXEC)
    assert "zz" in str(e.value)

def test_abstencao_nao_entra():
    r = montar([p(fonte="executivo", ref="4.711/2025")], EXEC)["perguntas"][0]
    assert 7 not in r["sim"] + r["nao"]
