import streamlit as st


def render_chat_message(message: dict[str, object]) -> None:
    role = message.get("role", "assistant")
    content = message.get("content", "")
    metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}

    with st.chat_message(role):
        st.write(content)

        if metadata:
            info_parts = []
            provider_label = metadata.get("provider_label") or metadata.get("provider")
            model = metadata.get("model")
            profile_label = metadata.get("prompt_profile_label") or metadata.get("prompt_profile")
            temperature = metadata.get("temperature")
            context_window = metadata.get("context_window")
            latency = metadata.get("latency_s")
            retrieval_latency = metadata.get("retrieval_latency_s")
            retrieved_chunks_count = metadata.get("retrieved_chunks_count")
            rag_top_k = metadata.get("rag_top_k")

            if provider_label:
                info_parts.append(str(provider_label))
            if model:
                info_parts.append(str(model))
            if profile_label:
                info_parts.append(f"profile: {profile_label}")
            if temperature is not None:
                info_parts.append(f"temp: {temperature}")
            if context_window is not None:
                info_parts.append(f"ctx: {context_window}")
            if latency is not None:
                info_parts.append(f"latency: {latency}s")
            if retrieval_latency is not None:
                info_parts.append(f"retrieval: {retrieval_latency}s")
            if retrieved_chunks_count is not None:
                info_parts.append(f"retrieved chunks: {retrieved_chunks_count}")
            if rag_top_k is not None:
                info_parts.append(f"top-k: {rag_top_k}")

            if info_parts:
                st.caption(" · ".join(info_parts))

            sources = metadata.get("sources")
            if isinstance(sources, list) and sources:
                with st.expander("Sources used"):
                    for index, source in enumerate(sources, start=1):
                        if not isinstance(source, dict):
                            continue
                        source_name = source.get("source", "document")
                        score = source.get("score")
                        snippet = source.get("snippet", "")
                        chunk_id = source.get("chunk_id")

                        title_parts = [f"{index}. {source_name}"]
                        if chunk_id is not None:
                            title_parts.append(f"chunk {chunk_id}")
                        if score is not None:
                            title_parts.append(f"score {score}")

                        st.markdown("**" + " · ".join(title_parts) + "**")
                        if snippet:
                            st.code(snippet)