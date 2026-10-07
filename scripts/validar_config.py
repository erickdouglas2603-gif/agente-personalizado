"""Confere o config.yaml e explica, em português, o que corrigir.

Como usar (na pasta do projeto):
    python scripts/validar_config.py              # valida o config.yaml
    python scripts/validar_config.py outro.yaml   # valida outro arquivo

Sai com código 0 se estiver tudo certo e 1 se houver erro
(é isso que faz o GitHub Actions parar a publicação).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CAMINHO_PADRAO, ErroDeConfiguracao, carregar_config  # noqa: E402


def _resumo_github(texto: str) -> None:
    """No GitHub Actions, escreve também no resumo da execução (Job summary)."""
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as arquivo:
            arquivo.write(texto + "\n")


def main(argumentos: list[str]) -> int:
    caminho = Path(argumentos[0]) if argumentos else CAMINHO_PADRAO
    try:
        config = carregar_config(caminho)
    except ErroDeConfiguracao as exc:
        titulo = f"❌ {caminho.name} tem {len(exc.erros)} problema(s). Corrija e salve de novo:"
        print(titulo)
        for erro in exc.erros:
            print(f"   • {erro}")
        _resumo_github(f"### {titulo}\n" + "\n".join(f"- {e}" for e in exc.erros))
        return 1

    provedores = " → ".join(f"{p.nome} ({p.modelo})" for p in config.ia.provedores)
    mensagem = f'✅ {caminho.name} está correto. Assistente: "{config.assistente.nome}". Provedores: {provedores}'
    print(mensagem)
    _resumo_github(f"### {mensagem}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
