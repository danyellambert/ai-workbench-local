# AI Workbench Local

Plataforma de IA aplicada para experimentar LLMs locais e integrações opcionais free-tier, conversar com documentos, usar ferramentas e agentes, comparar modelos, avaliar respostas e monitorar desempenho.

## Objetivo

Este projeto está sendo evoluído para se tornar um ativo forte de portfólio, demonstrando aplicação prática de IA com foco em:

- chat com modelos locais
- RAG com documentos
- outputs estruturados
- tools e agentes
- benchmarking, avaliação e observabilidade

## Casos de uso principais

1. **Chat com documentos (RAG)**
2. **Assistente de código**
3. **Extração estruturada de informação**

## Stack principal

- Python
- Streamlit
- Ollama
- OpenAI-compatible API
- LangChain
- LangGraph
- Chroma ou FAISS
- SQLite
- Pydantic

## Arquivos principais neste momento

- `main_qwen.py` → versão local com Ollama
- `main.py` → versão configurável para OpenAI por variável de ambiente
- `proximos_passos.md` → roadmap oficial do projeto

## Estrutura atual do projeto

```text
src/
  config.py
  prompt_profiles.py
  providers/
  services/
  storage/
  ui/
```

Essa estrutura foi introduzida na **Fase 2** e expandida na **Fase 3** para separar configuração, providers, perfis de prompt, persistência, estado de sessão e componentes de interface.

## Como rodar localmente

### 1. Instale as dependências

```bash
pip install -r requirements.txt
```

### 2. Revise o arquivo `.env`

O projeto já foi preparado para usar variáveis de ambiente. Se precisar recriar do zero:

```bash
cp .env.example .env
```

### 3. Garanta que o Ollama esteja disponível

Exemplo de modelo local configurado por padrão:

- `qwen2.5-coder:7b`

### 4. Execute a versão local

```bash
streamlit run main_qwen.py
```

### 5. Execute a versão OpenAI (opcional)

Preencha `OPENAI_API_KEY` no `.env` e rode:

```bash
streamlit run main.py
```

## Segurança

- O projeto usa `.env` para configuração local
- O arquivo `.env` está no `.gitignore`
- Nunca publique chaves reais no repositório
- Se uma chave já foi exposta, trate-a como comprometida e revogue-a

## Política de publicação

- O projeto deve permanecer em **repositório privado** até pelo menos a conclusão da **Fase 4** do roadmap
- A pasta `materials_local/` fica fora do versionamento para evitar publicar materiais de curso e arquivos não autorais
- O objetivo é publicar apenas o que for claramente parte do **projeto autoral**
- A licença padrão definida para o projeto é **MIT**

## Git e GitHub

Estratégia recomendada nesta fase:

- branch principal: `main`
- branch de integração: `dev`
- branches futuras: `feature/...`

Exemplos:

- `feature/fase-1-streaming`
- `feature/fase-2-arquitetura`
- `feature/fase-4-rag`

## Roadmap

O roadmap completo do projeto está em:

- `proximos_passos.md`

## Documentação de publicação

Guia da Fase 0.5:

- `docs/PUBLICATION_GUIDE.md`
- `docs/PHASE_3_NOTES.md`
- `docs/PHASE_4_NOTES.md`

## Repositório remoto

- GitHub (privado, por enquanto): `https://github.com/danyellambert/ai-workbench-local`

## Status atual

Fase atual em andamento:

- **Fase 5 — Outputs estruturados**

Última fase fechada na prática:

- **Fase 4.5 — RAG avançado e base documental**

Próxima etapa natural:

- transformar a base documental já estabilizada em fluxos com saída estruturada e validada

## Evolução do roadmap

O roadmap agora destaca explicitamente duas novas etapas de maturidade técnica:

- **Fase 4.5 — RAG avançado e base documental**
- **Fase 5.5 — Evolução com LangChain e LangGraph**

Isso ajuda o projeto a mostrar não só funcionalidades, mas também **progressão técnica real** ao longo das fases.

### O que já foi entregue na Fase 1

- streaming da resposta no chat local
- sidebar com configurações
- seletor de modelo local
- controle de temperatura
- botão para limpar conversa
- histórico simples persistido em arquivo local
- medição da latência da última resposta
- mensagens de erro mais amigáveis

### O que já foi entregue na Fase 3

- arquitetura preparada para múltiplos providers
- seleção explícita de provider na interface
- seleção de modelo por provider
- perfis de prompt (`neutro`, `programador`, `professor`, `resumidor`, `extrator`)
- metadados por mensagem com provider, modelo, perfil e temperatura
- base pronta para comparar providers/modelos sem acoplar tudo no mesmo arquivo

### O que já foi entregue na Fase 4

- upload de documentos (PDF, TXT, CSV, MD, PY)
- extração de texto por tipo de arquivo
- chunking local com overlap
- embeddings locais
- armazenamento do índice em `.rag_store.json`
- retrieval por similaridade cosseno
- injeção de contexto recuperado no prompt
- exibição de fontes usadas nas respostas
- limpeza e reindexação do índice RAG

### O que já foi entregue na Fase 4.5

- base para múltiplos documentos no índice RAG
- filtros por documento/tipo na camada de retrieval
- metadados mais ricos por documento e chunk
- JSON local (`.rag_store.json`) como índice canônico leve
- Chroma local como backend vetorial persistido e sincronizado com o índice canônico
- limpeza e remoção documental refletindo JSON + Chroma, sem depender só de delete incremental
- transparência na UI sobre status do backend vetorial (`sincronizado`, `dessincronizado` ou `fallback_local`)
- configuração explícita de janela de contexto no projeto
- controle visível de contexto para Ollama na sidebar
- caminho nativo do Ollama para parâmetros avançados como `num_ctx`
- controles visíveis de chunk size, overlap e top-k para teste
- métricas visíveis de documentos, chunks e tipos indexados
- telemetria básica de retrieval no chat
- modo opcional de debug de retrieval com scores, backend usado e snippets dos chunks recuperados

## Variáveis úteis para a Fase 3

Você pode ajustar no `.env`:

```env
OLLAMA_AVAILABLE_MODELS=qwen2.5-coder:7b,qwen2.5-coder:14b,deepseek-coder:6.7b
DEFAULT_PROMPT_PROFILE=neutro
OLLAMA_TEMPERATURE=0.2
OPENAI_AVAILABLE_MODELS=gpt-4o-mini
```

Essas variáveis ajudam a controlar quais modelos aparecem por provider e qual perfil de prompt é usado por padrão.

## Arquivo de histórico local

Durante a Fase 1, o chat passou a salvar o histórico localmente em:

- `.chat_history.json`

Esse arquivo fica fora do Git por segurança e para evitar versionar histórico de uso.

## Arquivo de índice RAG local

Durante a Fase 4, o índice de documentos passou a ser salvo localmente em:

- `.rag_store.json`

Esse arquivo também fica fora do Git para evitar versionar dados locais do usuário.

Na Fase 4.5, a arquitetura ficou explícita:

- `.rag_store.json` é o **índice canônico leve**
- `.chroma_rag/` é o **backend vetorial persistido**
- o app tenta manter os dois espelhados a cada indexação, remoção e limpeza do índice
- se o Chroma falhar, a aplicação continua operando com fallback local a partir do JSON

## Configuração explícita de contexto

O projeto agora também prevê configuração explícita de janela de contexto:

- `OLLAMA_CONTEXT_WINDOW`
- `OPENAI_CONTEXT_WINDOW`

Além do default em `.env.example`, o app mostra ajuste visível de contexto na sidebar quando o provider selecionado for **Ollama**.

Observação prática:

- no caso do Ollama, esse valor é enviado como `num_ctx` pela rota nativa `/api/chat`
- valores muito altos podem aumentar consumo de memória e latência
- se o índice RAG estiver grande, vale ajustar também `RAG_CHUNK_SIZE` e `RAG_TOP_K`
- a validação atual é **técnica e operacional**, combinando rota nativa, `/api/show` e sinal auxiliar de `ollama ps`
- isso não deve ser vendido como prova exaustiva do runtime interno, e sim como fechamento prático suficientemente forte para a Fase 4.5
- a camada OpenAI-compatible continua útil para compatibilidade, mas o caminho nativo é o mais confiável para parâmetros avançados