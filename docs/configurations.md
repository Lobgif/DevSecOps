# Configurations & décisions

Journal des décisions d'outillage et de configuration, tenu **au fil du projet**.
Chaque entrée : **date → décision → alternatives → pourquoi → comment (commandes) → à savoir**.
Les décisions d'architecture de fond restent dans le `README.md` ; ici on note le concret.

> **Règle :** toute documentation du projet se termine par une section **Ressources** listant les
> sources **officielles** consultées. Chaque nouvelle décision ajoute ses liens dans cette section.

---

## Sommaire

1. [Gestionnaire de paquets Python — uv](#1-gestionnaire-de-paquets-python--uv)
2. [Gestionnaire de paquets frontend — pnpm](#2-gestionnaire-de-paquets-frontend--pnpm)
3. [Nettoyage des autres gestionnaires](#3-nettoyage-des-autres-gestionnaires)
4. [Base de départ de l'application](#4-base-de-départ-de-lapplication)
5. [Hébergement Git — GitHub & GitLab](#5-hébergement-git--github--gitlab)
6. [Structure du backend — architecture en couches](#6-structure-du-backend--architecture-en-couches)
7. [Ressources](#ressources)

---

## 1. Gestionnaire de paquets Python — uv

**Date :** 2026-09-27

**Décision :** `uv` (Astral) pour le backend.

**Alternatives considérées :** pip + venv, Poetry, PDM, Pipenv.

**Pourquoi :**
- Lockfile (`uv.lock`) → builds reproductibles, indispensable pour la CI (phase 3) et le scan de
  dépendances (phase 8).
- `pyproject.toml` au format **standard** (PEP 621) → pas de verrouillage sur un format propriétaire.
- Gère aussi les versions de Python et les venv.
- Binaire unique, très rapide → Dockerfile simple et build rapide.
- Outil vers lequel l'écosystème converge sur les nouveaux projets.

**Installation :** installeur autonome (et non `pip install uv`), pour qu'uv ne dépende pas du Python
système qu'il est censé gérer.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

- Emplacement : `C:\Users\lahig\.local\bin\` (`uv.exe`, `uvx.exe`, `uvw.exe`), déjà dans le PATH utilisateur.
- Version installée : 0.12.19.
- Mise à jour : `uv self update`.

**Commandes du quotidien (dans `backend/`) :**

| Action | Commande |
|---|---|
| Créer le venv + installer depuis le lockfile | `uv sync` |
| Ajouter une dépendance | `uv add <paquet>` |
| Ajouter une dépendance de dev | `uv add --dev <paquet>` |
| Retirer une dépendance | `uv remove <paquet>` |
| Lancer une commande dans le venv | `uv run <commande>` |
| Lancer l'API en dev | `uv run fastapi dev main.py` |

**À savoir :** `uv.lock` **se commite**. `.venv/` **ne se commite pas**.

---

## 2. Gestionnaire de paquets frontend — pnpm

**Date :** 2026-09-27

**Décision :** `pnpm` pour le frontend (React + TS + Vite).

**Alternatives considérées :** npm, Yarn, Bun.

**Pourquoi :**
- Strict : un import d'une dépendance non déclarée échoue (npm le laisse passer → bugs cachés).
- Store partagé + liens → économe en disque et rapide.
- Lockfile `pnpm-lock.yaml`.
- Largement adopté (Vite, Vue, nombreux monorepos).

**Installation :** via **corepack** (livré avec Node), et non `npm i -g pnpm`.

```bash
corepack enable pnpm
```

- corepack place un shim `pnpm` dans le dossier de Node (`C:\nvm4w\nodejs\`), et télécharge la
  version de pnpm demandée au premier appel.
- Version active : 12.6.0.
- Node : v24.17.0 (géré par nvm4w).
- Cache des paquets conservé : `C:\Users\lahig\AppData\Local\pnpm\store\` (variable `PNPM_HOME`).

**À savoir :**
- Dans un projet, on pourra figer la version de pnpm avec le champ `"packageManager"` du
  `package.json` → corepack utilisera exactement celle-là (utile en CI et dans Docker).
- En Docker, une seule ligne suffit : `RUN corepack enable pnpm`.
- ⚠️ corepack est livré avec Node jusqu'à la v24 ; il ne l'est plus à partir de Node 25. À revoir si
  on monte de version de Node.

---

## 3. Nettoyage des autres gestionnaires

**Date :** 2026-09-27

**Supprimé :**

| Outil | Où il était | Comment |
|---|---|---|
| Poetry (via pip) | site-packages utilisateur Python 3.13 | `python -m pip uninstall poetry poetry-core` |
| Poetry (via pipx) | `C:\Users\lahig\pipx\venvs\poetry` | `pipx uninstall poetry` |
| Poetry (installeur officiel) | `%APPDATA%\pypoetry\` | dossier supprimé |
| Poetry (lanceurs orphelins) | `~\.local\bin\poetry.exe`, `%APPDATA%\Python\Scripts\poetry.exe` | fichiers supprimés |
| uv (via pip) | site-packages utilisateur Python 3.13 | `python -m pip uninstall uv` (remplacé par l'installeur autonome) |
| pipx | site-packages utilisateur Python 3.13 | `python -m pip uninstall pipx` + dossier `~\pipx` supprimé |
| pnpm (via npm global) | `%APPDATA%\npm\` | `npm uninstall -g pnpm` |
| pnpm (autonome) | `%LOCALAPPDATA%\pnpm\.tools\` + lanceurs | fichiers supprimés (store conservé) |

**Conservé volontairement :**

| Outil | Pourquoi |
|---|---|
| pip | Fait partie de Python. On ne l'utilise plus directement sur ce projet. |
| npm | Livré avec Node ; le supprimer peut casser Node / nvm4w. On ne l'utilise plus sur ce projet. Des outils globaux d'autres projets en dépendent encore (`@vue/cli`, `openapi-generator-cli`, …). |

**Remplacement de pipx :** pipx installait des **outils Python en ligne de commande** (ruff, black,
pre-commit…) chacun dans son propre venv isolé, disponibles partout. uv fait la même chose :

| pipx | uv |
|---|---|
| `pipx install ruff` | `uv tool install ruff` |
| `pipx run ruff` (sans installer) | `uvx ruff` |
| `pipx list` | `uv tool list` |
| `pipx upgrade-all` | `uv tool upgrade --all` |

---

## 4. Base de départ de l'application

**Date :** 2026-09-27

Point de départ volontairement **minimal** (générée par l'IA sur autorisation explicite ; tout le reste
se fait à la main) :

- `backend/main.py` : FastAPI + Pydantic, 2 routes.
  - `POST /positions` → valide `vehicle_id`, `lat` (-90..90), `lon` (-180..180), renvoie 201 ou 422.
  - `GET /positions` → liste des positions.
  - Stockage **en mémoire** (perdu au redémarrage) — PostGIS en phase 2.
- `backend/pyproject.toml` : dépendance unique `fastapi[standard]`.
- `frontend/index.html` : une page HTML/JS brute (formulaire + liste). Pas encore de React/Vite.

**Configuration à connaître :**
- API sur `http://localhost:8000`, doc Swagger sur `/docs`.
- CORS : seules les origines `http://localhost:5500` et `http://127.0.0.1:5500` sont autorisées →
  le frontend doit être servi sur le port 5500.
- Structure de dossiers **provisoire** : l'architecture reste à concevoir (README, section 5).

---

## 5. Hébergement Git — GitHub & GitLab

**Date :** 2026-09-27

**Décision :** le projet est hébergé sur **les deux plateformes**, créées **entièrement en ligne de
commande** (`gh`, `glab`) pour apprendre leurs CLI et leurs API. GitHub d'abord, GitLab ensuite.

| | GitHub | GitLab |
|---|---|---|
| Dépôt | `Lobgif/DevSecOps` | `personnel4344847/DevSecOps` (groupe « Personnel ») |
| URL | https://github.com/Lobgif/DevSecOps | https://gitlab.com/personnel4344847/DevSecOps |
| Visibilité | public | privé |
| Branche par défaut | aucune (dépôt vide) | `main` |
| Créé avec | `gh repo create DevSecOps --public` | `glab repo create DevSecOps --group personnel4344847` |

**Vocabulaire :** GitHub dit *repository*, GitLab dit *project*. Un groupe GitLab ≈ une organisation GitHub.

**Leçon — `name` vs `path` sur GitLab :**
- `name` = nom affiché (« Personnel ») ; `path` / `full_path` = identifiant dans les URL et pour l'API/CLI.
- Les chemins de premier niveau sont **uniques sur tout gitlab.com** : `personnel` étant pris, le groupe a
  reçu `personnel4344847`. D'où l'erreur `404 Not Found` avec `--group Personnel`.
- `--group` attend **uniquement** le `full_path` du groupe ; le nom du projet est un argument à part.
- Retrouver le chemin : `glab api "groups?search=Personnel&min_access_level=50" | jq -r '.[] | "\(.name) -> \(.full_path)"'`
  (`min_access_level=50` = Owner ; niveaux : 10 Guest, 20 Reporter, 30 Developer, 40 Maintainer, 50 Owner).
- `glab` 1.51 n'a pas de commande `group` → passer par `glab api groups` / `glab api namespaces`.

### 5.1 Remotes & authentification — HTTPS

**Décision :** remotes en **HTTPS** sur les deux plateformes (pas SSH), pour éviter la gestion de
clés multiples. Deux remotes nommés explicitement `github` et `gitlab` (plutôt qu'`origin`, qui n'est
qu'une convention pour un remote unique).

**Alternatives considérées :** SSH (voir 5.2, gardé comme référence).

**Qui fournit les identifiants en HTTPS :**
- **Git Credential Manager (GCM)**, livré avec Git for Windows, déjà configuré au niveau système
  (`credential.helper = manager`, `C:/Program Files/Git/etc/gitconfig`, GCM 2.5.0). Au premier `push`,
  il ouvre le navigateur (OAuth) puis stocke le jeton dans le gestionnaire d'identifiants Windows.
  Fonctionne pour GitHub **et** GitLab.
- Optionnel pour GitHub : `gh auth setup-git` fait utiliser à git le jeton déjà obtenu par `gh`
  (compte `Lobgif`), au lieu de GCM, uniquement pour `github.com`.

**Commandes (depuis la racine du projet) :**

```bash
# (optionnel) git réutilise l'authentification de gh pour github.com
gh auth setup-git

git remote add github https://github.com/Lobgif/DevSecOps.git
git remote add gitlab https://gitlab.com/personnel4344847/DevSecOps.git

# vérifier
git remote -v

# pousser une branche (-u = mémoriser la branche distante suivie)
git push -u github <branche>
git push -u gitlab <branche>
```

### 5.1 bis Premier push (sur les deux plateformes)

**Décision :** le premier push se fait **depuis la branche de travail `feature/github`**, vers les deux
remotes. `main` / `dev` seront alimentées ensuite par PR (GitHub) / MR (GitLab).

```bash
git add .
git status                        # relire la liste avant de commiter
git commit -m "Initial commit: base FastAPI en couches, page frontend, docs"
git push -u github feature/github
git push -u gitlab feature/github
```

**Conséquences à connaître :**
- Sur un dépôt distant vide, la **première branche poussée devient la branche par défaut** →
  `feature/github` le deviendra sur GitHub. À rebasculer une fois `main` créée :
  `gh repo edit Lobgif/DevSecOps --default-branch main` ;
  côté GitLab : `glab api -X PUT "projects/personnel4344847%2FDevSecOps" -f default_branch=main`.
- Une PR/MR a besoin d'une **branche cible qui existe** et d'un **historique commun**. Si `main` est créée
  plus tard à partir de ce même commit, la PR `feature/github → main` sera **vide** (rien à fusionner) :
  seuls les commits *suivants* de la branche de travail feront l'objet de PR/MR.
- Alternative (non retenue) : commencer `main` par un commit vide (`git commit --allow-empty`), la pousser,
  puis créer la branche de travail → la toute première PR/MR contient tout le code.

- `-u` (`--set-upstream`) mémorise la branche distante suivie → ensuite `git push` / `git pull` suffisent
  (vers le remote mémorisé ; pour l'autre, préciser le remote : `git push gitlab`).
- Premier push HTTPS → Git Credential Manager ouvre le navigateur pour s'authentifier (une fois par plateforme).

### 5.2 Référence SSH (non retenu, gardé pour plus tard)

**Diagnostic du 2026-09-27 :**

| Test | Résultat | Cause |
|---|---|---|
| `ssh -T git@github.com` | `Permission denied (publickey)` | aucune clé SSH enregistrée sur le compte `Lobgif` (https://github.com/Lobgif.keys vide) |
| `ssh -T git@gitlab.com` | `Welcome to GitLab, @IbrahimaFofana!` | une clé par défaut de `~/.ssh` est enregistrée sur GitLab |

- Le fichier de config SSH s'appelle `~/.ssh/config.txt` → **ignoré** : SSH ne lit que `~/.ssh/config`.
- S'il était renommé tel quel, `github.com` utiliserait `id_ed25519_github_ecoles` (un autre compte,
  a priori celui de l'école), pas `Lobgif`.
- La clé adaptée à `Lobgif` : `~/.ssh/id_ed25519_github` (commentaire `lahigic@gmail.com`).

**Si un jour on passe en SSH sur GitHub :**

```bash
# 1. donner à gh le droit de gérer les clés SSH (scope manquant)
gh auth refresh -h github.com -s admin:public_key

# 2. enregistrer la clé PUBLIQUE (.pub, jamais la privée)
gh ssh-key add ~/.ssh/id_ed25519_github.pub --title "IBRAHIMA-laptop"
```

3. Plusieurs comptes GitHub → **alias d'hôte** dans `~/.ssh/config` (en gardant l'entrée de l'école) :

```
Host github-lobgif
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github
  IdentitiesOnly yes
```

`IdentitiesOnly yes` = n'essayer que cette clé (sinon SSH peut s'authentifier avec le mauvais compte).

```bash
# 4. tester, puis utiliser l'alias dans l'URL du remote
ssh -T git@github-lobgif
git remote add github git@github-lobgif:Lobgif/DevSecOps.git

# GitLab en SSH (fonctionne déjà)
git remote add gitlab git@gitlab.com:personnel4344847/DevSecOps.git
```

**⚠️ Points ouverts (à régler par toi) :**
- ✅ Dépôt git imbriqué `./DevSecOps/.git` (créé par `glab repo create`) : supprimé.
- ✅ Remotes `github` et `gitlab` ajoutés au dépôt racine, en HTTPS (passés de SSH à HTTPS avec
  `git remote set-url`).
- Travail en cours sur la branche `feature/github` ; branche principale à aligner sur `main`
  (branche par défaut côté GitLab).
- Pas encore de `.gitignore` (à prévoir : `.venv/`, `__pycache__/`, `node_modules/`, `.idea/`).
- `glab` à mettre à jour (1.51.0 → 1.119.0 disponible) : `winget upgrade GLab.GLab`.

---

## 6. Structure du backend — architecture en couches

**Date :** 2026-09-27

**Décision :** backend organisé **en couches** (par rôle technique), avec un dossier par couche :

| Dossier | Rôle | Dépend de |
|---|---|---|
| routes | Couche HTTP : reçoit la requête, appelle un service, renvoie la réponse et le code HTTP. Aucune logique métier. | schemas, services |
| schemas | Modèles Pydantic : contrats d'entrée/sortie de l'API (validation, sérialisation). | — |
| services | Logique métier : règles, orchestration. Ne connaît ni HTTP ni SQL. | schemas, repositories |
| repositories | Accès aux données : seule couche qui parle à la base (PostGIS en phase 2). | base de données |

**Sens des dépendances :** `routes → services → repositories → base`. Une couche n'appelle jamais
celle du dessus (un repository n'importe pas un service, un service n'importe pas FastAPI).

**Alternatives considérées :** orientée domaine / *feature-based* (un dossier par domaine métier,
ex. `positions/`, `auth/`, chacun avec ses routes/services/…). Plus scalable, mais plus de cérémonie
pour une API de 2-5 routes. Voir README, section 5.

**Arborescence réalisée (2026-09-27) :**

```
backend/
├── main.py          # point d'entrée (création de l'app, branchement des routes)
├── pyproject.toml
├── .gitignore
├── core/            # config, secrets, sécurité (JWT, hash)
├── models/          # modèles de base de données (ORM) — phase 2
├── repositories/    # accès aux données
├── routes/          # couche HTTP (APIRouter)
├── schemas/         # modèles Pydantic (contrats API)
├── services/        # logique métier
└── utils/           # fonctions utilitaires transverses
```

| Dossier ajouté | Rôle |
|---|---|
| core | Configuration (variables d'environnement), secrets, sécurité (JWT, hash). |
| models | Modèles ORM (tables PostGIS) — distincts des schemas Pydantic. |
| utils | Petites fonctions transverses sans dépendance métier. ⚠️ Ne doit pas devenir un fourre-tout : si une fonction appartient à une couche, elle va dans cette couche. |

**Exemple de découpage (généré par l'IA sur autorisation explicite, 2026-09-27) :** l'ancien `main.py`
réparti dans les couches, comportement identique (testé : 201, 422, liste, CORS).

| Fichier | Contenu |
|---|---|
| `main.py` | crée l'app, ajoute le CORS, `app.include_router(position.router)` |
| `core/config.py` | `ALLOWED_ORIGINS` |
| `schemas/position.py` | `PositionIn`, `PositionOut` |
| `routes/position.py` | `APIRouter(prefix="/positions")` : `POST` et `GET`, délèguent au service |
| `services/position.py` | ajoute `recorded_at`, appelle le repository |
| `repositories/position.py` | stockage en mémoire : `save()`, `find_all()` |
| `*/__init__.py` | fichiers vides : font de chaque dossier un package et le rendent suivi par git |

- `models/` et `utils/` restent vides (pas d'ORM tant qu'il n'y a pas de base).
- Les imports sont **absolus depuis `backend/`** (`from schemas.position import ...`) : ça marche parce
  que `fastapi dev main.py` est lancé depuis `backend/`, qui est alors dans le chemin d'import Python.

**`.gitignore` :** un par zone (racine : `.idea` ; `backend/` : modèle officiel Python de GitHub ;
`frontend/` : modèle Node ; `infrastructures/` : modèle Terraform). Vérifié : `.venv` et `.env` sont
ignorés, `uv.lock` ne l'est **pas** (il doit être commité).

---

<!-- Ajouter les nouvelles décisions au-dessus de cette ligne, en suivant le même format. -->

## Ressources

Sources officielles uniquement. Vérifiées le 2026-09-27.

### uv
- Documentation — https://docs.astral.sh/uv/
- Installation (installeur autonome) — https://docs.astral.sh/uv/getting-started/installation/
- Projets (`pyproject.toml`, `uv.lock`, `uv sync`) — https://docs.astral.sh/uv/concepts/projects/
- Outils (`uv tool`, `uvx`, remplaçant de pipx) — https://docs.astral.sh/uv/guides/tools/

### Packaging Python (standard)
- Spécification `pyproject.toml` — https://packaging.python.org/en/latest/specifications/pyproject-toml/
- PEP 621 (métadonnées de projet dans `pyproject.toml`) — https://peps.python.org/pep-0621/

### pnpm & corepack
- Pourquoi pnpm (store partagé, strictness) — https://pnpm.io/motivation
- Installation (dont via corepack) — https://pnpm.io/installation
- Corepack (doc Node.js) — https://nodejs.org/api/corepack.html
- Corepack (dépôt officiel) — https://github.com/nodejs/corepack

### FastAPI & Pydantic
- FastAPI — https://fastapi.tiangolo.com/
- FastAPI CLI (`fastapi dev`) — https://fastapi.tiangolo.com/fastapi-cli/
- CORS — https://fastapi.tiangolo.com/tutorial/cors/
- Pydantic — https://docs.pydantic.dev/latest/
- Pydantic `Field` (contraintes `ge`, `le`, `min_length`…) — https://docs.pydantic.dev/latest/concepts/fields/
- Structurer une application plus grande (`APIRouter`, `include_router`) — https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Bases de données SQL avec FastAPI — https://fastapi.tiangolo.com/tutorial/sql-databases/
- Packages Python (`__init__.py`) — https://docs.python.org/3/tutorial/modules.html#packages

### GitHub (gh + API)
- Manuel gh — https://cli.github.com/manual/
- `gh api` (appeler l'API directement) — https://cli.github.com/manual/gh_api
- API REST GitHub — https://docs.github.com/en/rest
- Endpoints dépôts (création, etc.) — https://docs.github.com/en/rest/repos/repos

### GitLab (glab + API)
- glab — https://docs.gitlab.com/cli/
- API REST GitLab — https://docs.gitlab.com/api/rest/
- API Projects (création, etc.) — https://docs.gitlab.com/api/projects/
- API Groups (lister, `min_access_level`) — https://docs.gitlab.com/api/groups/
- API Namespaces (utilisateur + groupes) — https://docs.gitlab.com/api/namespaces/
- Niveaux d'accès / permissions — https://docs.gitlab.com/user/permissions/
- `glab api` — https://docs.gitlab.com/cli/api/
- `glab repo create` — https://docs.gitlab.com/cli/repo/create/

### Git
- `git remote` — https://git-scm.com/docs/git-remote
- `git init` (option `--initial-branch`) — https://git-scm.com/docs/git-init
- `git switch` — https://git-scm.com/docs/git-switch
- `git push` (option `-u` / `--set-upstream`) — https://git-scm.com/docs/git-push
- GitHub : changer la branche par défaut — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/changing-the-default-branch
- `gh repo edit` (`--default-branch`) — https://cli.github.com/manual/gh_repo_edit
- GitLab : branche par défaut — https://docs.gitlab.com/user/project/repository/branches/default/
- `gitignore` — https://git-scm.com/docs/gitignore
- Modèles `.gitignore` officiels de GitHub (Python, Node, Terraform…) — https://github.com/github/gitignore
- Sous-modules (pourquoi éviter un dépôt imbriqué) — https://git-scm.com/book/en/v2/Git-Tools-Submodules
- Manuel `gh repo create` — https://cli.github.com/manual/gh_repo_create
- À propos des remotes (HTTPS vs SSH) — https://docs.github.com/en/get-started/git-basics/about-remote-repositories
- Git Credential Manager — https://github.com/git-ecosystem/git-credential-manager
- `gh auth setup-git` — https://cli.github.com/manual/gh_auth_setup-git

### SSH
- GitHub : se connecter en SSH — https://docs.github.com/en/authentication/connecting-to-github-with-ssh
- GitLab : clés SSH — https://docs.gitlab.com/user/ssh/
- `gh auth refresh` (ajout de scopes) — https://cli.github.com/manual/gh_auth_refresh
- `gh ssh-key add` — https://cli.github.com/manual/gh_ssh-key_add
- `ssh_config` (Host, IdentityFile, IdentitiesOnly) — https://man.openbsd.org/ssh_config
- Mirroring de dépôts — https://docs.gitlab.com/user/project/repository/mirror/
