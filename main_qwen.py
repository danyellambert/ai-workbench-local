import json
import os
import subprocess
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

PROJECT_NAME = os.getenv("PROJECT_NAME", "AI Workbench Local")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
DEFAULT_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
HISTORY_PATH = Path(__file__).with_name(".chat_history.json")
FALLBACK_MODELS = [
    DEFAULT_MODEL,
    "qwen2.5-coder:7b",
    "qwen2.5-coder:14b",
    "deepseek-coder:6.7b",
    "qwen3-coder:480b-cloud",
]


def listar_modelos_disponiveis():
    modelos_encontrados = []

    try:
        resultado = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
        if resultado.returncode == 0:
            for linha in resultado.stdout.splitlines()[1:]:
                partes = linha.split()
                if partes:
                    modelos_encontrados.append(partes[0])
    except OSError:
        pass

    modelos_env = [
        modelo.strip()
        for modelo in os.getenv("OLLAMA_AVAILABLE_MODELS", "").split(",")
        if modelo.strip()
    ]

    modelos = []
    for modelo in [DEFAULT_MODEL, *modelos_env, *modelos_encontrados, *FALLBACK_MODELS]:
        if modelo and modelo not in modelos:
            modelos.append(modelo)

    return modelos


def carregar_historico():
    if not HISTORY_PATH.exists():
        return []

    try:
        dados = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(dados, list):
        return []

    historico = []
    for item in dados:
        if (
            isinstance(item, dict)
            and item.get("role") in {"user", "assistant"}
            and isinstance(item.get("content"), str)
        ):
            historico.append({"role": item["role"], "content": item["content"]})

    return historico


def salvar_historico(mensagens):
    HISTORY_PATH.write_text(
        json.dumps(mensagens, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def limpar_historico():
    st.session_state["lista_mensagens"] = []
    st.session_state["ultima_latencia_s"] = None
    if HISTORY_PATH.exists():
        HISTORY_PATH.unlink()


modelo_ia = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
)

if "lista_mensagens" not in st.session_state:
    st.session_state["lista_mensagens"] = carregar_historico()

if "ultima_latencia_s" not in st.session_state:
    st.session_state["ultima_latencia_s"] = None

modelos_disponiveis = listar_modelos_disponiveis()
indice_padrao = modelos_disponiveis.index(DEFAULT_MODEL) if DEFAULT_MODEL in modelos_disponiveis else 0

with st.sidebar:
    st.header("Configurações")
    modelo_escolhido = st.selectbox("Modelo local", modelos_disponiveis, index=indice_padrao)
    temperatura = st.slider(
        "Temperatura",
        min_value=0.0,
        max_value=1.5,
        value=min(max(DEFAULT_TEMPERATURE, 0.0), 1.5),
        step=0.1,
    )

    if st.button("🧹 Limpar conversa", use_container_width=True):
        limpar_historico()
        st.rerun()

    st.divider()
    st.metric("Mensagens na conversa", len(st.session_state["lista_mensagens"]))
    if st.session_state["ultima_latencia_s"] is not None:
        st.metric("Última resposta", f"{st.session_state['ultima_latencia_s']:.2f}s")

    st.caption(f"Base URL: `{OLLAMA_BASE_URL}`")
    st.caption(f"Histórico local: `{HISTORY_PATH.name}`")
    st.info("Chat com documentos entra na Fase 4 do roadmap.")

st.write(f"# {PROJECT_NAME}")
st.caption(
    f"Modelo atual: `{modelo_escolhido}` · Temperatura: `{temperatura:.1f}` · Histórico salvo localmente"
)

for mensagem in st.session_state["lista_mensagens"]:
    st.chat_message(mensagem["role"]).write(mensagem["content"])

texto_usuario = st.chat_input("Digite sua mensagem")

if texto_usuario:
    st.chat_message("user").write(texto_usuario)
    mensagem_usuario = {"role": "user", "content": texto_usuario}
    st.session_state["lista_mensagens"].append(mensagem_usuario)
    salvar_historico(st.session_state["lista_mensagens"])

    texto_resposta_ia = ""

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            inicio = time.perf_counter()
            stream = modelo_ia.chat.completions.create(
                messages=st.session_state["lista_mensagens"],
                model=modelo_escolhido,
                temperature=temperatura,
                stream=True,
            )

            partes = []
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    partes.append(delta)
                    placeholder.markdown("".join(partes) + "▌")

            texto_resposta_ia = "".join(partes).strip() or "A resposta veio vazia."
            placeholder.markdown(texto_resposta_ia)

            latencia = time.perf_counter() - inicio
            st.session_state["ultima_latencia_s"] = latencia
            st.caption(f"Resposta em {latencia:.2f}s")
        except Exception as erro:
            st.session_state["ultima_latencia_s"] = None
            texto_resposta_ia = (
                "Não foi possível obter resposta do Ollama.\n\n"
                "Verifique se:\n"
                f"- o servidor está ativo em `{OLLAMA_BASE_URL}`\n"
                f"- o modelo `{modelo_escolhido}` está instalado\n"
                "- o Ollama está respondendo normalmente\n\n"
                f"Detalhes técnicos: {erro}"
            )
            placeholder.empty()
            st.error(texto_resposta_ia)

    mensagem_ia = {"role": "assistant", "content": texto_resposta_ia}
    st.session_state["lista_mensagens"].append(mensagem_ia)
    salvar_historico(st.session_state["lista_mensagens"])
