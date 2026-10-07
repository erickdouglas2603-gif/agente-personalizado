"""Testes da tarefa 1: o esqueleto do projeto está completo e bem formado."""

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent


def _cabecalho_readme() -> dict:
    texto = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert texto.startswith("---\n"), "README.md precisa começar com o cabeçalho '---' do Space"
    bloco = texto.split("---\n")[1]
    return yaml.safe_load(bloco)


def test_arquivos_e_pastas_existem():
    for caminho in ["config.yaml", "assets/logo.svg", "requirements.txt",
                    "requirements-dev.txt", "README.md", ".gitignore", "src", "tests", "scripts"]:
        assert (RAIZ / caminho).exists(), f"Faltando: {caminho}"


def test_config_yaml_e_lido_sem_erro():
    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    assert config["assistente"]["nome"]
    assert [p["nome"] for p in config["ia"]["provedores"]] == ["openrouter", "anthropic", "openai"]


def test_logo_do_config_existe():
    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    assert (RAIZ / config["aparencia"]["logo"]).is_file()


def test_cabecalho_do_space_no_readme():  # T22
    cabecalho = _cabecalho_readme()
    assert cabecalho["sdk"] == "gradio"
    assert cabecalho["app_file"] == "app.py"
    assert cabecalho["sdk_version"], "fixe a versão do Gradio"
    assert cabecalho["python_version"], "fixe a versão do Python"
    assert len(cabecalho["short_description"]) <= 60, "short_description aceita até 60 caracteres"


def test_gitignore_protege_arquivos_de_segredo():
    assert ".env" in (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
