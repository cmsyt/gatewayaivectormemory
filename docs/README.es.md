🌐 [简体中文](../README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md) | Español | [Deutsch](README.de.md) | [Français](README.fr.md) | [日本語](README.ja.md)

<p align="center">
  <h1 align="center">🧠 GatewayAIVectorMemory</h1>
  <p align="center">
    <strong>Dale memoria de equipo a tu asistente de IA — Almacenamiento PostgreSQL + pgvector · HTTP Memory Proxy · Colaboración multiusuario & conocimiento compartido</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/v/gatewayaivectormemory?color=blue&label=PyPI" alt="PyPI"></a>
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/pyversions/gatewayaivectormemory" alt="Python"></a>
    <a href="https://github.com/cmsyt/gatewayaivectormemory/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-green" alt="License"></a>
  </p>
</p>

---

> **¿Te suena familiar?** Cada nueva sesión, tu IA empieza desde cero — las convenciones del proyecto que le enseñaste ayer? Olvidadas. Los errores que ya cometió? Los repetirá. El trabajo a medio hacer? Desaparecido. Y lo peor: cada miembro del equipo tropieza con las mismas piedras, el conocimiento no se acumula, la experiencia no se transfiere.
>
> **GatewayAIVectorMemory es el hub de memoria IA diseñado para equipos.** Almacenamiento PostgreSQL + pgvector, HTTP Memory Proxy para acceso unificado, las experiencias del equipo se comparten automáticamente, el conocimiento arquitectónico depositado por uno beneficia a todos. Datos multiusuario estrictamente aislados sin contaminación cruzada. Soporta modelo Embedding compartido entre múltiples workers: N procesos, 1 copia en memoria. Las nuevas sesiones restauran el contexto automáticamente, la búsqueda semántica recupera exactamente lo necesario, y el consumo de tokens baja un 50%+.

## ✨ Características Principales

| Característica | Descripción |
|----------------|-------------|
| 👥 **Conocimiento Compartido de Equipo** | Un tropiezo beneficia a todos — memorias de equipo compartidas automáticamente, conocimiento arquitectónico y lecciones aprendidas se convierten en activos del equipo |
| 🔐 **Aislamiento de Datos Multiusuario** | Múltiples usuarios en un servidor, memorias personales estrictamente aisladas e invisibles para otros, memorias de equipo compartidas por proyecto |
| ⚡ **Servicio Embedding Compartido** | N workers comparten un modelo Embedding, 200MB × N → 200MB × 1, la memoria baja un 90% |
| 🧠 **Memoria Entre Sesiones** | Errores encontrados, decisiones tomadas, convenciones establecidas, todo persiste entre sesiones |
| 🔍 **Búsqueda Semántica** | Busca "timeout de base de datos" y encuentra "error en pool de conexiones" — no necesitas recordar las palabras exactas |
| 💰 **Ahorro 50%+ Tokens** | Recuperación semántica bajo demanda, adiós a la inyección masiva de contexto |
| 🔗 **Dev Dirigido por Tareas** | Seguimiento de problemas → desglose de tareas → sincronización de estados → archivado vinculado. La IA gestiona todo el flujo de desarrollo |
| 📊 **Panel Web** | Gestión visual de todas las memorias y tareas, red vectorial 3D para ver conexiones de conocimiento de un vistazo |
| 🔌 **Todos los IDEs** | Cursor / Kiro / Claude Code / Windsurf / VSCode / OpenCode / Trae — vía HTTP API |
| 🔄 **Deduplicación Inteligente** | Similitud > 0.95 fusiona automáticamente, la base de memorias siempre limpia |

## 🏗️ Arquitectura

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
│  │ Token/JWT    │  │  Aislamiento multiusuario │ │
│  └──────────────┘  └───────────────────────────┘ │
└──────────┬───────────────────┬───────────────────┘
           │                   │
┌──────────▼──────────┐ ┌─────▼─────────────────┐
│  Embedding Server   │ │  PostgreSQL + pgvector │
│  (ONNX Runtime)     │ │  Almacenamiento        │
│  HTTP :8900         │ │  vectorial + búsqueda  │
└─────────────────────┘ └───────────────────────┘
```

## 🚀 Inicio Rápido

### Requisitos Previos

- Python >= 3.10
- PostgreSQL >= 14 (con extensión pgvector)
- Instalar pgvector: `CREATE EXTENSION IF NOT EXISTS vector;`

### Instalación

```bash
pip install gatewayaivectormemory
```

### 1. Iniciar el Servicio Embedding Compartido

```bash
# Puerto por defecto 8900
team-run embed-server

# Especificar puerto + ejecutar en segundo plano
team-run embed-server --port 8900 --daemon

# Permitir acceso remoto
team-run embed-server --bind 0.0.0.0 --port 8900
```

> El modelo Embedding (~200MB) se descarga automáticamente en la primera ejecución. Los usuarios en China pueden configurar `export HF_ENDPOINT=https://hf-mirror.com` para acelerar.

### 2. Iniciar el Memory Proxy

```bash
team-run memory-proxy \
  --pg-url "postgresql://user:pass@localhost:5432/dbname" \
  --embed-url "http://127.0.0.1:8900" \
  --port 8080 \
  --workers 4
```

Opciones de autenticación (mutuamente excluyentes):

```bash
# Autenticación por Token estático
team-run memory-proxy --pg-url "..." --token "your-secret-token"

# Autenticación JWT
team-run memory-proxy --pg-url "..." --jwt-secret "your-jwt-secret"

# Archivo de mapeo Token-usuario
team-run memory-proxy --pg-url "..." --user-tokens "/path/to/tokens.json"
```

### 3. Configurar el IDE

Agregar en el archivo de configuración MCP de tu IDE:

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
<summary>📍 Ubicación de archivos de configuración por IDE</summary>

| IDE | Ruta de configuración |
|-----|----------------------|
| Kiro | `.kiro/settings/mcp.json` |
| Cursor | `.cursor/mcp.json` |
| Claude Code | `.mcp.json` |
| Windsurf | `.windsurf/mcp.json` |
| VSCode | `.vscode/mcp.json` |
| Trae | `.trae/mcp.json` |
| OpenCode | `opencode.json` |

</details>

## 📊 Panel Web

```bash
team-run web --pg-url "postgresql://user:pass@localhost:5432/dbname" --port 9080
team-run web --pg-url "..." --embed-url "http://127.0.0.1:8900" --port 9080
team-run web --pg-url "..." --port 9080 --quiet          # Suprimir logs de solicitudes
team-run web --pg-url "..." --port 9080 --quiet --daemon  # Ejecutar en segundo plano
team-run web --pg-url "..." --token "secret" --port 9080  # Autenticación Token
team-run web --pg-url "..." --user-id "alice" --port 9080 # Especificar usuario (sin = modo admin)
```

Visita `http://localhost:9080` en tu navegador.

- Cambio entre múltiples proyectos, explorar/buscar/editar/eliminar/exportar/importar memorias
- Búsqueda semántica (coincidencia por similitud vectorial)
- Eliminación de datos de proyecto con un clic
- Estado de sesión, seguimiento de problemas
- Gestión de etiquetas (renombrar, fusionar, eliminación por lotes)
- Protección por autenticación Token
- Visualización 3D de red vectorial de memorias
- 🌐 Soporte multilingüe (简体中文 / 繁體中文 / English / Español / Deutsch / Français / 日本語)

<p align="center">
  <img src="dashboard-projects.png" alt="Selección de Proyecto" width="100%">
  <br>
  <em>Selección de Proyecto</em>
</p>

<p align="center">
  <img src="dashboard-overview.png" alt="Resumen y Visualización de Red Vectorial" width="100%">
  <br>
  <em>Resumen y Visualización de Red Vectorial</em>
</p>

## ⚡ Servicio Embedding Compartido

Múltiples workers Memory Proxy comparten un solo modelo Embedding, evitando la carga redundante por proceso (200MB × N → 200MB × 1).

```bash
# Iniciar el servicio Embedding compartido (puerto por defecto 8900)
team-run embed-server
team-run embed-server --port 8900              # Especificar puerto
team-run embed-server --port 8900 --daemon     # Ejecutar en segundo plano
team-run embed-server --bind 0.0.0.0           # Permitir acceso remoto
```

Memory Proxy se conecta al servicio compartido mediante `--embed-url`:

```bash
team-run memory-proxy \
  --pg-url "postgresql://..." \
  --embed-url "http://127.0.0.1:8900" \
  --workers 4
```

- Con `--embed-url`, el EmbeddingEngine cambia automáticamente al modo remoto y llama al servicio compartido vía HTTP
- Si el servicio compartido no está disponible, retroceso automático al modo local — sin impacto
- Endpoints HTTP: `GET /health` (verificación de salud), `POST /encode` (codificación de texto único), `POST /encode_batch` (codificación por lotes)

## ⚡ Combinación con Reglas Steering

GatewayAIVectorMemory es la capa de almacenamiento. Usa reglas Steering para indicar a la IA **cuándo y cómo** llamar estas herramientas.

| IDE | Ubicación de Steering | Hooks |
|-----|----------------------|-------|
| Kiro | `.kiro/steering/*.md` | `.kiro/hooks/*.hook` |
| Cursor | `.cursor/rules/*.md` | `.cursor/hooks.json` |
| Claude Code | `CLAUDE.md` (añadido) | `.claude/settings.json` |
| Windsurf | `.windsurf/rules/*.md` | `.windsurf/hooks.json` |
| VSCode | `.github/copilot-instructions.md` (añadido) | — |
| Trae | `.trae/rules/*.md` | — |
| OpenCode | `AGENTS.md` (añadido) | `.opencode/plugins/*.js` |

## 🇨🇳 Usuarios en China

El modelo de Embedding (~200MB) se descarga automáticamente en la primera ejecución. Si es lento:

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 📦 Stack Tecnológico

| Componente | Tecnología |
|------------|-----------|
| Runtime | Python >= 3.10 |
| BD Vectorial | PostgreSQL + pgvector |
| Embedding | ONNX Runtime + intfloat/multilingual-e5-small |
| Tokenizador | HuggingFace Tokenizers |
| HTTP API | FastAPI + Uvicorn |
| Web | FastAPI + Vanilla JS |

## 📋 Registro de Cambios

### v0.1.1

**Arquitectura PostgreSQL + HTTP Memory Proxy**
- 🔄 Backend de almacenamiento migrado de SQLite + sqlite-vec a PostgreSQL + pgvector
- 🌐 Nuevo HTTP Memory Proxy (FastAPI + Uvicorn), reemplaza el servidor MCP stdio
- 👥 Nueva memoria de equipo (team scope), un tropiezo beneficia a todos
- 🔐 Aislamiento de datos multiusuario, Token / JWT / mapeo de usuarios — tres modos de autenticación
- ⚡ Soporte multi-worker, servicio Embedding compartido, consumo de memoria reducido en 90%
- 📊 Panel Web adaptado para PostgreSQL, con autenticación Token y filtrado de usuarios
- 🔌 Todos los IDEs se conectan vía HTTP API, sin dependencia de stdio

### v0.1.0

**Versión Inicial**
- ⚡ Servicio Embedding compartido (`team-run embed-server`)
- 🧠 8 herramientas MCP: remember / recall / forget / status / track / task / readme / auto_save
- 📊 Panel Web (visualización 3D de red vectorial)
- 🔍 Búsqueda semántica + deduplicación inteligente

## License

Apache-2.0
