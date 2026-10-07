"""Testes da validação do config.yaml (T1 a T8 da spec)."""

import copy
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from src.config import CAMINHO_PADRAO, ErroDeConfiguracao, carregar_config, validar_dados

RAIZ = Path(__file__).resolve().parent.parent
BASE = yaml.safe_load(CAMINHO_PADRAO.read_text(encoding="utf-8"))


def _erros(dados) -> list[str]:
    """Valida e devolve a lista de mensagens de erro (falha o teste se não houver erro)."""
    with pytest.raises(ErroDeConfiguracao) as exc:
        validar_dados(dados, raiz=RAIZ)
    return exc.value.erros


def _alterar(caminho: str, valor):
    """Copia a config padrão e troca um campo. Ex.: _alterar('aparencia.cor_primaria', 'azul')."""
    dados = copy.deepcopy(BASE)
    *pais, ultimo = caminho.split(".")
    alvo = dados
    for parte in pais:
        alvo = alvo[parte]
    alvo[ultimo] = valor
    return dados


def test_t1_config_do_repositorio_e_valida():
    config = carregar_config()
    assert config.assistente.nome == "Professor de Dados & IA"
    assert [p.nome for p in config.ia.provedores] == ["openrouter", "anthropic", "openai"]


@pytest.mark.parametrize("cor", ["#12345G", "azul", "#FFF", "0B3D91", ""])
def test_t2_cor_invalida(cor):
    erros = _erros(_alterar("aparencia.cor_primaria", cor))
    assert len(erros) == 1
    assert erros[0].startswith("aparencia.cor_primaria:")
    assert "#RRGGBB" in erros[0]


@pytest.mark.parametrize("campo", ["assistente.nome", "assistente.descricao", "comportamento.instrucoes"])
@pytest.mark.parametrize("vazio", ["", "   "])
def test_t3_campo_obrigatorio_vazio(campo, vazio):
    erros = _erros(_alterar(campo, vazio))
    assert erros == [f"{campo}: está vazio. Preencha com um texto"]


def test_t3_campo_obrigatorio_ausente():
    dados = copy.deepcopy(BASE)
    del dados["assistente"]["nome"]
    assert _erros(dados) == ["assistente.nome: campo obrigatório não encontrado. Adicione este campo ao config.yaml"]


def test_t4_logo_inexistente():
    erros = _erros(_alterar("aparencia.logo", "assets/nao-existe.png"))
    assert erros[0].startswith("aparencia.logo:") and "não existe" in erros[0]


def test_t4_logo_fora_do_projeto_ou_formato_errado():
    assert "fora do projeto" in _erros(_alterar("aparencia.logo", "../../etc/passwd.png"))[0]
    assert "não é uma imagem" in _erros(_alterar("aparencia.logo", "config.yaml"))[0]


def test_t5_provedor_desconhecido():
    dados = _alterar("ia.provedores", [{"nome": "gemini", "modelo": "gemini-pro"}])
    erros = _erros(dados)
    assert erros[0].startswith("ia.provedores[1].nome:")
    assert "openrouter, anthropic, openai" in erros[0]


def test_t5_provedor_repetido():
    dados = _alterar("ia.provedores", [{"nome": "openai", "modelo": "a"}, {"nome": "openai", "modelo": "b"}])
    assert "aparece mais de uma vez" in _erros(dados)[0]


def test_t5_lista_de_provedores_vazia():
    assert _erros(_alterar("ia.provedores", []))[0].startswith("ia.provedores:")


def test_t5_modelo_vazio():
    dados = _alterar("ia.provedores", [{"nome": "anthropic", "modelo": ""}])
    assert _erros(dados) == ["ia.provedores[1].modelo: está vazio. Preencha com um texto"]


@pytest.mark.parametrize("exemplos", [[], [f"pergunta {i}" for i in range(7)]])
def test_t6_quantidade_de_exemplos(exemplos):
    assert _erros(_alterar("exemplos", exemplos))[0].startswith("exemplos:")


@pytest.mark.parametrize("campo,valor", [
    ("ia.max_tokens", 63), ("ia.max_tokens", 8193),
    ("ia.max_caracteres_pergunta", 99), ("ia.max_caracteres_pergunta", 10001),
    ("aparencia.logo_altura_px", 10), ("aparencia.logo_altura_px", 301),
])
def test_t6_numeros_fora_do_limite(campo, valor):
    erros = _erros(_alterar(campo, valor))
    assert erros[0].startswith(f"{campo}:") and "fora do permitido" in erros[0]


@pytest.mark.parametrize("campo,valor", [("ia.max_tokens", 64), ("ia.max_tokens", 8192),
                                         ("ia.max_caracteres_pergunta", 100), ("ia.max_caracteres_pergunta", 10000)])
def test_t6_numeros_no_limite_sao_aceitos(campo, valor):
    validar_dados(_alterar(campo, valor), raiz=RAIZ)


def test_t7_varios_erros_aparecem_juntos():
    dados = _alterar("aparencia.cor_primaria", "azul")
    dados["assistente"]["nome"] = ""
    dados["ia"]["max_tokens"] = 99999
    dados["exemplos"] = []
    campos = [e.split(":")[0] for e in _erros(dados)]
    assert set(campos) == {"aparencia.cor_primaria", "assistente.nome", "ia.max_tokens", "exemplos"}


@pytest.mark.parametrize("campo", ["api_key", "OPENAI_API_KEY", "secret", "hf_token", "token", "senha"])
def test_t8_campo_de_chave_e_proibido(campo):
    dados = copy.deepcopy(BASE)
    dados["ia"][campo] = "qualquer-coisa"
    assert any("NÃO podem ficar no config.yaml" in e for e in _erros(dados))


def test_t8_valor_com_cara_de_chave_e_proibido():
    chave_falsa = "sk-ant-" + "x" * 30
    erros = _erros(_alterar("assistente.descricao", f"minha chave {chave_falsa}"))
    assert any("parece uma chave de API" in e for e in erros)
    assert all(chave_falsa not in e for e in erros), "a mensagem nunca deve repetir a chave"


def test_campo_com_nome_errado_vira_erro():
    dados = copy.deepcopy(BASE)
    dados["aparencia"]["cor_primária"] = dados["aparencia"].pop("cor_primaria")
    campos = [e.split(":")[0] for e in _erros(dados)]
    assert "aparencia.cor_primária" in campos and "aparencia.cor_primaria" in campos


def test_yaml_mal_formatado_indica_a_linha(tmp_path):
    arquivo = tmp_path / "config.yaml"
    arquivo.write_text("assistente:\n  nome: \"ok\"\n   descricao: errado\n", encoding="utf-8")
    with pytest.raises(ErroDeConfiguracao) as exc:
        carregar_config(arquivo)
    assert "linha 3" in exc.value.erros[0]


def test_script_de_validacao_codigo_de_saida(tmp_path):
    script = RAIZ / "scripts" / "validar_config.py"
    ok = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert ok.returncode == 0 and "✅" in ok.stdout

    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "logo.svg").write_text("<svg/>", encoding="utf-8")
    ruim = copy.deepcopy(BASE)
    ruim["aparencia"]["cor_primaria"] = "#12345G"
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(ruim, allow_unicode=True), encoding="utf-8")
    falha = subprocess.run([sys.executable, str(script), str(tmp_path / "config.yaml")], capture_output=True, text=True)
    assert falha.returncode == 1
    assert "aparencia.cor_primaria" in falha.stdout and "❌" in falha.stdout
