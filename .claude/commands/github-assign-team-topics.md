# Assign GitHub Team Topics

Assign `team-*` topics to repositories in the WalletConnect and reown-com GitHub organizations.

## Organizations
- WalletConnect
- reown-com

## Available Team Topics
From `company/org-structure.md` plus existing usage:

| Topic | Team/Owner |
|-------|------------|
| `team-buyer-experience` | Luka's team |
| `team-pay-core` | Luka's team |
| `team-merchant-experience` | Cali's team |
| `team-cloud` | Cali's team |
| `team-walletconnect-network` | Mario's team |
| `team-backend` | Mario's team |
| `team-data` | Diego's team |
| `team-infra` | Ben |
| `team-appkit` | Mago |
| `team-wallet-experience` | Jakub's team |
| `team-walletkit` | (SDK repos) |
| `team-devrel` | Developer Relations |
| `team-wcn` | WalletConnect Network |
| `team-marketing` | Marketing |

## Additional Options Per Repo
- **Archive** - Mark repo as archived
- **Skip** - Leave repo without team topic
- **Custom** - User can specify a custom topic

## Instructions

1. First, list repos without a `team-*` topic:

```bash
# WalletConnect repos needing assignment
gh repo list WalletConnect --limit 200 --json name,repositoryTopics,isArchived \
  --jq '.[] | select(.isArchived == false) | select((.repositoryTopics // [] | map(.name) | any(startswith("team-"))) | not) | .name' | sort

# reown-com repos needing assignment
gh repo list reown-com --limit 200 --json name,repositoryTopics,isArchived \
  --jq '.[] | select(.isArchived == false) | select((.repositoryTopics // [] | map(.name) | any(startswith("team-"))) | not) | .name' | sort
```

2. For each repo, get details and ask user which topic to assign:

```bash
# Get repo details
gh repo view ORG/REPO --json name,description,repositoryTopics \
  --jq '"\(.name): \(.description // "no description") | Topics: \((.repositoryTopics // []) | map(.name) | join(", "))"'
```

3. Apply the chosen topic:

```bash
# Add a team topic
gh repo edit ORG/REPO --add-topic team-TOPIC

# Or archive the repo
gh repo archive ORG/REPO --yes
```

4. Use `AskUserQuestion` to ask about each repo, presenting relevant topic options based on the repo name/description.

## Workflow
- Skip repos that already have a `team-*` topic
- Skip archived repos
- Ask about each remaining repo interactively
- Apply topics immediately after user selection
- Note any archive failures (workspace repos can't be archived)

## Last Run
2026-01-10 - Completed full assignment for both orgs
