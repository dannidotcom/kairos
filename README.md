# Kairos

**Le bon message, au bon moment.**

Kairos est une plateforme SaaS B2B de prospection LinkedIn pilotée par signaux. Elle combine FastAPI, PostgreSQL, Redis/ARQ, React/Vite et des clients LLM Anthropic ou compatibles OpenAI.

## Démarrage rapide

```powershell
Copy-Item .env.example .env
docker compose -p kairos up --build -d
```

Services : API `8080`, frontend `8088`, MCP `8081`, PostgreSQL `5432`, Redis `6379`.

- API et OpenAPI : `http://localhost:8080/api/docs`
- Frontage : `http://localhost:8088`
- Santé API : `http://localhost:8080/health`

## Développement local

```powershell
docker compose -p kairos up --build
```

Pour arrêter : `docker compose -p kairos down`.

## Sécurité LinkedIn

L’automatisation doit respecter les conditions LinkedIn. Le mode Mock fournit un simulateur déterministe. L’intégration Unipile exige `UNIPILE_DSN` et `UNIPILE_API_KEY`. Les actions restent plafonnées par fenêtre horaire, quotas et warmup progressif.

## MCP

Le serveur MCP est accessible en HTTP streamable sur le port configuré. Chaque clé API est isolée à son organisation. Voir `docs/mcp.md`.

## Marque

Voir `docs/brand.md` pour les règles d’usage et de reproduction.
