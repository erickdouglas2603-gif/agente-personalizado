---
title: Professor de Dados & IA
emoji: 🎓
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 6.29.1
python_version: "3.10"
app_file: app.py
pinned: false
short_description: Tire dúvidas de engenharia de dados e IA
---

# Professor de Dados & IA

Chat com Inteligência Artificial que tira dúvidas sobre **engenharia de dados e IA**, de forma didática.

- **App no ar:** https://huggingface.co/spaces/Erickdds/agente-personalizado
- **Spec do projeto:** [`SPEC-parte1-cicd-deploy.md`](SPEC-parte1-cicd-deploy.md)

> O bloco entre `---` no topo deste arquivo é lido pelo Hugging Face para montar o Space.
> Não apague nem mude a indentação dele.

## Como personalizar

Edite só o arquivo [`config.yaml`](config.yaml), pelo próprio site do GitHub (ícone de lápis ✏️).
Lá você muda nome, descrição, cores, logo, provedores de IA, tamanho das respostas,
instruções de comportamento e perguntas de exemplo.

## Chaves de API

O app funciona com **qualquer uma** destas chaves (não precisa das três):

| Provedor   | Nome do secret        |
|------------|-----------------------|
| OpenRouter | `OPENROUTER_API_KEY`  |
| Anthropic  | `ANTHROPIC_API_KEY`   |
| OpenAI     | `OPENAI_API_KEY`      |

Cadastre-as **somente** em *Settings → Variables and secrets* do Space.
**Nunca** coloque chaves no código ou no `config.yaml`.

## Estrutura de pastas

```
config.yaml           ← o único arquivo que você edita
assets/logo.svg       ← logo exibida no topo
src/                  ← código do app (configuração, provedores, interface)
scripts/              ← scripts de apoio (ex.: validar a configuração)
tests/                ← testes automáticos (rodam sem chaves reais)
requirements.txt      ← dependências do app no Space
requirements-dev.txt  ← dependências extras para testar no computador
```

## Rodar os testes no computador

```bash
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
```
