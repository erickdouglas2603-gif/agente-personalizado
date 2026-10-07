# SPEC — Parte 1: assistente de IA no ar com CI/CD e deploy automático

> Documento no formato *spec-driven*: primeiro descrevemos **o que** o sistema deve fazer e **como vamos verificar**, depois implementamos **uma tarefa de cada vez**.
> Baseado em `IDEIA-parte1.md`. Escrito para quem está começando: termos técnicos vêm explicados na primeira vez que aparecem.

**Status:** rascunho para aprovação
**Decisões já tomadas com o autor:**

| Tema | Decisão |
|---|---|
| Provedores e ordem | 1º OpenRouter → 2º Anthropic → 3º OpenAI |
| Modelos | OpenRouter: `google/gemma-4-31b-it:free` · Anthropic: `claude-haiku-4-5` (opção mais caprichada: `claude-sonnet-5-5`) · OpenAI: `gpt-5-mini` (confirmar que aparece na sua conta) |
| Tamanho máximo da resposta | 1024 tokens (mais ou menos uma página) |
| Hardware do Space | **ZeroGPU** (ver restrições na seção 2.3) |
| Space no Hugging Face | Usuário `Erickdds`, Space `agente-personalizado` → `HF_SPACE_ID = Erickdds/agente-personalizado` (guardado como variável do GitHub, não no código). Página: https://huggingface.co/spaces/Erickdds/agente-personalizado · Link direto do app: https://erickdds-agente-personalizado.hf.space |
| Pendentes (usaremos o padrão abaixo até você dizer outra coisa) | Nome/descrição/cores/logo → padrões da seção 1. Ferramentas → Python + Gradio + pytest + gitleaks. Deploy a partir da branch `main`. |

---

## 1. Objetivo, público e escopo

### 1.1 Objetivo
Publicar na internet, de graça e com um link público, um **chat com IA** que tira dúvidas sobre **engenharia de dados e Inteligência Artificial**, respondendo de forma didática, como um professor.

### 1.2 Público
- **Usuários do chat:** alunos iniciantes e intermediários, falantes de português. Não precisam de conta.
- **Dono do projeto (você):** quer personalizar tudo por **um único arquivo de configuração**, editado pelo site do GitHub, sem instalar nada.

### 1.3 Identidade padrão (pode trocar depois no arquivo de configuração)
- **Nome:** "Professor de Dados & IA"
- **Descrição:** "Tire suas dúvidas sobre engenharia de dados e Inteligência Artificial"
- **Cores:** `#0B3D91` (azul-escuro) e `#6A1B9A` (roxo), em gradiente no fundo
- **Logo:** `assets/logo.svg`, um logo simples criado na implementação, com altura de 80 px

### 1.4 O que entra na Parte 1
- Chat em português, com respostas aparecendo aos poucos (*streaming*, ou seja, o texto chega em pedaços enquanto a IA escreve).
- Três provedores de IA (OpenRouter, Anthropic e OpenAI), com **troca automática** se um falhar.
- Um arquivo `config.yaml` para nome, descrição, cores, logo, provedores e modelos, tamanho das respostas, instruções de comportamento e perguntas de exemplo.
- **Validação automática** da configuração antes de publicar.
- **Bloqueio** da publicação se houver chave de API no código.
- **Deploy automático** (publicação) no Hugging Face Spaces a cada alteração na branch `main`, usando GitHub Actions.
- Testes automáticos que **não gastam crédito** (usam provedores simulados).

### 1.5 O que fica para depois
| Parte 2 | Parte 3 | Fora do projeto por enquanto |
|---|---|---|
| Base de conhecimento com os seus documentos (RAG, isto é, a IA consulta seus PDFs e textos antes de responder) | Site próprio, com domínio próprio e visual feito do zero | Login de usuários · conversas salvas · painel de estatísticas · cobrança |

---

## 2. Stack escolhida e restrições conhecidas

### 2.1 Stack (as ferramentas usadas)
| Peça | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3.10 | É a versão aceita pela ZeroGPU (ver 2.3) e tem as bibliotecas oficiais dos provedores |
| Interface do chat | Gradio (`gr.ChatInterface`) | É o padrão do Hugging Face Spaces e o único SDK aceito pela ZeroGPU |
| Arquivo de configuração | `config.yaml` (formato YAML: texto simples, fácil de editar no GitHub) | Legível por iniciantes |
| Validação da configuração | Pydantic, que confere tipos e campos obrigatórios e gera mensagens de erro claras | Diz exatamente qual campo está errado |
| Testes | pytest | Padrão do Python |
| Detecção de chaves vazadas | gitleaks | Ferramenta gratuita que procura padrões de chaves no código |
| CI/CD | GitHub Actions | Já vem no GitHub e é gratuito para repositórios públicos |
| Publicação | Hugging Face Spaces, enviado com a ferramenta oficial `huggingface_hub` (`hf upload`) | Grátis e com link público |

### 2.2 As três chaves de API e a troca automática
O app aceita **três tipos de chave**. Basta **uma**, não é preciso ter as três.

| Provedor | Nome do secret | Biblioteca (SDK) usada | Detalhe |
|---|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` | `openai` | Cliente criado com `base_url="https://openrouter.ai/api/v1"` |
| Anthropic | `ANTHROPIC_API_KEY` | `anthropic` (oficial) | API *Messages* |
| OpenAI | `OPENAI_API_KEY` | `openai` (oficial) | API *Chat Completions* |

**Como funciona a troca automática (*fallback*):**
1. O app lê a lista de provedores do `config.yaml`, **na ordem que você escreveu**.
2. Ignora os provedores que **não têm chave** cadastrada nos secrets.
3. Envia a pergunta ao primeiro provedor disponível.
4. Se ele **falhar antes de começar a responder** (limite de uso, sem crédito, chave inválida, modelo inexistente, fora do ar, tempo esgotado ou resposta vazia), guarda o motivo e **tenta o próximo**.
5. Se **todos** falharem, mostra no chat uma mensagem em português com o motivo de cada um.
6. Se um provedor falhar **no meio** da resposta, o texto já recebido continua na tela e o app acrescenta um aviso. Não trocamos de provedor nesse ponto, para não misturar duas respostas diferentes.

**Segurança das chaves:** elas ficam **somente** em *Settings → Variables and secrets* do Space no Hugging Face. Nunca no código, nunca no GitHub e nunca no `config.yaml`.

### 2.3 Restrições conhecidas do Hugging Face Spaces (e da ZeroGPU)
| Restrição | O que significa para nós |
|---|---|
| **ZeroGPU exige conta PRO** (paga, cerca de US$ 9/mês) ou uma organização Team/Enterprise | Sem PRO, a opção ZeroGPU não aparece. Alternativa gratuita: *CPU basic*. O código vai funcionar nos dois |
| **ZeroGPU só funciona com o SDK Gradio** (não aceita Docker nem Streamlit) | Por isso escolhemos Gradio |
| **ZeroGPU exige pelo menos uma função marcada com `@spaces.GPU`**; sem ela, o Space pode dar erro ao iniciar | O app terá uma função mínima com esse marcador. Se o pacote `spaces` não existir (no seu computador ou em CPU), o app segue sem ele |
| **A GPU não acelera nada neste projeto** | Os modelos rodam nos servidores do OpenRouter, da Anthropic e da OpenAI, e o Space só repassa a pergunta. A ZeroGPU passa a fazer sentido na Parte 2, se rodarmos modelos de *embeddings* localmente |
| **Versões de Python e Gradio suportadas pela ZeroGPU são limitadas** | Fixamos `python_version` e `sdk_version` no cabeçalho do `README.md` com versões aceitas |
| **O Space "dorme" depois de um tempo sem visitas** (em planos gratuitos) | A primeira visita depois disso demora alguns segundos para "acordar". É normal |
| **Os secrets do Space não vão junto com o código** | Precisam ser cadastrados à mão, uma vez (seção 7) |
| **Arquivos binários grandes (mais de 10 MB) precisam de Git LFS** | Mantemos a logo pequena (SVG ou PNG com menos de 1 MB) |
| **O cabeçalho YAML do `README.md` controla o Space** (SDK, versão, arquivo principal) | Um erro nesse cabeçalho impede o build, então ele também é validado |
| **Se o build falhar no Hugging Face, o Space pode ficar fora do ar** | Por isso **toda a validação acontece antes**, no GitHub. Se algo estiver errado, nada é enviado e o site antigo continua como está |

---

## 5. Requisitos funcionais

> "RF" = Requisito Funcional: algo que o sistema **deve fazer**.

### Configuração
- **RF1.** Toda a personalização fica em um único arquivo, `config.yaml`, na raiz do repositório.
- **RF2.** O `config.yaml` contém, no mínimo: nome e descrição do assistente; cor primária e cor secundária (formato `#RRGGBB`); caminho e altura da logo; lista ordenada de provedores (cada um com `nome` e `modelo`); `max_tokens`; instruções de comportamento (*system prompt*); de 1 a 6 perguntas de exemplo.
- **RF3.** Os nomes de provedor aceitos são exatamente `openrouter`, `anthropic` e `openai`. Cada um pode aparecer no máximo uma vez.
- **RF4.** O `config.yaml` **nunca** contém chaves de API. Se houver um campo com nome parecido com `api_key`, `token` ou `secret`, a validação falha.

Exemplo de como o arquivo vai ficar, só para ilustrar o formato:
```yaml
assistente:
  nome: "Professor de Dados & IA"
  descricao: "Tire suas dúvidas sobre engenharia de dados e Inteligência Artificial"
aparencia:
  cor_primaria: "#0B3D91"
  cor_secundaria: "#6A1B9A"
  logo: "assets/logo.svg"
  logo_altura_px: 80
ia:
  max_tokens: 1024
  provedores:            # ordem = preferência
    - nome: openrouter
      modelo: "google/gemma-4-31b-it:free"
    - nome: anthropic
      modelo: "claude-haiku-4-5"
    - nome: openai
      modelo: "gpt-5-mini"
comportamento:
  instrucoes: |
    Você é um professor paciente de engenharia de dados e IA...
exemplos:
  - "O que é um pipeline de dados?"
  - "Qual a diferença entre data lake e data warehouse?"
```

### Validação
- **RF5.** Um comando de validação confere o `config.yaml` e, para cada erro, mostra **em português** o campo, o problema e como corrigir. Exemplo: `aparencia.cor_primaria: "#12345G" não é uma cor válida. Use o formato #RRGGBB, por exemplo #0B3D91.`
- **RF6.** A validação falha se: um campo obrigatório estiver vazio; uma cor for inválida; o arquivo da logo não existir; a altura da logo estiver fora de 24 a 300 px; `max_tokens` estiver fora de 64 a 8192; a lista de provedores estiver vazia ou tiver um nome desconhecido ou repetido; um modelo estiver vazio; houver menos de 1 ou mais de 6 exemplos.
- **RF7.** A validação mostra **todos** os erros de uma vez, não só o primeiro.

### Provedores e troca automática
- **RF8.** O app detecta quais chaves existem nas variáveis de ambiente (`OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) e usa **apenas** os provedores da lista que têm chave.
- **RF9.** OpenRouter usa o SDK `openai` com `base_url` `https://openrouter.ai/api/v1`. OpenAI usa o SDK `openai`. Anthropic usa o SDK `anthropic`.
- **RF10.** Todos os provedores recebem as mesmas instruções de comportamento, o mesmo histórico da conversa e o mesmo limite `max_tokens`. Cada adaptador traduz isso para o formato do seu provedor. Exemplos: na Anthropic, as instruções vão no campo `system`; nos modelos GPT-5, o limite vai em `max_completion_tokens`.
- **RF11.** Se um provedor falhar **antes do primeiro pedaço de texto**, o app tenta o próximo da lista, sem o usuário precisar fazer nada.
- **RF12.** Cada tentativa tem tempo máximo de espera (padrão: 30 s até o primeiro pedaço de texto).
- **RF13.** Se todos falharem, o chat mostra uma mensagem como esta:
  > Não consegui responder agora. Motivos:
  > • OpenRouter: limite de uso atingido (429). Tente de novo em alguns minutos.
  > • Anthropic: sem crédito na conta (400/402).
  > • OpenAI: chave não cadastrada.
- **RF14.** Os motivos são traduzidos para português simples (limite de uso, sem crédito, chave inválida, modelo não encontrado, fora do ar, tempo esgotado, resposta vazia, erro desconhecido) e **nunca** mostram a chave nem trechos dela.
- **RF15.** Se **nenhuma** chave estiver cadastrada, o app **abre mesmo assim** e mostra, no lugar da resposta, uma orientação: "Nenhuma chave de API cadastrada. Cadastre pelo menos uma nos *Secrets* do Space."
- **RF16.** Os logs do Space (a tela de registro técnico) mostram qual provedor respondeu cada mensagem e por que os outros falharam, sem mostrar chaves.

### Interface
- **RF17.** O topo da página mostra a logo (na altura configurada), o nome e a descrição.
- **RF18.** O fundo usa as cores configuradas (gradiente da primária para a secundária). A área do chat tem fundo claro e texto escuro, com bom contraste.
- **RF19.** As perguntas de exemplo aparecem como botões clicáveis.
- **RF20.** Todos os textos da tela (botões, campo de digitação, avisos, erros) estão em português.
- **RF21.** A resposta aparece aos poucos (*streaming*).
- **RF22.** O app roda igual em CPU e em ZeroGPU (ver 2.3) e também no seu computador, com `python app.py`.

### Publicação e segurança
- **RF23.** A cada *push* (envio de alteração) na branch `main`, o GitHub Actions roda as verificações e, **só se todas passarem**, publica no Space.
- **RF24.** Se qualquer verificação falhar, a publicação **não acontece**, o site antigo continua no ar e o resumo da execução no GitHub mostra o que corrigir.
- **RF25.** Se houver uma chave de API em qualquer arquivo do repositório, a publicação é bloqueada.
- **RF26.** Em *pull requests* (propostas de alteração), as verificações rodam, mas a publicação não.

---

## 6. Verificações do padrão de testes

> "T" = Teste. Todos rodam com `pytest` no seu computador e no GitHub Actions, **sem chaves reais e sem gastar crédito**. Os provedores são simulados por "dublês" (*fakes*): objetos que fingem ser a API e respondem do jeito que o teste mandar.

### Configuração
- **T1.** O `config.yaml` do repositório passa na validação.
- **T2.** Uma cor inválida (`#12345G`, `azul`) gera erro que cita o campo `aparencia.cor_primaria`.
- **T3.** Campo obrigatório vazio (nome, descrição, instruções) gera erro com o nome do campo.
- **T4.** Logo apontando para um arquivo inexistente gera erro.
- **T5.** Provedor desconhecido (`gemini`), provedor repetido ou lista vazia geram erro.
- **T6.** Zero exemplos ou mais de 6 geram erro. `max_tokens` fora de 64 a 8192 gera erro.
- **T7.** Uma configuração com vários erros mostra todos de uma vez (RF7).
- **T8.** Um campo como `api_key: ...` dentro do `config.yaml` gera erro (RF4).

### Provedores e fallback
- **T9.** Só com `OPENROUTER_API_KEY` definida, apenas o OpenRouter é tentado. O mesmo vale para cada chave isolada (3 casos).
- **T10.** Com as três chaves e o primeiro provedor devolvendo erro 429, a resposta vem do segundo.
- **T11.** Com o primeiro e o segundo falhando (sem crédito, fora do ar), a resposta vem do terceiro.
- **T12.** Com os três falhando, a mensagem final lista os três provedores, cada um com o seu motivo em português.
- **T13.** Sem nenhuma chave, o app devolve a orientação do RF15 e não tenta chamar nenhuma API.
- **T14.** Um provedor que estoura o tempo ou devolve resposta vazia conta como falha e passa para o próximo.
- **T15.** Uma falha **depois** do primeiro pedaço de texto mantém o texto parcial, acrescenta um aviso e **não** chama o próximo provedor.
- **T16.** O adaptador do OpenRouter cria o cliente `openai` com `base_url` `https://openrouter.ai/api/v1`. O adaptador Anthropic manda as instruções no campo `system`.
- **T17.** Nenhuma mensagem de erro ou linha de log contém o valor da chave (teste com uma chave falsa conhecida).
- **T18.** A ordem de tentativa segue exatamente a ordem do `config.yaml`. Se a ordem do arquivo mudar, a ordem das tentativas muda junto.

### Interface e empacotamento
- **T19.** O app monta a interface (sem abrir o servidor) com a configuração padrão e sem nenhuma chave, sem dar erro.
- **T20.** A interface contém o nome, a descrição, os exemplos do `config.yaml` e textos em português (por exemplo, o rótulo do botão de enviar).
- **T21.** O CSS gerado contém as duas cores configuradas.
- **T22.** O cabeçalho YAML do `README.md` tem `sdk: gradio`, `app_file: app.py` e versões fixas de Python e Gradio.

### Segurança
- **T23.** O gitleaks roda no repositório e não encontra nada. Um arquivo de teste com uma chave falsa no formato `sk-ant-...` precisa ser detectado (o teste confirma que o detector funciona).

---

## 7. Pipeline de deploy com GitHub Actions

### 7.1 Como o pipeline funciona
Arquivo: `.github/workflows/deploy.yml`

```
push na main ─┐
pull request ─┼─► [Job 1: verificar] ──(passou e é push na main?)──► [Job 2: publicar]
manual       ─┘     1. baixa o código                                  1. envia os arquivos ao Space
                    2. gitleaks (procura chaves)                          com `hf upload` usando HF_TOKEN
                    3. instala as dependências                         2. espera o Space ficar "Running"
                    4. valida o config.yaml                               (até ~10 min); se der
                    5. roda o pytest                                      "Runtime error", marca falha
```

- **Gatilhos:** push na `main`, pull requests e execução manual (botão *Run workflow*).
- **Concorrência:** se você salvar duas alterações seguidas, só a mais recente é publicada.
- **Mensagens de erro:** cada passo que falha escreve no *Job summary* (resumo da execução) o que corrigir, em português.
- **Arquivos enviados ao Space:** só o necessário para rodar (`app.py`, `src/`, `config.yaml`, `assets/`, `requirements.txt`, `README.md`). Testes, workflows e specs não vão.

### 7.2 O que você precisa configurar à mão (uma única vez)

**No Hugging Face**
1. Criar a conta e assinar o **PRO** (necessário para ZeroGPU; se não quiser pagar, use *CPU basic*).
2. Criar o Space: *New Space* → owner `Erickdds`, nome `agente-personalizado` → SDK **Gradio** → hardware **ZeroGPU** → visibilidade **Public**.
3. No Space: *Settings → Variables and secrets → New secret*. Cadastrar **pelo menos uma**: `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`.
4. Criar um token de acesso: *Settings (do seu perfil) → Access Tokens → New token* → tipo **Fine-grained**, com permissão de **escrita só neste Space**. Copiar o token, que começa com `hf_`.

**No GitHub** (*repositório → Settings*)
5. *Secrets and variables → Actions → New repository secret*: nome `HF_TOKEN`, valor = o token do passo 4.
6. *Secrets and variables → Actions → Variables → New repository variable*: nome `HF_SPACE_ID`, valor `Erickdds/agente-personalizado`.
7. *Actions → General*: confirmar que as Actions estão habilitadas.
8. (Recomendado) *Branches → Add rule* para a `main`: exigir que o job "verificar" passe antes de aceitar um merge.

**Nas contas dos provedores**
9. OpenRouter: criar a chave em *openrouter.ai/keys*. Modelos `:free` não precisam de crédito, mas têm limite diário.
10. Anthropic: criar a chave em *console.anthropic.com* e colocar crédito.
11. OpenAI: criar a chave em *platform.openai.com*, colocar crédito e confirmar que `gpt-5-mini` aparece em *Limits / Models*.

---

## 8. Critérios de aceite

- [ ] Abro https://huggingface.co/spaces/Erickdds/agente-personalizado e vejo a logo, o nome e a descrição no topo, com o fundo nas minhas cores.
- [ ] Todos os textos da tela estão em português.
- [ ] Clico numa pergunta de exemplo e recebo uma resposta didática, que aparece aos poucos.
- [ ] Com **só** a chave do OpenRouter cadastrada, o chat funciona.
- [ ] Com **só** a chave da Anthropic cadastrada, o chat funciona.
- [ ] Com **só** a chave da OpenAI cadastrada, o chat funciona.
- [ ] Com uma chave inválida no 1º provedor e uma válida no 2º, a resposta chega e o log mostra a troca.
- [ ] Com todas as chaves inválidas, o chat mostra o motivo de cada provedor, sem mostrar as chaves.
- [ ] Sem nenhuma chave, o app abre e mostra a orientação para cadastrar uma.
- [ ] Mudo a ordem dos provedores no `config.yaml` pelo GitHub e o log mostra a nova ordem de tentativa.
- [ ] Mudo uma cor ou uma pergunta de exemplo pelo site do GitHub e, em poucos minutos, o Space mostra a mudança.
- [ ] Coloco uma cor inválida de propósito: o GitHub Actions fica vermelho com uma mensagem dizendo o que corrigir, e o site antigo continua no ar.
- [ ] Coloco uma chave falsa num arquivo de propósito: a publicação é bloqueada pelo gitleaks.
- [ ] `pytest` passa no meu computador e no GitHub Actions, sem nenhuma chave real.
- [ ] Nenhum arquivo do repositório contém chave de API.

---

## 9. Ordem das tarefas de implementação

> Uma tarefa por vez. Ao fim de cada uma, mostro como testar e espero você aprovar antes de seguir.

| # | Tarefa | Entrega | Como você vai testar |
|---|---|---|---|
| **1** | **Esqueleto do projeto** | Pastas (`src/`, `tests/`, `assets/`, `scripts/`), `config.yaml` com os padrões, `assets/logo.svg`, `requirements.txt`, `README.md` com o cabeçalho do Space, `.gitignore` | Ver os arquivos no GitHub e conferir o `config.yaml` |
| **2** | **Leitura e validação da configuração** | Módulo de configuração + comando `python scripts/validar_config.py` | Rodar o comando, quebrar uma cor de propósito e ver a mensagem (T1–T8) |
| **3** | **Adaptadores dos 3 provedores e a troca automática** | Um adaptador por provedor + o "orquestrador" do fallback + tradução dos erros | `pytest` com os fakes (T9–T18). Opcional: um teste manual com uma chave real |
| **4** | **Interface Gradio** | `app.py` com cabeçalho, cores, exemplos, streaming, textos em português e compatibilidade com ZeroGPU | `python app.py`, abrir no navegador (T19–T22) |
| **5** | **Proteção contra chaves vazadas** | Configuração do gitleaks + teste do detector | Rodar o gitleaks localmente; o teste com chave falsa precisa ser detectado (T23) |
| **6** | **Pipeline do GitHub Actions** | `.github/workflows/deploy.yml` (verificar → publicar) | Abrir um PR e ver o job "verificar" ficar verde |
| **7** | **Configuração manual e primeiro deploy** | Passo a passo da seção 7.2 aplicado + checagem dos critérios de aceite | Percorrer a checklist da seção 8 |

---

## 10. Erros comuns e como resolver

| Sintoma | Causa provável | Como resolver |
|---|---|---|
| Space mostra **"No @spaces.GPU function detected"** ou não inicia em ZeroGPU | A ZeroGPU exige uma função com `@spaces.GPU` | Confirmar que o `app.py` tem a função mínima (tarefa 4) e que `spaces` está no ambiente, ou trocar o hardware para *CPU basic* |
| Opção **ZeroGPU não aparece** ao criar o Space | A conta não é PRO | Assinar o PRO ou usar *CPU basic* |
| Chat diz **"Nenhuma chave de API cadastrada"** | Os secrets não foram criados no Space, ou o nome está errado | Conferir em *Settings → Variables and secrets* se o nome é **exatamente** `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY` ou `OPENAI_API_KEY`. Depois de cadastrar, clicar em *Restart Space* |
| OpenRouter: **429 / rate limit** | Modelo `:free` lotado ou limite diário atingido | Esperar, colocar um pouco de crédito no OpenRouter (o que aumenta o limite) ou deixar outro provedor como reserva |
| OpenRouter: **404 / "No endpoints found"** | O modelo gratuito mudou de nome ou foi retirado | Procurar o nome atual em *openrouter.ai/models* e atualizar o `config.yaml` |
| Gemma não segue bem as instruções | Alguns modelos abertos tratam as instruções de sistema de forma mais fraca | Deixar as instruções curtas e diretas, ou subir o Claude na ordem |
| Anthropic: **"credit balance is too low"** | Conta sem crédito | Colocar crédito em *console.anthropic.com → Billing* |
| Anthropic: **404 model not found** | Nome do modelo digitado errado | Usar exatamente `claude-haiku-4-5` (ou `claude-sonnet-5-5`) |
| OpenAI: **"Unsupported parameter: max_tokens"** | Modelos GPT-5 usam `max_completion_tokens` | Já tratado no adaptador (RF10). Se aparecer, avise |
| OpenAI: **resposta vazia** com GPT-5 mini | O modelo "pensou" e gastou todos os tokens antes de escrever | O adaptador usa esforço de raciocínio baixo. Se persistir, aumente `max_tokens` |
| OpenAI: **429 "insufficient_quota"** | Sem crédito (não é limite de velocidade) | Colocar crédito em *platform.openai.com → Billing* |
| GitHub Actions: **erro 401/403 no passo "publicar"** | `HF_TOKEN` ausente, expirado ou sem permissão de escrita no Space | Gerar um novo token *fine-grained* com escrita no Space e atualizar o secret `HF_TOKEN` |
| GitHub Actions: **"Repository not found"** | `HF_SPACE_ID` errado | Usar exatamente `Erickdds/agente-personalizado` (maiúsculas e minúsculas importam no usuário) |
| GitHub Actions: **validação falhou** | Erro no `config.yaml` | Ler a mensagem no *Job summary*: ela diz o campo e como corrigir |
| GitHub Actions: **gitleaks falhou** | Alguma chave (ou algo parecido com uma) foi para o código | **Revogar a chave no site do provedor imediatamente** (ela já está no histórico do Git), remover do arquivo e cadastrar a nova só nos secrets do Space |
| Erro de YAML: **"mapping values are not allowed"** | Indentação errada, ou texto com `:` sem aspas | Usar 2 espaços (nunca tab) e colocar textos entre aspas |
| Mudei o `config.yaml` e o site não mudou | O workflow falhou, ainda está rodando, ou o Space está reconstruindo | Ver a aba *Actions* no GitHub e depois a aba *Logs* do Space. A troca leva de 2 a 5 minutos |
| Space em **"Runtime error"** depois do deploy | Dependência faltando ou incompatível com a versão do Python | Ver a aba *Logs* do Space, ajustar o `requirements.txt` e conferir as versões fixadas no `README.md` |
| Primeira visita **demora** | O Space estava dormindo | Normal: espere alguns segundos |
