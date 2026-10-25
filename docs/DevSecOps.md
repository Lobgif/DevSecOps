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

**À quoi servent les user namespaces, et pourquoi rootless / userns-remap**

Problème de base : par défaut, **root dans le conteneur = root réel de l'hôte** (prouvé en 6.10). Invisible
tant que tout va bien ; dangereux dans deux cas :
- **évasion de conteneur** (une faille permet de « sortir ») → l'attaquant est root sur toute la machine ;
- **image piégée** téléchargée depuis Internet, dont le code root agit via un volume monté.

Question résolue : « si le conteneur s'échappe ou si l'image est piégée, l'attaquant devient-il root sur ma
machine ? »

Un **user namespace** traduit les utilisateurs : root du conteneur (0) → utilisateur **ordinaire** de l'hôte
(ex. 100000). C'est ce que décrit `/etc/subuid` (`lahigic:100000:65536` = UID 0–65535 du conteneur →
100000–165535 sur l'hôte). Dans le conteneur, le programme se croit root ; sur l'hôte, il n'a aucun privilège.
Analogie : un faux coffre de banque — même « réussir » le braquage ne vole rien de réel.

Buts concrets : serveur **partagé** (empêcher une prise de contrôle totale via Docker) ; secteur **réglementé**
(banque/santé exigent souvent que rien ne tourne en root — case d'audit) ; **moindre privilège** (fil rouge du
DevSecOps : une app web n'a aucune raison d'être root sur l'hôte).

Nuance entre les deux : **userns-remap** protège les conteneurs mais `dockerd` reste root (faille de `dockerd`
= problème entier) ; **rootless** fait tout tourner sans root, y compris `dockerd` (protection maximale, au
prix de limites : ports < 1024, overlay…).

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

## 11. User namespaces — opt-in, feature gates et Kubernetes

**Date :** 2026-10-05 (lecture du guide)

### 11.1 L'opt-in expliqué

| Terme | Ce que ça veut dire |
|---|---|
| **Alpha** | Expérimental, peut être retiré sans préavis |
| **Beta** | Prêt à tester, mais l'API peut encore changer ; pas garanti stable |
| **Feature gate** | Un interrupteur dans Kubernetes (flag à passer à `kube-apiserver`, `kubelet`…) à activer manuellement pour débloquer une fonction expérimentale |
| **Activé par défaut** | Depuis v1.33, le feature gate `UserNamespacesSupport` est `true` sans rien faire |
| **Opt-in au niveau du pod** | Même si la fonction est disponible, **chaque pod doit l'activer** dans sa spec |

Le pod doit écrire dans son YAML :
```yaml
spec:
  hostUsers: false   # false = activer le user namespace pour ce pod
```
Sans cette ligne : comportement classique, root dans le conteneur = UID 0 sur le nœud.

### 11.2 Cgroups v1 vs v2 — ce qui change concrètement

**v1 = une hiérarchie par contrôleur.** CPU, mémoire, blkio (I/O disque) : chacun a son propre arbre séparé.
Un processus peut figurer dans plusieurs arbres en même temps, parfois de façon incohérente.

**v2 = un seul arbre unifié.** Tout est cohérent, et ça ouvre des fonctions nouvelles, notamment les métriques
PSI (*Pressure Stall Information*) : Docker peut dire « ce conteneur a manqué de mémoire pendant 200 ms cette
minute », pas juste « il utilise 512 Mo ».

| | v1 (ma machine) | v2 |
|---|---|---|
| `--memory-swap` | ✅ | ✅ |
| Limitation débit disque (`blkio throttle`) | ❌ non supporté dans WSL2 (les 4 warnings de `docker info`) | ✅ |
| Métriques mémoire PSI | ❌ approximatives | ✅ précises |
| Kubernetes 1.25+ | Mode maintenance | Standard recommandé |

### 11.3 Pourquoi ma machine montre les deux

`mount | grep cgroup` montre cgroup v1 **et** v2 en même temps → mode **hybride** du noyau WSL2 :
- `cgroup2 on /sys/fs/cgroup/unified` → le noyau supporte v2
- `cgroup on /sys/fs/cgroup/memory` etc. → il monte quand même v1 en parallèle

`docker info` indique `Cgroup Version: 1` → `dockerd` utilise v1, malgré la disponibilité de v2.
Les 4 avertissements dans `docker info` indiquent que la migration vers v2 sera obligatoire (avant mai 2029).

**À faire sur ma machine :** rien. La migration v2 se fait au niveau du noyau et du démon. C'est un sujet de
production, pas d'apprentissage maintenant.

---

## 12. Seccomp — profils et filtrage des syscalls

**Date :** 2026-10-05 (lecture du guide)

### 12.1 Structure d'un profil personnalisé

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64"],
  "syscalls": [
    { "names": ["read", "write", "exit", "exit_group"], "action": "SCMP_ACT_ALLOW" }
  ]
}
```

| Champ | Rôle |
|---|---|
| `defaultAction: SCMP_ACT_ERRNO` | Tout syscall non listé est **refusé** — renvoie une erreur au processus |
| `SCMP_ACT_ALLOW` | Le syscall est autorisé |
| `SCMP_ACT_KILL` | Le processus est tué immédiatement (sans signal) |
| `architectures` | Limiter à une ou plusieurs ABI (x86_64, ARM64…) |

Ce profil ultra-restrictif est un exemple. En production, le profil par défaut de Docker (`moby/moby`)
autorise ~300 syscalls et en bloque une quarantaine.

### 12.2 Les syscalls bloqués par défaut — pourquoi

| Syscall | Ce qu'il fait | Pourquoi bloqué |
|---|---|---|
| `reboot` | Redémarre la machine | Inutile dans un conteneur ; dangereux |
| `mount` / `umount` | Monte / démonte des systèmes de fichiers | Permettrait d'échapper à l'isolation |
| `ptrace` | Surveille/contrôle un autre processus | Permet de lire ou modifier la mémoire d'autres processus |
| `clock_settime` | Change l'heure système | Affecte toute la machine |
| `kexec_load` | Charge un nouveau noyau | Remplacement de l'OS en cours d'exécution |
| `bpf` | Charge des programmes eBPF | Peut surveiller ou modifier tous les processus |
| `add_key` / `keyctl` | Gère le trousseau de clés du noyau | Accès aux secrets d'autres processus |
| `acct` | Active la comptabilité BSD des processus | Accès fichier root-only |
| `pivot_root` | Change la racine du système de fichiers | Sortie potentielle de l'isolation |
| `swapon` / `swapoff` | Active/désactive le swap | Affecte la machine entière |

### 12.3 Appliquer un profil personnalisé

```bash
docker run --security-opt seccomp=/chemin/vers/profil.json nginx
```

Pour désactiver complètement seccomp (⚠️ ne pas faire en prod) :
```bash
docker run --security-opt seccomp=unconfined nginx
```

---

## 13. Réseau Docker — bridge, NAT et isolation

**Date :** 2026-10-05 (lecture du guide)

### 13.1 Ce qui se passe par défaut

```
docker run nginx    # sans --network = réseau bridge par défaut
```

Docker branche le conteneur sur un réseau virtuel interne appelé **bridge** (`docker0`). Par défaut :
1. **Tous** les conteneurs sur ce bridge se voient **entre eux par adresse IP** (172.17.0.x)
2. Ils peuvent sortir vers Internet grâce à une règle **NAT** (comme ta box Internet pour tes appareils)
3. Aucun port n'est ouvert vers l'extérieur, sauf si on passe `-p host:conteneur`

### 13.2 Exemple concret — deux conteneurs qui se voient

```bash
# Lancer deux conteneurs sur le bridge par défaut
docker run -d --name serveur nginx
docker run -d --name client  alpine sleep 1000

# Trouver l'IP du serveur
docker inspect --format '{{.NetworkSettings.IPAddress}}' serveur
# → 172.17.0.2

# Depuis client, accéder au serveur par IP (aucun port publié, pourtant ça marche)
docker exec client wget -qO- http://172.17.0.2
# → la page d'accueil de nginx s'affiche
```

Résultat : deux conteneurs sans aucun lien configuré, mais ils se parlent directement par IP.
Si mon API et ma base de données sont sur le bridge par défaut, n'importe quel autre conteneur
peut **attaquer la base par IP**.

### 13.3 Contre-exemple — réseaux séparés

```bash
docker network create reseau_a
docker network create reseau_b
docker run -d --name serveur --network reseau_a nginx
docker run -d --name client  --network reseau_b alpine sleep 1000

docker exec client wget -qO- http://172.18.0.2
# → connexion refusée : les deux réseaux sont isolés
```

### 13.4 Contre-exemple — couper l'accès Internet

```bash
docker run --rm --network none alpine curl https://example.com
# → Network unreachable : aucune carte réseau, aucun accès
```

### 13.5 Bonne pratique

Créer un réseau dédié par application, n'y placer que les conteneurs qui doivent se parler :

```bash
docker network create fleettrack_network
docker run -d --name api --network fleettrack_network mon_api
docker run -d --name db  --network fleettrack_network postgres
# → api peut joindre db par nom (DNS interne Docker) ; aucun autre conteneur ne peut les joindre
```

Dans Docker Compose, chaque `docker-compose.yml` crée un réseau dédié automatiquement → les
conteneurs d'un projet ne voient pas ceux d'un autre projet.

### 13.6 NAT et sortie vers Internet

Docker ajoute une règle **iptables/nftables** sur l'hôte : tout trafic sortant d'un conteneur est
traduit vers l'IP de la machine (MASQUERADE). C'est pour ça qu'un conteneur peut faire
`curl https://example.com` sans aucune configuration supplémentaire.

Corollaire de sécurité : si un conteneur est compromis, il peut contacter l'extérieur (exfiltration,
téléchargement de code malveillant). Pour bloquer la sortie : `--network none`, ou des règles
iptables avancées (`--icc=false`, politiques sortantes).

### 13.7 Nettoyage des conteneurs de test

```bash
docker rm -f serveur client
docker network rm reseau_a reseau_b
```

---

## 14. Protocoles réseau, adressage IP et calculs de sous-réseaux

**Date :** 2026-10-05 (lecture + exercices)

### 14.1 TCP vs UDP

| | TCP | UDP |
|---|---|---|
| Connexion | Oui (handshake 3 voies) | Non |
| Fiabilité | Garantit livraison et ordre | Envoie et oublie |
| Vitesse | Plus lent (accusés de réception) | Plus rapide |
| Usage | HTTP, SSH, base de données | DNS, vidéo, VXLAN overlay |

**Handshake TCP :**
```
Client → Serveur : SYN        (« je veux me connecter »)
Serveur → Client : SYN-ACK    (« ok, je t'entends »)
Client → Serveur : ACK        (« parfait, on commence »)
```
Toute donnée perdue est retransmise automatiquement.

**Contre-exemple UDP :** un appel vidéo. Si un paquet est perdu, l'image pixelise une
fraction de seconde. Mieux vaut perdre un paquet que d'attendre sa retransmission et figer
l'image pendant 300 ms.

### 14.2 Ports Docker Swarm — pourquoi TCP *et* UDP pour 7946

| Port | Proto | Rôle |
|---|---|---|
| 2377/TCP | TCP | Gestion du cluster (ordres orchestrateur → nœuds) — fiabilité requise |
| 7946/TCP | TCP | Découverte fiable (liste des membres) |
| 7946/UDP | UDP | Gossip rapide (est-il encore en vie ?) |
| 4789/UDP | UDP | Trafic overlay VXLAN (paquets conteneurs encapsulés) — volume élevé, latence faible |

### 14.3 Adressage IPv4 — structure

Une adresse IPv4 = **32 bits**, écrite en 4 octets décimaux (0–255) séparés par des points.

```
192   .  168  .   1  .  42
11000000.10101000.00000001.00101010
```

**Plages privées (RFC 1918) — jamais routées sur Internet :**

| Plage | CIDR | Usage typique |
|---|---|---|
| 10.0.0.0 → 10.255.255.255 | 10.0.0.0/8 | Réseaux d'entreprise |
| 172.16.0.0 → 172.31.255.255 | 172.16.0.0/12 | Docker (172.17.x.x, 172.18.x.x…) |
| 192.168.0.0 → 192.168.255.255 | 192.168.0.0/16 | Box domestique |

**Contre-exemple :** `8.8.8.8` est publique (DNS Google). Si tu la mets dans un fichier de
config comme IP locale, les paquets partent sur Internet — le noyau ne la traite jamais comme
locale.

### 14.4 Notation CIDR et calculs

`/N` = les N premiers bits identifient le réseau. Les `32 − N` bits restants identifient les hôtes.

**Formule :**
- Adresses totales = **2^(32−N)**
- Hôtes utilisables = **2^(32−N) − 2** (−1 adresse réseau, −1 broadcast)

| CIDR | Masque | Adresses | Hôtes utilisables |
|---|---|---|---|
| /8 | 255.0.0.0 | 16 777 216 | 16 777 214 |
| /16 | 255.255.0.0 | 65 536 | 65 534 |
| /24 | 255.255.255.0 | 256 | **254** |
| /25 | 255.255.255.128 | 128 | 126 |
| /26 | 255.255.255.192 | 64 | 62 |
| /28 | 255.255.255.240 | 16 | 14 |
| /30 | 255.255.255.252 | 4 | **2** (liaison point à point) |
| /32 | 255.255.255.255 | 1 | 0 (une seule adresse, une interface) |

### 14.5 Calcul pas à pas — 192.168.10.0/26

```
/26 → 32 − 26 = 6 bits pour les hôtes
2^6 = 64 adresses

Adresse réseau    : 192.168.10.0   (bits hôtes = 000000)
Broadcast         : 192.168.10.63  (bits hôtes = 111111)
Plage utilisable  : 192.168.10.1 → 192.168.10.62  (62 hôtes)
```

**Découper 192.168.10.0/24 en 4 sous-réseaux /26 égaux :**

| Sous-réseau | Réseau | Plage hôtes | Broadcast |
|---|---|---|---|
| #1 | 192.168.10.0 | .1 → .62 | .63 |
| #2 | 192.168.10.64 | .65 → .126 | .127 |
| #3 | 192.168.10.128 | .129 → .190 | .191 |
| #4 | 192.168.10.192 | .193 → .254 | .255 |

**Contre-exemple :** `192.168.10.63` n'est **pas** un hôte — c'est le broadcast du sous-réseau #1.
Un paquet envoyé à cette adresse est reçu par **tous** les hôtes du réseau.

### 14.6 Protocoles applicatifs courants

| Protocole | Port | TCP/UDP | Rôle |
|---|---|---|---|
| SSH | 22 | TCP | Accès shell sécurisé |
| DNS | 53 | UDP (TCP si > 512 octets) | Résolution de noms |
| HTTP | 80 | TCP | Web non chiffré |
| HTTPS | 443 | TCP | Web chiffré (TLS) |
| PostgreSQL | 5432 | TCP | Base de données |
| Redis | 6379 | TCP | Cache |
| ICMP | — | ni TCP ni UDP | Ping, traceroute (messages de contrôle) |

**Contre-exemple DNS :** DNS utilise UDP par défaut. Si la réponse dépasse 512 octets, le client
refait la requête en TCP. Si le pare-feu bloque TCP/53, certaines résolutions DNS échouent
silencieusement — piège classique de configuration.

### 14.7 Ce que ça donne dans Docker

```bash
docker network inspect bridge
# "Subnet": "172.17.0.0/16"
# "Gateway": "172.17.0.1"   ← l'hôte, pont vers l'extérieur
```

- `172.17.0.1` = la passerelle (l'hôte Docker)
- `172.17.0.2`, `172.17.0.3`… = les conteneurs
- `/16` → 65 534 conteneurs max théoriques sur ce réseau

Quand on crée un réseau custom (`docker network create fleettrack`), Docker prend le prochain
bloc disponible dans `172.16.0.0/12` → `172.18.0.0/16`, `172.19.0.0/16`, etc.

---

## 15. Docker standalone vs Docker Swarm — toutes les différences

**Date :** 2026-10-05 (lecture + comparaison)

### 15.1 La différence fondamentale

| | Docker standalone | Docker Swarm |
|---|---|---|
| **Quoi** | Un seul moteur sur une seule machine | Plusieurs machines (nœuds) = cluster |
| **Qui décide** | Toi, à la main | Le **manager** Swarm (orchestrateur) |
| **Unité de base** | Le conteneur | Le **service** |
| **Résilience** | Si le conteneur meurt, il est mort | Swarm en recrée un automatiquement |

### 15.2 Conteneur vs Task vs Service

```
Service  = la définition (« je veux 3 nginx »)
Task     = une instance du service = un conteneur en cours d'exécution
Conteneur = ce que runc exécute réellement

docker service create --name web --replicas 3 nginx
→ 1 service  "web"
→ 3 tasks    "web.1", "web.2", "web.3"
→ 3 conteneurs, un par nœud disponible
```

| Commande standalone | Équivalent Swarm |
|---|---|
| `docker ps` | `docker service ps web` |
| `docker run` | `docker service create` |
| `docker stop` | `docker service rm` |
| `docker logs mon_conteneur` | `docker service logs web` |
| `docker inspect` | `docker service inspect web` |

### 15.3 Image — identique, mais doit être dans un registre

L'image est la même. Ce qui change : chaque nœud doit pouvoir la télécharger.

**Contre-exemple :** `docker build` local crée une image **uniquement sur ta machine**. Les
autres nœuds ne l'ont pas. Il faut la pousser dans un registre avant de la déployer en Swarm.

### 15.4 Réseau — bridge local vs overlay distribué

| | bridge (standalone) | overlay (Swarm) |
|---|---|---|
| Portée | Une seule machine | Tous les nœuds du cluster |
| Technologie | Pont virtuel Linux | VXLAN : encapsule les paquets dans UDP/4789 |
| DNS interne | Par nom de conteneur | Par **nom de service** |
| Chiffrement | Non | Optionnel (`--opt encrypted`) |

```bash
docker network create --driver overlay mon_overlay
# Les services se joignent par nom de service :
# dans "api", "db" résout vers l'IP virtuelle (VIP) de "db"
# → Swarm fait le load balancing entre les tasks automatiquement
```

**Réseau ingress (automatique) :** quand on publie un port (`-p 80:80`), n'importe quel nœud
du cluster peut recevoir le trafic, même sans task locale → **routing mesh**.
```
Utilisateur → nœud 3 (port 80) → Swarm redirige vers nœud 1 (qui a la task)
```

### 15.5 Volume — le piège principal de Swarm

Un volume `driver: local` reste **sur le nœud courant**. Si la task migre, le volume ne suit pas.

| Solution | Principe |
|---|---|
| NFS | Dossier réseau monté sur tous les nœuds |
| Pilote distribué (Longhorn, Portworx) | Plugin Docker qui synchronise |
| Serveur externe | Base de données hors Swarm, les tasks s'y connectent |

**Contre-exemple critique :** PostgreSQL en Swarm avec `--replicas 2` et volume local → deux
instances écrivent chacune dans leur propre volume → **corruption de données garantie**.
PostgreSQL n'est pas conçu pour s'exécuter en deux instances sur deux volumes différents.

### 15.6 Stack — l'équivalent Swarm de docker compose up

| | Docker Compose | Docker Stack |
|---|---|---|
| Commande | `docker compose up` | `docker stack deploy -c fichier.yml mon_stack` |
| État | Conteneurs sur une machine | Services distribués sur le cluster |
| Mise à jour | Downtime | Rolling update (zéro downtime) |

Section `deploy:` dans le compose : ignorée par `docker compose`, utilisée par Swarm :

```yaml
services:
  web:
    image: nginx
    deploy:
      replicas: 3
      update_config:
        parallelism: 1          # mettre à jour 1 replica à la fois
        delay: 10s
      restart_policy:
        condition: on-failure
      placement:
        constraints:
          - node.role == worker # ne pas déployer sur le manager
```

### 15.7 Nœuds — concept absent en standalone

| Rôle | Fonction |
|---|---|
| **Manager** | Prend les décisions, maintient l'état (Raft consensus), peut exécuter des tasks |
| **Worker** | Exécute les tasks, ne prend pas de décisions |

```bash
docker node ls
docker node update --availability drain mon_noeud   # vider un nœud pour maintenance
```

Pour la HA : **au moins 3 managers** (quorum Raft : tolère 1 panne). Avec 1 seul manager,
si il tombe, le cluster est en lecture seule.

### 15.8 Secrets et configs — spécifiques à Swarm

```bash
# Secret : données sensibles
echo "mot_de_passe" | docker secret create db_password -
docker service create --secret db_password postgres
# → monté en lecture seule dans /run/secrets/db_password dans le conteneur
```

En standalone, les secrets passent par `-e` (variable d'environnement) → visible dans
`docker inspect` et les logs du démon. Pas sécurisé.

```bash
# Config : fichier de configuration
docker config create nginx_conf ./nginx.conf
docker service create --config nginx_conf nginx
```

### 15.9 Résumé en tableau

| Élément | Standalone | Swarm |
|---|---|---|
| Unité déployée | `container` | `service` → `tasks` |
| Commande déploiement | `docker run` | `docker service create` |
| Fichier config | `docker compose up` | `docker stack deploy` |
| Réseau | `bridge` (local) | `overlay` (cross-nœuds) |
| Volume | Local à la machine | Doit être partagé (NFS/plugin) |
| Secrets | Variable d'environnement | `docker secret` (chiffré, monté) |
| Ports | Publiés sur l'hôte | Routing mesh (n'importe quel nœud répond) |
| Résilience | Manuelle | Automatique |
| Mise à jour | Downtime | Rolling update (zéro downtime) |
| Nœuds | Aucune notion | Managers + Workers |

---

## 16. Réseau macvlan — conteneur avec une vraie IP sur le réseau physique

**Date :** 2026-10-05 (lecture + comparaison)

### 16.1 Le problème que macvlan résout

Tous les réseaux Docker vus jusqu'ici utilisent du **NAT** : le conteneur a une IP privée
(`172.17.0.x`) masquée derrière l'IP de la machine hôte.

Avec **macvlan**, le conteneur a une **vraie IP du réseau local** et une **vraie adresse MAC**.
Les autres appareils (box, serveurs) le voient comme un appareil physique indépendant.

```
Sans macvlan : Conteneur (172.17.0.2) → NAT → Hôte (192.168.1.10) → Réseau
Avec macvlan : Conteneur (192.168.1.50, MAC propre)                → Réseau directement
```

### 16.2 D'où viennent subnet, parent, gateway

`ip -br link` et `ip route` donnent les valeurs à copier.

```bash
ip -br link
# eth0  UP  52:54:00:ab:cd:ef   ← la carte réseau → valeur de --opt parent

ip route
# default via 192.168.1.1 dev eth0   ← box/routeur → valeur de --gateway
# 192.168.1.0/24 dev eth0            ← réseau local → valeur de --subnet
```

```bash
docker network create \
  --driver macvlan \
  --subnet 192.168.1.0/24 \
  --gateway 192.168.1.1 \
  --opt parent=eth0 \
  mon_macvlan

docker run --rm --network mon_macvlan --ip 192.168.1.50 nginx
# → nginx visible sur 192.168.1.50 depuis tout le réseau local
```

### 16.3 Quand l'utiliser (et quand ne pas l'utiliser)

| Cas utile | Cas inutile |
|---|---|
| Appliance réseau (firewall, routeur) dans un conteneur | API web → bridge + `-p 80:80` |
| Système legacy qui attend une IP fixe du réseau physique | Base de données → réseau interne |
| Pi-hole, AdGuard (domotique / home lab) | Stack applicatif complet → Compose |
| Monitoring SNMP | **FleetTrack → pas de macvlan** |

### 16.4 Limitation sur WSL2

Macvlan exige de mettre la carte en **mode promiscuous**. Hyper-V bloque ça sur ses
adaptateurs virtuels → macvlan ne fonctionne pas correctement dans WSL2.

**Contre-exemple :** la création du réseau ne donne pas d'erreur, mais les paquets ne
sortent pas de WSL2 vers le réseau physique. Pour tester macvlan, il faut une VM
VirtualBox avec adaptateur en mode **Bridged/Promiscuous**, ou une vraie VM cloud.

### 16.5 À retenir

```
ip -br link  → nom de la carte (eth0, ens3…)  → "parent"
ip route     → ton réseau (192.168.1.0/24)    → "subnet"
             → ta box (192.168.1.1)            → "gateway"

macvlan = conteneur avec une vraie IP sur le réseau physique, sans NAT
→ cas spécifiques (appliances, legacy, home lab)
→ pas utile pour FleetTrack
→ ne fonctionne pas dans WSL2 sans config Hyper-V
```

---

## 17. Apprendre les réseaux hors Docker — plan et ressources

**Date :** 2026-10-05

### 17.1 Ce que macvlan/ipvlan suppose de connaître

| Notion | Ce que c'est |
|---|---|
| Adresse MAC | Identifiant physique d'une carte réseau (couche 2) |
| L2 / L3 | Couche liaison (MAC, switch) vs couche réseau (IP, routeur) |
| VLAN | Réseau local virtuel — segmentation L2 |
| Bridge / switch | Connecte des appareils au niveau MAC |
| Routage | Décision de vers où envoyer un paquet |
| NAT | Traduction d'adresse (ce que fait la box) |
| iptables / nftables | Pare-feu Linux (manipulé automatiquement par Docker) |

### 17.2 ipvlan vs macvlan

| | macvlan | ipvlan |
|---|---|---|
| MAC par conteneur | Propre MAC distincte | Partage la MAC de l'hôte |
| Quand | Réseau qui autorise plusieurs MAC par port | Cloud providers, commutateurs stricts (1 seule MAC autorisée par port) |

Sur une VM cloud (AWS, Oracle, GCP), macvlan échoue souvent car la carte n'accepte qu'une MAC.
ipvlan L3 fonctionne car il n'en ajoute pas de nouvelle.

### 17.3 Plan d'apprentissage

```
Maintenant        → Stéphane Robert Docker network (lecture en cours)
Semaine suivante  → Professor Messer : OSI, IP Addressing, Routing (3-4h)
Ensuite           → Julia Evans "Networking!" zine (pratique, visuel)
Ensuite           → iproute2 : pratiquer ip link, ip route, ip addr
Ensuite           → Revenir à macvlan/ipvlan : tout sera clair
```

Pour FleetTrack : bridge + overlay (Swarm) suffisent. Le reste est de la culture réseau
utile pour comprendre les pare-feux, load balancers et CNI Kubernetes.

---

## 18. Volumes partagés — entre services et entre clusters

**Date :** 2026-10-20

### 18.1 Le problème

Un volume `local` vit **sur un seul nœud**. Dès que plusieurs services (ou clusters)
doivent lire/écrire les mêmes données, il faut un stockage **accessible depuis
l'extérieur des nœuds**.

### 18.2 Plusieurs services du même cluster — NFS (le plus simple)

Docker crée un volume NFS nativement :

```bash
docker volume create --driver local \
  --opt type=nfs \
  --opt o=addr=192.168.1.100,rw \
  --opt device=:/export/partage \
  vol_partage

docker service create --name api --mount source=vol_partage,target=/data nginx
```

Tous les réplicas, sur n'importe quel nœud, voient le même `/data`.

| Autre solution | Quand |
|---|---|
| CIFS/SMB | Partage Windows/NAS déjà en place |
| AWS EFS (via NFS) | Sur EC2 — managé, scalable, zéro serveur à maintenir |
| GlusterFS / Ceph | Redondance (éviter le serveur NFS unique = point de panne) |
| Portworx / Longhorn / REX-Ray | Stockage distribué avancé (snapshots, réplication) |

### 18.3 Entre plusieurs clusters

Le volume Docker ne suffit plus : stockage réseau atteint par tous les clusters.

| Solution | Principe |
|---|---|
| NFS / EFS partagé | Les deux clusters montent le même export réseau |
| Ceph / GlusterFS | Cluster de stockage séparé, accessible par les deux |
| Object storage (S3 / MinIO) | Les apps lisent/écrivent via l'API S3, pas via un montage disque — idéal fichiers, backups, artefacts |

### 18.4 Piège majeur : l'écriture concurrente

Partager un volume ≠ partager n'importe quelle donnée.

- ✅ **Fichiers statiques, configs, uploads, assets** → NFS parfait, plusieurs
  lecteurs/écrivains OK.
- ❌ **Bases de données** (PostgreSQL, MySQL) → **jamais** deux instances sur le même
  volume NFS, elles se corrompent mutuellement. Pour scaler une DB, utiliser sa
  **réplication native** (streaming replication Postgres), pas un volume partagé.

**Règle :** le volume partagé sert aux données « plates » (fichiers). Les données
transactionnelles (DB) se répliquent au niveau applicatif, pas au niveau stockage.

### 18.5 Préparer un export NFS — pourquoi `chown 65534`

```bash
sudo mkdir -p /srv/nfs/partage /srv/nfs/projets   # -p : crée aussi les dossiers parents
sudo chown 65534:65534 /srv/nfs/partage /srv/nfs/projets
```

`65534` = l'utilisateur **`nobody`** (groupe `nogroup`), l'identité « anonyme » Linux.

**Pourquoi.** Par défaut NFS applique le **root squash** : un client connecté **en root**
qui écrit dans le partage ne reçoit pas les droits root réels — le serveur « écrase »
(*squash*) son identité vers `nobody` (UID 65534). Protection : sans ça, root sur une
machine cliente = root sur les fichiers du serveur NFS.

Comme les clients écrivent *en tant que* `nobody`, le dossier doit **appartenir à
`nobody`** pour qu'ils puissent y écrire. Laissé à `root:root` en `755`, ils ne
pourraient que lire.

**D'où vient le chiffre.** UID sur 16 bits → max 65535. Réservés : `65535` = `-1`
(invalide), `65534` = `nobody` juste en dessous. Vérifier : `id 65534`.

**⚠️ Nuance.** `65534` partout = tout le monde partage la même identité anonyme : aucune
séparation entre clients (A peut écraser les fichiers de B). Pour de vrais droits par
utilisateur : conserver les UID réels (`no_root_squash`, ou mappage NFSv4 `idmapd` /
Kerberos) — plus complexe, à ouvrir seulement quand le besoin arrive.

### 18.6 Volume plugins (pilotes de stockage tiers)

Un volume plugin = un pilote tiers branché sur Docker pour parler à un stockage externe
que le pilote `local` ne sait pas gérer.

```bash
docker plugin install vieux/sshfs
docker plugin ls
docker volume create -d vieux/sshfs \
  -o sshcmd=user@serveur:/data -o password=xxx  mon_volume
```

| Plugin | Cible |
|---|---|
| REX-Ray | AWS EBS, GCP, OpenStack (historique) |
| Portworx | Stockage distribué d'entreprise (snapshots, chiffrement, réplication) |
| vieux/sshfs | Dossier distant via SSH (simple, pour tester) |
| local-persist | Volume local à un chemin fixe |
| GlusterFS / Ceph RBD | Stockage distribué redondant |

**Plugin vs `--opt type=nfs` :** le NFS via `--driver local --opt type=nfs` utilise le
pilote **intégré** (pas de plugin, suffit dans 90 % des cas). Le plugin sert quand Docker
ne sait pas gérer le stockage nativement (EBS, Portworx, snapshots, chiffrement…).

**En 2026 :** côté Docker Swarm l'écosystème de plugins stagne (beaucoup abandonnés), on
reste souvent sur NFS/`local`. Côté Kubernetes, les volume plugins sont remplacés par le
**CSI** (*Container Storage Interface*), le standard moderne — c'est en CSI que
s'installent les drivers EBS/EFS, Longhorn, Ceph.

### 18.7 Où installer le plugin, où créer le volume

| Élément | Où |
|---|---|
| Backend de stockage (serveur NFS, Ceph…) | Une machine **joignable par tous les nœuds** |
| Plugin / pilote de volume | Sur **CHAQUE nœud** qui exécutera une task utilisant le volume |
| Création du volume | Déclarée **une fois** (dans la stack) — matérialisée sur chaque nœud où une task atterrit |

⚠️ **En Swarm, aucune distribution automatique des plugins** : les installer à la main
sur chaque nœud (ou via Ansible).

**Cas 1 — une seule machine, plusieurs services :** tout au même endroit. Plugin installé
1 fois, `docker volume create` 1 fois, tous les services partagent. Le pilote `local`
suffit, pas besoin de NFS.

**Cas 2 — 3 machines (vrai cluster) :**
1. Monter le backend (NFS/Ceph) sur une machine à part joignable par les 3 (ne pas le
   coloc sur un nœud Swarm → point de panne unique).
2. Installer le plugin — ou `nfs-common` si NFS intégré — sur les **3** nœuds.
3. **Ne pas** faire `docker volume create` à la main sur un seul nœud. Déclarer le volume
   dans la **stack** pour que la définition (`driver_opts`) soit distribuée :
   ```yaml
   services:
     api:
       image: nginx
       deploy: { replicas: 3 }
       volumes:
         - partage:/data
   volumes:
     partage:
       driver: local
       driver_opts:
         type: nfs
         o: "addr=192.168.1.100,rw"
         device: ":/srv/nfs/partage"
   ```
   Chaque nœud monte le même export → `api.1/2/3` voient le même `/data`.

**Piège :** un `docker volume create` manuel sur un seul nœud → les tasks des autres
nœuds ne voient rien (ou créent un volume local vide). D'où la déclaration dans la stack.

### 18.8 Équivalent Kubernetes

Même logique sous un autre nom : les **PersistentVolumes**, avec des modes d'accès :

| Mode | Signification |
|---|---|
| `ReadWriteOnce` (RWO) | Monté en lecture/écriture par **un seul** nœud |
| `ReadWriteMany` (RWX) | Lecture/écriture par **plusieurs** nœuds (nécessite NFS/Ceph/EFS) |
| `ReadOnlyMany` (ROX) | Lecture seule par plusieurs nœuds |

---

## 19. SSH : WSL ≠ Git Bash — deux environnements séparés

**Date :** 2026-10-20

Sur une même machine Windows, **Git Bash (MINGW64)** et **WSL** sont deux mondes
indépendants, chacun avec son propre `~/.ssh/` (clés, `config`, `known_hosts`).

| | Git Bash (MINGW64) | WSL (Ubuntu) |
|---|---|---|
| `~` pointe vers | `C:\Users\lahig` | `/home/lahigic` |
| `~/.ssh/` | `C:\Users\lahig\.ssh\` | `/home/lahigic/.ssh/` |
| Accès à l'autre | — | les fichiers Windows via `/mnt/c/Users/lahig/.ssh/` |

**Conséquence :** un alias ou une clé qui marche dans l'un **n'existe pas** dans l'autre.
`ssh aws-vm1` qui fonctionne dans Git Bash échouera dans WSL si la clé et le bloc `Host`
ne sont pas aussi présents dans `/home/lahigic/.ssh/config`.

**Symptôme vécu :** `Identity file /c/Users/lahig/.ssh/vm1.pem not accessible: No such
file or directory` → la clé n'était pas à ce chemin dans cet environnement ; le vrai
chemin était défini dans le `~/.ssh/config` de l'autre shell.

**Règle pratique :**
- Docker tourne dans **WSL** → pour tout ce qui touche Docker (volume sshfs, plugins,
  déploiement SSH), c'est la clé et la config **côté WSL** qui comptent.
- Pour partager une clé Windows vers WSL :
  ```bash
  cp /mnt/c/Users/lahig/.ssh/<cle> ~/.ssh/ && chmod 600 ~/.ssh/<cle>
  ```
- Toujours vérifier dans **quel** shell on est avant de débugger un « Permission denied
  (publickey) » : le prompt `MINGW64` = Git Bash, un prompt Linux classique = WSL.

---

## 20. Clés SSH : emplacement, permissions, config, EC2

**Date :** 2026-10-23

### 20.1 Le piège de l'emplacement

`ssh-keygen` sauve la clé **là où tu réponds au prompt**. Si tu tapes un nom seul
(`id_ed25519_gitlab`) au lieu d'un chemin complet, la clé atterrit dans le **dossier
courant**, pas dans `~/.ssh/`.

```bash
# ✅ chemin complet → va dans ~/.ssh/
ssh-keygen -t ed25519 -C "mail@ex.com" -f ~/.ssh/id_ed25519_github
```

### 20.2 Permissions (et pourquoi)

| Cible | Droits | Pourquoi |
|---|---|---|
| Dossier `~/.ssh/` | `700` (`rwx------`) | Un dossier a besoin de `x` pour qu'on « entre » dedans ; personne d'autre |
| Clé **privée** | `600` (`rw-------`) | Secret absolu ; SSH **refuse** une clé privée trop ouverte |
| Clé **publique** | `644` (`rw-r--r--`) | Faite pour être partagée, aucun risque |

Lecture : chaque chiffre = `r(4)+w(2)+x(1)`, pour **propriétaire · groupe · autres**.

### 20.3 Config multi-hôtes (`~/.ssh/config`)

```
Host gitlab.com
    User git
    IdentityFile ~/.ssh/id_ed25519_gitlab
    IdentitiesOnly yes

Host github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes
```

`IdentitiesOnly yes` force SSH à n'essayer **que** la clé indiquée pour cet hôte (évite
le « Too many authentication failures » quand tu as plusieurs clés). ⚠️ Ne jamais éditer
ce fichier avec `sudo` : il appartiendrait à root et SSH l'ignorerait.

### 20.4 Se connecter à une VM EC2 (AWS)

| Point | Détail |
|---|---|
| Clé | AWS fournit un `.pem` (clé privée) ; `chmod 400` obligatoire |
| Utilisateur | `ubuntu` (Ubuntu), `ec2-user` (Amazon Linux), `admin`/`debian` (Debian) |
| IP publique | Visible dans la console EC2 (**Public IPv4**) ; **change à chaque stop/start** |
| IP fixe | Attacher une **Elastic IP** (gratuite tant qu'attachée à une instance active) |
| Échec `Permission denied (publickey)` | Clé non fournie (`-i`), mauvaise clé, ou mauvais utilisateur |
| Échec `timed out` | Security Group : port 22 fermé, ou instance stoppée |

```bash
ssh -i ~/.ssh/ma-cle.pem ubuntu@13.37.224.250
```

### 20.5 Copier une clé de Windows vers WSL

```bash
cp /mnt/c/Users/lahig/.ssh/<cle> ~/.ssh/ && chmod 600 ~/.ssh/<cle>
```
Voir [[docs-two-journals]] et la section 19 : WSL et Git Bash ont des `~/.ssh/` séparés.
`gh` n'est pas installé dans WSL (il l'est côté Windows) → on peut appeler `gh.exe`
depuis WSL, ou installer `gh` via le dépôt officiel.

---

## 21. Voir les adresses réseau par couche + `ss` + sockets

**Date :** 2026-10-23

### 21.1 Modèle en couches

Sur une machine Windows+WSL+Docker, les réseaux sont **emboîtés** :
```
Windows (vraie machine)
  └── WSL2 = VM Linux cachée        ← IP: ip -br addr → eth0
        ├── Docker (docker0, br-*)  ← 172.17/18/19…
        └── libvirt/KVM (virbr0)    ← 192.168.122.x
```

| Couche | Commande |
|---|---|
| Windows | `ipconfig` |
| Linux/WSL/VM/EC2 | `ip -br addr`, `ip route`, `ip -br link` |
| Docker (réseaux) | `docker network ls`, `docker network inspect <net>` |
| Docker (conteneur) | `docker inspect <c> -f '{{.NetworkSettings.Networks.<net>.IPAddress}}'` |

Lire `ip route` : la ligne `default via X dev eth0` = la sortie ; `src Y` = l'IP portée
par la machine sur cette interface ; `linkdown` = bridge sans conteneur connecté.

### 21.2 `ss -tlnp` : qu'est-ce qui écoute (= surface d'attaque)

| Option | Rôle |
|---|---|
| `-t` | TCP · `-u` | UDP |
| `-l` | sockets en écoute (LISTEN) |
| `-n` | numérique (garde les numéros de port) |
| `-p` | le processus (**nécessite `sudo`**) |

Colonne décisive = **Local Address** :

| Adresse | Qui peut se connecter |
|---|---|
| `127.0.0.1` / `%lo` | la machine elle-même → sûr |
| `0.0.0.0` / `*` | **toutes les interfaces** → exposé à l'extérieur ⚠️ |
| `[::]` | idem en IPv6 |

`Recv-Q` sur un LISTEN = connexions en attente d'acceptation ; `Send-Q` = taille max de
la file (backlog). Tout ce qui est en `0.0.0.0` est à questionner (NFS 2049, Swarm
2377/7946… à restreindre par pare-feu).

### 21.3 Socket ≠ réseau ≠ protocole

| Notion | Analogie téléphone | En vrai |
|---|---|---|
| Réseau | câbles, central | IP, routeurs, NAT |
| Protocole | la langue | TCP, UDP, HTTP, SSH |
| Port | le numéro de poste | quel service (80, 22…) |
| **Socket** | le combiné d'un programme | point de communication qu'un programme ouvre |

Deux familles de sockets :
- **Socket réseau** (TCP/UDP) : identifié par **IP:port**, entre machines.
- **Socket Unix** : identifié par un **chemin de fichier**, même machine.

**`docker.sock` n'est PAS un fichier texte** : c'est un **socket Unix**
(`srw-rw----`, le `s` le prouve), la porte d'entrée du démon. Le client écrit une requête
HTTP dedans, le démon lit et répond. Qui peut écrire dessus = **root** sur la machine.

---

## 22. L2 vs L3 et ipvlan (complète la section 16)

**Date :** 2026-10-23

### 22.1 La notion

| | Couche 2 (L2) | Couche 3 (L3) |
|---|---|---|
| Adresse | MAC | IP |
| Équipement | switch | routeur |
| Portée | un même réseau local | **entre** réseaux |
| Résolution | ARP (IP→MAC) | routage |

Règle : même sous-réseau → échange direct en L2 (ARP). Sous-réseaux différents → il faut
un routeur (L3). Preuve : `docker exec c ip neigh` (table ARP = L2) vs `ip route`
(route par défaut = le routeur L3).

### 22.2 macvlan vs ipvlan L2 vs ipvlan L3

| | macvlan | ipvlan L2 | ipvlan L3 |
|---|---|---|---|
| MAC | 1 par conteneur | partagée (hôte) | partagée (hôte) |
| Broadcast/ARP | oui | oui | **non** |
| Sous-réseaux multiples | non | non | **oui** |
| Rôle de l'hôte | pont L2 | pont L2 | **routeur L3** |
| Cas typique | home lab, appliance | **cloud (1 MAC/port)** | grande échelle, sans broadcast |

```bash
docker network create -d ipvlan -o parent=eth0 -o ipvlan_mode=l2 … ipvlan_l2
docker network create -d ipvlan -o parent=eth0 -o ipvlan_mode=l3 … ipvlan_l3
```

**Piège ipvlan L3 :** le reste du réseau ne connaît pas tes sous-réseaux → il faut
ajouter une **route statique** sur le routeur physique vers l'IP de l'hôte, sinon les
réponses ne reviennent jamais.

**Mode host — preuve vécue :** `docker run --network host … hostname -I` affiche **toutes**
les IP de l'hôte (les `.1` = gateways de l'hôte, pas des conteneurs). Un `.2`+ signalerait
du bridge. Sur WSL, « hôte » = la VM WSL, pas Windows.

---

## 23. Débugger méthodiquement : étude de cas WordPress + MySQL

**Date :** 2026-10-23

Un WordPress Compose renvoyait *« Error establishing a database connection »* (HTTP 500).
Méthode : **lire l'erreur exacte, éliminer les causes une par une avec des preuves.**

### 23.1 Lire le message mysqli — chaque erreur a un sens précis

| Erreur mysqli | Signification |
|---|---|
| `Access denied for user X@host` | TCP OK, **auth** refusée (mauvais mot de passe / user@host) |
| `Unknown database 'X'` | connecté mais la base n'existe pas |
| `Unknown MySQL server host` / getaddrinfo | **DNS** : le nom ne résout pas |
| `Connection refused` | le nom résout, mais **rien n'écoute** sur le port par ce chemin |
| `Can't connect` / timeout | réseau / pare-feu |

### 23.2 Le piège socket ≠ TCP

`docker compose exec mysql mysql -uwordpress -p… -e "SELECT 1"` **passe** → mais via le
**socket Unix local** du conteneur. Ça **ne prouve pas** que le port 3306 est joignable en
**TCP** depuis un autre conteneur. Le vrai test reproduit ce que fait l'app :
```bash
docker compose exec wordpress php -r '$m=@mysqli_connect("mysql","wordpress","PWD","wordpress"); echo $m?"OK\n":mysqli_connect_error()."\n";'
```

### 23.3 Le vrai coupable : l'init MySQL ne se fait qu'une fois

MySQL (et Postgres, Mongo…) ne crée l'utilisateur / la base / le mot de passe qu'au
**premier démarrage, sur un volume vide**. Preuve dans les logs :
- volume **neuf** → `Initializing database files` + `Creating user wordpress`
- volume **réutilisé** → `XA crash recovery` et **aucune** ligne `Creating…`

Si le volume existe déjà (d'un essai précédent, d'un autre fichier compose), les variables
`MYSQL_USER`/`MYSQL_PASSWORD` sont **ignorées** → l'utilisateur garde son **ancien** mot de
passe → `Access denied`. D'où une erreur qui **change** d'un test à l'autre quand on relance
sans cesse (`Connection refused` au boot, puis `Access denied` sur vieux volume).

**Règle d'or :** quand on change les identifiants d'une base en dev → **repartir d'un
volume vide** :
```bash
docker compose down -v        # supprime conteneurs ET volumes
docker volume ls | grep <projet>   # vérifier qu'ils ont disparu
docker compose up -d
```
⚠️ `down -v` ne supprime que les volumes **déclarés dans le compose actuel** ; les volumes
d'un ancien fichier (`db` vs `db_data`) restent orphelins → `docker volume rm` à la main.

### 23.4 La vraie correction : healthcheck + `service_healthy`

`depends_on: - mysql` attend que mysql **démarre**, pas qu'il soit **prêt**. D'où un
`Connection refused` au boot (l'app tente trop tôt, puis le navigateur garde le 500 en
cache).

```yaml
  mysql:
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "-uroot", "-p$$MYSQL_ROOT_PASSWORD"]
      interval: 5s
      timeout: 5s
      retries: 15
  wordpress:
    depends_on:
      mysql:
        condition: service_healthy
```

### 23.5 Ce qui ne change RIEN à la connexion (à savoir)

- `MYSQL_ROOT_PASSWORD` / `MYSQL_RANDOM_ROOT_PASSWORD` → concernent **root** ; WordPress se
  connecte en `wordpress`, pas root.
- `volumes: - wordpress:/var/www/html` → persiste les **fichiers** PHP, aucun lien avec la DB.

---

## 24. Registre d'images : bake, format de référence, GHCR

**Date :** 2026-10-23

### 24.1 `docker buildx bake` : `type=docker` vs `type=registry`

| `output` | Effet |
|---|---|
| `type=docker` | charge l'image **en local uniquement** ; ne supporte pas le multi-plateforme |
| `type=registry` | **pousse** sur le registre ; gère le multi-archi (OCI index) |

Conséquence : avec `type=docker`, Swarm avertit *« image could not be accessed on a
registry »* car l'image n'est que locale → sur un cluster multi-nœuds, les autres nœuds
ne peuvent pas la tirer. En Swarm, l'image **doit** vivre dans un registre.

### 24.2 Format de référence : un seul `:tag`

Erreur `invalid reference format` sur un cache :
```hcl
ref=${REGISTRY}/app:buildcache:${TAG}   # ghcr.io/lobgif/app:buildcache:dev → DEUX tags ❌
```
Une référence OCI = `registre/namespace/nom:UN_seul_tag`. Corriger en mettant l'étiquette
**dans** le tag : `app:buildcache-${TAG}` (= `buildcache-dev`, un seul tag) ✅.

### 24.3 Pousser sur GHCR

- Namespace = ton **compte GitHub** (`ghcr.io/lobgif`, pas l'email `lahigic`). On ne peut
  pousser que dans un compte/org qu'on possède.
- Auth : `gh auth token | docker login ghcr.io -u <compte> --password-stdin` (après
  `gh auth refresh -s write:packages`), ou un PAT classique avec `write:packages`.
- Vérifier sans navigateur : `docker buildx imagetools inspect ghcr.io/<compte>/<image>:<tag>`
  → s'il répond (archis + attestations SBOM/provenance), c'est publié.

### 24.4 Pourquoi « je ne vois pas mon package »

- Le package GHCR est **privé par défaut** → un visiteur **non connecté** (ou un autre
  compte) voit une page vide. Indice : le profil montre « Follow » / « Block or report user »
  au lieu de « Edit profile » = **pas connecté au bon compte** dans ce navigateur.
- Il se voit sur le **profil → onglet Packages** (`github.com/<compte>?tab=packages`), **pas**
  dans `Settings → Packages` (qui ne gère que permissions et paquets supprimés).
- Pour l'afficher sur la page du dépôt (comme GitLab le fait nativement dans
  *Deploy → Container Registry*) : page du package → **Connect repository** + *Change
  visibility* pour le rendre public.

---

## 25. Secrets Compose par fichier (`_FILE`) sans les pousser

**Date :** 2026-10-23

### 25.1 Le pattern `_FILE`

Les variables en `_FILE` disent à l'image de **lire le mot de passe dans un fichier**, pas
dans une variable d'environnement en clair. Compose monte chaque fichier dans le conteneur
à `/run/secrets/<nom>`.

```yaml
services:
  wordpress:
    environment:
      WORDPRESS_DB_PASSWORD_FILE: /run/secrets/WORDPRESS_DB_PASSWORD
    secrets:
      - WORDPRESS_DB_PASSWORD
  mysql:
    environment:
      MYSQL_PASSWORD_FILE: /run/secrets/MYSQL_PASSWORD
      MYSQL_ROOT_PASSWORD_FILE: /run/secrets/MYSQL_ROOT_PASSWORD
    secrets:
      - MYSQL_PASSWORD
      - MYSQL_ROOT_PASSWORD

secrets:
  WORDPRESS_DB_PASSWORD:
    file: ./secrets/wordpress_db_password.txt
  MYSQL_PASSWORD:
    file: ./secrets/mysql_password.txt
  MYSQL_ROOT_PASSWORD:
    file: ./secrets/mysql_root_password.txt
```

**Gain sécurité :** le mot de passe n'est plus en clair dans le `docker-compose.yml` ni
visible dans `docker inspect` / l'environnement du conteneur (Shift Left).

### 25.2 Où vivent les fichiers

| | Sur la machine | Dans le dépôt |
|---|---|---|
| `secrets/*.txt` (vrais) | ✅ obligatoire (Compose les lit au `up`) | ❌ jamais |
| `secrets/*.txt.example` | optionnel | ✅ modèles versionnés |
| `docker-compose.yml` | ✅ | ✅ (plus de mot de passe dedans) |

Le dossier `secrets/` vit **à côté** du `docker-compose.yml`, en local.

### 25.3 Créer les fichiers — deux pièges

```bash
mkdir -p secrets
printf 'MotDePasseFort123' > secrets/wordpress_db_password.txt
printf 'MotDePasseFort123' > secrets/mysql_password.txt       # MÊME valeur
printf 'RootTresFort456'   > secrets/mysql_root_password.txt
```

- ⚠️ **`printf` / `echo -n`, jamais `echo` seul** : `echo` ajoute un `\n` qui ferait partie
  du mot de passe → `Access denied` incompréhensible.
- ⚠️ `wordpress_db_password.txt` = `mysql_password.txt` (même mot de passe du même
  utilisateur `wordpress`, côté app et côté base).

### 25.4 Ne jamais pousser les vrais secrets

```gitignore
secrets/*.txt
!secrets/*.example
```
→ les `.example` (valeurs factices) partent dans le dépôt comme modèles, les vrais `.txt`
restent locaux.

### 25.5 Changer le mécanisme = volume à vider

Passer de `MYSQL_PASSWORD` à `MYSQL_PASSWORD_FILE` change la source du mot de passe. Si le
volume existe déjà, il garde l'**ancien** → `Access denied`. Repartir d'un volume vide
(voir section 23) :
```bash
docker compose down -v && docker compose up -d
```

> Note : ce sont les secrets **Compose** (montage d'un fichier local dans `/run/secrets/`),
> à ne pas confondre avec les secrets **Swarm** (`docker secret create`, chiffrés dans le
> Raft), voir section 15.8.

---

## 26. Réseaux Compose : qui doit parler à qui (moindre privilège)

**Date :** 2026-10-23

### 26.1 La règle absolue

**Deux conteneurs ne peuvent communiquer que s'ils partagent au moins un réseau.**
La bonne question pour chaque service : « avec qui a-t-il besoin de parler ? » → le mettre
sur le(s) réseau(x) qui couvre(nt) ces interlocuteurs, **et rien de plus** (moindre privilège).

Exemple de chaîne : `web → api → db`. `api` est au milieu → il lui faut un réseau commun
avec `web` **et** un réseau commun avec `db`.

### 26.2 « public » ≠ exposé à Internet

Piège de nom : `public` et `internal` ne sont que **deux réseaux bridge**, les noms sont une
**convention**. Mettre un service sur le réseau `public` ne l'expose **pas** au monde. Un
conteneur n'est joignable de l'extérieur **que** s'il a `ports:` (publication sur l'hôte).

### 26.3 Trois topologies valables pour `web → api → db`

```
Option A (simple) — api sur les deux
  public   : web, api
  internal : api, db          → db reste privé ✅

Option B — web aussi en interne
  public   : web
  internal : web, api, db     → api reste internal-only

Option C (prod, reverse proxy) — le plus sûr
  public   : proxy (Traefik/nginx)   ← seul à publier des ports
  internal : proxy, web, api, db      → rien d'autre n'est joignable de l'extérieur
```

| Moment | Choix |
|---|---|
| Apprentissage | Option A (direct, ça marche) |
| Durcissement / prod | Option C (surface minimale, cf. agoraci + Traefik) |

### 26.4 Grille de revue d'un compose (checklist)

- [ ] **Secrets jamais commités** : `secrets/*.txt` dans `.gitignore`, seuls les `.example` versionnés (section 25).
- [ ] **Réseaux cohérents** : chaque service partage un réseau avec ses interlocuteurs (sinon `Connection refused`).
- [ ] **Base non exposée** : pas de `ports:` sur la DB si seule l'app la joint (elle passe par le réseau interne).
- [ ] **Healthcheck compatible `_FILE`** : `${VAR}` est une interpolation **hôte** (vide si la valeur n'est qu'en secret) → lire `/run/secrets/<nom>` dans le conteneur.
- [ ] **Config DB sur l'app** : le service applicatif a bien ses variables de connexion (sinon migrations/app ne savent pas où est la base).
- [ ] **`depends_on` en forme longue** avec `condition: service_healthy` (attendre prêt, pas démarré).
- [ ] **Chemins relatifs** résolus depuis le dossier du compose (attention aux `./infra/...` quand le compose est déjà dans `infra/`).
- [ ] **Mot de passe non vide** (ex : Postgres refuse de s'initialiser sans `POSTGRES_PASSWORD`).

---

## 27. Quatre pièges d'images/versions (stack multi-services)

**Date :** 2026-10-23 (rencontrés en montant un stack Compose db+redis+rabbitmq+minio+api+web)

### 27.1 MinIO : les images communautaires ont disparu

`minio/minio` (Docker Hub) et `quay.io/minio/minio` ne sont **plus téléchargeables** (MinIO
Inc a verrouillé la communauté en 2025). Symptôme : `pull access denied ... repository does
not exist` **même après `docker login`** (« repository does not exist » = ce n'est pas de
l'auth, le dépôt n'est plus là).

**Solution :** le fork libre **`pgsty/silo`** (AGPL, par Pigsty), compatible à 100% (mêmes
variables `MINIO_*`, même commande `server /data`). Épinglé :
```yaml
image: pgsty/silo:RELEASE.2026-09-16T00-00-00Z@sha256:635197cb9f36d01bee221d34d1c7d7960f6a95c48b0b6c01d99cd13bdae51a46
```

### 27.2 RabbitMQ 4 : les variables `_FILE` ne marchent plus

`RABBITMQ_DEFAULT_USER_FILE` / `RABBITMQ_DEFAULT_PASS_FILE` sont **indisponibles depuis la
3.9** → en v4 le conteneur **sort en erreur** (`deprecated environment variables detected`).
Les variables **plaines** `RABBITMQ_DEFAULT_USER` / `RABBITMQ_DEFAULT_PASS`, elles, marchent
encore.

**Solution (garder les secrets en fichiers)** — un entrypoint qui lit le secret et exporte
la variable plaine :
```yaml
  rabbitmq:
    image: rabbitmq:4-management-alpine@sha256:...
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        export RABBITMQ_DEFAULT_USER="$$(cat /run/secrets/rabbitmq_user)"
        export RABBITMQ_DEFAULT_PASS="$$(cat /run/secrets/rabbitmq_password)"
        exec docker-entrypoint.sh rabbitmq-server
    secrets: [rabbitmq_user, rabbitmq_password]
```
`$$` = échappe l'interpolation Compose → `$(cat …)` exécuté dans le conteneur. Avantage sur
un `rabbitmq.conf` : **pas de duplication** du mot de passe (une seule source, les fichiers
secrets lus aussi par l'app). Alternative officielle v4 : `rabbitmq.conf` avec `default_user`
/ `default_pass` dans `/etc/rabbitmq/rabbitmq.conf`.

### 27.3 PostgreSQL 18 : monter `/var/lib/postgresql`, pas `/data`

PG 18 range les données dans un sous-dossier par version majeure et attend le montage sur le
**parent**. Monter `/var/lib/postgresql/data` (layout ≤ 17) → le conteneur **refuse de
démarrer** (« PostgreSQL data in /var/lib/postgresql/data (unused mount/volume) »).
```yaml
volumes:
  - pgdata:/var/lib/postgresql    # et non /var/lib/postgresql/data
```
Breaking change lié à la version → d'où l'importance de lire les notes de version d'une image.

### 27.4 Contexte de build en monorepo

Un Dockerfile qui fait `COPY backend/…` (avec préfixe de dossier) a besoin que le **contexte
englobe `backend/`** → le contexte est le **parent**, pas le dossier du service :
```yaml
  api:
    build:
      context: ..                  # racine qui contient backend/ et frontend/
      dockerfile: backend/Dockerfile
```
`context: ../backend` échoue (`"/backend": not found`) car le Dockerfile cherche un
sous-dossier `backend/` qui n'existe pas dans ce contexte. Voir section 24 (contexte = boîte).

### 27.5 Le fil conducteur

Trois de ces quatre pièges sont des **breaking changes de version d'image** (MinIO retiré,
RabbitMQ 4 sans `_FILE`, PG18 nouveau layout). La parade : épingler par **digest**, et lire
l'erreur exacte (`docker compose logs <service>`) — chaque message nommait précisément la
cause. Voir la méthode section 23.

---

## 28. Swarm, Raft, consensus et quorum

**Date :** 2026-10-24

### 28.1 Rôles : managers, workers, leader, followers

| Rôle | Fonction |
|---|---|
| **Manager** | **Décide** (scheduling, état du cluster), répond aux `docker service …` |
| **Worker** | **Exécute** les tasks ; ne décide rien |
| **Leader** | LE manager qui mène : reçoit tous les changements et les réplique |
| **Follower** | Manager qui suit le leader, copie son journal, prêt à prendre la relève |

Un manager peut aussi exécuter des tasks ; un worker ne décide jamais. On scale les
**workers** librement (des centaines), mais pas les managers.

### 28.2 Consensus, Raft, quorum

Plusieurs managers doivent partager **le même état**. S'accorder malgré pannes/coupures =
le **consensus**, résolu par l'algorithme **Raft**. Le **quorum** = nombre minimum de
managers d'accord et joignables pour **décider** :
```
quorum = (n / 2) + 1        (strictement plus de la moitié)
```

**Pourquoi la majorité (et pas la moitié) :** éviter le **split-brain**. Si le réseau coupe
le cluster en deux, un seul groupe peut atteindre la majorité → un seul décide → cohérence.
Avec la moitié, les deux groupes décideraient → états contradictoires.

### 28.3 Tolérance aux pannes et nombre impair

```
pannes tolérées = n - quorum
```

| Managers | Quorum | Pannes tolérées |
|---|---|---|
| 1 | 1 | 0 |
| 3 | 2 | **1** |
| 4 | 3 | 1 |
| 5 | 3 | **2** |
| 7 | 4 | 3 |

3 et 4 tolèrent tous deux **1** panne, mais 4 exige un quorum plus grand → plus fragile,
zéro bénéfice. **Toujours un nombre impair** (3 ou 5). Quorum perdu → cluster en **lecture
seule** (les tasks continuent, mais plus aucune nouvelle décision).

### 28.4 Pourquoi plus de managers ralentit les écritures

Chaque écriture (service create/update/scale, chaque statut de task…) doit obtenir le
consensus : le **leader** réplique à **tous** les followers et attend la **majorité** d'acks.
Plus de managers = quorum plus grand (plus d'acks à attendre) **et** leader qui réplique à
plus de monde (goulot unique). Les écritures ne se répartissent pas (tout passe par le
leader) → ajouter un manager **ralentit**, sans gagner en débit. D'où **3 ou 5**. Garder les
managers **proches** (faible latence) car chaque écriture attend des acks sur le réseau.

### 28.5 Élection du leader

On ne choisit **pas** le leader, il est **élu** :
1. **Minuteur aléatoire** (ex. 150–300 ms) remis à zéro à chaque heartbeat.
2. Le leader tombe → plus de heartbeats → un follower expire en premier → devient
   **candidate**, passe au **terme** suivant, vote pour lui-même.
3. Il envoie **`RequestVote`** aux autres (terme, id, index/terme de sa dernière entrée).
4. Chaque manager vote **oui** si : terme ≥ le sien, **pas déjà voté** ce terme, et **journal
   du candidat au moins aussi à jour** que le sien.
5. Majorité atteinte (`(n/2)+1`) → **leader** → heartbeats.

Le choix ne dépend **pas** de la puissance de la machine : juste **qui expire en premier**
(hasard) + **journal à jour**.

**L'élection peut échouer** (split vote : deux candidats se partagent les voix → aucune
majorité → nouveau terme, nouveaux minuteurs). Un manager **refuse de voter** s'il a déjà
voté ce terme, si le journal du candidat est **en retard**, ou si le terme est plus vieux.

### 28.6 Le journal (log) et « committed »

Le **journal** = suite ordonnée, append-only, d'**entrées** = opérations d'état sérialisées :
```
index 40, terme 6 : CreateService "web" (replicas=2)
index 41, terme 6 : UpdateService "web" replicas=4
index 42, terme 6 : AssignTask web.3 → worker1
index 43, terme 7 : TaskStatus web.3 = running
```
Une entrée est **committed** quand **une majorité** de managers l'a dans son journal (pas
tout le monde). Le leader avance alors son `commitIndex`, applique l'entrée, et le signale
aux followers (heartbeat). « Committed » = durable même si le leader meurt.

### 28.7 RPC, gRPC, AppendEntries, le terme

- **RPC** (*Remote Procedure Call*) = appeler une fonction qui s'exécute sur une **autre
  machine** comme si elle était locale. Orienté **action** (≠ REST orienté ressource).
- **gRPC** = l'implémentation de Google (HTTP/2 + Protocol Buffers), utilisée par SwarmKit
  sur le port **2377**.
- **`AppendEntries`** = l'un des deux RPC de Raft (avec `RequestVote`). Double usage :
  **répliquer** des entrées, ou **heartbeat** quand il est vide.
- **Le terme** = horloge logique de Raft : entier croissant découpant le temps en mandats
  (un terme = une élection, au plus un leader). Chaque message porte son terme : un terme
  **plus grand** vu → on devient follower ; un terme **plus petit** reçu → rejeté. C'est ce
  qui détecte un vieux leader revenu et empêche les deux leaders.

### 28.8 Flux complet d'une décision (`docker service scale web=4`)

```
toi → API (un manager) → [redirige vers le LEADER]
  LEADER : orchestrator (désiré=4, actuel=2 → 2 tasks)
         → allocator (IP/réseau) → scheduler (quel nœud)
         → RAFT : réplique aux followers (AppendEntries), attend la MAJORITÉ → committed
         → DISPATCHER (gRPC) → agents des WORKERS
  WORKERS : agent → dockerd → conteneur démarre → statut remonte
         → RAFT (réécriture du statut) → visible dans docker service ps
  [boucle de réconciliation : compare désiré vs réel en continu → auto-réparation]
```

### 28.9 Ce qu'on peut réellement observer

Raft est **interne** : Docker n'expose **ni les votes ni le journal brut** (stocké chiffré
dans `/var/lib/docker/swarm/raft/`). On observe les **résultats** :
```bash
docker node ls                                              # Leader / Reachable
docker node inspect manager1 --format '{{ json .ManagerStatus }}'
docker info                                                 # section Swarm (Managers, Nodes…)
docker events                                               # création/arrêt de tasks
journalctl -u docker | grep -i raft                         # messages Raft bas niveau (manager)
```
Pour *voir* Raft en action : la visualisation interactive (voir Ressources).

---

## 29. Swarm sur AWS EC2 : le join qui échoue (Security Groups)

**Date :** 2026-10-25

### 29.1 Le vocabulaire AWS (ce qu'il faut comprendre)

| Terme | Signification |
|---|---|
| **EC2** | Service de machines virtuelles. Une **instance** = une VM louée |
| **AMI** | Modèle d'OS d'où part l'instance (≈ image Docker, mais pour une VM) |
| **VPC** | Réseau privé isolé dans AWS où vivent tes instances (≈ ton réseau local) |
| **Subnet** | Subdivision du VPC (souvent une par zone de disponibilité) |
| **CIDR** (`172.31.0.0/16`) | Plage d'IP du VPC ; les instances reçoivent une IP dedans |
| **IP privée** (`172.31.x.x`) | Joignable **dans** le VPC ; les nœuds Swarm s'en servent entre eux |
| **IP publique** (`13.x.x.x`) | Joignable depuis Internet (SSH) ; **change au stop/start** sauf Elastic IP |
| **ENI** | La carte réseau virtuelle de l'instance ; les SG s'y attachent |
| **Security Group (SG)** | **Pare-feu virtuel** autour de l'instance : règles inbound/outbound |
| **Key pair** | La clé SSH (`.pem`) associée à l'instance au lancement |
| **Région / AZ** | Zone géographique / datacenter ; la HA répartit sur plusieurs AZ |

### 29.2 Le problème

`docker swarm join --token … <ip>:2377` → `Timeout was reached before node joined`, puis
`docker info` montre :
```
Swarm: error
  Error: rpc error: code = DeadlineExceeded ... while waiting for connections to become ready
  Node Address: 172.31.7.80
```

**Lecture (méthode section 23) :** `DeadlineExceeded waiting for connections` = le worker a
tenté d'ouvrir la connexion gRPC vers le manager sur **2377** mais n'y est **jamais arrivé**.
Catégorie = **joignabilité réseau**. `Node Address: 172.31.7.80` = IP privée du VPC.

### 29.3 La cause

Le **Security Group** (pare-feu AWS) n'autorisait que le port **22** (SSH). Les ports Swarm
étaient **bloqués** :

| Port | Rôle | À ouvrir sur |
|---|---|---|
| **2377/TCP** | gestion du cluster (join) | les managers |
| **7946/TCP+UDP** | découverte entre nœuds | tous |
| **4789/UDP** | trafic overlay | tous |

### 29.4 La correction — un SG dédié attaché à tous les nœuds

Idée clé : une instance peut porter **plusieurs SG** (les règles **s'additionnent**). On crée
**un** SG `swarm-cluster` et on l'attache aux 3 nœuds.

1. **Créer le SG** : EC2 → Security Groups → Create → nom `swarm-cluster`, VPC par défaut.
2. **Inbound rules** — 4 règles, Source = **le CIDR du VPC** `172.31.0.0/16` (= uniquement
   les machines du VPC, pas Internet) :

| Type | Port | Source |
|---|---|---|
| Custom TCP | 2377 | 172.31.0.0/16 |
| Custom TCP | 7946 | 172.31.0.0/16 |
| Custom UDP | 7946 | 172.31.0.0/16 |
| Custom UDP | 4789 | 172.31.0.0/16 |

   (Encore plus strict : Source = **ce SG lui-même** — mais impossible de se référencer
   pendant la création ; à resserrer après coup.)
3. **Outbound** : ne pas toucher. `All traffic → 0.0.0.0/0` est le **défaut** qui laisse
   l'instance **initier** des connexions (pull d'images, worker→manager). L'enlever casse
   le join et les pulls.
4. **Attacher `swarm-cluster` aux 3 instances** : EC2 → Instances → Actions → Security →
   Change security groups → ajouter `swarm-cluster` (garder le SG SSH). **À faire sur chaque
   nœud** (le SG est par instance).

### 29.5 Pourquoi Source = le VPC et pas `0.0.0.0/0`

`0.0.0.0/0` = tout Internet. Le port **2377** donne le **contrôle du cluster** → jamais
public (même logique que « ne jamais ouvrir 2375 »). Source = `172.31.0.0/16` = seules les
machines **de ton VPC** se parlent sur ces ports.

### 29.6 Notion clé : le SG est **stateful**

Un Security Group est **à états** : quand une connexion **entrante** est autorisée, la
**réponse** repart automatiquement (pas besoin d'ouvrir les deux sens). **Mais** toute
connexion que l'instance **initie** (sortante) a besoin d'une règle **outbound**. D'où :
supprimer l'outbound `All → 0.0.0.0/0` empêche les pulls d'images **et** le worker de
contacter le manager. Avec plusieurs SG, c'est l'**union** des règles qui compte.

### 29.7 Vérifier et rejoindre

```bash
# depuis le worker : le port est-il ouvert maintenant ?
nc -zv 172.31.X.X 2377        # attendu : "... port [tcp/*] succeeded!"

# le background a peut-être déjà fini le join (ports ouverts) :
docker info | grep -i Swarm   # "active" = déjà rejoint, rien à faire

# sinon, réinitialiser puis rejoindre :
docker swarm leave --force
docker swarm join --token <TOKEN-WORKER> 172.31.X.X:2377

# sur le manager :
docker node ls                # les 3 nœuds doivent être Ready
```

**`docker swarm leave --force`** : fait quitter le swarm et réinitialise le nœud. Sans lui,
un re-`join` est refusé (`This node is already part of a swarm`). Inutile si `docker info`
montre déjà `Swarm: active`.

---

## 30. Swarm `deploy` : replicated/global, HA stateful, placement, resources

**Date :** 2026-10-25

### 30.1 replicated vs global

| | replicated (défaut) | global |
|---|---|---|
| Quoi | **N** instances placées n'importe où | **1 par nœud**, auto (nouveau nœud → une instance) |
| Pour | stateless à scaler (api, web) | agents **par nœud** (monitoring, logs, parfois proxy) |

Question à se poser : « ça doit tourner **sur chaque** nœud ? » → **global**. « Je veux juste
N copies ? » → **replicated**. « C'est une base de données ? » → **replicated: 1** + placement.

### 30.2 Qui a des replicas dans un vrai stack

| Service | Type | Mode | Pourquoi |
|---|---|---|---|
| api, web | stateless | replicated (2-3) | copies interchangeables → scale/HA |
| postgres | stateful | 1 replica + placement | 2 instances/même volume = corruption ; HA = réplication native |
| redis | stateful | 1 (ou Sentinel/Cluster) | HA via clustering Redis |
| rabbitmq | stateful | 1 (ou cluster 3 nœuds) | cluster configuré dans RabbitMQ |
| minio | stateful | 1 (ou distribué 4+) | mode distribué MinIO |
| node-exporter, cadvisor, agent logs | agent | **global** | collectent les données **de chaque** nœud |

### 30.3 HA des services stateful = clustering natif, PAS des replicas Swarm

`replicas: 3` = 3 copies **indépendantes** qui ne se connaissent pas, chacune ses données →
incohérence/corruption. Le clustering exige que les instances **se coordonnent** → c'est une
fonctionnalité **du logiciel**, pas de Swarm.

| Logiciel | Mécanisme natif |
|---|---|
| **Postgres** | **streaming replication** (1 primary → N standbys ; failover). Outils : **Patroni**, repmgr, ou DB managée (RDS/Aurora) |
| **Redis** | **Sentinel** (HA) ou **Redis Cluster** (sharding) |
| **RabbitMQ** | **cluster** + **quorum queues** (qui utilisent Raft) |
| **MinIO** | **mode distribué** (erasure coding sur 4+ nœuds), déclaré au lancement |

→ Swarm replicas = **stateless uniquement**. Le stateful se cluster **dans le logiciel**, ou
part sur un **service managé**.

### 30.4 placement : où tourne une task

```yaml
placement:
  constraints:                 # règles DURES : où la task A LE DROIT de tourner
    - node.role == worker      # jamais sur les managers
    - node.hostname == node-db # ÉPINGLER un stateful au nœud de son volume
    - node.labels.disk == ssd  # matériel (label posé avec: docker node update --label-add)
  preferences:                 # répartition SOUPLE
    - spread: node.labels.zone # étaler sur les AZ
  max_replicas_per_node: 1
```

⚠️ Le placement vaut pour **tout** service stateful à **volume local** (pas que la DB) : un
volume local vit sur **un seul** nœud ; sans épinglage, une reprogrammation sur un autre nœud
ne retrouve pas les données. Alternatives : stockage **partagé** (NFS/Ceph) ou clustering natif.

### 30.5 update_config / rollback_config (rolling update)

```yaml
update_config:
  parallelism: 1          # tasks mises à jour EN MÊME TEMPS (1 = prudent, 0 = toutes)
  delay: 10s              # attente ENTRE chaque lot
  order: start-first      # start-first = nouvelle avant d'arrêter l'ancienne (zéro coupure) ; stop-first = défaut
  failure_action: rollback # si échec : continue / pause / rollback (retour auto)
  monitor: 30s            # observer une task N s après maj ; plante dans ce délai = échec
  max_failure_ratio: 0.2  # % d'échecs toléré avant failure_action
rollback_config:          # mêmes champs, pour le retour arrière
```

### 30.6 resources : plafonds, réservations, et comment dimensionner

```yaml
resources:
  limits:          # PLAFOND : dépassement mémoire → conteneur tué (OOM, 137)
    cpus: "0.50"   # 0.50 = moitié d'UN coeur ("1.0" = un coeur entier)
    memory: 512M
    pids: 100      # max processus (anti fork-bomb)
  reservations:    # MINIMUM GARANTI : le scheduler ne place que si le nœud a au moins ça de libre
    cpus: "0.25"
    memory: 256M
```

**Méthode pour fixer les valeurs :**
1. **Capacité de la machine** :
   ```bash
   nproc ; free -h ; docker info | grep -E "CPUs|Total Memory"
   ```
2. **Conso réelle sous charge** :
   ```bash
   docker stats            # CPU% / MEM par conteneur
   ```
3. **Régler** : `reservations` ≈ conso typique ; `limits` ≈ pic + marge (≈ reservations × 1.5-2).
4. **Ne pas sur-réserver** : somme des `reservations` d'un nœud ≤ capacité, en gardant 10-20%
   pour l'OS + Docker.

Règle : toujours mettre des **limits** en prod (un conteneur qui fuit ne doit pas tuer le nœud).
Plus tard, Prometheus/Grafana donne l'historique pour affiner.

### 30.7 Référence rapide de toutes les clés `deploy`

| Clé | Rôle |
|---|---|
| `mode` | replicated / global / replicated-job / global-job |
| `replicas` | nb d'instances (mode replicated) |
| `endpoint_mode` | `vip` (IP virtuelle load-balancée) / `dnsrr` (DNS round-robin) |
| `labels` | labels sur le **service** (ex. règles Traefik) |
| `update_config` | déroulé des mises à jour (voir 30.5) |
| `rollback_config` | déroulé des retours arrière |
| `restart_policy` | relance d'une task qui sort (condition/delay/max_attempts/window) |
| `placement` | constraints/preferences/max_replicas_per_node (voir 30.4) |
| `resources` | limits/reservations (voir 30.6) |

---

<!-- Ajouter les nouvelles entrées au-dessus de cette ligne, en suivant le même format. -->

## Ressources

Documentations officielles, plus le guide de Stéphane Robert (signalé à part). Vérifiées les 2026-09-28,
2026-10-03 et 2026-10-05 (chaque URL répond).

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
- WSL : accès aux fichiers Windows (`/mnt/c`) vs Linux — https://learn.microsoft.com/en-us/windows/wsl/filesystems
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

### Apprendre les réseaux (hors Docker)
- Professor Messer Network+ (vidéos gratuites, OSI, IP, routage, switching) — https://www.professormesser.com/network-plus/n10-008/n10-008-video/n10-008-training-course/
- Julia Evans "Networking!" zine (pratique, Linux) — https://wizardzines.com/zines/networking/
- iproute2 par exemple (`ip link`, `ip route`, `ip addr`) — https://baturin.org/docs/iproute2/
- nftables wiki (pare-feu Linux, remplace iptables) — https://wiki.nftables.org/wiki-nftables/index.php/Main_Page
- Stéphane Robert — réseau Docker (bridge, overlay, macvlan, ipvlan, host, none) — https://blog.stephane-robert.info/docs/conteneurs/moteurs-conteneurs/docker/network/

### Volumes partagés
- Volumes Docker (options NFS/CIFS) — https://docs.docker.com/engine/storage/volumes/
- `docker volume create` — https://docs.docker.com/reference/cli/docker/volume/create/
- AWS EFS — https://docs.aws.amazon.com/efs/latest/ug/whatisefs.html
- Ceph — https://docs.ceph.com/en/latest/
- GlusterFS — https://docs.gluster.org/en/latest/
- Longhorn — https://longhorn.io/docs/
- MinIO (S3 self-hosted) — https://min.io/docs/minio/linux/index.html
- Kubernetes PersistentVolumes (modes d'accès RWO/RWX/ROX) — https://kubernetes.io/docs/concepts/storage/persistent-volumes/
- Docker : étendre avec des plugins — https://docs.docker.com/engine/extend/
- `docker plugin` (install, ls, enable) — https://docs.docker.com/reference/cli/docker/plugin/
- Kubernetes CSI (Container Storage Interface) — https://kubernetes-csi.github.io/docs/
- Kubernetes : types de volumes — https://kubernetes.io/docs/concepts/storage/volumes/

### AWS (EC2, VPC, Security Groups)
- `ssh-keygen` — https://man.openbsd.org/ssh-keygen
- EC2 : concepts (instances, AMI) — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html
- EC2 : paires de clés — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html
- EC2 : Elastic IP (IP fixe) — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html
- EC2 : interfaces réseau (ENI) — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-eni.html
- VPC : qu'est-ce que c'est — https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html
- VPC : blocs CIDR — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html
- Security Groups (pare-feu, stateful, inbound/outbound) — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
- Ports requis par Docker Swarm — https://docs.docker.com/engine/swarm/swarm-tutorial/

### Sockets & diagnostic réseau
- `ss(8)` (sockets en écoute) — https://man7.org/linux/man-pages/man8/ss.8.html
- `unix(7)` (sockets Unix, ex docker.sock) — https://man7.org/linux/man-pages/man7/unix.7.html
- `socket(7)` — https://man7.org/linux/man-pages/man7/socket.7.html

### Réseau macvlan & ipvlan
- Pilote macvlan — https://docs.docker.com/engine/network/drivers/macvlan/
- Pilote ipvlan (modes L2/L3) — https://docs.docker.com/engine/network/drivers/ipvlan/
- `ip-route(8)` — https://man7.org/linux/man-pages/man8/ip-route.8.html
- `ip-link(8)` — https://man7.org/linux/man-pages/man8/ip-link.8.html

### Compose, bases de données & registre
- Images officielles MySQL (init, variables) — https://hub.docker.com/_/mysql
- Image officielle WordPress — https://hub.docker.com/_/wordpress
- Compose : services (`depends_on`, `healthcheck`, `condition: service_healthy`) — https://docs.docker.com/reference/compose-file/services/
- docker buildx bake — https://docs.docker.com/build/bake/
- `docker buildx bake` (référence CLI) — https://docs.docker.com/reference/cli/docker/buildx/bake/
- GitHub Container Registry (GHCR) — https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- OCI distribution spec (format des références) — https://github.com/opencontainers/distribution-spec

### Pièges images/versions (stack multi-services)
- MinIO communautaire retiré / fork libre (guide Stéphane Robert) — https://www.stephane-robert.info/docs/services/stockage/minio/
- Pigsty (éditeur du fork `pgsty/silo`) — https://github.com/pgsty/pigsty
- `pgsty/silo` sur Docker Hub — https://hub.docker.com/r/pgsty/silo
- RabbitMQ : configuration (`default_user`/`default_pass`, rabbitmq.conf) — https://www.rabbitmq.com/docs/configure
- RabbitMQ image Docker (variables `_FILE` indisponibles ≥ 3.9) — https://hub.docker.com/_/rabbitmq
- PostgreSQL 18 : nouveau layout des données (montage `/var/lib/postgresql`) — https://github.com/docker-library/postgres/pull/1259
- Docker : contexte de build — https://docs.docker.com/build/concepts/context/

### Swarm deploy, HA & clustering stateful
- Compose : section `deploy` (référence complète) — https://docs.docker.com/reference/compose-file/deploy/
- Swarm : services (replicated/global, scaling) — https://docs.docker.com/engine/swarm/services/
- `docker stats` (mesurer CPU/mémoire) — https://docs.docker.com/reference/cli/docker/container/stats/
- PostgreSQL : haute disponibilité & réplication — https://www.postgresql.org/docs/current/high-availability.html
- Patroni (HA Postgres automatisée) — https://patroni.readthedocs.io/en/latest/
- Redis Sentinel — https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/
- RabbitMQ : clustering — https://www.rabbitmq.com/docs/clustering
- RabbitMQ : quorum queues — https://www.rabbitmq.com/docs/quorum-queues
- MinIO : déploiement distribué (multi-nœuds) — https://min.io/docs/minio/linux/operations/install-deploy-manage/deploy-minio-multi-node-multi-drive.html

### Swarm, Raft & consensus
- Raft dans Swarm (gestion du quorum) — https://docs.docker.com/engine/swarm/raft/
- Administrer un Swarm (HA des managers, quorum, nombre impair) — https://docs.docker.com/engine/swarm/admin_guide/
- Nœuds Swarm (managers/workers) — https://docs.docker.com/engine/swarm/how-swarm-mode-works/nodes/
- Raft (site officiel, papier) — https://raft.github.io/
- Papier Raft (PDF) — https://raft.github.io/raft.pdf
- Visualisation interactive de Raft — https://thesecretlivesofdata.com/raft/
- SwarmKit (la lib derrière Swarm) — https://github.com/moby/swarmkit
- gRPC — https://grpc.io/
- Protocol Buffers — https://protobuf.dev/

### Docker Swarm
- Vue d'ensemble Swarm — https://docs.docker.com/engine/swarm/
- Démarrer avec Swarm (tutorial officiel) — https://docs.docker.com/engine/swarm/swarm-tutorial/
- `docker service create` — https://docs.docker.com/reference/cli/docker/service/create/
- `docker stack deploy` — https://docs.docker.com/reference/cli/docker/stack/deploy/
- Réseau overlay Swarm — https://docs.docker.com/engine/network/drivers/overlay/
- Routing mesh (ingress) — https://docs.docker.com/engine/swarm/ingress/
- Secrets Swarm — https://docs.docker.com/engine/swarm/secrets/
- Configs Swarm — https://docs.docker.com/engine/swarm/configs/
- Nœuds (managers/workers, Raft) — https://docs.docker.com/engine/swarm/how-swarm-mode-works/nodes/
- Rolling updates — https://docs.docker.com/engine/swarm/swarm-tutorial/rolling-update/

### Protocoles réseau & adressage IP
- IPv4 (RFC 791) — https://datatracker.ietf.org/doc/html/rfc791
- TCP (RFC 793) — https://datatracker.ietf.org/doc/html/rfc793
- UDP (RFC 768) — https://datatracker.ietf.org/doc/html/rfc768
- Adresses IP privées (RFC 1918) — https://datatracker.ietf.org/doc/html/rfc1918
- CIDR (RFC 4632) — https://datatracker.ietf.org/doc/html/rfc4632
- Numéros de ports officiels (IANA) — https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml
- `ip(7)` — https://man7.org/linux/man-pages/man7/ip.7.html
- Ports Docker Swarm requis — https://docs.docker.com/engine/swarm/swarm-tutorial/

### Réseau Docker
- Vue d'ensemble des réseaux Docker — https://docs.docker.com/engine/network/
- Pilote bridge (réseau bridge, NAT, DNS interne) — https://docs.docker.com/engine/network/drivers/bridge/
- `docker network create` — https://docs.docker.com/reference/cli/docker/network/create/
- Filtrage de paquets et pare-feu (iptables/nftables, MASQUERADE) — https://docs.docker.com/engine/network/packet-filtering-firewalls/

### Cgroups v1 / v2
- Documentation du noyau Linux — cgroup v2 — https://docs.kernel.org/admin-guide/cgroup-v2.html
- cgroups(7) — https://man7.org/linux/man-pages/man7/cgroups.7.html

### Kubernetes — user namespaces
- User namespaces dans les pods — https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/

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
