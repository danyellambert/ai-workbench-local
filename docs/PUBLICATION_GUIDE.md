# Publication Guide — Fase 0.5

## Objetivo

Concluir a Fase 0.5 do roadmap preparando o projeto para:

- versionamento local com Git
- repositório privado no GitHub
- futura publicação pública com segurança e clareza

---

## Decisões adotadas nesta fase

- Nome recomendado do repositório: `ai-workbench-local`
- Visibilidade inicial: **privado**
- Licença: **MIT**
- Pasta `materials_local/`: **fora do versionamento**
- Publicação pública recomendada: **após a Fase 4**

---

## O que não deve ir para o repositório público

- `.env`
- materiais de curso
- PDF da aula
- vídeo da aula
- qualquer gabarito ou resposta pronta que não seja parte autoral do projeto

No estado atual do projeto, isso significa manter `materials_local/` fora do versionamento público.

---

## Fluxo recomendado

### Etapa 1 — Git local

```bash
git init -b main
git add .
git commit -m "chore: initialize repository and publication policy"
git branch dev
```

### Etapa 2 — GitHub privado

Se estiver autenticado no GitHub CLI:

```bash
gh auth login
gh repo create ai-workbench-local --private --source=. --remote=origin --push
```

Se preferir pelo site:

1. criar um repositório privado chamado `ai-workbench-local`
2. copiar a URL remota
3. rodar:

```bash
git remote add origin <URL_DO_REPO>
git push -u origin main
git push -u origin dev
```

---

## Critério para abrir o repositório ao público

O projeto só deve ficar público quando:

- não houver segredo exposto
- o README estiver forte
- houver pelo menos um fluxo forte demonstrável
- os materiais de curso estiverem fora do repositório público
- a estrutura já parecer autoral e profissional

Minha recomendação: tornar público **no fim da Fase 4**.

---

## Checklist da Fase 0.5

- [x] Git local inicializado
- [ ] Commit inicial limpo criado
- [ ] Branch `dev` criada
- [x] Licença adicionada
- [x] Política de publicação definida
- [x] `materials_local/` fora do versionamento
- [ ] Repositório GitHub privado criado
- [ ] Remote `origin` configurado
- [ ] Push inicial realizado

---

## Observação importante

Mesmo com tudo preparado localmente, a criação do repositório remoto no GitHub depende de:

- autenticação no GitHub (`gh auth login`) **ou**
- criação manual do repositório pelo site

Ou seja: a parte local pode ser totalmente automatizada; a parte de conta/remoto depende do acesso ao GitHub.