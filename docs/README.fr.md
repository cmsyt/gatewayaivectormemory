🌐 [简体中文](../README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md) | [Español](README.es.md) | [Deutsch](README.de.md) | Français | [日本語](README.ja.md)

<p align="center">
  <h1 align="center">🧠 GatewayAIVectorMemory</h1>
  <p align="center">
    <strong>Donnez une mémoire d'équipe à votre assistant IA — Stockage PostgreSQL + pgvector · HTTP Memory Proxy · Collaboration multi-utilisateurs & partage de connaissances</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/v/gatewayaivectormemory?color=blue&label=PyPI" alt="PyPI"></a>
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/pyversions/gatewayaivectormemory" alt="Python"></a>
    <a href="https://github.com/cmsyt/gatewayaivectormemory/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-green" alt="License"></a>
  </p>
</p>

---

> **Ça vous parle ?** À chaque nouvelle session, votre IA repart de zéro — les conventions de projet enseignées hier ? Oubliées. Les erreurs déjà commises ? Elle les refera. Le travail en cours ? Disparu. Pire encore : chaque membre de l'équipe tombe indépendamment dans les mêmes pièges, les connaissances ne s'accumulent jamais, l'expérience ne se transmet jamais.
>
> **GatewayAIVectorMemory est le hub de mémoire IA conçu pour les équipes.** Stockage PostgreSQL + pgvector, HTTP Memory Proxy pour un accès unifié, les expériences d'erreurs de l'équipe sont automatiquement partagées, les connaissances architecturales déposées par un seul profitent à tous. Les données multi-utilisateurs sont strictement isolées sans contamination croisée. Supporte le partage du modèle Embedding entre plusieurs workers : N processus, 1 seule copie en mémoire. Les nouvelles sessions restaurent automatiquement le contexte, la recherche sémantique retrouve exactement ce qu'il faut, et la consommation de tokens chute de 50%+.

## ✨ Fonctionnalités Principales

| Fonctionnalité | Description |
|----------------|-------------|
| 👥 **Partage de Connaissances d'Équipe** | L'erreur d'un seul devient la leçon de tous — les mémoires d'équipe sont automatiquement partagées, les connaissances architecturales et les leçons apprises deviennent des actifs d'équipe |
| 🔐 **Isolation Multi-Utilisateurs** | Plusieurs utilisateurs sur un serveur, mémoires personnelles strictement isolées et invisibles aux autres, mémoires d'équipe partagées par projet |
| ⚡ **Service Embedding Partagé** | N workers partagent un seul modèle Embedding, 200Mo × N → 200Mo × 1, consommation mémoire réduite de 90% |
| 🧠 **Mémoire Inter-Sessions** | Erreurs rencontrées, décisions prises, conventions établies, tout persiste entre les sessions |
| 🔍 **Recherche Sémantique** | Chercher « timeout base de données » trouve « erreur pool de connexions » — pas besoin de se rappeler les mots exacts |
| 💰 **Économie 50%+ Tokens** | Récupération sémantique à la demande, adieu l'injection massive de contexte |
| 🔗 **Dev Piloté par Tâches** | Suivi des problèmes → découpage en tâches → synchronisation des statuts → archivage lié. L'IA gère tout le workflow de développement |
| 📊 **Tableau de Bord Web** | Gestion visuelle de toutes les mémoires et tâches, réseau vectoriel 3D pour voir les connexions de connaissances d'un coup d'œil |
| 🔌 **Tous les IDEs** | Cursor / Kiro / Claude Code / Windsurf / VSCode / OpenCode / Trae — via HTTP API |
| 🔄 **Déduplication Intelligente** | Similarité > 0.95 fusionne automatiquement, la base de mémoires reste propre |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   AI IDE                         │
│  Cursor / Kiro / Claude Code / Windsurf / ...   │
└──────────────────────┬──────────────────────────┘
                       │ HTTP API
┌──────────────────────▼──────────────────────────┐
│           Memory Proxy (FastAPI + Uvicorn)       │
│                                                  │
│  POST /memory/remember  POST /memory/recall      │
│  POST /memory/forget    POST /memory/status      │
│  POST /memory/track     POST /memory/task        │
│  POST /memory/auto_save POST /memory/readme      │
│  GET  /memory/health                             │
│                                                  │
│  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ Auth Layer   │  │  X-User-Id / X-Project-Dir│ │
│  │ Token/JWT    │  │  Isolation multi-user     │ │
│  └──────────────┘  └───────────────────────────┘ │
└──────────┬───────────────────┬───────────────────┘
           │                   │
┌──────────▼──────────┐ ┌─────▼─────────────────┐
│  Embedding Server   │ │  PostgreSQL + pgvector │
│  (ONNX Runtime)     │ │  Stockage vectoriel +  │
│  HTTP :8900         │ │  recherche plein texte │
└─────────────────────┘ └───────────────────────┘
```

## 🚀 Démarrage Rapide

### Prérequis

- Python >= 3.10
- PostgreSQL >= 14 (avec extension pgvector)
- Installer pgvector : `CREATE EXTENSION IF NOT EXISTS vector;`

### Installation

```bash
pip install gatewayaivectormemory
```

### 1. Démarrer le Service Embedding Partagé

```bash
# Port par défaut 8900
team-run embed-server

# Spécifier le port + exécuter en arrière-plan
team-run embed-server --port 8900 --daemon

# Autoriser l'accès distant
team-run embed-server --bind 0.0.0.0 --port 8900
```

> Le modèle Embedding (~200Mo) est téléchargé automatiquement au premier lancement. Les utilisateurs en Chine peuvent définir `export HF_ENDPOINT=https://hf-mirror.com` pour accélérer.

### 2. Démarrer le Memory Proxy

```bash
team-run memory-proxy \
  --pg-url "postgresql://user:pass@localhost:5432/dbname" \
  --embed-url "http://127.0.0.1:8900" \
  --port 8080 \
  --workers 4
```

Options d'authentification (mutuellement exclusives) :

```bash
# Authentification par Token statique
team-run memory-proxy --pg-url "..." --token "your-secret-token"

# Authentification JWT
team-run memory-proxy --pg-url "..." --jwt-secret "your-jwt-secret"

# Fichier de mapping Token-utilisateur
team-run memory-proxy --pg-url "..." --user-tokens "/path/to/tokens.json"
```

### 3. Configurer l'IDE

Ajouter dans le fichier de configuration MCP de votre IDE :

```json
{
  "mcpServers": {
    "memory": {
      "type": "http",
      "url": "http://127.0.0.1:8080/memory",
      "headers": {
        "Authorization": "Bearer your-secret-token",
        "X-User-Id": "your-user-id",
        "X-Project-Dir": "/path/to/your/project"
      }
    }
  }
}
```

<details>
<summary>📍 Emplacements des fichiers de configuration par IDE</summary>

| IDE | Chemin de configuration |
|-----|------------------------|
| Kiro | `.kiro/settings/mcp.json` |
| Cursor | `.cursor/mcp.json` |
| Claude Code | `.mcp.json` |
| Windsurf | `.windsurf/mcp.json` |
| VSCode | `.vscode/mcp.json` |
| Trae | `.trae/mcp.json` |
| OpenCode | `opencode.json` |

</details>

## 📊 Tableau de Bord Web

```bash
team-run web --pg-url "postgresql://user:pass@localhost:5432/dbname" --port 9080
team-run web --pg-url "..." --embed-url "http://127.0.0.1:8900" --port 9080
team-run web --pg-url "..." --port 9080 --quiet          # Supprimer les logs de requêtes
team-run web --pg-url "..." --port 9080 --quiet --daemon  # Exécuter en arrière-plan
team-run web --pg-url "..." --token "secret" --port 9080  # Authentification Token
team-run web --pg-url "..." --user-id "alice" --port 9080 # Spécifier l'utilisateur (sans = mode admin)
```

Visitez `http://localhost:9080` dans votre navigateur.

- Basculement entre projets, parcourir/rechercher/modifier/supprimer/exporter/importer les mémoires
- Recherche sémantique (correspondance par similarité vectorielle)
- Suppression des données de projet en un clic
- État de session, suivi des problèmes
- Gestion des étiquettes (renommer, fusionner, suppression par lots)
- Protection par authentification Token
- Visualisation 3D du réseau vectoriel de mémoires
- 🌐 Support multilingue (简体中文 / 繁體中文 / English / Español / Deutsch / Français / 日本語)

<p align="center">
  <img src="dashboard-projects.png" alt="Sélection de Projet" width="100%">
  <br>
  <em>Sélection de Projet</em>
</p>

<p align="center">
  <img src="dashboard-overview.png" alt="Aperçu & Visualisation du Réseau Vectoriel" width="100%">
  <br>
  <em>Aperçu & Visualisation du Réseau Vectoriel</em>
</p>

## ⚡ Service Embedding Partagé

Plusieurs workers Memory Proxy partagent un seul modèle Embedding, évitant le chargement redondant par processus (200Mo × N → 200Mo × 1).

```bash
# Démarrer le service Embedding partagé (port par défaut 8900)
team-run embed-server
team-run embed-server --port 8900              # Spécifier le port
team-run embed-server --port 8900 --daemon     # Exécuter en arrière-plan
team-run embed-server --bind 0.0.0.0           # Autoriser l'accès distant
```

Memory Proxy se connecte au service partagé via `--embed-url` :

```bash
team-run memory-proxy \
  --pg-url "postgresql://..." \
  --embed-url "http://127.0.0.1:8900" \
  --workers 4
```

- Avec `--embed-url`, l'EmbeddingEngine bascule automatiquement en mode distant et appelle le service partagé via HTTP
- En cas d'indisponibilité du service partagé, repli automatique sur le mode local — aucun impact
- Points de terminaison HTTP : `GET /health` (vérification de santé), `POST /encode` (encodage de texte unique), `POST /encode_batch` (encodage par lots)

## ⚡ Combinaison avec les Règles Steering

GatewayAIVectorMemory est la couche de stockage. Utilisez les règles Steering pour indiquer à l'IA **quand et comment** appeler ces outils.

| IDE | Emplacement Steering | Hooks |
|-----|---------------------|-------|
| Kiro | `.kiro/steering/*.md` | `.kiro/hooks/*.hook` |
| Cursor | `.cursor/rules/*.md` | `.cursor/hooks.json` |
| Claude Code | `CLAUDE.md` (ajouté) | `.claude/settings.json` |
| Windsurf | `.windsurf/rules/*.md` | `.windsurf/hooks.json` |
| VSCode | `.github/copilot-instructions.md` (ajouté) | — |
| Trae | `.trae/rules/*.md` | — |
| OpenCode | `AGENTS.md` (ajouté) | `.opencode/plugins/*.js` |

## 🇨🇳 Utilisateurs en Chine

Le modèle Embedding (~200Mo) est téléchargé automatiquement au premier lancement. Si c'est lent :

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 📦 Stack Technique

| Composant | Technologie |
|-----------|-----------|
| Runtime | Python >= 3.10 |
| BD Vectorielle | PostgreSQL + pgvector |
| Embedding | ONNX Runtime + intfloat/multilingual-e5-small |
| Tokenizer | HuggingFace Tokenizers |
| HTTP API | FastAPI + Uvicorn |
| Web | FastAPI + Vanilla JS |

## 📋 Journal des Modifications

### v0.1.1

**Architecture PostgreSQL + HTTP Memory Proxy**
- 🔄 Backend de stockage migré de SQLite + sqlite-vec vers PostgreSQL + pgvector
- 🌐 Nouveau HTTP Memory Proxy (FastAPI + Uvicorn), remplace le serveur MCP stdio
- 👥 Nouvelle mémoire d'équipe (team scope), l'erreur d'un seul profite à tous
- 🔐 Isolation des données multi-utilisateurs, Token / JWT / mapping utilisateur — trois modes d'authentification
- ⚡ Support multi-worker, service Embedding partagé, consommation mémoire réduite de 90%
- 📊 Tableau de bord Web adapté pour PostgreSQL, avec authentification Token et filtrage utilisateur
- 🔌 Tous les IDEs se connectent via HTTP API, plus de dépendance stdio

### v0.1.0

**Version Initiale**
- ⚡ Service Embedding partagé (`team-run embed-server`)
- 🧠 8 outils MCP : remember / recall / forget / status / track / task / readme / auto_save
- 📊 Tableau de bord Web (visualisation 3D du réseau vectoriel)
- 🔍 Recherche sémantique + déduplication intelligente

## License

Apache-2.0
