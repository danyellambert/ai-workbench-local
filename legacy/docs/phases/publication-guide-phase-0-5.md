# Publication Guide — Phase 0.5

## Objective

Complete Phase 0.5 of the roadmap by preparing the project for:

- local version control with Git
- a private GitHub repository
- future public release with safety and clarity

---

## Decisions adopted in this phase

- Recommended repository name: `ai-workbench-local`
- Initial visibility: **private**
- License: **MIT**
- Folder `materials_local/`: **excluded from version control**
- Recommended public release: **after Phase 4**

---

## What should not go into the public repository

- `.env`
- course materials
- class PDF
- class video
- any answer key or pre-made solution that is not an original part of the project

In the current state of the project, that means keeping `materials_local/` out of public version control.

---

## Recommended workflow

### Step 1 — Local Git

```bash
git init -b main
git add .
git commit -m "chore: initialize repository and publication policy"
git branch dev
```

### Step 2 — Private GitHub

If you are authenticated in the GitHub CLI:

```bash
gh auth login
gh repo create ai-workbench-local --private --source=. --remote=origin --push
```

If you prefer using the website:

1. create a private repository named `ai-workbench-local`
2. copy the remote URL
3. run:

```bash
git remote add origin <REPO_URL>
git push -u origin main
git push -u origin dev
```

---

## Criteria for opening the repository to the public

The project should only become public when:

- no secrets are exposed
- the README is strong
- there is at least one strong demonstrable flow
- course materials are outside the public repository
- the structure already looks original and professional

My recommendation: make it public **at the end of Phase 4**.

---

## Phase 0.5 checklist

- [x] Local Git initialized
- [x] Clean initial commit created
- [x] Branch `dev` created
- [x] License added
- [x] Publication policy defined
- [x] `materials_local/` excluded from version control
- [x] Private GitHub repository created
- [x] `origin` remote configured
- [x] Initial push completed

---

## Important note

Even with everything prepared locally, creating the remote GitHub repository depends on:

- GitHub authentication (`gh auth login`) **or**
- manual repository creation through the website

In other words: the local part can be fully automated; the account/remote part depends on GitHub access.

---

## Current status

Phase 0.5 was completed successfully for the main items:

- Git initialized
- initial commit created
- `dev` branch created
- private repository created on GitHub
- `origin` configured
- initial push completed

Recommended next step:

- start **Phase 1 — Product foundation with a better experience**

Current remote repository:

- `https://github.com/danyellambert/ai-workbench-local`