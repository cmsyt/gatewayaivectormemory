🌐 [简体中文](../README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md) | [Español](README.es.md) | Deutsch | [Français](README.fr.md) | [日本語](README.ja.md)

<p align="center">
  <h1 align="center">🧠 GatewayAIVectorMemory</h1>
  <p align="center">
    <strong>Gib deinem KI-Programmierassistenten ein Team-Gedächtnis — PostgreSQL + pgvector Speicher · HTTP Memory Proxy · Multi-User-Zusammenarbeit & Wissensaustausch</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/v/gatewayaivectormemory?color=blue&label=PyPI" alt="PyPI"></a>
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/pyversions/gatewayaivectormemory" alt="Python"></a>
    <a href="https://github.com/cmsyt/gatewayaivectormemory/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-green" alt="License"></a>
  </p>
</p>

---

> **Kommt dir das bekannt vor?** Jede neue Sitzung startet deine KI von Null — Projektkonventionen, die du ihr gestern beigebracht hast? Vergessen. Fehler, die sie schon gemacht hat? Macht sie wieder. Halbfertige Arbeit? Weg. Schlimmer noch: Jedes Teammitglied tritt unabhängig in dieselben Fallen, Wissen sammelt sich nie an, Erfahrung wird nie weitergegeben.
>
> **GatewayAIVectorMemory ist der KI-Gedächtnis-Hub für Teams.** PostgreSQL + pgvector Speicher, HTTP Memory Proxy für einheitlichen Zugriff, Team-Fehlererfahrungen werden automatisch geteilt, Architekturwissen von einem hinterlegt profitiert alle. Multi-User-Daten sind strikt isoliert ohne Kreuzkontamination. Unterstützt gemeinsame Nutzung des Embedding-Modells durch mehrere Worker: N Prozesse, 1 Kopie im Speicher. Neue Sitzungen stellen den Kontext automatisch wieder her, semantische Suche ruft genau das Richtige ab, und der Token-Verbrauch sinkt um 50%+.

## ✨ Kernfunktionen

| Funktion | Beschreibung |
|----------|-------------|
| 👥 **Team-Wissensaustausch** | Ein Fehler einer Person wird zur Lektion für alle — Team-Erinnerungen werden automatisch geteilt, Architekturwissen und Fehlererfahrungen werden zu Team-Assets |
| 🔐 **Multi-User-Datenisolation** | Mehrere Benutzer auf einem Server, persönliche Erinnerungen strikt isoliert und unsichtbar für andere, Team-Erinnerungen projektweise geteilt |
| ⚡ **Gemeinsamer Embedding-Service** | N Worker teilen sich ein Embedding-Modell, 200MB × N → 200MB × 1, Speicherverbrauch sinkt um 90% |
| 🧠 **Sitzungsübergreifendes Gedächtnis** | Fehler, Entscheidungen, Konventionen bleiben über Sessions hinweg erhalten |
| 🔍 **Semantische Suche** | Suche „Datenbank-Timeout" und finde „Connection-Pool-Problem" — kein exakter Wortlaut nötig |
| 💰 **50%+ Tokens sparen** | Semantischer Abruf bei Bedarf statt Masseninjektion des Kontexts |
| 🔗 **Aufgabengesteuertes Dev** | Problem-Tracking → Aufgabenzerlegung → Status-Sync → verknüpfte Archivierung. KI verwaltet den gesamten Dev-Workflow |
| 📊 **Web-Dashboard** | Visuelle Verwaltung aller Erinnerungen und Aufgaben, 3D-Vektornetzwerk zeigt Wissensverbindungen auf einen Blick |
| 🔌 **Alle IDEs** | Cursor / Kiro / Claude Code / Windsurf / VSCode / OpenCode / Trae — über HTTP API |
| 🔄 **Intelligente Deduplizierung** | Ähnlichkeit > 0.95 führt automatisch zusammen, Wissensspeicher bleibt sauber |

## 🏗️ Architektur

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
│  │ Token/JWT    │  │  Multi-User-Isolation     │ │
│  └──────────────┘  └───────────────────────────┘ │
└──────────┬───────────────────┬───────────────────┘
           │                   │
┌──────────▼──────────┐ ┌─────▼─────────────────┐
│  Embedding Server   │ │  PostgreSQL + pgvector │
│  (ONNX Runtime)     │ │  Vektorspeicher +      │
│  HTTP :8900         │ │  Volltextsuche         │
└─────────────────────┘ └───────────────────────┘
```

## 🚀 Schnellstart

### Voraussetzungen

- Python >= 3.10
- PostgreSQL >= 14 (mit pgvector-Erweiterung)
- pgvector installieren: `CREATE EXTENSION IF NOT EXISTS vector;`

### Installation

```bash
pip install gatewayaivectormemory
```

### 1. Embedding-Shared-Service starten

```bash
# Standardport 8900
team-run embed-server

# Port angeben + im Hintergrund ausführen
team-run embed-server --port 8900 --daemon

# Remote-Zugriff erlauben
team-run embed-server --bind 0.0.0.0 --port 8900
```

> Das Embedding-Modell (~200MB) wird beim ersten Start automatisch heruntergeladen. Nutzer in China können `export HF_ENDPOINT=https://hf-mirror.com` setzen.

### 2. Memory Proxy starten

```bash
team-run memory-proxy \
  --pg-url "postgresql://user:pass@localhost:5432/dbname" \
  --embed-url "http://127.0.0.1:8900" \
  --port 8080 \
  --workers 4
```

Authentifizierungsoptionen (gegenseitig ausschließend):

```bash
# Statische Token-Authentifizierung
team-run memory-proxy --pg-url "..." --token "your-secret-token"

# JWT-Authentifizierung
team-run memory-proxy --pg-url "..." --jwt-secret "your-jwt-secret"

# Benutzer-Token-Mapping-Datei
team-run memory-proxy --pg-url "..." --user-tokens "/path/to/tokens.json"
```

### 3. IDE konfigurieren

In der MCP-Konfigurationsdatei deiner IDE hinzufügen:

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
<summary>📍 Konfigurationsdatei-Pfade nach IDE</summary>

| IDE | Konfigurationspfad |
|-----|-------------------|
| Kiro | `.kiro/settings/mcp.json` |
| Cursor | `.cursor/mcp.json` |
| Claude Code | `.mcp.json` |
| Windsurf | `.windsurf/mcp.json` |
| VSCode | `.vscode/mcp.json` |
| Trae | `.trae/mcp.json` |
| OpenCode | `opencode.json` |

</details>

## 📊 Web-Dashboard

```bash
team-run web --pg-url "postgresql://user:pass@localhost:5432/dbname" --port 9080
team-run web --pg-url "..." --embed-url "http://127.0.0.1:8900" --port 9080
team-run web --pg-url "..." --port 9080 --quiet          # Anfrage-Logs unterdrücken
team-run web --pg-url "..." --port 9080 --quiet --daemon  # Im Hintergrund ausführen
team-run web --pg-url "..." --token "secret" --port 9080  # Token-Authentifizierung
team-run web --pg-url "..." --user-id "alice" --port 9080 # Benutzer angeben (ohne = Admin-Modus)
```

Besuche `http://localhost:9080` im Browser.

- Mehrere Projekte wechseln, Erinnerungen durchsuchen/bearbeiten/löschen/exportieren/importieren
- Semantische Suche (Vektorähnlichkeits-Matching)
- Projektdaten mit einem Klick löschen
- Sitzungsstatus, Problem-Tracking
- Tag-Verwaltung (Umbenennen, Zusammenführen, Stapellöschung)
- Token-Authentifizierungsschutz
- 3D-Vektornetzwerk-Visualisierung
- 🌐 Mehrsprachige Unterstützung (简体中文 / 繁體中文 / English / Español / Deutsch / Français / 日本語)

<p align="center">
  <img src="dashboard-projects.png" alt="Projektauswahl" width="100%">
  <br>
  <em>Projektauswahl</em>
</p>

<p align="center">
  <img src="dashboard-overview.png" alt="Übersicht & Vektornetzwerk-Visualisierung" width="100%">
  <br>
  <em>Übersicht & Vektornetzwerk-Visualisierung</em>
</p>

## ⚡ Gemeinsamer Embedding-Service

Mehrere Memory Proxy Worker teilen sich ein Embedding-Modell, um redundantes Laden pro Prozess zu vermeiden (200MB × N → 200MB × 1).

```bash
# Gemeinsamen Embedding-Service starten (Standardport 8900)
team-run embed-server
team-run embed-server --port 8900              # Port angeben
team-run embed-server --port 8900 --daemon     # Im Hintergrund ausführen
team-run embed-server --bind 0.0.0.0           # Remote-Zugriff erlauben
```

Memory Proxy verbindet sich über `--embed-url` mit dem gemeinsamen Service:

```bash
team-run memory-proxy \
  --pg-url "postgresql://..." \
  --embed-url "http://127.0.0.1:8900" \
  --workers 4
```

- Mit `--embed-url` schaltet die EmbeddingEngine automatisch in den Remote-Modus und ruft den gemeinsamen Service über HTTP auf
- Bei Nichtverfügbarkeit des gemeinsamen Service automatischer Fallback auf lokalen Modus — keine Auswirkungen
- HTTP-Endpunkte: `GET /health` (Gesundheitscheck), `POST /encode` (Einzeltext-Encoding), `POST /encode_batch` (Batch-Encoding)

## ⚡ Kombination mit Steering-Regeln

GatewayAIVectorMemory ist die Speicherschicht. Verwende Steering-Regeln, um der KI mitzuteilen, **wann und wie** sie diese Tools aufrufen soll.

| IDE | Steering-Pfad | Hooks |
|-----|--------------|-------|
| Kiro | `.kiro/steering/*.md` | `.kiro/hooks/*.hook` |
| Cursor | `.cursor/rules/*.md` | `.cursor/hooks.json` |
| Claude Code | `CLAUDE.md` (angehängt) | `.claude/settings.json` |
| Windsurf | `.windsurf/rules/*.md` | `.windsurf/hooks.json` |
| VSCode | `.github/copilot-instructions.md` (angehängt) | — |
| Trae | `.trae/rules/*.md` | — |
| OpenCode | `AGENTS.md` (angehängt) | `.opencode/plugins/*.js` |

## 🇨🇳 Nutzer in China

Das Embedding-Modell (~200MB) wird beim ersten Start automatisch heruntergeladen. Falls langsam:

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 📦 Technologie-Stack

| Komponente | Technologie |
|------------|-----------|
| Laufzeit | Python >= 3.10 |
| Vektor-DB | PostgreSQL + pgvector |
| Embedding | ONNX Runtime + intfloat/multilingual-e5-small |
| Tokenizer | HuggingFace Tokenizers |
| HTTP API | FastAPI + Uvicorn |
| Web | FastAPI + Vanilla JS |

## 📋 Änderungsprotokoll

### v0.1.1

**PostgreSQL + HTTP Memory Proxy Architektur**
- 🔄 Speicher-Backend von SQLite + sqlite-vec zu PostgreSQL + pgvector migriert
- 🌐 Neuer HTTP Memory Proxy (FastAPI + Uvicorn), ersetzt stdio MCP Server
- 👥 Neues Team-Gedächtnis (team scope), ein Fehler einer Person profitiert alle
- 🔐 Multi-User-Datenisolation, Token / JWT / Benutzer-Mapping — drei Authentifizierungsmodi
- ⚡ Multi-Worker-Unterstützung, gemeinsamer Embedding-Service, Speicherverbrauch sinkt um 90%
- 📊 Web-Dashboard für PostgreSQL angepasst, mit Token-Authentifizierung und Benutzerfilterung
- 🔌 Alle IDEs verbinden sich über HTTP API, keine stdio-Abhängigkeit mehr

### v0.1.0

**Erstveröffentlichung**
- ⚡ Gemeinsamer Embedding-Service (`team-run embed-server`)
- 🧠 8 MCP-Werkzeuge: remember / recall / forget / status / track / task / readme / auto_save
- 📊 Web-Dashboard (3D-Vektornetzwerk-Visualisierung)
- 🔍 Semantische Suche + intelligente Deduplizierung

## License

Apache-2.0
