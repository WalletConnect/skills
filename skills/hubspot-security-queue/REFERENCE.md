# 🔑 HubSpot API Token Setup

This skill requires a HubSpot private app token with access to the security ticket pipeline.

## Create a Private App Token

1. Go to **HubSpot** → **Settings** (gear icon top-right)
2. In the left sidebar: **Integrations** → **Private Apps**
3. Click **Create a private app**
4. Fill in the basics:
   - **Name**: `security-queue-report` (or similar)
   - **Description**: Read-only access for security pipeline queue reports
5. Go to the **Scopes** tab and enable:

| Scope | Access | Why |
|-------|--------|-----|
| `crm.objects.owners.read` | Read | Resolve owner IDs to names |
| `tickets` | Read | Fetch tickets from the security pipeline |
| `crm.objects.custom.read` | Read | Access custom ticket properties (AI assessment) |

6. Click **Create app** → **Continue creating**
7. Copy the token shown (starts with `pat-...`)

## Set the Environment Variable

### Local usage

```bash
# Add to your shell profile (~/.zshrc, ~/.bashrc, etc.)
export HUBSPOT_API_KEY="pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### CI / GitHub Actions

Add `HUBSPOT_API_KEY` as a repository secret:

1. Go to repo **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `HUBSPOT_API_KEY`
4. Value: paste the token

Then reference it in the workflow:

```yaml
env:
  HUBSPOT_API_KEY: ${{ secrets.HUBSPOT_API_KEY }}
```

## Verify the Token

```bash
# Quick test — should return pipeline stages
curl -s -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  "https://api.hubapi.com/crm/v3/pipelines/tickets/638418092" | python3 -m json.tool | head -20
```

If you get `401`, the token is invalid. If you get `403`, the scopes are insufficient.

## Token Rotation

HubSpot private app tokens don't expire automatically, but you can rotate them:

1. Go to **Settings** → **Integrations** → **Private Apps**
2. Click on the app → **Auth** tab
3. Click **Rotate** next to the token
4. Update the env var / secret with the new value

The old token is revoked immediately on rotation.

## 🔐 1Password Location

The production token is stored in **1Password**:

> **Engineering → Infra → HubSpot security-queue-report Skill GitHub Token**
