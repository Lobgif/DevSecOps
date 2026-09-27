# FleetTrack

Système de suivi de position en temps réel — **projet d'apprentissage**.

> Ce dépôt n'est pas un produit, c'est un terrain d'entraînement. L'objectif n'est pas de livrer vite,
> c'est de comprendre en profondeur. Certaines décisions sont donc volontairement faites « à la main »
> (ex. l'authentification) là où, en vraie production, on prendrait une solution clé en main.

---

## 1. Pourquoi ce projet

Apprendre **l'ops de bout en bout** (conteneurisation, orchestration Kubernetes, GitOps, observabilité,
DevSecOps) sur un vrai projet déployé, tout en pratiquant réellement TypeScript (via un framework) et
FastAPI. L'application est délibérément **minimale** : elle sert de support à l'infra, elle n'est pas le but.

Trois raisons d'avoir choisi ce projet précis :

- **Il s'appuie sur une force existante — le géospatial.** PostGIS, une carte : terrain déjà maîtrisé,
  donc la difficulté se concentre là où on la veut (l'ops), pas partout.
- **Il traverse pile les couches visées.** 2-3 petits services (microservices sans sur-ingénierie),
  des données qui bougent (idéal pour l'observabilité), de la charge qu'on peut faire monter (idéal pour
  le scaling et le self-healing sur Kubernetes).
- **Il fait double emploi comme pièce de portfolio** : montre « géomaticien qui code ET qui déploie sur
  Kubernetes » — un positionnement rare et recherché.

**Périmètre :** application minimale (2-3 services, 2-5 routes). La profondeur vient des couches empilées,
pas du nombre de fonctionnalités.

---

## 2. Objectifs d'apprentissage

- FastAPI en profondeur (async, Pydantic, dépendances, structuration).
- TypeScript en profondeur via un framework frontend.
- Notions d'architecture d'API (couches, validation, gestion d'erreurs, versioning).
- Conteneurisation (Docker) et CI.
- Orchestration Kubernetes réelle, multi-nœuds.
- Observabilité (métriques, logs, dashboards).
- GitOps (déploiement déclaratif piloté par Git).
- DevSecOps (secrets, scan d'images, RBAC, network policies).

## 3. Hors périmètre (volontaire — ne PAS faire)

- Pas de SSR / méta-framework (voir décision frontend).
- Pas de gestion d'état complexe côté frontend (Redux & co.).
- Pas de SSO.
- Pas de « 10 microservices » : on plafonne à 3.
- Pas d'ajout de features tant que les couches ops ne sont pas maîtrisées.

---

## 4. Décisions technologiques

Format : **choix → alternatives considérées → justification**. Ces décisions sont figées ; arrête de
ré-optimiser le choix des outils et va construire.

### Backend — FastAPI
*Alternatives :* Django, Flask (Python) ; Express/NestJS (Node).
*Pourquoi :* async natif (adapté à de l'ingestion de positions), validation Pydantic intégrée, doc OpenAPI
automatique, doc officielle excellente sur JWT. Django est trop lourd/opinionated pour une petite API ;
Flask demande d'assembler soi-même trop de briques ; passer au Node casserait l'objectif « FastAPI en profondeur ».

### Base de données — PostgreSQL + PostGIS
*Alternatives :* MongoDB ; PostgreSQL seul.
*Pourquoi :* les positions sont des données **spatiales** — PostGIS donne les types et requêtes géo natifs,
et c'est le standard du monde SIG (valeur carrière). Mongo n'apporte rien ici et perd le relationnel ;
Postgres sans PostGIS obligerait à réimplémenter le spatial à la main.

### Frontend — React + TypeScript + Vite
*Alternatives :* Next.js, Nuxt (Vue), Angular.
*Pourquoi :* le backend est déjà FastAPI, donc le principal atout de Next/Nuxt (être aussi le backend + SSR)
est redondant ou en conflit. L'app est un dashboard **privé, derrière login** → pas de SEO, le SSR ne sert
à rien et se marie mal avec une carte WebGL. Vite compile en **fichiers statiques** servis par un petit
conteneur nginx : l'artefact de déploiement idéal pour l'objectif ops. Angular est trop lourd pour une carte.
*Note :* Vue 3 + TS est une alternative valable si on veut une courbe plus douce. Éviter absolument
Next/Nuxt « en SPA, SSR désactivé » = toute la complexité, aucun bénéfice.

### Cartographie — MapLibre GL
*Alternatives :* OpenLayers, Leaflet.
*Pourquoi :* rendu WebGL fluide, adapté à des points qui s'animent en temps réel ; API moderne ;
`react-map-gl` pour une intégration propre. OpenLayers est plus complet côté SIG lourd (projections, WFS/WMS)
mais verbeux et inutile ici — à garder pour un approfondissement SIG futur. Leaflet ne gère pas le WebGL
aussi bien pour l'animation temps réel.

### Authentification — JWT « maison » (phase 1)
*Alternatives :* OAuth2/OIDC délégué (« login Google ») ; SSO.
*Pourquoi (apprentissage) :* coder le login/hash (bcrypt ou argon2), l'émission et la validation du JWT,
les refresh tokens et la protection des routes = valeur d'apprentissage maximale ; on voit les mécanismes
que tout le reste cache. OAuth2/OIDC = enhancement optionnel en phase 2 pour voir le flow délégué.
SSO = over-engineering pour une seule app.
*Honnêteté :* rouler sa propre auth est bon pour **apprendre**, pas pour la vraie prod — en prod (ex. KlassIvoire),
préférer une solution éprouvée.

### Orchestration — Kubernetes via k3s (3 VM)
*Alternatives :* Docker Swarm ; kubeadm ; Kubernetes managé (EKS/GKE/AKS).
*Pourquoi :* Kubernetes est le standard (~82 % d'adoption en prod, enquête CNCF 2025) et **tout l'écosystème
visé — GitOps/ArgoCD, Helm, networking avancé — est K8s-natif** (inexistant côté Swarm). k3s = vrai Kubernetes,
léger, multi-nœuds réel sur les 3 VM, bien moins douloureux que kubeadm. Swarm est plus simple mais marginal
(~2,5 % de marché) et sans l'écosystème visé → au mieux 2 jours d'échauffement, sinon skip. Managé (EKS/GKE)
cacherait précisément ce qu'on veut apprendre (nœuds, control plane, réseau). kubeadm = « mode difficile »
pour plus tard si on veut disséquer le control plane.

### Déploiement continu — GitOps avec ArgoCD
*Alternatives :* Flux ; push CI classique (`kubectl apply` depuis la CI).
*Pourquoi :* modèle déclaratif piloté par Git, cœur du platform engineering moderne ; ArgoCD a une UI qui
aide à *voir* la synchro pendant l'apprentissage. Flux est excellent aussi (plus « pur », moins d'UI).
Le push CI classique n'enseigne pas le modèle GitOps.

### Observabilité — Prometheus + Grafana + Loki
*Alternatives :* stack ELK/EFK ; solution hébergée (Datadog, Grafana Cloud).
*Pourquoi :* standard cloud-native, s'installe sur le cluster, enseigne métriques (Prometheus),
dashboards (Grafana) et logs (Loki) avec le *pourquoi*. ELK est plus lourd et orienté logs ; l'hébergé
cacherait le fonctionnement qu'on veut comprendre.

---

## 5. Architecture & organisation des dossiers — **À CONCEVOIR (par toi)**

> Cette section est **volontairement vide de réponses**. Concevoir la structure, c'est l'apprentissage clé
> de « notions d'architecture d'API ». Je te donne les patterns et les critères ; tu décides, tu remplis,
> et tu me montres pour critique. Ne me demande pas de générer l'arborescence — demande-moi de critiquer la tienne.

### Patterns de structuration backend FastAPI (à choisir)
- **En couches (layered)** : séparer par *rôle technique* — ex. routers / services (logique métier) /
  repositories (accès données) / models (ORM) / schemas (Pydantic) / core (config, sécurité).
  *Force :* clair pour un petit projet. *Faiblesse :* se disperse quand les domaines grossissent.
- **Orienté domaine (feature-based)** : séparer par *domaine métier* — chaque domaine (ex. `positions`,
  `auth`) porte ses propres routers/services/models.
  *Force :* scalable, cohésion forte. *Faiblesse :* un peu de cérémonie pour un très petit projet.

### Frontend (à choisir)
- Par type (components / hooks / services / pages) vs par feature.
- Où isole-t-on l'appel à l'API ? Comment structure-t-on la logique carte vs le reste ?

### Mono-repo vs multi-repo (à trancher)
- Un seul dépôt pour les 3 services + le frontend + les manifests, ou séparés ? Quel impact sur la CI et le GitOps ?

### Questions que TU dois trancher
- Quels sont exactement tes 2-3 services et leur responsabilité (frontière de chacun) ?
- Quelles sont tes 2-5 routes et leurs contrats (entrée/sortie) ?
- Quel schéma PostGIS minimal (table positions : quoi comme colonnes, quel type géométrie, quel index) ?
- Comment les services se parlent-ils, et lesquels sont exposés via l'ingress ?
- Où vivent les secrets (clé JWT, identifiants DB) à chaque phase ?

*→ Une fois conçue, documente TA structure ici.*

---

## 6. Règles d'apprentissage (le cadre anti-pilote-automatique)

Ce projet est en **mode apprentissage** (à distinguer de KlassIvoire, qui reste en **mode production**, IA à fond).
Sur CE dépôt :

- L'IA **n'écrit jamais** le code ni les YAML. Ligne rouge.
- Tu **tentes toujours en premier**, même faux, même moche — *ensuite* tu demandes.
- Quand tu es bloqué : tu restes avec l'erreur, tu cherches, puis tu demandes **« pourquoi / explique »**,
  jamais **« répare / génère »**.
- Tu **tapes**, tu ne colles pas.
- Test de fin d'étape : **laptop fermé, je sais refaire et réexpliquer**. Sinon, ce n'est pas appris.

---

## 7. Feuille de route par phases

Chaque phase produit quelque chose qui marche, sur lequel la suivante se pose. On ne saute jamais en avant.

- [ ] **Phase 0 — Soutenance.** On ne lance rien avant qu'elle soit passée.
- [ ] **Phase 1 — App minimale.** 2-3 services containerisables + JWT de base (routes protégées, vrais secrets).
      *Fini quand :* ça tourne en local et je réexplique chaque partie.
- [ ] **Phase 2 — Architecture API & PostGIS.** Refactor en couches/domaines, validation, gestion d'erreurs,
      schéma spatial. *Fini quand :* structure défendable et données géo lues/écrites proprement.
- [ ] **Phase 3 — Conteneurisation + CI.** Docker (à fond), pipeline (tests + build d'image au push).
      *Fini quand :* un push produit les images automatiquement.
- [ ] **Phase 4 — k3s sur 3 VM + déploiement.** Cluster réel, Deployments/Services/Ingress/Secrets.
      *Fini quand :* l'app est accessible depuis le cluster et je comprends chaque manifest.
- [ ] **Phase 5 — Orchestration.** Scaling, rolling updates, self-healing, health probes, resource limits.
      *Fini quand :* je provoque une panne et je la vois se réparer.
- [ ] **Phase 6 — Observabilité.** Prometheus/Grafana/Loki : métriques, logs, dashboards.
      *Fini quand :* je lis la latence/le débit et je retrouve un log précis.
- [ ] **Phase 7 — GitOps/ArgoCD.** Déploiements déclaratifs pilotés par Git.
      *Fini quand :* un commit sur le repo de manifests déploie tout seul.
- [ ] **Phase 8 — DevSecOps.** Secrets (Vault), scan d'images, RBAC, network policies, shift-left.
      *Fini quand :* je sais dire ce que chaque mesure protège et pourquoi.

---

*Rappel de tempo : même minimal, fait à la main et en profondeur sur l'infra, c'est plusieurs mois à temps
partiel. La profondeur est lente — c'est normal, pas un échec.*
