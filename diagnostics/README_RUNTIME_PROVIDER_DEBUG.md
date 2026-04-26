# Runtime provider debug pack

Este pacote serve para descobrir, com evidência de terminal, qual provider/modelo/chave o backend realmente está chamando.

Ele não imprime chaves em claro. Ele imprime apenas fingerprints `sha256:<12 chars>` para comparar se a chave usada mudou.

## 1) Copiar arquivos

Copie a pasta `diagnostics/` para a raiz do repositório.

## 2) Diagnóstico estático

Na raiz do repositório, com o mesmo virtualenv do backend ativo:

```bash
python diagnostics/diagnose_runtime_state.py --show-state-files | tee runtime-state-diagnosis.txt
```

Envie o arquivo `runtime-state-diagnosis.txt`.

## 3) Trace real de uma execução de workflow

Pare o backend atual. Depois suba o backend com o tracer habilitado.

Se o backend normalmente roda assim:

```bash
python -m uvicorn src.app.main:app --reload
```

rode assim:

```bash
PYTHONPATH="$PWD/diagnostics:${PYTHONPATH:-}" \
RUNTIME_TRACE_FILE="$PWD/runtime-provider-trace.log" \
RUNTIME_TRACE_STACK=1 \
python -m uvicorn src.app.main:app --reload
```

Se o seu comando normal for outro, mantenha o mesmo comando e só adicione estes prefixos antes dele:

```bash
PYTHONPATH="$PWD/diagnostics:${PYTHONPATH:-}" RUNTIME_TRACE_FILE="$PWD/runtime-provider-trace.log" RUNTIME_TRACE_STACK=1 <SEU_COMANDO_NORMAL_DO_BACKEND>
```

Com o backend rodando:

1. Abra Preferences.
2. Escolha `Deep Review` como active profile.
3. Salve uma chave nova no `Ollama Hosted`.
4. Rode um workflow curto que reproduz o problema.
5. Pare o backend.
6. Envie `runtime-provider-trace.log`.

## 4) O que olhar no trace

Procure linhas com:

- `host` contendo o domínio/base URL do Ollama Hosted;
- `path` como `/api/chat`, `/v1/chat/completions`, `/api/generate` ou similar;
- `body.model` como `nemotron-3-super:cloud`;
- `auth.authorization` com o fingerprint da chave nova.

Se aparecer host/path do Hugging Face, o trace vai mostrar a stack de código que fez essa chamada.
