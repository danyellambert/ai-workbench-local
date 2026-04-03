# Hugging Face providers no projeto

O projeto agora pode trabalhar com 3 trilhas principais de provider:

1. `ollama`
2. `huggingface_server`
3. `huggingface_inference`

`huggingface_local` continua existindo como trilha experimental in-process, mas a recomendação para comparação séria de providers é priorizar os providers HTTP.

---

## 1. `huggingface_server`

Use este provider quando você tiver um servidor local persistido fora do projeto, exposto por HTTP.

### Recomendação

O servidor deve idealmente expor um contrato **OpenAI-compatible / chat completions compatible**.

### Variáveis

```env
HUGGINGFACE_SERVER_BASE_URL=http://127.0.0.1:8010/v1
HUGGINGFACE_SERVER_API_KEY=
HUGGINGFACE_SERVER_MODEL=Qwen/Qwen2.5-7B-Instruct
HUGGINGFACE_SERVER_AVAILABLE_MODELS=Qwen/Qwen2.5-7B-Instruct
HUGGINGFACE_SERVER_CONTEXT_WINDOW=8192
```

### Observações

- mantenha os pesos/cache fora do repositório
- o endpoint só fica disponível enquanto o servidor estiver rodando
- isso é o caminho mais próximo de usar Hugging Face “como se fosse Ollama”
- o app encaminha `temperature`, `ctx_size`, `top_p` e `max_tokens` como overrides operacionais via `provider_config`, mas a aplicação real desses parâmetros depende do serviço/hub por trás do alias

---

## 2. `huggingface_inference`

Use este provider para chamar um endpoint remoto da sua conta Hugging Face.

### Passo a passo

1. entre na sua conta da Hugging Face
2. gere um token de acesso
3. confirme qual endpoint/contrato você vai usar
4. preencha o `.env`

### Variáveis

```env
HUGGINGFACE_INFERENCE_API_KEY=hf_xxx
HUGGINGFACE_INFERENCE_BASE_URL=https://router.huggingface.co/v1
HUGGINGFACE_INFERENCE_MODEL=meta-llama/Llama-3.1-8B-Instruct
HUGGINGFACE_INFERENCE_AVAILABLE_MODELS=meta-llama/Llama-3.1-8B-Instruct,Qwen/Qwen2.5-7B-Instruct
HUGGINGFACE_INFERENCE_CONTEXT_WINDOW=8192
```

### Observações

- o endpoint ideal é compatível com chat completions
- isso é especialmente útil para deploy em VPS com pouca memória
- para Oracle VPS, este provider faz mais sentido do que tentar subir modelos grandes localmente na VM
- o app pode encaminhar `temperature`, `top_p` e `max_tokens`, mas não assume um equivalente universal de `num_ctx` nesse caminho

---

## 3. Quando usar cada provider

### `ollama`
- baseline principal
- desenvolvimento local
- comparação local-first

### `huggingface_server`
- comparar com modelos que o Ollama não oferece
- manter pesos fora do projeto
- fazer benchmark local por API

### `huggingface_inference`
- comparar provider remoto
- usar na VPS/Oracle quando a máquina não comportar os modelos
- fallback remoto/produção leve

---

## 4. Nota importante sobre embeddings

Os providers `huggingface_server` e `huggingface_inference` só entram como providers de embedding se você configurar explicitamente um modelo de embedding para eles.

Na UI principal:

- `huggingface_server` aparece em Embeddings quando o serviço publica aliases com `supports_embeddings=true`
- `huggingface_inference` aparece em Embeddings quando `HUGGINGFACE_INFERENCE_EMBEDDING_MODEL` estiver configurado
- quando não estiverem disponíveis, o app os mostra como desabilitados com uma explicação operacional

Se você não configurar isso, o caminho mais simples continua sendo:

- geração via `ollama` / `huggingface_server` / `huggingface_inference`
- embeddings via `ollama`
