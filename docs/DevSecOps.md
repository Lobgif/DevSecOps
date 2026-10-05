# DevSecOps — journal d'apprentissage

Tout ce que j'apprends et pratique **en dehors du projet FleetTrack** : outils, commandes, options, et
surtout le **pourquoi**. Tenu au fil de l'eau.

> **Règle de rangement**
> - Par défaut, ce que je fais va **ici** (`docs/DevSecOps.md`).
> - Quand un message commence par **« projet : … »**, ça concerne FleetTrack et va dans
>   [`configurations.md`](configurations.md).
>
> **Format d'une entrée :** date → ce que j'ai fait → **pourquoi** → les **commandes** avec chaque
> **option** expliquée → pièges rencontrés → sources dans la section Ressources.
>
> **Sources, pour chaque entrée, toujours les deux :**
> 1. la **documentation officielle** de l'outil ;
> 2. la page correspondante du **guide de Stéphane Robert** (blog.stephane-robert.info), quand elle existe.

---

## Sommaire

1. [Environnement Docker — WSL2 sans Docker Desktop](#1-environnement-docker--wsl2-sans-docker-desktop)
2. [asdf — gestionnaire de versions d'outils](#2-asdf--gestionnaire-de-versions-doutils)
3. [`wsl` ou `ssh` : entrer dans une machine](#3-wsl-ou-ssh--entrer-dans-une-machine)
4. [Images multi-plateformes — `docker buildx`](#4-images-multi-plateformes--docker-buildx)
5. [Artefacts OCI — un registre ne stocke pas que des images](#5-artefacts-oci--un-registre-ne-stocke-pas-que-des-images)
6. [Concepts Docker — image, conteneur, couches, isolation](#6-concepts-docker--image-conteneur-couches-isolation)
7. [autoheal — redémarrer les conteneurs « unhealthy »](#7-autoheal--redémarrer-les-conteneurs--unhealthy-)
8. [Logs d'un conteneur : `docker logs` et les pilotes de logs](#8-logs-dun-conteneur--docker-logs-et-les-pilotes-de-logs)
9. [`docker stats` : quelles colonnes surveiller, et pourquoi](#9-docker-stats--quelles-colonnes-surveiller-et-pourquoi)
10. [PID 1 et les signaux : pourquoi `docker stop` met 10 secondes](#10-pid-1-et-les-signaux--pourquoi-docker-stop-met-10-secondes)
11. [Ressources](#ressources)

---

## 1. Environnement Docker — WSL2 sans Docker Desktop

**Date :** 2026-09-28

### 1.1 Décision

**Décision :** apprendre Docker sur un **Docker Engine natif installé dans WSL2 (Ubuntu-24.04)**, sans passer
par Docker Desktop.

**Alternatives considérées :**

| Option | Pourquoi pas (maintenant) |
|---|---|
| Docker Desktop | Cache le démon dans sa propre distribution (`docker-desktop`) : on ne voit ni systemd, ni `dockerd`, ni les namespaces/cgroups (chapitre 3 du guide Stéphane Robert). |
| VirtualBox / VM locale | Exclu volontairement. |
| Dual boot | Linux 100 % natif, mais redémarrage pour changer d'OS. |
| VM dans le cloud | Vraie IP publique, proche de la prod — **retenu pour la phase 4** (k3s sur 3 nœuds), pas pour apprendre Docker. |

**Pourquoi WSL2 :** vrai noyau Linux (Microsoft le fait tourner dans une VM légère qu'on n'administre pas),
gratuit, sans risque, déjà installé. Limites : une seule machine (pas de multi-nœuds), réseau NATé par Windows,
et le disque virtuel `ext4.vhdx` grossit sans rétrécir tout seul.

### 1.2 Coexistence avec Docker Desktop (constat du 2026-09-28)

Distributions WSL présentes (`wsl -l -v`) : `Ubuntu` (par défaut), `Ubuntu-24.04`, `docker-desktop`.

| Réglage Docker Desktop (`%APPDATA%\Docker\settings-store.json`) | Valeur | Conséquence |
|---|---|---|
| Intégration avec la distribution par défaut | activée | ne touche que `Ubuntu` |
| Intégration avec d'autres distributions | aucune | **`Ubuntu-24.04` n'est pas concernée** → pas de conflit |
| Démarrage automatique | désactivé | — |

- ⚠️ **Ne pas** faire `wsl --set-default Ubuntu-24.04` : l'intégration « distribution par défaut » s'y
  appliquerait et deux Docker se marcheraient dessus.
- Ouvrir la bonne distribution : `wsl -d Ubuntu-24.04` (nom **exact**, sensible à la casse : `ubuntu24.04`
  → `WSL_E_DISTRO_NOT_FOUND`). Astuce : `wsl -l -v` pour les noms, `Tab` pour compléter.
- Piège : avant l'installation, `docker` dans Ubuntu pointait sur le `docker.exe` **Windows**
  (`/mnt/c/Program Files/Docker/...`), injecté par l'interop WSL (PATH Windows ajouté). Après l'installation,
  `/usr/bin/docker` passe devant. Vérifier avec `which -a docker`. Option pour supprimer l'ambiguïté :
  `appendWindowsPath=false` dans `/etc/wsl.conf` (non fait).
- Toujours savoir à quel démon on parle : `docker context ls`, `docker info`.

### 1.3 Installation de Docker Engine

Source : dépôt apt **officiel Docker** (pas le paquet `docker.io` d'Ubuntu, souvent en retard), procédure
de la doc « Install Docker Engine on Ubuntu ».

1. Clé GPG de Docker dans `/etc/apt/keyrings/docker.asc` + dépôt dans `/etc/apt/sources.list.d/docker.sources`.
2. `sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin`

**Versions installées :** Docker Engine **29.8.1**, containerd **2.3.6**, Buildx **0.37.1**,
Docker Compose **v5.5.1** (+ `docker-ce-rootless-extras`, dépendance → mode rootless disponible).

**Vérifications faites :**

| Contrôle | Résultat |
|---|---|
| PID 1 | `systemd` (donc `systemctl` fonctionne dans WSL) |
| `systemctl is-active docker` | `active` ; service `enabled` (démarrage auto déjà activé par défaut sur Ubuntu) |
| `which -a docker` | `/usr/bin/docker` en premier (`/bin/docker` = même fichier, `/bin` → `/usr/bin`) |
| `systemctl status docker` | `/usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock` → Docker s'appuie sur containerd |

**Avertissements `WARNING: No blkio…` au démarrage :** normaux sous WSL2 — le noyau n'expose pas certains
contrôleurs cgroups d'I/O disque ; Docker ne pourra pas limiter le débit disque d'un conteneur. Sans impact
pour apprendre.

**Leçons en passant :**
- Travailler dans `~` (`/home/lahigic`), pas dans `/mnt/c/WINDOWS/system32` (dossier de départ d'un terminal
  lancé depuis un PowerShell admin). `cd -` = dossier **précédent** (erreur `OLDPWD not set` s'il n'y en a pas) ;
  `cd ~` ou `cd` = dossier personnel.
- `systemctl status` ouvre un pager : `q` pour quitter.

### 1.4 Post-installation : groupe `docker`

```bash
sudo groupadd docker            # déjà existant (créé par le paquet docker-ce) → sans effet
sudo usermod -aG docker $USER   # -G : groupes secondaires ; -a : AJOUTER (sans -a, la liste est remplacée → perte de sudo !)
newgrp docker                   # nouveau shell qui connaît le groupe, dans CE terminal seulement
```

- Les groupes sont lus **à l'ouverture de session** → `newgrp` est temporaire (un `exit` en sort). Solution
  durable dans WSL : `wsl --terminate Ubuntu-24.04` puis rouvrir. Vérifier avec `id`.
- Pourquoi ça donne l'accès : `/var/run/docker.sock` est `srw-rw---- root docker`.
- ⚠️ **DevSecOps : groupe `docker` = équivalent root** (ex. `docker run -v /:/host …` monte tout le système).
  Acceptable sur une machine d'apprentissage ; sur un serveur, limiter ce groupe ou passer en **rootless**.
- Test : `docker run hello-world` sans `sudo` → OK. Le message décrit l'architecture : client → démon (via le
  socket) → pull depuis un registre (Docker Hub) → création du conteneur → sortie renvoyée au client.

### 1.5 Rotation des logs des conteneurs

**Pourquoi :** le pilote `json-file` écrit un fichier par conteneur qui grossit sans limite ; dans WSL2 le
`ext4.vhdx` ne rend pas l'espace libéré.

**Choix :** `json-file` **avec rotation** plutôt que `local` (rotation par défaut mais format interne) — car
les fichiers JSON sont lisibles par les collecteurs de logs → **prépare la phase 6 (Loki)**.

Fichier `/etc/docker/daemon.json` (créé sans éditeur, avec `sudo tee` + heredoc) :

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

→ au plus 3 fichiers de 10 Mo par conteneur (30 Mo). `max-file` est une **chaîne** (entre guillemets).

**Leçons :**
- `sudo echo '…' > fichier` échoue : la redirection `>` est faite par **mon** shell, sans les droits root.
  `sudo tee fichier` : c'est le programme qui écrit qui a les droits. `> /dev/null` masque l'écho de `tee`.
  Heredoc `<<'EOF'` : les guillemets empêchent l'interprétation de `$` ; le `EOF` final seul sur sa ligne.
- Valider le JSON **avant** de redémarrer : `python3 -m json.tool /etc/docker/daemon.json`
  (une virgule de trop = démon qui ne redémarre plus → `sudo journalctl -u docker -n 20`).
- `sudo systemctl restart docker` puis `docker info --format '{{.LoggingDriver}}'` → `json-file`
  (ne prouve pas la rotation : c'était déjà le défaut).
- La config ne s'applique qu'aux **nouveaux** conteneurs. Preuve de la rotation, avec `docker create`
  (crée sans lancer) : `docker inspect --format '{{.HostConfig.LogConfig}}' testlog` →
  `{json-file map[max-file:3 max-size:10m]}` ✅
- `--rm` supprime le conteneur dès qu'il s'arrête (impossible de l'inspecter ensuite) ; sans `--rm`, les
  conteneurs arrêtés s'accumulent (`docker ps -a`, `docker rm <nom>`, `docker container prune`).
  `Exited (0)` = fin sans erreur ; noms aléatoires (`gracious_euclid`) quand on ne met pas `--name`.

### 1.6 Portainer (interface web) — ⏳ procédure prévue, pas encore installé

Guide **Linux** de Portainer (pas celui « Windows Container Service », voir 1.7).

```bash
docker volume create portainer_data
docker run -d -p 127.0.0.1:9443:9443 --name portainer --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:lts
```

**Écarts volontaires par rapport à la doc :**
- `127.0.0.1:9443:9443` au lieu de `9443:9443` → UI accessible **seulement en local** (moindre privilège).
- Pas de `-p 8000:8000` : ce port ne sert qu'à l'**Edge Agent** (gérer à distance des hôtes Docker derrière
  NAT). Mes futures machines distantes (phase 4+) se gèreront avec SSH, kubectl, Helm, ArgoCD, Ansible.
  Si besoin un jour : recréer le conteneur avec le port en plus — les données restent dans le **volume**.

**Première connexion :** `docker logs portainer 2>&1 | grep setup_token` → jeton à usage unique
(protège l'instance contre une prise de contrôle par un tiers), valable 5 min d'inactivité
(sinon `docker restart portainer`). Puis `https://localhost:9443` (certificat auto-signé → avertissement
normal), création de l'admin avec un mot de passe fort.

⚠️ Portainer monte `docker.sock` → **mêmes pouvoirs que root**. Ne jamais l'exposer sur le réseau.

### 1.7 Incident : règles de pare-feu Windows ouvertes par erreur — ⏳ à nettoyer

**Ce qui s'est passé :** en suivant le guide Portainer « **Docker Swarm on Windows Container Service** »
(fait pour des **serveurs Windows avec conteneurs Windows**, pas pour mon cas), 6 règles entrantes ont été
créées avec `netsh advfirewall firewall add rule …`.

| Règle | Port | Rôle Swarm |
|---|---|---|
| `cluster_management` | TCP 2377 | communication avec le manager (join, ordres) |
| `node_communication_tcp` / `_udp` | TCP+UDP 7946 | découverte / santé des nœuds (gossip) |
| `overlay_network` | UDP 4789 | réseau overlay VXLAN entre conteneurs — **non chiffré, non authentifié** |
| `swarm_dns_tcp` / `_udp` | TCP+UDP 53 | **inutile** : le DNS de Swarm est interne (127.0.0.11) |

**Analyse (2026-09-28) :** règles actives, source `Any`, profils `Any` (y compris réseau **Public** — le
Wi-Fi Freebox est classé Public). Rien n'écoute sur 2377/7946/4789 → pas d'exposition réelle aujourd'hui.
**UDP 53** : un `svchost` (DNS du NAT WSL/Hyper-V) écoute sur `0.0.0.0:53` → joignable depuis le réseau local.
Le script `install-docker-ce.ps1` du même guide **n'a pas** été lancé (aucun service Docker Windows).

**Correctif (PowerShell admin, une commande par règle) :**

```bash
netsh advfirewall firewall delete rule name="cluster_management"
netsh advfirewall firewall delete rule name="node_communication_tcp"
netsh advfirewall firewall delete rule name="node_communication_udp"
netsh advfirewall firewall delete rule name="overlay_network"
netsh advfirewall firewall delete rule name="swarm_dns_tcp"
netsh advfirewall firewall delete rule name="swarm_dns_udp"
```

Vérif : `netsh advfirewall firewall show rule name=all | findstr /i "cluster_management node_communication overlay_network swarm_dns"` → vide.

**Leçon DevSecOps :** lire le **périmètre** d'un guide avant d'exécuter ses commandes ; ne jamais ouvrir un
port sans savoir **qui écoute derrière** et **depuis où** il doit être joignable (source, profil réseau).

### 1.8 Serveur dans le cloud : même chose ?

Pour Docker, oui (vrai Linux). Différences :

| | WSL2 | VM cloud |
|---|---|---|
| Coût | gratuit | quelques €/mois ou offre gratuite limitée |
| Accès | local | SSH |
| Réseau | NAT Windows | **IP publique** |
| Multi-nœuds (k3s) | ❌ | ✅ |
| Sécurité | rien d'exposé | **à durcir dès la 1re minute** |

Durcissement minimal d'une VM exposée : SSH par **clé uniquement** (pas de mot de passe, pas de root) ;
pare-feu minimal ; **ne jamais exposer l'API Docker (2375)** ; ⚠️ **Docker contourne `ufw`** : un
`-p 8080:80` est joignable depuis Internet même si `ufw` bloque 8080 (Docker écrit ses propres règles
iptables/nftables).

**Plan :** WSL2 maintenant pour Docker ; VM cloud (Hetzner / Scaleway / OVHcloud, ou offres gratuites —
vérifier prix et limites au moment du choix) pour la phase 4.

### 1.9 Questions du guide « Conteneurs » — mes réponses

**Environnement**
- *Linux, macOS ou Windows ?* Windows, mais je travaille **dans Linux** (WSL2). Nuance sur la fiche :
  Docker Desktop n'est **payant que pour les grandes entreprises** (gratuit pour usage perso, éducation,
  petites structures).
- *Docker Compose ?* Oui (FleetTrack local : API + PostGIS + front) → `docker compose` v5.5.1 installé.
- *Cluster Kubernetes ?* Oui en phase 4 : **k3s embarque son propre containerd** → pas de Docker sur les
  nœuds pour exécuter les pods ; Docker sert à **construire** les images (poste + CI).

**Sécurité**
- *Rootless obligatoire ?* Non pour apprendre ; atout pour banque/santé. `docker-ce-rootless-extras` est
  installé → exercice prévu en phase 8.
- *Groupe `docker` ≈ root ?* Compris (1.4) ; idem pour Portainer via `docker.sock` (1.6).

**Distinctions appliquées à ma stack**
- **Moteur vs runtime :** Docker Engine (build + run + UX) s'appuie sur **containerd** (exécution) — visible
  dans `--containerd=/run/containerd/containerd.sock`. Sur k3s : containerd seul.
- **Kubernetes ≥ 1.24 (dockershim supprimé) :** K8s ne parle plus à Docker, mais les **images construites
  avec Docker y tournent** (standard **OCI**).
- **Portabilité OCI :** l'image est portable ; le **réseau, les volumes et les contextes de sécurité** ne le
  sont pas → mon `docker-compose.yml` devra être traduit en manifests Kubernetes (phase 4).
- **LXC/Incus :** autre famille (conteneurs « système », proches d'une VM) — culture générale, hors feuille
  de route.

> **Docker pour construire, containerd pour exécuter, OCI pour relier les deux.**

---

## 2. asdf — gestionnaire de versions d'outils

**Date :** 2026-10-03

**Ce que c'est :** asdf installe **plusieurs versions d'un même outil** et choisit la bonne par projet, grâce
à un fichier `.tool-versions`. Un seul outil pour tout, via des plugins.

**Pourquoi (et pour quoi) :** utile pour les outils d'infrastructure à venir (`kubectl`, `helm`, `terraform`,
`k9s`…). **Pas** pour Python ni Node/pnpm : dans FleetTrack, c'est déjà le rôle d'uv et de corepack
(un seul gestionnaire par langage).

**Où :** dans **Ubuntu-24.04 (WSL)** — asdf ne tourne pas nativement sous Windows.

**Méthode retenue :** binaire précompilé (asdf ≥ 0.16 est un simple exécutable écrit en Go).
Alternatives : `brew install asdf`, `go install`.

**Guide suivi :** Stéphane Robert, « asdf-vm ». Sa page cite la v0.18.0 ; j'ai installé la **v0.20.2**,
dernière version publiée sur GitHub au 2026-10-03 (même méthode, même syntaxe de commandes).

### 2.1 Installation (état : ✅ binaire installé, v0.20.2)

```bash
sudo apt install git bash
curl -LO https://github.com/asdf-vm/asdf/releases/download/v0.20.2/asdf-v0.20.2-linux-amd64.tar.gz
tar -xzf asdf-v0.20.2-linux-amd64.tar.gz
sudo mv asdf /usr/local/bin/
type -a asdf        # → asdf is /usr/local/bin/asdf
asdf --version      # → v0.20.2
```

| Commande / option | Rôle |
|---|---|
| `apt install git bash` | Dépendances d'asdf (déjà présentes : « already the newest version ») |
| `curl -L` | Suit les **redirections** (GitHub redirige vers un autre serveur ; sans `-L` : fichier vide) |
| `curl -O` | Enregistre sous le **nom du fichier distant** |
| `tar -x` | e**x**traire |
| `tar -z` | décompresser le g**z**ip (`.gz`) |
| `tar -f <fichier>` | l'archive à traiter (**f**ile) — toujours en dernier dans `-xzf` |
| `sudo mv asdf /usr/local/bin/` | `/usr/local/bin` = dossier du PATH réservé aux programmes installés à la main (root requis) |
| `type -a asdf` | Montre **tous** les emplacements où bash trouve la commande, dans l'ordre de priorité |

**Piège rencontré :** `curl -LO asdf-v0.20.2-linux-amd64.tar.gz` → `curl: Remote file name has no length`.
curl attend une **URL complète** ; avec un simple nom de fichier, il le prend pour un nom de site.

**Réflexe DevSecOps — vérifier l'intégrité d'un téléchargement :** comparer l'empreinte du fichier à celle
publiée par l'éditeur.

```bash
md5sum asdf-v0.20.2-linux-amd64.tar.gz
curl -sL https://github.com/asdf-vm/asdf/releases/download/v0.20.2/asdf-v0.20.2-linux-amd64.tar.gz.md5
```

(`-s` = silencieux, sans barre de progression.) MD5 détecte une corruption, pas une attaque sérieuse :
quand l'éditeur publie un SHA-256 ou une signature, les préférer.

### 2.2 Reste à faire

- Ajouter les **shims** au PATH, à la fin de `~/.bashrc` (les shims sont les petits lanceurs qu'asdf crée
  pour chaque outil installé) :
  `export PATH="${ASDF_DATA_DIR:-$HOME/.asdf}/shims:$PATH"`
  — `${VAR:-défaut}` = valeur de `VAR` si elle existe, sinon `défaut`. La doc cite `~/.bash_profile` ; sur
  Ubuntu, le terminal lit `~/.bashrc`.
- Optionnel, complétion Tab : `. <(asdf completion bash)` dans `~/.bashrc`.
- Recharger : `source ~/.bashrc`.
- Supprimer l'archive devenue inutile : `rm ~/asdf-v0.20.2-linux-amd64.tar.gz`.

### 2.3 Commandes essentielles — ⏳ à pratiquer

Tirées du guide de Stéphane Robert et de la doc officielle (pas encore exécutées ici).

| Commande | Rôle |
|---|---|
| `asdf plugin add <outil>` | Ajoute le **plugin** qui sait installer cet outil (un plugin par outil : `kubectl`, `helm`, `terraform`…) |
| `asdf install <outil> <version>` | Télécharge et installe une version précise |
| `asdf set <outil> <version>` | Fixe la version **pour le projet courant** : écrit dans `./.tool-versions` |
| `asdf set --home <outil> <version>` | Fixe la version **par défaut de l'utilisateur** : écrit dans `~/.tool-versions` |
| `asdf list <outil>` | Versions installées |
| `asdf current <outil>` | Version active, et **quel fichier** l'a décidée |
| `asdf reshim` | Régénère les shims (à faire si une commande fraîchement installée reste introuvable) |
| `asdf plugin update --all` | Met à jour tous les plugins |

**`.tool-versions` :** fichier texte à la racine d'un projet, une ligne par outil (`kubectl 1.31.0`).
Versionné dans git → toute l'équipe et la CI utilisent les mêmes versions (reproductibilité).

**Point d'attention DevSecOps :** un plugin asdf est un dépôt git de scripts **exécutés sur ma machine**.
N'ajouter que des plugins connus et regarder leur dépôt source avant `plugin add`.

### 2.4 Première pratique : `crane` et `jq` (2026-10-03)

**État vérifié :**

| Outil | Version | Plugin (dépôt source) | Dans `~/.tool-versions` ? |
|---|---|---|---|
| `crane` | 0.21.7 | `github.com/dmpe/asdf-crane` | ✅ `crane 0.21.7` |
| `jq` | 1.8.2 | `github.com/lsanwick/asdf-jq` | ❌ pas encore |

Les deux plugins sont des dépôts **communautaires** (ni Google, ni jqlang) : le binaire téléchargé vient bien
du dépôt officiel (`github.com/jqlang/jq/releases/...`, affiché par asdf), mais le script d'installation est
celui d'un tiers.

```bash
asdf plugin add jq          # ajoute le plugin
asdf install jq latest      # "latest" = dernière version stable → 1.8.2
```

**Erreur rencontrée :**

```
$ crane manifest nginx:1.25 | jq -r '.mediaType'
No version is set for command jq
Consider adding one of the following versions in your config file at /home/lahigic/.tool-versions
jq 1.8.2
```

**Pourquoi :** `asdf install` **installe** une version mais ne l'**active** pas. Le shim `jq` cherche quelle
version lancer dans un `.tool-versions` (dossier courant, puis parents, puis `~`) et n'en trouve aucune.

**Correctif :**

```bash
asdf set --home jq 1.8.2    # écrit "jq 1.8.2" dans ~/.tool-versions (version par défaut de l'utilisateur)
asdf current                # vérifie : outil, version active, fichier qui l'a décidée
```

**⚠️ Shims non permanents :** la ligne `export PATH="…/.asdf/shims:$PATH"` n'est dans **aucun** fichier de
démarrage (`~/.bashrc`, `~/.profile`) → `crane` et `jq` ne marchent que dans le terminal où le PATH a été
exporté à la main. À ajouter à la fin de `~/.bashrc` (voir 2.2).

#### `jq` — c'est quoi ?

Un outil en ligne de commande pour **lire, filtrer et transformer du JSON** (« le `grep`/`sed` du JSON »).
Indispensable en DevOps : presque tous les outils et API répondent en JSON (`docker inspect`, `kubectl -o json`,
`glab api`, `gh api`, `crane`…).

```bash
crane manifest nginx:1.25 | jq -r '.mediaType'
```

| Élément | Rôle |
|---|---|
| `crane manifest nginx:1.25` | Demande au registre (Docker Hub) le **manifeste** de l'image, **sans la télécharger** — renvoie du JSON |
| `\|` | Envoie cette sortie à la commande suivante |
| `jq '<filtre>'` | Applique un filtre au JSON reçu |
| `.mediaType` | Le filtre : « donne-moi la valeur de la clé `mediaType` à la racine » |
| `-r` (*raw*) | Affiche la valeur **brute**, sans les guillemets JSON (utile dans un script) |

Filtres de base :

| Filtre | Effet |
|---|---|
| `.` | Tout le JSON, indenté et coloré |
| `.cle` / `.a.b` | Une clé / une clé imbriquée |
| `.[0]` / `.[]` | Le 1er élément d'un tableau / chaque élément |
| `.manifests[].platform.architecture` | Parcourir un tableau et extraire un champ |
| `select(.x == "y")` | Ne garder que les éléments qui vérifient une condition |
| `-c` | Sortie compacte, une ligne par objet |

**Résultat (vérifié le 2026-10-03) :** `application/vnd.oci.image.index.v1+json`.
`mediaType` donne le **type** du manifeste : ici un **index OCI**, c'est-à-dire une liste de manifestes
(16 entrées pour `nginx:1.25` : une par plateforme — amd64, arm64… — plus des attestations), et non le
manifeste d'une seule image. C'est ce qui permet à `docker pull nginx` de choisir tout seul la bonne
architecture — lien direct avec la norme **OCI** (section 1.9).

**`grep` ou `jq` ?**

| | `grep` | `jq` |
|---|---|---|
| Travaille sur | des **lignes de texte** | la **structure JSON** (clés, valeurs, tableaux) |
| Question posée | « quelles lignes contiennent ce motif ? » | « quelle est la valeur de cette clé ? » |
| Résultat | la ligne entière | la valeur exacte |
| Transformer | non | oui (filtrer, trier, reconstruire) |

Exemple avec `{"name":"nginx","tag":"1.25"}` : `grep name` renvoie toute la ligne ; `jq -r '.name'` renvoie
`nginx`.

- `grep` : texte libre — logs, fichiers de configuration, code source.
- `jq` : dès que c'est du JSON — réponses d'API, `docker inspect`, `kubectl -o json`.
- `grep` sur du JSON est fragile : JSON sur une seule ligne → tout est renvoyé ; mot présent dans une autre
  clé → faux résultats.

Déjà utilisé sans le savoir : `glab api … | jq -r '.[] | "\(.name) -> \(.full_path)"'` pour retrouver le
chemin du groupe GitLab.

#### `crane` — c'est quoi ?

Outil de Google (projet *go-containerregistry*) pour **interroger et manipuler les images dans un registre
sans démon Docker** : lire un manifeste, lister les tags, copier une image d'un registre à l'autre.
Sert à comprendre ce qu'est réellement une image (manifeste, config, couches).

---

## 3. `wsl` ou `ssh` : entrer dans une machine

**Date :** 2026-10-03

| Outil | Sert à | Exemple |
|---|---|---|
| `wsl -d <distribution>` | Entrer dans une distribution Linux **de mon PC** | `wsl -d Ubuntu-24.04` |
| `ssh utilisateur@adresse` | Se connecter à une machine **distante**, par le réseau | futurs serveurs cloud |

**Pièges rencontrés (depuis Git Bash) :**
- `ssh ubunt-24.04` → `Could not resolve hostname` : SSH cherche une **machine sur le réseau** portant ce
  nom ; une distribution WSL n'en est pas une.
- `ssh -b ubunt-24.04` → affiche l'aide : `-b` = *bind address* (adresse locale de départ), donc il ne
  reste plus de destination.
- `wsl -d ubuntu24.04` → `WSL_E_DISTRO_NOT_FOUND` : le nom doit être **exact** (`Ubuntu-24.04`).
  `wsl -l -v` liste les noms ; `Tab` complète.
- Préférer PowerShell ou le Terminal Windows à Git Bash (`MINGW64`) pour lancer `wsl`.

**Pour s'entraîner à SSH plus tard :** installer `openssh-server` dans Ubuntu puis `ssh lahigic@localhost`
(clés, `sshd_config`) — préparation de la phase « serveurs distants ».


### 3.1 Pourquoi `ssh <alias>` fonctionne : `~/.ssh/config`, clés, `known_hosts`

Un **alias** se déclare dans `~/.ssh/config` (ici celui de Windows). Forme générale :

```
Host mon-alias
    HostName <adresse IP ou nom du serveur>
    User <utilisateur distant>
    IdentityFile ~/.ssh/<clé privée>
    IdentitiesOnly yes
```

| Ligne | Rôle |
|---|---|
| `Host` | Le nom court que l'on tape |
| `HostName` | La vraie adresse du serveur |
| `User` | L'utilisateur distant |
| `IdentityFile` | La **clé privée** à présenter |
| `IdentitiesOnly yes` | N'essayer **que** cette clé (pas toutes celles de `~/.ssh`) |

`ssh mon-alias` équivaut donc à `ssh -i ~/.ssh/<clé> <utilisateur>@<adresse>`.

**Trois éléments doivent être réunis :**
1. l'**alias** dans `~/.ssh/config` (poste de travail) ;
2. la **paire de clés** : privée sur le poste, publique dans `~/.ssh/authorized_keys` de l'utilisateur distant —
   le serveur accepte celui qui prouve posséder la clé privée, sans mot de passe ;
3. l'**empreinte du serveur** dans `~/.ssh/known_hosts` : SSH vérifie à chaque connexion que c'est la même machine.

**À savoir :**
- `ssh ubunt-24.04` échouait (section 3) : ni alias, ni adresse réelle.
- Le `~/.ssh` de **Windows** et celui d'**Ubuntu WSL** sont deux dossiers différents : un alias défini dans l'un
  n'existe pas dans l'autre.
- Une clé privée ne se partage ni ne se commite jamais.
- J'ai un alias de ce type vers ma VM Oracle Cloud (ARM, partagée avec des sites en production → pas d'essais
  risqués dessus).

---

## 4. Images multi-plateformes — `docker buildx`

**Date :** 2026-10-03 (lu dans le guide, pas encore pratiqué)

**Pourquoi je n'ai jamais mis `--platform` ni `buildx` :** par défaut, Docker construit pour **la machine
qui construit** (`linux/amd64` sur mon PC), et `docker build` utilise déjà buildx/BuildKit en coulisses.

**Plateforme = `système/processeur` :** `linux/amd64` (PC, la plupart des serveurs — Intel/AMD) ;
`linux/arm64` (Mac M1 et suivants, Raspberry Pi, serveurs cloud ARM). Une image amd64 ne tourne pas sur arm64
→ on construit **une image par plateforme**, réunies sous un même nom par un **index** (voir 2.4, `crane manifest`).

```bash
docker buildx create --name multi-arch --driver docker-container --use
docker buildx build --platform linux/amd64,linux/arm64 --tag mon-registry/mon-app:v1.0 --push .
docker manifest inspect mon-registry/mon-app:v1.0
```

| Commande / option | Rôle |
|---|---|
| `buildx create` | Crée un nouveau **builder** (moteur de construction) |
| `--name multi-arch` | Nom du builder |
| `--driver docker-container` | Le builder (BuildKit) tourne dans un conteneur ; le builder par défaut (`docker`) ne produit pas d'image multi-plateforme avec le stockage d'images classique |
| `--use` | Le sélectionne pour les prochains builds |
| `buildx build --platform a,b` | Construit une version par plateforme |
| `--tag` | Nom et version de l'image |
| `--push` | Envoie au registre — nécessaire : le stockage local classique ne sait pas garder une image multi-plateforme |
| `.` | Contexte de build (dossier du Dockerfile) |
| `docker manifest inspect` | Affiche l'index : une entrée par plateforme |

**QEMU, c'est quoi ?** Un **émulateur** : il fait croire à un programme qu'il tourne sur un autre processeur,
en traduisant à la volée ses instructions (arm64 → amd64). Docker s'en sert pour exécuter les `RUN` d'un
Dockerfile arm64 sur un PC amd64. Fonctionne, mais lentement (souvent 5 à 10 fois plus).

**À savoir :**
- Construire de l'arm64 sur un PC amd64 passe par l'**émulation QEMU** (à installer sur Docker Engine, lente).
- Utile si les serveurs cibles sont ARM ou si l'image doit tourner sur un Mac récent. Pas nécessaire tant que
  tout est en amd64.

---

## 5. Artefacts OCI — un registre ne stocke pas que des images

**Date :** 2026-10-03 (lu dans le guide « Conteneurs »)

La norme OCI permet de ranger dans un registre (Docker Hub, GitLab Registry…) **d'autres fichiers que des
images**, avec le même système de noms, de versions et de droits.

| Artefact | Ce que c'est | À quoi ça sert | Outils |
|---|---|---|---|
| Helm charts | Paquet décrivant une application Kubernetes | Installer une application sur un cluster en une commande | `helm push` |
| SBOM | *Software Bill of Materials* : liste de tous les composants d'une image | Savoir si l'image contient une bibliothèque vulnérable | ORAS, Syft |
| Signatures | Preuve cryptographique de qui a construit l'image | Vérifier l'origine et l'intégrité | Cosign, Notation |
| Policies | Règles écrites en code (OPA / langage Rego) | Refuser automatiquement ce qui n'est pas conforme (ex. conteneur root) | Conftest |
| Modules WASM | Programmes WebAssembly | Exécuter du code de façon plus légère qu'un conteneur | ORAS |

**Pourquoi c'est important :** SBOM + signatures + policies = le cœur du **DevSecOps** (chaîne
d'approvisionnement logicielle) : savoir ce que contient une image, prouver d'où elle vient, bloquer ce qui
n'est pas conforme. À pratiquer plus tard.

---

## 6. Concepts Docker — image, conteneur, couches, isolation

**Date :** 2026-10-04 (lecture du guide « Concepts Docker »)

| Concept | L'essentiel | Déjà vu en pratique |
|---|---|---|
| Image / conteneur | Image = **modèle immuable** fait de couches, stocké sur disque. Conteneur = **instance en exécution** avec une couche lecture/écriture éphémère. 1 image → N conteneurs indépendants | `hello-world` : une image, plusieurs conteneurs |
| `docker run` | Enchaîne `docker pull` → `docker create` → `docker start` | `docker create` seul pour `testlog` (1.5) |
| Cycle de vie | created → running ↔ paused → exited → removed | `Exited (0)` dans `docker ps -a` |
| `docker stop` | Envoie **SIGTERM** (arrêt propre), puis **SIGKILL** après 10 s | — |
| `docker kill` | **SIGKILL** immédiat | — |
| Code de sortie 137 | 128 + 9 (SIGKILL) : arrêt forcé — `docker kill` ou manque de mémoire (OOM) | — |
| Couches (layers) | Partagées entre images : moins de disque, cache de build, téléchargements plus courts | — |
| Copy-on-Write | Modifier un fichier le **copie** d'abord dans la couche R/W du conteneur ; cette couche **disparaît** à la suppression du conteneur | D'où le **volume** `portainer_data` (1.6) |
| Namespaces | Isolent ce que le conteneur **voit** : PID, réseau, mount, UTS (nom d'hôte), IPC, user | — |
| Cgroups | Limitent ce qu'il **consomme** : `--cpus`, `--memory` | Avertissements `No blkio` (1.3) |
| PID 1 | Le processus principal du conteneur ; c'est lui qui reçoit les signaux | — |
| Architecture | Client `docker` → API REST → démon `dockerd` (root) via `/var/run/docker.sock` ; registres : Docker Hub, Harbor, ECR… | Message de `hello-world`, `systemctl status docker` |
| Sécurité | Accès au socket ou groupe `docker` = équivalent **root** sur l'hôte | `usermod -aG docker` (1.4), `docker.sock` de Portainer (1.6) |

### 6.1 Namespaces et cgroups en détail

Deux mécanismes du **noyau Linux** (Docker ne les a pas inventés, il les assemble).

**Namespaces — ce que le conteneur *voit*** (des murs) : chaque namespace donne au processus sa propre vue
d'une partie du système.

| Namespace | Isole | Effet dans le conteneur |
|---|---|---|
| PID | les processus | ne voit que les siens ; son programme principal est le n° 1 |
| net | cartes réseau, IP, ports | sa propre IP, ses propres ports |
| mnt | les points de montage | son propre système de fichiers |
| UTS | le nom d'hôte | son propre hostname |
| IPC | la mémoire partagée | pas de communication avec les processus des autres conteneurs |
| user | les utilisateurs | le root du conteneur peut être un utilisateur ordinaire sur l'hôte (**rootless**) |

**Cgroups — ce que le conteneur *consomme*** (un compteur avec un plafond) : limitent et mesurent CPU,
mémoire, I/O disque, nombre de processus d'un groupe de processus.

```bash
docker run --memory 256m --cpus 0.5 nginx
```

| Option | Rôle |
|---|---|
| `--memory 256m` | Plafond de mémoire ; dépassement → le noyau tue le conteneur (**OOM**, code de sortie 137) |
| `--cpus 0.5` | Au plus la moitié d'un cœur |

**Pour l'observer (à pratiquer) :**

```bash
docker run --rm alpine ps      # un seul processus, PID 1 → namespace PID (comparer avec `ps aux` sur l'hôte)
docker stats --no-stream       # consommation et limites par conteneur → cgroups
```

`--no-stream` : affiche une seule mesure au lieu de rafraîchir en continu.

### 6.2 La couche R/W (lecture/écriture) par l'exemple

**R/W** = *Read/Write*. Les couches d'une image sont en **lecture seule**. Au lancement d'un conteneur, Docker
ajoute par-dessus une couche fine où le conteneur peut écrire. Image = livre imprimé ; couche R/W = feuille
de calque posée dessus : on écrit sur le calque, jamais sur le livre.

**Exemple 1 — ce qu'on écrit disparaît avec le conteneur**

```bash
docker run --name test1 alpine sh -c 'echo bonjour > /monfichier.txt'
docker rm test1
docker run --rm alpine cat /monfichier.txt      # → No such file or directory
```

Le fichier vivait dans la couche R/W de `test1`, supprimée avec lui. L'image `alpine` n'a pas changé.

**Exemple 2 — voir le contenu de la couche R/W**

```bash
docker run --name test2 alpine sh -c 'echo bonjour > /monfichier.txt; rm /etc/hostname'
docker diff test2
docker rm test2
```

| Sortie de `docker diff` | Sens |
|---|---|
| `A /monfichier.txt` | **A**jouté |
| `D /etc/hostname` | supprimé (**D**eleted) |
| `C /etc` | modifié (**C**hanged) |

**Exemple 3 — deux conteneurs, deux couches R/W**

```bash
docker run -d --name a nginx
docker run -d --name b nginx
```

`a` et `b` partagent les mêmes couches de l'image (stockées une seule fois) mais ont chacun leur couche R/W :
modifier un fichier dans `a` ne change rien dans `b`.

| Élément | Rôle |
|---|---|
| `sh -c '<commandes>'` | Lance un shell dans le conteneur pour exécuter plusieurs commandes |
| `docker diff <conteneur>` | Liste les changements du conteneur par rapport à son image |

**Conséquence :** une base de données sans **volume** perd tout à la suppression du conteneur. Un volume vit
en dehors de la couche R/W (`-v portainer_data:/data`).

### 6.3 Volumes : stocker en dehors du conteneur

Un **volume** est un espace de stockage **hors de la couche R/W** : les données survivent à la suppression du
conteneur.

| Type | Où sont les données | Usage | Exemple |
|---|---|---|---|
| Volume nommé | Dossier géré par Docker (`/var/lib/docker/volumes/`) | Données d'application (base, fichiers envoyés) | `-v portainer_data:/data` |
| Bind mount | Dossier **de l'hôte** que je choisis | Développement : le conteneur voit mes modifications tout de suite | `-v /home/lahigic/monprojet:/app` |
| tmpfs | Mémoire vive, jamais sur disque | Données temporaires ou sensibles | `--tmpfs /tmp` |
| Volume anonyme | Volume sans nom, identifiant aléatoire | À éviter (difficile à retrouver) | `-v /data` |

- Distinguer dans `-v` : `nom:/chemin` (pas de `/` au début) = **volume nommé** ; `/chemin/hote:/chemin` = **bind mount**.
- `:ro` à la fin = lecture seule (`-v /home/lahigic/conf:/conf:ro`).
- ⚠️ Un bind mount donne un accès direct aux fichiers de l'hôte ; `-v /:/host` donne **toute** la machine.

### 6.4 Capabilities : ce que le conteneur a le droit de faire

Sous Linux, root a tous les droits. Les **capabilities** découpent ce pouvoir en petits droits séparés, qu'on
donne ou retire un par un.

| Capability | Autorise |
|---|---|
| `NET_BIND_SERVICE` | Écouter sur un port < 1024 (80, 443) |
| `CHOWN` | Changer le propriétaire d'un fichier |
| `NET_ADMIN` | Modifier la configuration réseau et le pare-feu |
| `SYS_ADMIN` | Une très large part des pouvoirs de root (montages…) — la plus dangereuse |
| `SYS_TIME` | Changer l'heure du système |

**Par défaut**, Docker ne laisse au conteneur qu'une liste réduite de capabilities, même si le processus est
root dedans (`SYS_ADMIN`, `NET_ADMIN`, `SYS_TIME`… sont retirées).

```bash
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE nginx
```

| Option | Rôle |
|---|---|
| `--cap-drop ALL` | Retire toutes les capabilities |
| `--cap-add <nom>` | En rend une seule (moindre privilège) |
| `--privileged` | ⚠️ Donne **toutes** les capabilities et l'accès au matériel : équivalent root sur l'hôte. À éviter |

**Les trois protections :** namespaces = ce qu'il **voit** ; cgroups = ce qu'il **consomme** ; capabilities =
ce qu'il a le **droit de faire**.

### 6.5 seccomp et AppArmor

**seccomp** — filtre les **appels système** (les demandes d'un programme au noyau : ouvrir un fichier, créer
un processus, changer l'heure… plus de 300). Le profil par défaut de Docker en bloque une quarantaine, les
plus dangereux (charger un module noyau, redémarrer la machine, changer l'heure…).

**AppArmor** — associe à un programme un **profil** listant les fichiers et actions autorisés ; même root
dans le conteneur ne peut pas en sortir. Profil Docker : `docker-default` (interdit par ex. d'écrire dans
`/proc` et `/sys`). Équivalent sur Red Hat et dérivés : **SELinux**.

**Vérifié sur ma machine (2026-10-04) :**

```bash
docker info --format '{{.SecurityOptions}}'      # → [name=seccomp,profile=builtin]
```

seccomp est actif (profil intégré). AppArmor **n'apparaît pas** : le noyau de WSL2 ne l'active pas — il le
serait sur un vrai serveur Ubuntu.

**Défense en profondeur — les 5 protections d'un conteneur :**

| Protection | Contrôle |
|---|---|
| Namespaces | ce qu'il **voit** |
| Cgroups | ce qu'il **consomme** |
| Capabilities | les **pouvoirs de root** qu'il garde |
| seccomp | les **appels au noyau** permis |
| AppArmor / SELinux | les **fichiers et actions** autorisés par profil |

### 6.6 `dockerd`, `containerd`, `runc` : qui fait quoi

« Démon Docker » = `dockerd` (c'est le nom du programme).

| | `dockerd` | `containerd` |
|---|---|---|
| Rôle | Chef d'orchestre de Docker | Exécutant des conteneurs |
| Fait | Reçoit les commandes `docker` (API), construit les images, gère réseaux et volumes | Télécharge les images, démarre / arrête / surveille les conteneurs |
| Qui lui parle | le client `docker` | `dockerd`, ou Kubernetes directement (CRI) |

```
docker (client) → dockerd → containerd → containerd-shim → runc → conteneur
```

- **`runc`** : crée réellement le conteneur (namespaces, cgroups, capabilities, seccomp), lance le programme,
  puis se termine.
- **`containerd-shim`** : un par conteneur, reste à côté pour le surveiller → on peut redémarrer `dockerd`
  sans arrêter les conteneurs.

**Vérifié sur ma machine :** `ps -eo comm | grep -E "dockerd|containerd"` → 1 `dockerd`, 1 `containerd`,
3 `containerd-shim` (donc 3 conteneurs en marche) ; runtime par défaut `runc` v1.5.1.

**Pourquoi ça compte :** Kubernetes n'a pas besoin de `dockerd` ; il parle directement à containerd — ce que
fera k3s.

### 6.7 Lire `systemctl status docker` ligne par ligne

Sortie observée le 2026-10-04 (`sudo systemctl status docker`).

**En-tête**

| Ligne | Signification |
|---|---|
| `● docker.service - Docker Application Container Engine` | Nom et description du service ; point vert = en marche |
| `Loaded: loaded (/usr/lib/systemd/system/docker.service; enabled; preset: enabled)` | Fichier d'unité lu par systemd ; `enabled` = démarre automatiquement ; `preset` = réglage par défaut de la distribution |
| `Active: active (running) since …; 23h ago` | État et durée de fonctionnement |
| `TriggeredBy: ● docker.socket` | **Activation par socket** : systemd écoute `/run/docker.sock` et lance `dockerd` à la première connexion |
| `Main PID: 283 (dockerd)` | Processus principal |
| `Tasks: 17` | Fils d'exécution du service |
| `Memory: 149.7M` | Mémoire du démon lui-même (hors conteneurs) |
| `CGroup: /system.slice/docker.service` | cgroup où systemd range le service (même mécanisme que pour les conteneurs) |
| `└─283 /usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock` | Commande exacte : `-H fd://` = écouter sur le socket transmis par systemd ; `--containerd=` = socket pour parler à containerd |

**Journal** — format `date machine programme[PID]: message`

| Message | Signification |
|---|---|
| `level=info` | Information, pas une erreur |
| `image pulled digest="sha256:…"` | Image téléchargée ; **digest** = empreinte unique de son contenu |
| `sbJoin: gwep4 ''->'91c9…', gwep6 ''->'' … ep=pedantic_chatelet net=bridge` | Un conteneur est branché au réseau : `ep` = son nom, `net=bridge` = réseau par défaut, `gwep4` = passerelle IPv4, `gwep6` vide = pas d'IPv6 |
| `received task-delete event from containerd container=…` | containerd signale à dockerd qu'un conteneur s'est terminé |

Lignes coupées (`>` en fin de ligne) → `journalctl -u docker --no-pager -n 20`
(`-u` = unité ; `--no-pager` = sans défilement ; `-n 20` = 20 dernières lignes).

**Lecture sécurité**

| Élément | Ce qu'il faut vérifier |
|---|---|
| `-H fd://` | ✅ écoute locale seulement. `-H tcp://0.0.0.0:2375` = API ouverte au réseau **sans authentification** = root offert |
| `Main PID … (dockerd)` | Le démon tourne en **root** : qui lui parle a le pouvoir de root |
| `docker.socket` | Tout repose sur les droits du socket (`root:docker`, `660`) |
| `digest` | Un tag (`nginx:1.25`) peut changer de contenu ; un digest jamais → en production, épingler `image@sha256:…` |
| Journal | Révèle noms de conteneurs, images, horaires ; lisible par root et les groupes `adm` / `systemd-journal` |

**`runc` et `containerd-shim` (rappel de 6.6) :** `runc` crée le conteneur puis se termine ;
`containerd-shim` reste à côté de chaque conteneur (garde ses entrées/sorties et son code de fin) et permet
de redémarrer `dockerd` sans arrêter les conteneurs.

### 6.8 Le fichier `docker.service` ligne par ligne

`/usr/lib/systemd/system/docker.service` (lu le 2026-10-04) = la fiche d'instructions de systemd : comment
lancer `dockerd`, dans quel ordre, quoi faire s'il plante. Le lire montre comment Docker démarre réellement
sur un serveur, et permet de vérifier qu'il n'est pas configuré dangereusement.

**`[Unit]` — identité et dépendances**

| Ligne | Signification |
|---|---|
| `Description=`, `Documentation=` | Texte et lien affichés par `systemctl status` |
| `After=network-online.target nss-lookup.target docker.socket firewalld.service containerd.service time-set.target` | **Ordre** : démarrer après le réseau, la résolution de noms, le socket, le pare-feu, containerd, l'heure |
| `Wants=network-online.target containerd.service` | Demande leur démarrage ; s'ils échouent, Docker démarre quand même |
| `Requires=docker.socket` | **Exige** le socket ; s'il échoue, Docker ne démarre pas |
| `StartLimitBurst=3`, `StartLimitIntervalSec=60` | Au plus 3 démarrages en 60 s, puis systemd abandonne (anti-boucle) |

**`[Service]` — lancement**

| Ligne | Signification |
|---|---|
| `Type=notify` | `dockerd` prévient systemd quand il est prêt (`Daemon has completed initialization`) |
| `ExecStart=/usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock` | Commande lancée ; `-H fd://` = socket transmis par systemd |
| `ExecReload=/bin/kill -s HUP $MAINPID` | `systemctl reload docker` : signal HUP → relit la configuration sans s'arrêter |
| `TimeoutStartSec=0` | Pas de délai maximal de démarrage |
| `Restart=always`, `RestartSec=2` | Relance toujours, après 2 s |
| `LimitNPROC=infinity`, `LimitCORE=infinity`, `TasksMax=infinity` | Aucune limite de processus, de fichiers *core*, de tâches (sinon le nombre de conteneurs serait plafonné) |
| `Delegate=yes` | systemd laisse Docker gérer les cgroups de ses conteneurs |
| `KillMode=process` | À l'arrêt du service, ne tue que `dockerd`, **pas les conteneurs** |
| `OOMScoreAdjust=-500` | En cas de manque de mémoire, le noyau tue d'autres programmes avant `dockerd` |

**`[Install]`** : `WantedBy=multi-user.target` → `systemctl enable docker` rattache le service au démarrage
normal (lien `multi-user.target.wants/docker.service` vu à l'installation).

**Lecture sécurité**

| Ligne | À regarder |
|---|---|
| `ExecStart … -H fd://` | La plus importante : un `-H tcp://0.0.0.0:2375` ajouté = API ouverte sans authentification |
| Pas de `User=` | `dockerd` tourne en **root** |
| `…=infinity` | Aucune limite sur le démon → les limites se posent **par conteneur** (`--memory`, `--cpus`, `--pids-limit`) |
| `Restart=always` | Bon pour la disponibilité, mais un plantage en boucle se lit dans le journal |

**Ne jamais modifier ce fichier** (écrasé à chaque mise à jour du paquet) : utiliser `sudo systemctl edit docker`
(fichier de surcharge) ou `/etc/docker/daemon.json`.

### 6.9 `journalctl -u docker.service` : le journal du démon

**À quoi ça sert :** comprendre une panne (Docker ne démarre pas après une erreur dans `daemon.json`), vérifier
un changement après un `restart`, retracer ce qui s'est passé (image tirée, conteneur arrêté, à quelle heure).

**Séquence de démarrage observée** (deux démarrages : 28/09 21:27:30, PID 7732, à l'installation ; 21:49:11,
PID 275, après redémarrage de WSL) :

| Message | Étape |
|---|---|
| `Starting up` | Démarrage |
| `OTEL tracing is not configured` | Pas d'export de traces OpenTelemetry (normal) |
| `CDI directory does not exist, skipping` | Pas de matériel spécial (GPU…) déclaré |
| `Creating a containerd client address=/run/containerd/containerd.sock` | Connexion à containerd |
| `Loading containers: start.` … `done.` | Restauration des conteneurs existants |
| `Deleting nftables IPv4/IPv6 rules` | Remise à zéro des règles réseau de Docker avant de les recréer |
| `Docker daemon commit=… storage-driver=overlayfs` | Version et pilote de stockage (couches) |
| `Initializing buildkit` / `Completed buildkit initialization` | Moteur de build prêt |
| `Daemon has completed initialization` | Prêt (notifié à systemd) |
| `API listen on /run/docker.sock` | Écoute sur le socket local |

**Avertissements sans gravité sous WSL2 :** `No blkio throttle…` (pas de limitation du débit disque),
`failed check for fsverity support` (vérification d'intégrité non proposée par le système de fichiers),
`cgroup v1 is deprecated` (WSL2 utilise encore l'ancienne version des cgroups).

Options utiles : `-u <unité>`, `-n 50` (dernières lignes), `-f` (suivre en direct), `--since "1 hour ago"`,
`-p warning` (à partir du niveau warning), `--no-pager`.

### 6.10 Pourquoi le groupe `docker` équivaut à root — la démonstration

```bash
docker run -v /:/hostroot -it alpine chroot /hostroot      # → shell root sur l'hôte
```

| Élément | Rôle |
|---|---|
| `-v /:/hostroot` | Bind mount de **tout le disque de l'hôte** dans le conteneur |
| `-i` | Garde l'entrée standard ouverte |
| `-t` | Crée un terminal |
| `chroot /hostroot` | Change la racine : le shell prend `/hostroot` pour `/` → on est « dans » l'hôte |

**Pourquoi ça marche :** le processus du conteneur est **root** par défaut ; le montage est fait par `dockerd`
(root), qui ne vérifie pas les droits de l'utilisateur qui le demande. Résultat : accès à tous les fichiers de
l'hôte (`/etc/shadow`, `/etc/sudoers`, clés SSH de root…) sans `sudo` ni mot de passe.

**Démonstration sans risque (lecture seule, `:ro`) :**

```bash
cat /etc/shadow                                                        # → Permission denied
docker run --rm -v /:/hostroot:ro alpine cat /hostroot/etc/shadow       # → affiche le fichier
```

**Règles :**
- N'ajouter au groupe `docker` que des personnes à qui on donnerait `sudo`.
- Ne pas monter `docker.sock` dans un conteneur sans nécessité (même pouvoir) — cas de Portainer (1.6).
- Sur un serveur : **mode rootless** (`dockerd` sous un utilisateur ordinaire) → l'attaque ne donne plus root.

### 6.11 Le client `docker` : `DOCKER_HOST` et `~/.docker/config.json`

Le client `docker` et le démon `dockerd` sont **deux programmes** : le client envoie des requêtes à l'API du
démon — par défaut via `/var/run/docker.sock`, mais aussi vers un démon **distant**.

```bash
export DOCKER_HOST=tcp://remote-host:2376
docker ps
cat ~/.docker/config.json
```

| Élément | Rôle |
|---|---|
| `export` | Définit une variable pour ce terminal et les programmes qu'il lance |
| `DOCKER_HOST` | Adresse du démon que le client doit contacter |
| `tcp://` | Par le réseau, au lieu du socket local |
| `2376` | Port de l'API Docker **chiffrée (TLS)** ; `2375` = sans chiffrement ni authentification (dangereux) |
| `~/.docker/config.json` | Configuration du **client** : identifiants de registres, proxy, format d'affichage… |

**Ce que j'ai obtenu (2026-10-04) et pourquoi :**

| Sortie | Explication |
|---|---|
| `cat: …/config.json: No such file or directory` | Normal : le fichier n'est créé qu'au premier `docker login` ou réglage du client |
| `failed to connect … lookup remote-host on 10.255.255.254:53: no such host` | `remote-host` est un **nom d'exemple** du guide ; le DNS de WSL (`10.255.255.254`) ne le connaît pas |

**Piège :** après l'`export`, **toutes** les commandes `docker` du terminal échouent (le client cherche le
serveur distant). Annuler avec `unset DOCKER_HOST`.

**Lecture sécurité :**
- `config.json` peut contenir les **mots de passe de registre en base64** (encodage, pas chiffrement) quand
  aucun gestionnaire d'identifiants n'est configuré → ne jamais le commiter ni le copier dans une image.
- Ne jamais ouvrir le port 2375.
- Méthode recommandée pour un démon distant : **SSH** + **contexte**, sans port supplémentaire ni variable à annuler :

```bash
docker context create monserveur --docker "host=ssh://utilisateur@adresse"
docker context use monserveur
docker context use default        # retour au Docker local
```

### 6.12 Socket Unix ou réseau — `/var/run/docker.sock` et le port 2375

Un **socket** est un point de connexion entre deux programmes.

| | Socket Unix | Socket réseau (TCP) |
|---|---|---|
| Forme | Un **fichier** : `/var/run/docker.sock` | Une **IP + un port** : `192.168.1.10:2375` |
| Qui peut s'y connecter | Les programmes de **la même machine** | Toute machine qui peut joindre l'adresse |
| Contrôle d'accès | Droits du fichier (propriétaire, groupe) | Pare-feu, mot de passe ou certificat — sinon rien |

**Le fichier `/var/run/docker.sock`** = la porte d'entrée de `dockerd`.

```bash
ls -l /var/run/docker.sock     # srw-rw---- 1 root docker 0 … /var/run/docker.sock
```

| Partie | Signification |
|---|---|
| `s` | Type **socket** (ni fichier `-`, ni dossier `d`) |
| `rw-` `rw-` `---` | Propriétaire : lecture/écriture ; groupe : lecture/écriture ; autres : rien |
| `root` / `docker` | Propriétaire / groupe → d'où l'accès donné par le groupe `docker` |
| `0` | Taille nulle : un point de passage, pas un contenu |

- `/var/run` → lien vers `/run` : `/run/docker.sock` est le même fichier (`API listen on /run/docker.sock`).
- Créé par systemd (`docker.socket`) ; `/run` est en mémoire, il disparaît à l'arrêt.
- Ce qui y circule est une **API HTTP** — on peut lui parler sans le client `docker` :

```bash
curl --unix-socket /var/run/docker.sock http://localhost/version      # même requête que `docker version`
```

`--unix-socket <fichier>` : curl passe par ce socket au lieu du réseau.

**Pourquoi ne jamais ouvrir le port 2375 :**
1. C'est la même API en version réseau, **sans chiffrement ni authentification** : les droits du fichier
   (`root:docker`) n'existent plus.
2. Parler à `dockerd` = être **root** sur la machine (6.10).
3. Une seule commande à distance suffit : `docker -H tcp://serveur:2375 run -v /:/hostroot alpine …`.
4. Des robots scannent Internet en permanence pour ce port (usage typique : minage de cryptomonnaie).

**Alternatives sûres :** contexte Docker par **SSH** (`host=ssh://…`, aucun port en plus) ; ou port **2376**
avec **TLS et certificats client**.

### 6.13 `docker debug` n'existe pas dans Docker Engine — alternatives

`docker debug web` → `docker: unknown command: docker debug` : la commande est une fonction de **Docker
Desktop** (abonnement payant), absente de Docker Engine.

| Besoin | Commande |
|---|---|
| Shell dans un conteneur en marche | `docker exec -it web sh` |
| Conteneur sans shell (image minimale) | `docker run --rm -it --pid=container:web --network=container:web busybox sh` |

| Option | Rôle |
|---|---|
| `exec -it <conteneur> <commande>` | Lance une commande dans un conteneur déjà en marche, avec un terminal |
| `--pid=container:web` | Partage le **namespace PID** de `web` : on voit ses processus |
| `--network=container:web` | Partage son **namespace réseau** : même IP, mêmes ports |

Le second cas applique directement les namespaces (6.1) : un conteneur d'outils « entre » dans les namespaces
d'un autre.

### 6.14 `exec: "ps": executable file not found` — voir les processus d'un conteneur minimal

**Erreur rencontrée (2026-10-05) :** `docker exec web ps aux` →
`OCI runtime exec failed: … exec: "ps": executable file not found in $PATH`.

**Pourquoi :** l'image `nginx:1.25` ne contient pas `ps`. Les images officielles sont réduites au minimum
(moins de programmes = moins de failles, image plus légère). `docker exec` ne lance que ce qui **existe dans
le conteneur**.

```bash
docker top web                                                    # 1. processus lus depuis l'hôte
docker run --rm --pid=container:web nicolaka/netshoot ps aux      # 2. conteneur d'outils dans le même namespace PID
docker inspect --format '{{.State.Pid}}' web                      # 3. PID côté hôte (→ 10607 chez moi)
ps -fp 10607                                                      #    détail de ce processus sur l'hôte
sudo ls -l /proc/10607/ns                                         #    ses namespaces (pid, net, mnt, uts, ipc…)
```

| Élément | Rôle |
|---|---|
| `docker top <conteneur>` | Liste les processus du conteneur sans rien exécuter dedans |
| `.State.Pid` | PID du processus principal **vu de l'hôte** ; dans le conteneur, c'est le **PID 1** (namespace PID) |
| `ps -f -p <pid>` | `-p` = ce processus seulement ; `-f` = format complet |
| `/proc/<pid>/ns` | Un lien par namespace auquel appartient le processus |
| `nicolaka/netshoot` | Image communautaire remplie d'outils de diagnostic (898 Mo) — pour dépanner, jamais comme base d'application |

**Colonnes de `docker images` :** `DISK USAGE` = place réelle sur le disque (décompressée) ; `CONTENT SIZE` =
taille compressée téléchargée ; `EXTRA` `U` = image **u**tilisée par au moins un conteneur.

### 6.15 Rootless et userns-remap : ne pas confondre (et ne pas installer maintenant)

**Deux approches différentes**, souvent mélangées :

| | Classique (le mien) | userns-remap | Rootless |
|---|---|---|---|
| `dockerd` tourne en | root | root | **utilisateur ordinaire** |
| root du conteneur = | vrai root de l'hôte | utilisateur ordinaire (traduit) | utilisateur ordinaire |
| Mise en place | — | `daemon.json` | `dockerd-rootless-setuptool.sh install` |
| Protection | faible | moyenne | forte |

**Vérifier si les user namespaces sont actifs :**

```bash
docker info | grep -i userns      # aucune ligne chez moi → non activé (root conteneur = root hôte)
```

**⚠️ Pourquoi je n'installe PAS le rootless maintenant (vérifié 2026-10-05) :**
- Prérequis **manquants** : paquet `uidmap` (fournit `newuidmap`/`newgidmap`) et `slirp4netns` (réseau)
  → `dockerd-rootless-setuptool.sh install` échouerait sur `newuidmap: command not found`.
- Le rootless crée un **second Docker séparé** : le conteneur `web`, les images et la config de logs du Docker
  classique n'y seraient pas visibles.
- Sujet de la **phase 8**, pas de l'apprentissage de base — à faire plus tard, sur une machine/VM dédiée.

Le jour venu : `sudo apt install uidmap slirp4netns`, puis arrêter le Docker classique avant d'installer le rootless.

**À retenir :**
1. Une image ne change jamais ; un conteneur est jetable.
2. Tout ce qui doit survivre va dans un **volume**.
3. Un conteneur n'est pas une machine virtuelle : c'est un **processus Linux isolé** (namespaces) et **limité** (cgroups).

---

## 7. autoheal — redémarrer les conteneurs « unhealthy »

**Date :** 2026-10-04 (notion lue, pas encore pratiquée)

**Le problème :** Docker sépare deux mécanismes.
- `HEALTHCHECK` : teste régulièrement si l'application répond → état `healthy` / `unhealthy`.
- Politique de redémarrage (`--restart=always`) : relance le conteneur **seulement quand son programme s'arrête**.

Une application **bloquée mais pas arrêtée** est marquée `unhealthy`… et Docker ne fait rien. **autoheal**
(conteneur communautaire `willfarrell/autoheal`) surveille les conteneurs et redémarre ceux qui passent
`unhealthy`.

```bash
docker run -d --name autoheal --restart=always -e AUTOHEAL_CONTAINER_LABEL=autoheal   -v /var/run/docker.sock:/var/run/docker.sock willfarrell/autoheal
docker run -d --label autoheal=true --health-cmd "curl -f http://localhost/ || exit 1" --health-interval 30s nginx
```

| Option | Rôle |
|---|---|
| `-e AUTOHEAL_CONTAINER_LABEL=autoheal` | Nom du label à surveiller (`all` = tous les conteneurs) |
| `-v /var/run/docker.sock:…` | Lui permet de piloter Docker pour redémarrer les conteneurs |
| `--label autoheal=true` | Marque le conteneur comme « à surveiller » |
| `--health-cmd` | Commande de test : code 0 = sain, 1 = malade |
| `--health-interval 30s` | Fréquence du test |

**À savoir :**
- ⚠️ Monte `docker.sock` → **pouvoir de root** sur l'hôte (comme Portainer) ; projet communautaire, pas officiel
  Docker → lire son code avant usage.
- Redémarrer ne répare pas la cause : une application malade toutes les heures a un vrai problème → lire les logs.
- Inutile sur **Kubernetes** (les *liveness probes* redémarrent nativement un conteneur malade : self-healing)
  et sur Docker Swarm. Utile avec Docker seul ou Docker Compose.

---

## 8. Logs d'un conteneur : `docker logs` et les pilotes de logs

**Date :** 2026-10-04 (lecture du guide)

Ce qu'un conteneur écrit sur sa sortie est récupéré par Docker et confié à un **pilote de logs** (*log driver*),
qui décide **où** vont les lignes.

| Pilote | Destination | `docker logs` ? |
|---|---|---|
| `json-file` | Fichier sur l'hôte, géré par Docker | ✅ |
| `local` | Idem, format compact | ✅ |
| `journald` | Journal de systemd | ✅ (Docker sait le relire) ; aussi `journalctl CONTAINER_NAME=<nom>` |
| `syslog` | Service de journalisation du système | ❌ chercher dans syslog |
| `fluentd` | Collecteur de logs externe | ❌ chercher dans le collecteur |

Avec un pilote qui envoie les logs ailleurs, Docker n'en garde pas de copie → `docker logs` vide. (Les versions
récentes gardent par défaut une petite copie locale, le *dual logging*, qui peut être désactivée.)

```bash
docker inspect --format='{{.HostConfig.LogConfig.Type}}' mon_conteneur
```

| Élément | Rôle |
|---|---|
| `docker inspect` | Toute la configuration du conteneur, en JSON |
| `--format='{{…}}'` | N'affiche qu'un champ (modèle Go) |
| `.HostConfig.LogConfig.Type` | Chemin du champ : le pilote de logs du conteneur |

**Chez moi :** `json-file` (réglé dans `daemon.json`, voir 1.5) → `docker logs` fonctionne. Le cas se posera
quand les logs partiront vers Loki.

**Quoi chercher dans des logs :**

| Message | Indique en général |
|---|---|
| `permission denied` | Droits : fichier, volume, port < 1024, utilisateur non root |
| `connection refused` | Service visé injoignable : mauvais port ou nom d'hôte, ou pas encore démarré |
| *stack trace* | Fonctions en cours au moment du plantage ; l'erreur réelle est en première ou dernière ligne |

---

## 9. `docker stats` : quelles colonnes surveiller, et pourquoi

**Date :** 2026-10-04 (lecture du guide)

```bash
docker stats --no-stream        # une seule mesure (sans --no-stream : rafraîchi en continu)
```

| Colonne | Pourquoi la surveiller | Si ça dérape |
|---|---|---|
| **MEM USAGE / LIMIT** | La plus critique : la mémoire ne se « ralentit » pas | À la limite, le noyau **tue** le conteneur (OOM, code 137). Une courbe qui monte sans redescendre = **fuite de mémoire** |
| **CPU %** | Travail normal, boucle infinie ou saturation | Le conteneur est **ralenti**, pas tué ; 100 % en continu sans raison = alerte |
| **NET I/O** | Le conteneur communique-t-il, et combien | Zéro sur un serveur web = il ne reçoit rien ; sortant énorme inattendu = boucle d'appels ou conteneur **compromis** |

**Différence clé :** le CPU est une ressource **compressible** (on étrangle, le conteneur continue) ; la mémoire
est **incompressible** (on refuse, le conteneur est tué).

**Autres colonnes :** `MEM %` (même info en pourcentage) ; `BLOCK I/O` (lectures/écritures disque — bases de
données) ; `PIDS` (nombre de processus — une explosion = programme qui se multiplie sans fin).

**Piège :** sans `--memory`, la colonne `LIMIT` affiche **toute la mémoire de l'hôte** → aucune limite réelle.
Toujours fixer `--memory` (et `--cpus`, `--pids-limit`).

### 9.1 Le swap et `--memory-swap`

**Swap** = une partie du **disque** utilisée comme mémoire de secours quand la RAM est pleine : Linux y déplace
les données les moins utilisées. Le programme n'est pas tué, mais le disque est des milliers de fois plus lent
que la RAM.

```bash
docker run -d --memory=512m --memory-swap=1g mon_app
```

| Option | Rôle |
|---|---|
| `--memory=512m` | RAM maximale |
| `--memory-swap=1g` | **Total** RAM + swap (pas la quantité de swap) → ici 512 Mo de swap |

| Réglage | Résultat |
|---|---|
| `--memory=512m --memory-swap=1g` | 512 Mo RAM + 512 Mo swap |
| `--memory=512m --memory-swap=512m` | 512 Mo RAM, aucun swap |
| `--memory=512m` seul | Par défaut, autant de swap que de RAM |
| `--memory-swap=-1` | Swap illimité |

**Déconseillé en production :** masque le manque de mémoire (lenteur silencieuse au lieu d'un OOM clair, code
137) ; ralentit toute la machine (disque partagé) ; Kubernetes demande traditionnellement de désactiver le
swap sur les nœuds. Vraie réponse : augmenter `--memory` ou corriger la fuite.

---

## 10. PID 1 et les signaux : pourquoi `docker stop` met 10 secondes

**Date :** 2026-10-04 (lecture du guide ; exemples à pratiquer)

**Vocabulaire**
- **Signal** : message envoyé par le système à un programme. `SIGTERM` = « arrête-toi proprement » ;
  `SIGKILL` = tué immédiatement, impossible à intercepter.
- **Handler** : la partie du programme qui réagit à un signal (finir les requêtes, fermer les fichiers…).
- **PID 1** : premier programme du conteneur. Règle du noyau : PID 1 **ignore** un signal pour lequel il n'a
  pas de handler (un processus ordinaire, lui, serait arrêté).

**Conséquence :** `docker stop` envoie SIGTERM → ignoré → Docker attend le délai de grâce (10 s) → SIGKILL.
Pas d'arrêt propre : connexions et écritures en cours coupées net.

**Démonstration**

```bash
docker run -d --name lent alpine sleep 1000
time docker stop lent            # ≈ 10 s : sleep (PID 1, sans handler) ignore SIGTERM, puis SIGKILL

docker run -d --init --name rapide alpine sleep 1000
time docker stop rapide          # < 1 s : tini (PID 1) reçoit SIGTERM et le relaie à sleep

docker rm lent rapide
```

| Élément | Rôle |
|---|---|
| `--init` | Place un mini-init (`tini`) en PID 1 : il relaie les signaux et nettoie les processus zombies |
| `time <commande>` | Mesure la durée d'exécution |

**Cas réels**

| Cas | Ce qui se passe sans arrêt propre |
|---|---|
| Base de données (PostgreSQL) | Pas le temps d'écrire les données en attente → réparation au redémarrage, perte possible |
| API web (FastAPI) | Requête en cours coupée → le client reçoit une erreur pendant le déploiement |
| Kubernetes | Délai de grâce de 30 s attendu **pour chaque** conteneur remplacé → mises à jour très lentes |
| Script `start.sh` qui lance `./mon_app` | Le **shell** est PID 1, sans handler, et ne transmet rien à l'application |
| `CMD python app.py` (forme shell) | PID 1 = `/bin/sh -c`, même piège |

**Solutions**

| Solution | Quand |
|---|---|
| `docker run --init` | Image non modifiable, ou programme qui ne gère pas les signaux |
| `exec ./mon_app` dans le script | `exec` **remplace** le shell par l'application, qui devient PID 1 |
| `CMD ["python", "app.py"]` (forme exec) | PID 1 = l'application directement — forme à préférer |
| `STOPSIGNAL SIGINT` (Dockerfile) | L'application s'arrête proprement sur un autre signal que SIGTERM |

**Diagnostic :** `docker stop` qui dure toujours ~10 s et code de sortie **137** → l'application n'a pas reçu
(ou pas traité) SIGTERM.

---

<!-- Ajouter les nouvelles entrées au-dessus de cette ligne, en suivant le même format. -->

## Ressources

Documentations officielles, plus le guide de Stéphane Robert (signalé à part). Vérifiées les 2026-09-28 et
2026-10-03 (chaque URL répond).

### Guide suivi — Stéphane Robert (non officiel, fil conducteur de l'apprentissage)
- Conteneurs — https://blog.stephane-robert.info/docs/conteneurs/
- Concepts Docker — https://blog.stephane-robert.info/docs/conteneurs/moteurs-conteneurs/docker/concepts/
- asdf-vm — https://blog.stephane-robert.info/docs/outils/systeme/asdf-vm/
- jq : traiter du JSON en ligne de commande — https://blog.stephane-robert.info/docs/admin-serveurs/linux/references/jq/
- crane — https://blog.stephane-robert.info/docs/conteneurs/outils/crane/

### Docker & WSL2
- Installer Docker Engine sur Ubuntu — https://docs.docker.com/engine/install/ubuntu/
- Post-installation (groupe `docker`, démarrage) — https://docs.docker.com/engine/install/linux-postinstall/
- Configurer les pilotes de logs — https://docs.docker.com/engine/logging/configure/
- Dual logging (lire les logs malgré un pilote distant) — https://docs.docker.com/engine/logging/dual-logging/
- Pilote `journald` — https://docs.docker.com/engine/logging/drivers/journald/
- `docker logs` — https://docs.docker.com/reference/cli/docker/container/logs/
- `docker inspect` (`--format`) — https://docs.docker.com/reference/cli/docker/inspect/
- Pilote de logs `json-file` (rotation `max-size`, `max-file`) — https://docs.docker.com/engine/logging/drivers/json-file/
- Mode rootless — https://docs.docker.com/engine/security/rootless/
- userns-remap (remappage des user namespaces) — https://docs.docker.com/engine/security/userns-remap/
- `user_namespaces(7)` — https://man7.org/linux/man-pages/man7/user_namespaces.7.html
- Surface d'attaque du démon Docker (groupe `docker` ≈ root) — https://docs.docker.com/engine/security/#docker-daemon-attack-surface
- Docker et les pare-feu (contournement d'`ufw`) — https://docs.docker.com/engine/network/packet-filtering-firewalls/
- Licence Docker Desktop (qui doit payer) — https://docs.docker.com/subscription/desktop-license/
- Docker Desktop et WSL (intégration par distribution) — https://docs.docker.com/desktop/features/wsl/
- systemd dans WSL — https://learn.microsoft.com/fr-fr/windows/wsl/systemd
- Configuration WSL (`wsl.conf`, `appendWindowsPath`) — https://learn.microsoft.com/fr-fr/windows/wsl/wsl-config
- `usermod` (options `-a`, `-G`) — https://man7.org/linux/man-pages/man8/usermod.8.html
- `newgrp` — https://man7.org/linux/man-pages/man1/newgrp.1.html

### Concepts Docker
- Vue d'ensemble de Docker (architecture client / démon / registre) — https://docs.docker.com/get-started/docker-overview/
- `docker run` — https://docs.docker.com/reference/cli/docker/container/run/
- `docker stop` (SIGTERM puis SIGKILL) — https://docs.docker.com/reference/cli/docker/container/stop/
- `docker kill` — https://docs.docker.com/reference/cli/docker/container/kill/
- Pilotes de stockage (couches, copy-on-write) — https://docs.docker.com/engine/storage/drivers/
- Stockage : volumes, bind mounts, tmpfs (vue d'ensemble) — https://docs.docker.com/engine/storage/
- Volumes — https://docs.docker.com/engine/storage/volumes/
- Bind mounts — https://docs.docker.com/engine/storage/bind-mounts/
- tmpfs — https://docs.docker.com/engine/storage/tmpfs/
- Capabilities du noyau et Docker — https://docs.docker.com/engine/security/#linux-kernel-capabilities
- `--cap-add`, `--cap-drop`, `--privileged` — https://docs.docker.com/engine/containers/run/#runtime-privilege-and-linux-capabilities
- `capabilities(7)` — https://man7.org/linux/man-pages/man7/capabilities.7.html
- `chroot(1)` — https://man7.org/linux/man-pages/man1/chroot.1.html
- Profils seccomp pour Docker — https://docs.docker.com/engine/security/seccomp/
- `seccomp(2)` — https://man7.org/linux/man-pages/man2/seccomp.2.html
- Profils AppArmor pour Docker — https://docs.docker.com/engine/security/apparmor/
- AppArmor (site officiel) — https://apparmor.net/
- `dockerd` (référence) — https://docs.docker.com/reference/cli/dockerd/
- containerd (site officiel) — https://containerd.io/
- runc — https://github.com/opencontainers/runc
- `systemctl` — https://www.freedesktop.org/software/systemd/man/latest/systemctl.html
- `systemd.unit` (`After`, `Wants`, `Requires`, `StartLimit…`, `WantedBy`) — https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html
- `systemd.service` (`Type`, `ExecStart`, `Restart`, `TimeoutStartSec`) — https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- `systemd.exec` (`Limit…`, `OOMScoreAdjust`) — https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- `systemd.resource-control` (`TasksMax`, `Delegate`) — https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html
- `systemd.kill` (`KillMode`) — https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html
- Configurer le démon Docker (systemd, `daemon.json`) — https://docs.docker.com/engine/daemon/
- Lire les logs du démon — https://docs.docker.com/engine/daemon/logs/
- `systemd.socket` (activation par socket) — https://www.freedesktop.org/software/systemd/man/latest/systemd.socket.html
- `journalctl` — https://www.freedesktop.org/software/systemd/man/latest/journalctl.html
- Variables d'environnement du client (`DOCKER_HOST`) — https://docs.docker.com/reference/cli/docker/#environment-variables
- Fichier `config.json` du client — https://docs.docker.com/reference/cli/docker/#docker-cli-configuration-file-configjson-properties
- Contextes Docker — https://docs.docker.com/engine/manage-resources/contexts/
- `docker login` et stockage des identifiants — https://docs.docker.com/reference/cli/docker/login/#credential-stores
- API du moteur Docker (Engine API) — https://docs.docker.com/reference/api/engine/
- `unix(7)` (sockets Unix) — https://man7.org/linux/man-pages/man7/unix.7.html
- Protéger l'accès au démon Docker — https://docs.docker.com/engine/security/protect-access/
- Accès distant au démon (risques du port 2375) — https://docs.docker.com/engine/daemon/remote-access/
- Tirer une image par son digest — https://docs.docker.com/reference/cli/docker/image/pull/#pull-an-image-by-digest-immutable-identifier
- Live restore (conteneurs qui survivent au redémarrage du démon) — https://docs.docker.com/engine/daemon/live-restore/
- Limites de ressources (`--cpus`, `--memory`) — https://docs.docker.com/engine/containers/resource_constraints/
- `--memory-swap` en détail — https://docs.docker.com/engine/containers/resource_constraints/#--memory-swap-details
- Kubernetes et le swap — https://kubernetes.io/docs/concepts/cluster-administration/swap-memory-management/
- `docker debug` (Docker Desktop uniquement) — https://docs.docker.com/reference/cli/docker/debug/
- `docker exec` — https://docs.docker.com/reference/cli/docker/container/exec/
- `docker top` — https://docs.docker.com/reference/cli/docker/container/top/
- `docker image ls` — https://docs.docker.com/reference/cli/docker/image/ls/
- netshoot (image d'outils réseau, communautaire) — https://github.com/nicolaka/netshoot
- `proc(5)` (`/proc/<pid>/ns`) — https://man7.org/linux/man-pages/man5/proc.5.html
- `docker diff` — https://docs.docker.com/reference/cli/docker/container/diff/
- `docker stats` — https://docs.docker.com/reference/cli/docker/container/stats/
- `namespaces(7)` — https://man7.org/linux/man-pages/man7/namespaces.7.html
- `cgroups(7)` — https://man7.org/linux/man-pages/man7/cgroups.7.html

### Santé des conteneurs & autoheal
- `HEALTHCHECK` (Dockerfile) — https://docs.docker.com/reference/dockerfile/#healthcheck
- Options de santé de `docker run` (`--health-cmd`, `--health-interval`) — https://docs.docker.com/reference/cli/docker/container/run/#health
- Politiques de redémarrage — https://docs.docker.com/engine/containers/start-containers-automatically/
- autoheal (projet communautaire) — https://github.com/willfarrell/docker-autoheal
- Kubernetes : liveness, readiness et startup probes — https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/

### PID 1 & signaux
- `docker run --init` — https://docs.docker.com/reference/cli/docker/container/run/#init
- Dockerfile : formes shell et exec (`CMD`, `ENTRYPOINT`) — https://docs.docker.com/reference/dockerfile/#shell-and-exec-form
- Dockerfile : `STOPSIGNAL` — https://docs.docker.com/reference/dockerfile/#stopsignal
- tini (le mini-init utilisé par `--init`) — https://github.com/krallin/tini
- `signal(7)` — https://man7.org/linux/man-pages/man7/signal.7.html
- `kill(2)` (règle des signaux envoyés à PID 1) — https://man7.org/linux/man-pages/man2/kill.2.html
- Kubernetes : arrêt d'un pod (délai de grâce) — https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination

### Portainer & Swarm
- Installer Portainer CE sous Linux — https://docs.portainer.io/start/install-ce/server/docker/linux
- Setup token Portainer — https://docs.portainer.io/faqs/installing/setup-token
- Guide « Swarm on Windows Container Service » (celui suivi par erreur) — https://docs.portainer.io/start/install-ce/server/swarm/wcs
- Ports réellement requis par Swarm — https://docs.docker.com/engine/swarm/swarm-tutorial/#open-protocols-and-ports-between-the-hosts

### Conteneurs : runtimes & standards
- FAQ suppression de dockershim (Kubernetes 1.24) — https://kubernetes.io/blog/2022/02/17/dockershim-faq/
- k3s : configuration avancée (containerd embarqué) — https://docs.k3s.io/advanced
- Open Container Initiative (OCI) — https://opencontainers.org/

### asdf
- Démarrer avec asdf (installation, shims, complétion) — https://asdf-vm.com/guide/getting-started.html
- Versions publiées (binaires + empreintes) — https://github.com/asdf-vm/asdf/releases
- Gérer les plugins (`plugin add`, `plugin update`) — https://asdf-vm.com/manage/plugins.html
- Gérer les versions (`install`, `set`, `list`, `current`) — https://asdf-vm.com/manage/versions.html
- Configuration (`.tool-versions`, variables d'environnement) — https://asdf-vm.com/manage/configuration.html

### Build multi-plateforme
- Builds multi-plateformes (plateformes, QEMU, index) — https://docs.docker.com/build/building/multi-platform/
- Driver `docker-container` — https://docs.docker.com/build/builders/drivers/docker-container/
- `docker buildx create` — https://docs.docker.com/reference/cli/docker/buildx/create/
- `docker buildx build` (`--platform`, `--push`) — https://docs.docker.com/reference/cli/docker/buildx/build/
- `docker manifest inspect` — https://docs.docker.com/reference/cli/docker/manifest/inspect/

### QEMU
- QEMU (site officiel) — https://www.qemu.org/
- Émulation en mode utilisateur — https://www.qemu.org/docs/master/user/main.html

### Artefacts OCI & chaîne d'approvisionnement
- OCI : recommandations sur les artefacts — https://github.com/opencontainers/image-spec/blob/main/artifacts-guidance.md
- Helm : utiliser un registre OCI (`helm push`) — https://helm.sh/docs/topics/registries/
- ORAS — https://oras.land/
- Syft (génération de SBOM) — https://github.com/anchore/syft
- SBOM (CISA) — https://www.cisa.gov/sbom
- Cosign (signature) — https://docs.sigstore.dev/cosign/signing/overview/
- Notation (Notary Project) — https://notaryproject.dev/
- Conftest — https://www.conftest.dev/
- Open Policy Agent / Rego — https://www.openpolicyagent.org/docs/latest/
- WebAssembly — https://webassembly.org/

### jq & crane
- jq (site officiel) — https://jqlang.org/
- Manuel de jq (filtres, options `-r`, `-c`) — https://jqlang.org/manual/
- crane (README officiel, go-containerregistry) — https://github.com/google/go-containerregistry/blob/main/cmd/crane/README.md
- Spécification OCI : manifeste d'image — https://github.com/opencontainers/image-spec/blob/main/manifest.md
- Spécification OCI : index d'image (multi-architecture) — https://github.com/opencontainers/image-spec/blob/main/image-index.md
- Plugin asdf utilisé pour jq (communautaire) — https://github.com/lsanwick/asdf-jq
- Plugin asdf utilisé pour crane (communautaire) — https://github.com/dmpe/asdf-crane

### Commandes shell
- `curl` (`-L`, `-O`, `-s`) — https://curl.se/docs/manpage.html
- `grep` (manuel GNU) — https://www.gnu.org/software/grep/manual/grep.html
- `tar` (`-x`, `-z`, `-f`) — https://man7.org/linux/man-pages/man1/tar.1.html
- `md5sum` — https://man7.org/linux/man-pages/man1/md5sum.1.html
- Manuel de bash (`type`, `${VAR:-défaut}`, heredoc, `source`) — https://www.gnu.org/software/bash/manual/bash.html
- `ssh` (`-b`, `-i`, destination, authentification par clé) — https://man.openbsd.org/ssh
- `ssh_config` (`Host`, `HostName`, `User`, `IdentityFile`, `IdentitiesOnly`) — https://man.openbsd.org/ssh_config
- `sshd` : format de `authorized_keys` — https://man.openbsd.org/sshd#AUTHORIZED_KEYS_FILE_FORMAT
- Commandes de base de WSL (`wsl -d`, `-l -v`, `--terminate`) — https://learn.microsoft.com/fr-fr/windows/wsl/basic-commands
