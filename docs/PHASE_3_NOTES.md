# Fase 3 — Multi-modelo e base multi-provider

## Objetivo da fase

Preparar o projeto para trabalhar com múltiplos modelos e múltiplos providers sem depender de cloud desde o início.

## O que foi implementado

- seleção explícita de provider na interface
- seleção de modelo por provider
- perfis de prompt configuráveis
- system prompt gerado a partir do perfil escolhido
- metadados por mensagem:
  - provider
  - modelo
  - perfil de prompt
  - temperatura
  - latência (na resposta da IA)
- renderização do histórico com contexto visual desses metadados
- base de registry para providers

## Providers considerados nesta fase

### Ativo por padrão
- `ollama`

### Opcional por configuração
- `openai`

## Importante

Mesmo com a arquitetura pronta para múltiplos providers, o foco principal de benchmark com cloud continua planejado para a **Fase 7**.

## Benefício arquitetural

Essa fase reduz acoplamento e prepara o terreno para:

- comparação entre modelos locais
- futura comparação local vs cloud
- logging por provider/modelo
- evals futuras por cenário

## Próxima fase

**Fase 4 — Chat com documentos (RAG)**