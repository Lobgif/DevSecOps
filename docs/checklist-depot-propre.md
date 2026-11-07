# Checklist — Dépôt public propre, esthétique et efficace

> À cocher **au fur et à mesure** de l'implémentation sur `devsecops-portfolio`.
> Légende : `[ ]` à faire · `[x]` fait · `[~]` en cours.
> Détails et « pourquoi » dans [`DevSecOps.md`](DevSecOps.md) (section 48).

## 1. README (la vitrine)

- [ ] Titre + tagline (1 phrase : quoi / pourquoi)
- [ ] Rangée de badges (voir §2)
- [ ] Schéma d'architecture (Mermaid / Excalidraw / draw.io)
- [ ] Capture ou GIF de démo
- [ ] Problématique & Solution (le « pourquoi »)
- [ ] Quickstart (`git clone` → `make deploy` / `terraform apply`)
- [ ] Stack technique (liste des outils)
- [ ] Structure du dépôt (arbo commentée)
- [ ] Table des matières (si long)

## 2. Badges (shields.io)

- [ ] CI status (workflow)
- [ ] Licence
- [ ] Dernière release
- [ ] Langages / dernier commit
- [ ] Couverture de tests (Codecov / Coveralls)
- [ ] Style de code (Ruff / ESLint / Prettier)
- [ ] Conventional Commits
- [ ] **OpenSSF Scorecard**
- [ ] **OpenSSF Best Practices**
- [ ] SLSA level
- [ ] Image signée (cosign)
- [ ] SBOM (CycloneDX)

## 3. Fichiers d'hygiène (racine)

- [ ] `LICENSE`
- [ ] `README.md`
- [ ] `CONTRIBUTING.md`
- [ ] `CODE_OF_CONDUCT.md`
- [ ] `SECURITY.md` (signaler une faille)
- [ ] `CHANGELOG.md` (généré auto, voir §5)
- [x] `.gitignore` / `.dockerignore`
- [ ] `.editorconfig`
- [x] `.gitattributes` (`* text=auto eol=lf`)
- [ ] `CODEOWNERS`
- [ ] `Makefile` / `justfile` (commandes standard)

## 4. Templates `.github/`

- [ ] `ISSUE_TEMPLATE/` (bug_report, feature_request)
- [ ] `PULL_REQUEST_TEMPLATE.md`
- [ ] `dependabot.yml` **ou** Renovate (maj deps + actions)

## 5. Release automatique

- [ ] **Conventional Commits** adoptés (+ commitlint)
- [ ] Outil de release choisi et branché :
  - [ ] **release-please** (recommandé, monorepo, language-agnostic), ou
  - [ ] **semantic-release** (100% auto), ou
  - [ ] **git-cliff** (changelog seul), ou
  - [ ] **GoReleaser** (release conteneurs : Docker + cosign + SBOM)
- [ ] `CHANGELOG.md` généré automatiquement
- [ ] GitHub Releases remplies (notes auto)

## 6. Qualité & sécurité (CI)

- [ ] Linters : Ruff/Black, ESLint/Prettier, **hadolint** (Dockerfile), **actionlint** (workflows), yamllint
- [ ] **pre-commit** (hooks locaux : lint, format, secrets)
- [ ] **Gitleaks** (secrets dans le code)
- [ ] **CodeQL** (SAST natif GitHub)
- [x] Trivy / Grype (CVE images & deps) — *dans build-sign-publish.yml*
- [ ] **Dependabot / Renovate**
- [ ] **OpenSSF Scorecard action** (génère le badge)
- [x] Images signées (cosign) + **provenance SLSA** + **SBOM attesté** — *dans build-sign-publish.yml*

## 7. Découvrabilité (réglages GitHub)

- [ ] Description + website + **Topics/tags**
- [ ] **Social preview image** (Settings)
- [ ] **Branch protection** + required checks (CI avant merge)
- [ ] Doc publiée : **GitHub Pages** / **MkDocs Material**
- [ ] Repos épinglés sur le profil

## Ordre d'impact (si tu priorises)

1. README soigné + badges + schéma
2. LICENSE + SECURITY.md + CONTRIBUTING
3. Topics + description + social preview
4. Release automatique + CHANGELOG
5. Scorecard + badges sécurité (le « wow » DevSecOps)

## Ressources

Documentations officielles (vérifiées le 2026-11-07).

- Conventional Commits — https://www.conventionalcommits.org/
- release-please — https://github.com/googleapis/release-please
- semantic-release — https://semantic-release.gitbook.io/semantic-release/
- git-cliff — https://git-cliff.org/
- GoReleaser — https://goreleaser.com/
- OpenSSF Scorecard — https://scorecard.dev/
- OpenSSF Best Practices — https://www.bestpractices.dev/
- pre-commit — https://pre-commit.com/
- Renovate — https://docs.renovatebot.com/
- Shields.io (badges) — https://shields.io/
