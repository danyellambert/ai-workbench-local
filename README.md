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

## Repositório remoto

- GitHub (privado, por enquanto): `https://github.com/danyellambert/ai-workbench-local`

## Status atual

Fase atual em andamento:

- **Fase 2 — Arquitetura modular**

Próxima etapa natural:

- organizar melhor a estrutura do projeto para sair de um arquivo único e preparar a evolução das próximas fases

### O que já foi entregue na Fase 1

- streaming da resposta no chat local
- sidebar com configurações
- seletor de modelo local
- controle de temperatura
- botão para limpar conversa
- histórico simples persistido em arquivo local
- medição da latência da última resposta
- mensagens de erro mais amigáveis

## Arquivo de histórico local

Durante a Fase 1, o chat passou a salvar o histórico localmente em:

- `.chat_history.json`

Esse arquivo fica fora do Git por segurança e para evitar versionar histórico de uso.