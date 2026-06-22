# Bot Registration and Deployment API

## Base URL

All endpoints are served by the lobby server.

```text
https://<lobby-host>/api/bots
```

All request and response bodies are JSON. All mutating endpoints require an
access token for an account with the `developer` role.

Authorization header:

```http
Authorization: Bearer <access_token>
```

Non-developer accounts receive:

```json
{
  "code": "insufficient_role",
  "message": "The authenticated account does not have the required role."
}
```

Service-level direct calls return `developer_role_required`.

## Discover Public Bots

```http
GET /api/bots
```

Authentication is not required.

Response:

```json
{
  "providers": [],
  "definitions": [],
  "deployments": []
}
```

Response type: `BotDiscoveryResponse`.

## List My Registered Bots

```http
GET /api/bots/mine
```

Requires `developer`.

Response type: `BotDiscoveryResponse`.

## Register Provider

```http
POST /api/bots/providers
```

Requires `developer`.

Request type: `RegisterBotProviderRequest`.

```json
{
  "display_name": "Acme Guandan Lab",
  "contact_email": "bots@example.com"
}
```

Response type: `BotRegistrationResponse`.

```json
{
  "provider": {
    "provider_id": "PABCDE",
    "display_name": "Acme Guandan Lab",
    "owner_account_id": "user-id",
    "contact_email": "bots@example.com",
    "status": "pending",
    "created_at": "2026-06-03T00:00:00.000Z",
    "updated_at": "2026-06-03T00:00:00.000Z"
  },
  "definition": null,
  "deployment": null
}
```

## Create Bot Definition

```http
POST /api/bots/definitions
```

Requires `developer`. The authenticated account must own the provider.

Request type: `CreateBotDefinitionRequest`.

```json
{
  "provider_id": "PABCDE",
  "display_name": "Acme Tempo Bot",
  "version": "1.0.0",
  "description": "A tempo-oriented bot for classic four-player Guandan.",
  "strength": "advanced",
  "supported_rule_sets": ["classic"],
  "supported_protocol_versions": ["guandan-bot-v1"],
  "visibility": "private"
}
```

Response type: `BotRegistrationResponse`.

Definitions start with status `draft`.

## Register Deployment

```http
POST /api/bots/deployments
```

Requires `developer`. The authenticated account must own the provider.

Request type: `RegisterBotDeploymentRequest`.

HTTP deployment:

```json
{
  "provider_id": "PABCDE",
  "transport_type": "http",
  "supported_bot_definition_ids": ["BBCDEF"],
  "supported_protocol_versions": ["guandan-bot-v1"],
  "max_concurrent_sessions": 128,
  "region": "us-west"
}
```

Response type: `BotRegistrationResponse`. For HTTP deployments the response
includes one-time `deployment_management_key` and `bot_invocation_token`
fields. `api_key` remains a deprecated alias for `deployment_management_key`.
The lobby stores only the management-key hash, but retains the invocation
token internally so game servers can authenticate bot calls.

HTTP deployment response excerpt:

```json
{
  "deployment": {
    "deployment_id": "DDDDDDDD",
    "transport_type": "http",
    "base_url": null,
    "status": "pending_verification"
  },
  "deployment_management_key": "one-time-management-key",
  "api_key": "one-time-management-key",
  "bot_invocation_token": "one-time-runtime-token"
}
```

HTTP bot deployment procedure:

1. Register or select a provider in Developer Center.
2. Create or select a bot definition for the provider.
3. Register an HTTP deployment. The platform issues a
   `deployment_management_key` and `bot_invocation_token`.
4. Configure `bot_invocation_token` inside the bot HTTP server.
5. Enter the stable HTTPS `base_url` in the deployment page.
6. The platform calls
   `GET {base_url}/health` with
   `Authorization: Bearer <bot_invocation_token>` and
   `X-Api-Key: <bot_invocation_token>`.
7. If the health endpoint returns 2xx with status `ok` or `healthy`, the
   deployment becomes `healthy`.
8. Runtime game servers route HTTP bot requests only to verified healthy HTTP
   deployments.

Loopback HTTP URLs are accepted for local development. Hosted HTTP bot
deployments must use HTTPS. The submitted URL must be reachable from the lobby
server process. For same-host local development use `127.0.0.1`; if the lobby
runs in Docker on macOS, use a host-reachable address such as
`host.docker.internal`.

## Verify HTTP Deployment Base URL

```http
POST /api/bots/deployments/{deployment_id}/verify
```

Requires `developer`. The authenticated account must own the deployment.

Request type: `VerifyBotDeploymentRequest`.

```json
{
  "base_url": "https://bot.example.com/guandan"
}
```

Response type: `BotRegistrationResponse`. On success, the deployment has
status `healthy`, `base_url` set to the verified URL, and `last_healthy_at`
set.

WebSocket deployment:

```json
{
  "provider_id": "PABCDE",
  "transport_type": "websocket",
  "base_url": "wss://bot.example.com/guandan",
  "supported_bot_definition_ids": ["BBCDEF"],
  "supported_protocol_versions": ["guandan-bot-v1"],
  "max_concurrent_sessions": 128,
  "region": "us-west"
}
```

Response type: `BotRegistrationResponse`.

Deployments start with status `pending_verification`.

## Admin Endpoints

Site administrators can manage all bot providers, definitions, and deployments
regardless of ownership.

### List All Providers

```http
GET /api/admin/bots/providers
```

Requires `site_admin`.

Response:

```json
{
  "providers": [{ "provider_id": "...", ... }]
}
```

### Get Provider Detail

```http
GET /api/admin/bots/providers/{provider_id}
```

Requires `site_admin`. Returns the provider with all its definitions and
deployments.

Response type: `BotDiscoveryResponse`.

### Delete Provider (Admin)

```http
DELETE /api/admin/bots/providers/{provider_id}
```

Requires `site_admin`. Cascade-deletes the provider, all its definitions, and
all its deployments.

### Delete Definition (Admin)

```http
DELETE /api/admin/bots/definitions/{definition_id}
```

Requires `site_admin`. Cascade-deletes the definition and all deployments that
reference it.

## Error Codes

| Code | Status | Meaning |
| --- | ---: | --- |
| `missing_bearer_token` | 401 | Mutating endpoint requires authentication. |
| `insufficient_role` | 403 | Token user does not have `developer`. |
| `site_admin_role_required` | 403 | Action requires `site_admin` role. |
| `developer_role_required` | 403 | Direct service call used a non-developer account. |
| `missing_display_name` | 400 | Provider display name is empty. |
| `invalid_contact_email` | 400 | Provider contact email is invalid. |
| `bot_provider_not_found` | 404 | Requested provider does not exist. |
| `bot_definition_not_found` | 404 | Requested bot definition does not exist. |
| `bot_provider_forbidden` | 403 | Account does not own the provider. |
| `missing_definition_metadata` | 400 | Definition name or version is empty. |
| `missing_protocol_support` | 400 | Definition lacks rule sets or protocol versions. |
| `missing_deployment_base_url` | 400 | Non-HTTP deployment omitted `base_url`. |
| `invalid_http_bot_base_url` | 400 | HTTP bot URL is not absolute HTTPS or local loopback HTTP. |
| `missing_deployment_support` | 400 | Deployment lacks bot definitions or protocols. |
| `invalid_session_capacity` | 400 | Deployment capacity is less than one. |
| `unsupported_bot_definition` | 400 | Deployment references another provider's definition. |
| `unsupported_deployment_verification` | 400 | Verification was requested for a non-HTTP deployment. |
| `missing_bot_invocation_token` | 409 | HTTP deployment has no invocation token to verify with. |
| `http_bot_health_check_failed` | 502 | Platform could not complete authenticated HTTP bot health verification. |
| `invalid_payload` | 400 | Body is not a JSON object. |

## Dart Client Usage

The Flutter app client exposes matching helpers:

```dart
final provider = await lobbyAuthClient.registerBotProvider(
  const RegisterBotProviderRequest(
    displayName: 'Acme Guandan Lab',
    contactEmail: 'bots@example.com',
  ),
);

final definition = await lobbyAuthClient.createBotDefinition(
  CreateBotDefinitionRequest(
    providerId: provider.providerId,
    displayName: 'Acme Tempo Bot',
    version: '1.0.0',
    description: 'Tempo-oriented classic Guandan bot.',
    supportedRuleSets: const ['classic'],
    supportedProtocolVersions: const ['guandan-bot-v1'],
  ),
);

await lobbyAuthClient.registerBotDeployment(
  RegisterBotDeploymentRequest(
    providerId: provider.providerId,
    transportType: BotTransportType.http,
    supportedBotDefinitionIds: [definition.botDefinitionId],
    supportedProtocolVersions: const ['guandan-bot-v1'],
    maxConcurrentSessions: 128,
  ),
);

await lobbyAuthClient.verifyBotDeploymentBaseUrl(
  deploymentId: '<deployment-id>',
  request: VerifyBotDeploymentRequest(
    baseUrl: Uri.parse('https://bot.example.com/guandan'),
  ),
);
```
