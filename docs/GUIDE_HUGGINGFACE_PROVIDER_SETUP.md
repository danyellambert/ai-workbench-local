# Hugging Face providers in the project

The project can now work with 3 main provider tracks:

1. `ollama`
2. `huggingface_server`
3. `huggingface_inference`

`huggingface_local` still exists as an experimental in-process track, but the recommendation for serious provider comparison is to prioritize HTTP providers.

---

## 1. `huggingface_server`

Use this provider when you have a persistent local server outside the project exposed over HTTP.

### Recommendation

The server should ideally expose an **OpenAI-compatible / chat-completions-compatible** contract.

### Variables

```env
HUGGINGFACE_SERVER_BASE_URL=http://127.0.0.1:8010/v1
HUGGINGFACE_SERVER_API_KEY=
HUGGINGFACE_SERVER_MODEL=Qwen/Qwen2.5-7B-Instruct
HUGGINGFACE_SERVER_AVAILABLE_MODELS=Qwen/Qwen2.5-7B-Instruct
HUGGINGFACE_SERVER_CONTEXT_WINDOW=8192
```

### Notes

- keep weights/cache outside the repository
- the endpoint is only available while the server is running
- this is the closest path to using Hugging Face “as if it were Ollama”
- the app forwards `temperature`, `ctx_size`, `top_p`, and `max_tokens` as operational overrides via `provider_config`, but the actual application of those parameters depends on the service/hub behind the alias

---

## 2. `huggingface_inference`

Use this provider to call a remote endpoint from your Hugging Face account.

### Step by step

1. sign in to your Hugging Face account
2. generate an access token
3. confirm which endpoint/contract you will use
4. fill in the `.env`

### Variables

```env
HUGGINGFACE_INFERENCE_API_KEY=hf_xxx
HUGGINGFACE_INFERENCE_BASE_URL=https://router.huggingface.co/v1
HUGGINGFACE_INFERENCE_MODEL=meta-llama/Llama-3.1-8B-Instruct
HUGGINGFACE_INFERENCE_AVAILABLE_MODELS=meta-llama/Llama-3.1-8B-Instruct,Qwen/Qwen2.5-7B-Instruct
HUGGINGFACE_INFERENCE_CONTEXT_WINDOW=8192
```

### Notes

- the ideal endpoint is compatible with chat completions
- this is especially useful for deployment on VPS machines with limited memory
- for Oracle VPS, this provider makes more sense than trying to run large local models on the VM
- the app can forward `temperature`, `top_p`, and `max_tokens`, but it does not assume a universal `num_ctx` equivalent on this path

---

## 3. When to use each provider

### `ollama`
- main baseline
- local development
- local-first comparison

### `huggingface_server`
- compare with models that Ollama does not offer
- keep weights outside the project
- run local API-based benchmarks
- publish in the catalog only aliases that truly work on this path; if an alias such as DeepSeek R1 is failing via `huggingface_server`, it is better to temporarily leave it out of the catalog until the provider path is fixed

### `huggingface_inference`
- compare a remote provider
- use it on VPS/Oracle when the machine cannot support the models
- lightweight remote/production fallback

---

## 4. Important note about embeddings

The `huggingface_server` and `huggingface_inference` providers only become embedding providers if you explicitly configure an embedding model for them.

In the main UI:

- `huggingface_server` appears in Embeddings when the service publishes aliases with `supports_embeddings=true`
- `huggingface_inference` appears in Embeddings when `HUGGINGFACE_INFERENCE_EMBEDDING_MODEL` is configured
- when they are not available, the app shows them as disabled with an operational explanation

If you do not configure this, the simplest path remains:

- generation via `ollama` / `huggingface_server` / `huggingface_inference`
- embeddings via `ollama`
