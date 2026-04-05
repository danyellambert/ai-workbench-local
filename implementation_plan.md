# Implementation Plan

[Overview]
Construir uma nova superfície de produto em Gradio, mantendo o Streamlit atual como AI Lab dashboard e reaproveitando a camada de serviços já existente.

O repositório já tem a maior parte do backend que o produto precisa: ingestão documental, indexação RAG, montagem de contexto, execução de tasks estruturadas, EvidenceOps e geração de decks. O problema atual não é falta de capability; é falta de separação clara entre a superfície de negócio e a superfície de engenharia. Hoje `main_qwen.py` concentra upload, chat, structured outputs, benchmarking, MCP e observabilidade num único app Streamlit, com bastante acoplamento a `st.session_state` e a componentes de UI específicos de Streamlit.

O plano para o Gradio deve ser aditivo e não destrutivo. A primeira entrega não substitui o app Streamlit; ela cria uma nova entrada de produto (`main_gradio.py`) que consome serviços compartilhados e apresenta quatro workflows de negócio: `Document Review`, `Policy / Contract Comparison`, `Action Plan / Evidence Review` e `Candidate Review`. O Streamlit continua existindo, mas passa a ser explicitamente reposicionado como AI Lab, concentrando benchmark, evals, observabilidade, workflow traces, debugging avançado e console operacional do MCP/EvidenceOps.

Para reduzir risco, o Gradio não deve tentar reutilizar os renderers de `src/ui/*.py`, porque eles são fortemente acoplados ao Streamlit. Em vez disso, a implementação deve introduzir uma camada de domínio de produto, com tipos e serviços próprios, apoiada nos contratos já existentes (`StructuredResult`, `TaskExecutionRequest`, payloads estruturados e `presentation_export_service`). Essa camada será reutilizável tanto pela UI em Gradio quanto por uma futura evolução para backend HTTP/app web.

O corte arquitetural recomendado é: backend compartilhado continua em `src/services`, `src/structured`, `src/rag`, `src/storage`; a nova orquestração de produto entra em um pacote novo (`src/product`); a superfície Gradio entra em um pacote de UI novo (`src/gradio_ui`); e o Streamlit atual sofre apenas os ajustes necessários para deixar de parecer homepage do produto. O objetivo é sair de um app monolítico de demonstração para duas superfícies complementares com boundary explícito.

Além da correção arquitetural, a superfície Gradio deve ser desenhada para causar forte impressão em entrevista de AI Engineer. Isso significa evitar uma aparência genérica de demo técnica e buscar uma estética de produto AI-first: hero claro, workflow cards fortes, hierarquia visual limpa, estados bem definidos, grounded preview elegante, área de resultados com sensação de "decision cockpit" e ações finais que pareçam prontas para uso real. A UI precisa mostrar gosto de produto, mas sem esconder profundidade técnica.

O princípio visual deve ser: **parecer produto para o usuário e parecer sistema sério para o entrevistador**. Para isso, a experiência deve expor sinais de engenharia de forma controlada — grounding, confiança, warnings, artefatos, tempo de execução e handoff — sem cair em cara de console. O Streamlit, por sua vez, fica como a prova explícita de profundidade técnica. O contraste entre as duas superfícies passa a ser uma vantagem narrativa na entrevista.

[Types]
Adicionar tipos de produto e configuração do Gradio sem alterar os contratos estruturados já consolidados.

Os contratos atuais de backend devem continuar canônicos:
- `src/structured/envelope.py::StructuredResult`
- `src/structured/envelope.py::TaskExecutionRequest`
- `src/structured/base.py::{ExtractionPayload, SummaryPayload, ChecklistPayload, CVAnalysisPayload, DocumentAgentPayload}`

Novos tipos recomendados:

1. `src/config.py::GradioProductSettings` (`@dataclass(frozen=True)`)
   - `server_name: str`
   - `server_port: int`
   - `theme: str`
   - `default_workflow: str`
   - `max_upload_files: int`
   - `enable_deck_generation: bool`
   - `show_api_docs_hint: bool`
   - Validação: `server_port > 0`; `default_workflow` deve pertencer ao catálogo de workflows; `max_upload_files >= 1`.

2. `src/product/models.py::ProductWorkflowId`
   - Tipo literal com os valores:
     - `document_review`
     - `policy_contract_comparison`
     - `action_plan_evidence_review`
     - `candidate_review`

3. `src/product/models.py::ProductWorkflowDefinition` (Pydantic ou dataclass)
   - `workflow_id: ProductWorkflowId`
   - `label: str`
   - `headline: str`
   - `description: str`
   - `required_document_count_min: int`
   - `required_document_count_max: int | None`
   - `supports_optional_prompt: bool`
   - `default_export_kind: str | None`
   - `backend_task_types: list[str]`
   - Uso: catálogo exibido na home do Gradio e validação de inputs.

4. `src/product/models.py::ProductDocumentRef`
   - `document_id: str`
   - `name: str`
   - `file_type: str | None`
   - `char_count: int`
   - `chunk_count: int`
   - `indexed_at: str | None`
   - `loader_strategy_label: str | None`
   - Uso: representar documentos indexados de forma agnóstica à UI.

5. `src/product/models.py::GroundingPreview`
   - `strategy: str`
   - `document_ids: list[str]`
   - `context_chars: int`
   - `source_block_count: int`
   - `preview_text: str`
   - `warnings: list[str]`
   - Uso: exibir preview grounded no Gradio antes da execução.

6. `src/product/models.py::ProductWorkflowRequest`
   - `workflow_id: ProductWorkflowId`
   - `document_ids: list[str]`
   - `input_text: str`
   - `provider: str`
   - `model: str`
   - `temperature: float`
   - `context_window_mode: str`
   - `context_window: int | None`
   - `use_document_context: bool`
   - `context_strategy: str`
   - Validação por workflow:
     - `candidate_review`: idealmente 1 documento por execução
     - `policy_contract_comparison`: mínimo 2 documentos
     - `document_review`: mínimo 1 documento
     - `action_plan_evidence_review`: mínimo 1 documento ou insumo de EvidenceOps

7. `src/product/models.py::ProductArtifact`
   - `artifact_type: Literal["pptx", "contract_json", "payload_json", "review_json"]`
   - `label: str`
   - `path: str | None`
   - `download_name: str | None`
   - `available: bool`

8. `src/product/models.py::ProductWorkflowResult`
   - `workflow_id: ProductWorkflowId`
   - `workflow_label: str`
   - `status: Literal["completed", "warning", "error"]`
   - `summary: str`
   - `highlights: list[str]`
   - `structured_result: StructuredResult | None`
   - `grounding_preview: GroundingPreview | None`
   - `artifacts: list[ProductArtifact]`
   - `deck_export_kind: str | None`
   - `deck_available: bool`
   - `warnings: list[str]`
   - `debug_metadata: dict[str, Any]`
   - Relação: encapsula o resultado de negócio sem alterar o contrato estruturado bruto.

9. `src/gradio_ui/state.py::ProductSessionState`
   - `selected_workflow: ProductWorkflowId`
   - `indexed_document_ids: list[str]`
   - `latest_result: ProductWorkflowResult | None`
   - `latest_deck_result: dict[str, Any] | None`
   - `last_error: str | None`
   - Uso: estado leve de sessão para `gr.State`, sem depender de `streamlit.session_state`.

Princípio de tipagem: os tipos de produto devem envolver os payloads existentes, e não duplicar os schemas de `ExtractionPayload`, `SummaryPayload`, `ChecklistPayload`, `CVAnalysisPayload` ou `DocumentAgentPayload`.

[Files]
Criar uma nova camada de produto/Gradio e ajustar poucos pontos do app Streamlit para firmar o split entre produto e lab.

Novos arquivos a criar:
- `main_gradio.py`
  - Novo entrypoint do produto em Gradio.
  - Responsável por montar bootstrap, construir `gr.Blocks` e fazer `launch()`.

- `src/app/product_bootstrap.py`
  - Bootstrap específico da superfície de produto.
  - Reúne settings do produto, settings compartilhadas, registry de providers, catálogos de workflow e serviços necessários ao Gradio.

- `src/product/__init__.py`
  - Exporta tipos e serviços do domínio de produto.

- `src/product/models.py`
  - Define tipos Pydantic/dataclass de workflow, grounding preview, resultado e artefatos.

- `src/product/service.py`
  - Orquestra os workflows de negócio usando os serviços atuais (`structured_service`, `build_structured_document_context`, `generate_executive_deck`, stores de EvidenceOps, etc.).

- `src/product/presenters.py`
  - Converte `StructuredResult` e payloads estruturados em seções amigáveis para UI de produto (cards, bullets, tabelas simples, warnings e labels).

- `src/gradio_ui/__init__.py`
  - Namespace da nova UI.

- `src/gradio_ui/theme.py`
  - Define tema, tokens visuais, helpers de CSS e identidade visual do produto.

- `src/gradio_ui/components.py`
  - Componentes reutilizáveis de apresentação (hero, workflow cards, stat cards, evidence cards, result sections, download area).

- `src/gradio_ui/state.py`
  - Helpers para inicializar/atualizar `ProductSessionState` com `gr.State`.

- `src/gradio_ui/app.py`
  - Monta o app Gradio, layout, callbacks e wiring dos componentes.

- `tests/test_product_service_unittest.py`
  - Cobre mapeamento workflow -> task/backend -> export kind.

- `tests/test_gradio_app_smoke_unittest.py`
  - Smoke test da montagem do `gr.Blocks` e da presença dos workflows principais.

Arquivos existentes a modificar:
- `requirements.txt`
  - Adicionar `gradio`.

- `src/config.py`
  - Adicionar `GradioProductSettings` e `get_gradio_product_settings()`.
  - Incluir leitura de envs do produto/Gradio.
  - Incluir parâmetros de tema/branding se necessário (`theme`, `accent_color`, `default_density`).

- `src/ui/executive_deck_generation.py`
  - Permitir filtragem da superfície por `allowed_export_kinds` ou `surface`.
  - Objetivo: Streamlit lab mostrar só o que pertence ao lab; produto em Gradio usar a mesma service layer sem depender da UI Streamlit.

- `main_qwen.py`
  - Ajustar posicionamento textual para AI Lab dashboard.
  - Remover protagonismo de fluxos de produto na home do Streamlit.
  - Restringir o painel de deck generation do lab ao caso benchmark/eval ou rotulá-lo explicitamente como capability de lab.

- `tests/test_streamlit_app_smoke_unittest.py`
  - Atualizar asserts para refletir o reposicionamento do Streamlit como AI Lab.

- `tests/test_app_bootstrap_smoke_unittest.py`
  - Atualizar apenas se o bootstrap compartilhado mudar; caso `ProductBootstrap` seja novo e isolado, criar teste novo sem alterar este arquivo.

Arquivos que não devem ser movidos nem reescritos neste slice:
- `src/structured/*`
- `src/services/presentation_export_service.py`
- `src/services/presentation_export.py`
- `src/services/document_context.py`
- `src/rag/*`
- `src/storage/*`

Esses módulos já são a base compartilhada e devem ser consumidos, não duplicados.

[Functions]
Introduzir funções de orquestração de produto e deixar a UI de Streamlit o mais intacta possível fora do reposicionamento para AI Lab.

Novas funções recomendadas:

1. `src/app/product_bootstrap.py::build_product_bootstrap() -> ProductBootstrap`
   - Monta providers, settings, rag settings, evidence config, presentation export settings e catálogo de workflows para o Gradio.

2. `src/product/service.py::build_product_workflow_catalog() -> dict[ProductWorkflowId, ProductWorkflowDefinition]`
   - Catálogo único da home do produto e das validações dos workflows.

3. `src/product/service.py::list_product_documents() -> list[ProductDocumentRef]`
   - Converte o índice RAG atual em referências agnósticas à UI.

4. `src/product/service.py::build_grounding_preview(*, query: str, document_ids: list[str], strategy: str) -> GroundingPreview`
   - Encapsula `build_structured_document_context()` e produz preview seguro para UI.

5. `src/product/service.py::run_product_workflow(request: ProductWorkflowRequest) -> ProductWorkflowResult`
   - Dispatcher central por `workflow_id`.

6. `src/product/service.py::run_document_review_workflow(request: ProductWorkflowRequest) -> ProductWorkflowResult`
   - Usa principalmente `document_agent`, `summary` e/ou `extraction` conforme o mínimo necessário.
   - Saída de negócio: summary grounded, findings, risks/gaps, recommended actions.

7. `src/product/service.py::run_policy_contract_comparison_workflow(request: ProductWorkflowRequest) -> ProductWorkflowResult`
   - Usa `document_agent` em modo de comparação grounded.
   - Saída: diferenças relevantes, impactos, watchouts e recommendation.

8. `src/product/service.py::run_action_plan_evidence_review_workflow(request: ProductWorkflowRequest) -> ProductWorkflowResult`
   - Usa `checklist` e/ou `document_agent`, além de leitura do EvidenceOps quando aplicável.
   - Saída: owners, tarefas, prazos, backlog operacional e sinais de evidence review.

9. `src/product/service.py::run_candidate_review_workflow(request: ProductWorkflowRequest) -> ProductWorkflowResult`
   - Usa `cv_analysis` como engine interna.
   - A UI nunca expõe `cv_analysis` nominalmente; só `Candidate Review`.

10. `src/product/service.py::generate_product_workflow_deck(result: ProductWorkflowResult) -> dict[str, Any]`
    - Resolve o `export_kind` do workflow e chama `generate_executive_deck()`.

11. `src/product/presenters.py::build_product_result_sections(result: ProductWorkflowResult) -> dict[str, Any]`
    - Gera estrutura amigável para cards, tabelas, bullets e warnings.

12. `src/gradio_ui/theme.py::build_product_theme()`
    - Retorna tema/configuração visual do Gradio com aparência premium e consistente com a narrativa AI-first.

13. `src/gradio_ui/components.py::build_product_hero(...)`
    - Monta a hero area com headline do produto, subtítulo forte e orientação inicial dos workflows.

14. `src/gradio_ui/components.py::build_workflow_cards(...)`
    - Renderiza os 4 workflows principais como cards com alto apelo visual e clareza narrativa.

15. `src/gradio_ui/components.py::build_result_panels(...)`
    - Renderiza summary, findings, evidence, actions e artifacts em blocos visualmente fortes para demo/interview.

16. `src/gradio_ui/state.py::create_initial_product_state(default_workflow: ProductWorkflowId) -> ProductSessionState`
    - Estado inicial do app Gradio.

17. `src/gradio_ui/state.py::update_product_state(state: ProductSessionState, **changes) -> ProductSessionState`
    - Atualização imutável/segura do estado da sessão.

18. `src/gradio_ui/app.py::build_gradio_product_app(bootstrap: ProductBootstrap)`
    - Monta o `gr.Blocks` com home, shell comum, upload/indexação, preview grounded, área de resultados e ações finais.

19. Callbacks internos em `src/gradio_ui/app.py`
    - `_handle_document_upload(...)`
    - `_handle_document_selection_change(...)`
    - `_handle_preview_grounding(...)`
    - `_handle_run_workflow(...)`
    - `_handle_generate_deck(...)`
    - `_handle_reset_session(...)`
    - Cada callback deve operar sobre tipos puros e `gr.State`, nunca sobre `st.session_state`.

Diretrizes funcionais de design a refletir nessas funções:
- toda execução deve gerar uma leitura visual de progresso e status clara;
- grounding deve aparecer como evidência útil, não como debug cru;
- warnings e confidence devem ser mostrados em linguagem de produto;
- áreas de resultado devem privilegiar escaneabilidade em demo ao vivo.

Funções existentes a modificar:

1. `src/config.py::get_gradio_product_settings() -> GradioProductSettings`
   - Nova função; não substituir as getters existentes.

2. `src/ui/executive_deck_generation.py::render_executive_deck_generation_panel(...)`
   - Adicionar parâmetro opcional para filtrar deck kinds visíveis por superfície (`lab` vs `product` ou lista explícita de kinds).

3. Top-level composition em `main_qwen.py`
   - Ajustar textos/copy, limitar deck surface de produto e reforçar leitura de AI Lab.
   - Não reescrever toda a lógica do app atual neste slice.

Funções que não devem ser removidas:
- `structured_service.execute_task`
- `build_structured_document_context`
- `generate_executive_deck`
- `render_structured_result`
- `render_evidenceops_mcp_panel`
- `render_chat_sidebar`

Elas continuam válidas; o Gradio apenas não deve depender diretamente das versões `render_*` de Streamlit.

[Classes]
Adicionar poucas classes novas e preservar as classes estruturadas já existentes como contratos de backend.

Novas classes:

1. `src/config.py::GradioProductSettings`
   - Dataclass de configuração do app de produto.
   - Sem herança.

2. `src/app/product_bootstrap.py::ProductBootstrap`
   - Dataclass com:
     - `product_settings: GradioProductSettings`
     - `app_settings: OllamaSettings`
     - `rag_settings: RagSettings`
     - `evidence_config: Any`
     - `provider_registry: dict[str, dict[str, object]]`
     - `prompt_profiles: dict[str, dict[str, str]]`
     - `structured_task_registry: Any`
     - `presentation_export_settings: PresentationExportSettings`
     - `workflow_catalog: dict[ProductWorkflowId, ProductWorkflowDefinition]`

3. `src/product/models.py::ProductWorkflowDefinition`
   - Metadados de cada workflow do produto.

4. `src/product/models.py::ProductDocumentRef`
   - Referência documental normalizada para exibição no produto.

5. `src/product/models.py::GroundingPreview`
   - Representação tipada da prévia grounded.

6. `src/product/models.py::ProductArtifact`
   - Representação tipada dos artefatos gerados/downloadáveis.

7. `src/product/models.py::ProductWorkflowRequest`
   - Request de orquestração de negócio.

8. `src/product/models.py::ProductWorkflowResult`
   - Resultado canônico de negócio consumido pelo Gradio.

9. `src/gradio_ui/state.py::ProductSessionState`
   - Dataclass/pydantic model do estado local de sessão do Gradio.

Classes existentes a manter sem mudanças estruturais profundas:
- `AppBootstrap` em `src/app/bootstrap.py`
- `StructuredResult` em `src/structured/envelope.py`
- `TaskExecutionRequest` em `src/structured/envelope.py`
- `ExtractionPayload`, `SummaryPayload`, `ChecklistPayload`, `CVAnalysisPayload`, `DocumentAgentPayload` em `src/structured/base.py`

Estratégia recomendada: não ampliar `StructuredResult` nem os payloads estruturados para resolver preocupação de UI. O produto deve adaptar esses contratos por fora.

[Dependencies]
Adicionar somente a dependência necessária para a nova superfície Gradio e evitar introduzir um backend HTTP novo neste slice.

Mudanças recomendadas:
- `requirements.txt`
  - adicionar `gradio`

Sem novas dependências obrigatórias neste momento para:
- FastAPI
- React/Vite
- Redis/Celery
- `gradio_client`

Racional:
- o objetivo deste slice é entregar uma superfície de produto local, não iniciar ainda a Fase 10.25C de backend HTTP;
- o app já possui serviços suficientes para rodar localmente;
- quanto menos dependências novas forem adicionadas, menor o risco de regressão no Streamlit atual.

Dependência opcional, só se o Gradio nativo não bastar para o nível de acabamento esperado:
- nenhuma por padrão; primeiro explorar tema/CSS/custom HTML do próprio Gradio antes de considerar expansão de stack.

[Testing]
Cobrir a nova camada de produto com testes unitários e smoke tests, preservando a estabilidade do Streamlit como AI Lab.

Testes novos:
- `tests/test_product_service_unittest.py`
  - validar catálogo de workflows;
  - validar mapeamento `workflow_id -> task_type(s) -> export_kind`;
  - garantir que `candidate_review` usa `cv_analysis` internamente sem expor o nome técnico na camada de produto;
  - validar geração de `GroundingPreview` e `ProductWorkflowResult` com mocks.

- `tests/test_gradio_app_smoke_unittest.py`
  - importar `build_gradio_product_app()`;
  - garantir que o `Blocks` monta sem exceção;
  - verificar presença dos quatro workflows principais, entrada documental, preview grounded, botão de execução e ação de deck/download.

Testes existentes a ajustar:
- `tests/test_streamlit_app_smoke_unittest.py`
  - manter asserts sobre tabs/controles de engenharia;
  - adicionar verificação do reposicionamento textual do app como AI Lab, se a mudança de copy for coberta por smoke.

- `tests/test_presentation_export_service_unittest.py` ou testes correlatos
  - adicionar cobertura para a filtragem de export kinds por superfície, se o filtro entrar em `src/ui/executive_deck_generation.py`.

Estratégia de validação manual após implementação:
1. subir `main_gradio.py` localmente;
2. indexar 1-2 documentos;
3. executar cada um dos quatro workflows;
4. validar geração de deck onde houver insumo disponível;
5. subir `main_qwen.py` e conferir que continua operando como AI Lab sem regressão funcional.

Critérios extras de validação visual para entrevista:
6. verificar se a home comunica o produto em menos de 10 segundos;
7. verificar se cada workflow parece distinto e não apenas uma variação de formulário;
8. verificar se os resultados ficam escaneáveis em screen share;
9. verificar se há contraste claro entre "superfície produto" e "superfície lab";
10. validar se a UI passa sensação de sistema confiável, não só protótipo bonito.

[Implementation Order]
Executar primeiro o backend compartilhado do produto, depois a UI em Gradio e só então o reposicionamento final do Streamlit.

1. Adicionar `gradio` em `requirements.txt` e criar `GradioProductSettings` em `src/config.py`.
2. Criar `src/app/product_bootstrap.py` para inicializar a nova superfície sem tocar no bootstrap do Streamlit.
3. Criar `src/product/models.py` com os tipos de workflow, grounding, artefatos, request e result.
4. Implementar `src/product/service.py` com o catálogo de workflows e as funções `run_*_workflow`, reaproveitando `structured_service`, `document_context`, `presentation_export_service` e stores existentes.
5. Implementar `src/product/presenters.py` para traduzir `StructuredResult` em conteúdo amigável ao produto sem depender de `src/ui/structured_outputs.py`.
6. Criar `src/gradio_ui/theme.py` e `src/gradio_ui/components.py` para fixar a linguagem visual premium antes da montagem final do app.
7. Criar `src/gradio_ui/state.py` para substituir qualquer necessidade de `streamlit.session_state` na superfície de produto.
8. Criar `src/gradio_ui/app.py` com o shell comum do produto: home, seleção do workflow, upload/seleção documental, preview grounded, findings/recommendations e ações finais.
9. Criar `main_gradio.py` e ligar o app Gradio ao `ProductBootstrap`.
10. Ajustar `src/ui/executive_deck_generation.py` para suportar filtro de export kinds por superfície, reutilizando a mesma service layer.
11. Atualizar `main_qwen.py` para reforçar a leitura de AI Lab e remover o protagonismo de fluxos de produto da home do Streamlit.
12. Adicionar `tests/test_product_service_unittest.py` e `tests/test_gradio_app_smoke_unittest.py`.
13. Atualizar os smoke tests do Streamlit e rodar regressão mínima nos dois apps.
14. Fazer uma rodada final de polish visual orientada a entrevista: headline, spacing, contraste, states, resultado escaneável e wow factor sem sacrificar clareza.