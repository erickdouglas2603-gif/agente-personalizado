"""Leitura e validação do config.yaml.

Uso:
    from src.config import carregar_config
    config = carregar_config()          # lê o config.yaml da raiz do projeto

Se houver erros, levanta ErroDeConfiguracao com TODOS os problemas encontrados,
cada um em português, dizendo o campo, o problema e como corrigir.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_PADRAO = RAIZ_PROJETO / "config.yaml"

PROVEDORES_ACEITOS = ("openrouter", "anthropic", "openai")
EXTENSOES_LOGO = (".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif")

_COR = re.compile(r"^#[0-9A-Fa-f]{6}$")
# Nomes de campo que sugerem uma chave/segredo (max_tokens NÃO casa aqui).
_CAMPO_SEGREDO = re.compile(r"(api[_-]?key|apikey|secret|senha|password|^token$|_token$|^chave)", re.IGNORECASE)
# Valores com cara de chave de API (OpenAI/OpenRouter/Anthropic/Hugging Face).
_VALOR_SEGREDO = re.compile(r"\b(sk-[A-Za-z0-9_-]{16,}|hf_[A-Za-z0-9]{16,})")


class ErroDeConfiguracao(Exception):
    """A configuração tem um ou mais problemas. `erros` traz a lista de mensagens."""

    def __init__(self, erros: list[str]):
        self.erros = erros
        super().__init__("\n".join(erros))


# --------------------------------------------------------------------------
# Modelo da configuração (espelha o config.yaml)
# --------------------------------------------------------------------------

class _Base(BaseModel):
    # forbid: campo com nome errado vira erro (em vez de ser ignorado em silêncio)
    # str_strip_whitespace: "   " conta como vazio
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)


class Assistente(_Base):
    nome: str = Field(min_length=1)
    descricao: str = Field(min_length=1)


class Aparencia(_Base):
    cor_primaria: str
    cor_secundaria: str
    logo: str = Field(min_length=1)
    logo_altura_px: int = Field(ge=24, le=300)

    @field_validator("cor_primaria", "cor_secundaria")
    @classmethod
    def _cor_valida(cls, valor: str) -> str:
        if not _COR.match(valor):
            raise ValueError(f'"{valor}" não é uma cor válida. Use o formato #RRGGBB, por exemplo #0B3D91')
        return valor.upper()

    @field_validator("logo")
    @classmethod
    def _logo_existe(cls, valor: str, info: ValidationInfo) -> str:
        raiz = Path((info.context or {}).get("raiz", RAIZ_PROJETO)).resolve()
        arquivo = (raiz / valor).resolve()
        if raiz not in arquivo.parents:
            raise ValueError(f'"{valor}" aponta para fora do projeto. Coloque a logo dentro da pasta assets/')
        if arquivo.suffix.lower() not in EXTENSOES_LOGO:
            raise ValueError(f'"{valor}" não é uma imagem aceita. Use um destes formatos: {", ".join(EXTENSOES_LOGO)}')
        if not arquivo.is_file():
            raise ValueError(f'o arquivo "{valor}" não existe. Envie a imagem para o repositório ou corrija o caminho')
        return valor


class Provedor(_Base):
    nome: Literal["openrouter", "anthropic", "openai"]
    modelo: str = Field(min_length=1)


class IA(_Base):
    max_tokens: int = Field(ge=64, le=8192)
    max_caracteres_pergunta: int = Field(ge=100, le=10000)
    provedores: list[Provedor] = Field(min_length=1)

    @field_validator("provedores")
    @classmethod
    def _sem_repetidos(cls, provedores: list[Provedor]) -> list[Provedor]:
        nomes = [p.nome for p in provedores]
        repetidos = sorted({n for n in nomes if nomes.count(n) > 1})
        if repetidos:
            raise ValueError(f"o provedor {', '.join(repetidos)} aparece mais de uma vez. Deixe só uma entrada para cada")
        return provedores


class Comportamento(_Base):
    instrucoes: str = Field(min_length=1)


class Config(_Base):
    assistente: Assistente
    aparencia: Aparencia
    ia: IA
    comportamento: Comportamento
    exemplos: list[str] = Field(min_length=1, max_length=6)

    @field_validator("exemplos")
    @classmethod
    def _exemplos_preenchidos(cls, exemplos: list[str]) -> list[str]:
        vazios = [str(i) for i, texto in enumerate(exemplos, start=1) if not texto]
        if vazios:
            raise ValueError(f"o(s) exemplo(s) {', '.join(vazios)} está(ão) vazio(s). Escreva a pergunta ou apague a linha")
        return exemplos


# --------------------------------------------------------------------------
# Tradução dos erros para português
# --------------------------------------------------------------------------

def _caminho(loc: tuple) -> str:
    """('ia', 'provedores', 0, 'nome') -> 'ia.provedores[1].nome' (contagem a partir de 1)."""
    texto = ""
    for parte in loc:
        if isinstance(parte, int):
            texto += f"[{parte + 1}]"
        else:
            texto += f".{parte}" if texto else str(parte)
    return texto or "(arquivo inteiro)"


def _traduzir(erro: dict) -> str:
    tipo, ctx, valor = erro["type"], erro.get("ctx", {}), erro.get("input")
    if tipo == "value_error":
        return str(ctx.get("error", erro["msg"]))
    if tipo == "missing":
        return "campo obrigatório não encontrado. Adicione este campo ao config.yaml"
    if tipo == "extra_forbidden":
        return "campo desconhecido. Confira se o nome está escrito certo (sem acento e com _ no lugar de espaço) ou apague-o"
    if tipo == "string_too_short":
        return "está vazio. Preencha com um texto"
    if tipo in ("string_type",):
        return "deveria ser um texto. Coloque o valor entre aspas"
    if tipo in ("int_parsing", "int_type", "int_from_float"):
        return f'"{valor}" não é um número inteiro. Use só algarismos, por exemplo 1024'
    if tipo in ("greater_than_equal", "less_than_equal"):
        return f"o valor {valor} está fora do permitido. Use um número entre {_limites(erro)}"
    if tipo == "literal_error":
        return f'provedor desconhecido "{valor}". Use um destes: {", ".join(PROVEDORES_ACEITOS)}'
    if tipo == "too_short":
        return f"a lista precisa ter pelo menos {ctx.get('min_length')} item(ns)"
    if tipo == "too_long":
        return f"a lista pode ter no máximo {ctx.get('max_length')} itens (hoje tem {ctx.get('actual_length')}). Apague alguns"
    if tipo in ("list_type",):
        return "deveria ser uma lista. Escreva um item por linha, começando com '- '"
    if tipo in ("model_type", "dict_type"):
        return "deveria ser um grupo de campos (com os campos indentados abaixo dele)"
    return erro["msg"]


_LIMITES = {
    "logo_altura_px": "24 e 300",
    "max_tokens": "64 e 8192",
    "max_caracteres_pergunta": "100 e 10000",
}


def _limites(erro: dict) -> str:
    return _LIMITES.get(str(erro["loc"][-1]), "os limites indicados")


# --------------------------------------------------------------------------
# Proteção contra chaves no config.yaml (RF4)
# --------------------------------------------------------------------------

def _procurar_segredos(dado: Any, loc: tuple = ()) -> list[str]:
    erros = []
    if isinstance(dado, dict):
        for chave, valor in dado.items():
            sub = loc + (str(chave),)
            if _CAMPO_SEGREDO.search(str(chave)):
                erros.append(f"{_caminho(sub)}: chaves de API e segredos NÃO podem ficar no config.yaml. "
                             "Apague este campo e cadastre a chave nos Secrets do Space no Hugging Face")
            else:
                erros += _procurar_segredos(valor, sub)
    elif isinstance(dado, list):
        for i, item in enumerate(dado):
            erros += _procurar_segredos(item, loc + (i,))
    elif isinstance(dado, str) and _VALOR_SEGREDO.search(dado):
        erros.append(f"{_caminho(loc)}: este texto parece uma chave de API. Apague-a daqui, "
                     "REVOGUE a chave no site do provedor e cadastre uma nova só nos Secrets do Space")
    return erros


# --------------------------------------------------------------------------
# Função principal
# --------------------------------------------------------------------------

def validar_dados(dados: Any, raiz: Path = RAIZ_PROJETO) -> Config:
    """Valida um dicionário já lido do YAML. Levanta ErroDeConfiguracao com todos os erros."""
    if not isinstance(dados, dict):
        raise ErroDeConfiguracao(["config.yaml: o arquivo está vazio ou não tem o formato esperado "
                                  "(grupos como 'assistente:', 'aparencia:', 'ia:'...)"])
    erros = _procurar_segredos(dados)
    try:
        config = Config.model_validate(dados, context={"raiz": raiz})
    except ValidationError as exc:
        ja_avisados = {e.split(":")[0] for e in erros}  # campos de segredo já têm mensagem própria
        erros += [f"{_caminho(e['loc'])}: {_traduzir(e)}" for e in exc.errors()
                  if not (e["type"] == "extra_forbidden" and _caminho(e["loc"]) in ja_avisados)]
        config = None
    if erros:
        raise ErroDeConfiguracao(erros)
    return config


def carregar_config(caminho: Path | str = CAMINHO_PADRAO) -> Config:
    """Lê e valida o config.yaml. A pasta do arquivo é usada como raiz para achar a logo."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroDeConfiguracao([f"{caminho.name}: arquivo não encontrado em {caminho.parent}"])
    try:
        dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        marca = getattr(exc, "problem_mark", None)
        onde = f" (linha {marca.line + 1}, coluna {marca.column + 1})" if marca else ""
        raise ErroDeConfiguracao([
            f"{caminho.name}{onde}: o arquivo tem um erro de formato YAML. Confira a indentação "
            "(2 espaços, nunca TAB) e coloque textos com ':' ou '#' entre aspas"
        ]) from exc
    return validar_dados(dados, raiz=caminho.parent)
