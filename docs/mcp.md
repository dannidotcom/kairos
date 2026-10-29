# Guide MCP Kairos

Le serveur MCP Kairos expose des outils read/write isolés par organisation.

## Configuration Claude

Ajoutez dans la configuration cliente Claude Desktop :

```json
{
  "mcpServers": {
    "kairos": {
      "url": "http://localhost:8081/mcp",
      "headers": {
        "Authorization": "Bearer VOTRE_CLE_API_KAIROS"
      }
    }
  }
}
```

## Authentification

Utilisez une clé API créée dans l’organisation Kairos. La clé n’accorde jamais accès à une autre organisation. Les outils d’envoi sont limités au mode validation manuelle ou exigent une confirmation explicite.

## Principaux outils

- `create_icp`, `list_icps`
- `list_hot_leads`
- `get_prospect`
- `create_campaign`, `start_campaign`, `pause_campaign`, `list_campaigns`
- `preview_icebreaker`
- `list_conversations`, `get_conversation`, `draft_reply`
- `get_pipeline_stats`

Le transport HTTP streamable MCP doit être placé derrière HTTPS en production.
