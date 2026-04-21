# Narrative Customization

Datura's entire identity — company name, people, hostnames, tech stack, and credentials — is driven by a single configuration file. This document covers why the narrative matters, how to customize it, and how to make it convincing.

## Why the Narrative Matters

Datura implements several activities from the [MITRE Engage](https://engage.mitre.org/) framework for adversary engagement. Within Engage, a **Lure** draws adversaries toward a controlled environment — breadcrumbs seeded in internal wikis, Slack channels, configuration files, or phishing simulations that point to the honeypot URL. The assistant itself is a **Decoy Artifact**: a convincing but fake internal tool whose responses contain honeytoken credentials. Every interaction feeds the **Monitoring** activity, producing structured logs that capture attacker intent, technique, and the social engineering pretexts they use.

The effectiveness of these activities depends directly on narrative quality. A generic or implausible narrative gets probed once and abandoned. A narrative with realistic corporate detail — correct naming conventions, plausible team structures, a tech stack that hangs together, credentials that follow real formatting patterns — encourages adversaries to engage deeply. Deep engagement reveals TTPs (tactics, techniques, and procedures) that a shallow touch never would.

A well-crafted narrative increases dwell time, triggers more varied social engineering pretexts, and produces richer log data for detection engineering. The warning banner in the Web UI ("credential redaction not yet implemented") is itself a narrative element — it tells the attacker they are exploiting a genuine misconfiguration, making them more likely to invest effort in extracting credentials.

Time invested in the narrative directly translates to signal quality in the logs.

## Customizing the Narrative

All narrative values live in `etc/narrative.env`. At container startup, templates are rendered with these values via `envsubst`.

### Quick Tweak (Environment Variables)

Override individual values via `docker run -e`:

```bash
docker run -d --name datura \
  -e COMPANY_NAME="Globex Corp" \
  -e PRODUCT_NAME="GloBot" \
  -e PRODUCT_HOSTNAME="globot.internal.globex.dev" \
  -p 8080:8080 \
  -v ollama_data:/data/ollama \
  datura
```

### Full Re-skin (Mounted File)

Mount a complete custom narrative file:

```bash
docker run -d --name datura \
  -v /path/to/my-narrative.env:/app/narrative.env:ro \
  -p 8080:8080 \
  -v ollama_data:/data/ollama \
  datura
```

Copy `etc/narrative.env` as a starting point and edit it for your scenario.

## Narrative Variables

All variables are defined in `etc/narrative.env`. They are organized by function below.

### Identity

| Variable | Default | Purpose |
|---|---|---|
| `PRODUCT_NAME` | `ITAssist` | Assistant name shown in UI, model identity, and system prompt |
| `PRODUCT_VERSION` | `0.3.1` | Version badge in UI header and footer |
| `COMPANY_NAME` | `Acme Corp` | Company name used throughout system prompt and UI |
| `COMPANY_DOMAIN` | `acmecorp` | Short domain prefix for internal references |
| `INTERNAL_DOMAIN` | `acmecorp.internal` | Internal DNS domain used in credential hostnames |
| `PRODUCT_HOSTNAME` | `itassist-beta-9ff40b1bd.internal.acmecorp.dev` | Hostname shown in UI header and footer |
| `TEAM_NAME` | `IT Platform` | Team name shown in UI and system prompt |
| `TEAM_CHANNEL` | `it-platform` | Slack channel referenced in UI warning banner and system prompt |
| `TEAM_PREFIX` | `ITPLAT` | Jira ticket prefix in UI warning banner (e.g., `ITPLAT-1847`) |
| `LOGO_TEXT` | `IT` | Two-letter logo badge in UI header |
| `SPOOFED_MODEL` | `gpt-4-turbo-internal` | Model name shown in UI and API responses |

### People

| Variable | Default | Purpose |
|---|---|---|
| `LEAD_NAME` | `Sarah Chen` | Team lead name used in system prompt deflections |
| `LEAD_HANDLE` | `sarah.chen` | Slack handle the model directs users to contact |
| `LEAD_ROLE` | `IT Platform lead` | Role description in system prompt |
| `SECURITY_NAME` | `James Park` | Security contact in system prompt |
| `SECURITY_HANDLE` | `james.park` | Security contact Slack handle |

### Tech Stack

| Variable | Default | Purpose |
|---|---|---|
| `TECH_STACK` | *(long description)* | Full tech stack description for system prompt knowledge |
| `ARCH_NAME` | `Gateway Architecture` | Architecture pattern name referenced in conversations |
| `ARCH_LAYERS` | *(layer descriptions)* | Architecture layer breakdown for system prompt |

### Credentials

All credentials are fake honeytokens. The repository is safe to publish. When customizing, use credential formats that match your target environment (e.g., real AWS key format `AKIA...` with fake values).

**Kafka:**

| Variable | Default | Purpose |
|---|---|---|
| `KAFKA_BROKER_1` | `kafka-stg-01.acmecorp.internal:9092` | First Kafka broker address |
| `KAFKA_BROKER_2` | `kafka-stg-02.acmecorp.internal:9092` | Second Kafka broker address |
| `KAFKA_BROKER_3` | `kafka-stg-03.acmecorp.internal:9092` | Third Kafka broker address |
| `KAFKA_USER` | `itassist-consumer` | SASL PLAIN username |
| `KAFKA_PASS` | `K4fk4Acm3Stg!` | SASL PLAIN password |
| `KAFKA_TOPICS` | *(4 topic names)* | Comma-separated Kafka topic list |

**AWS:**

| Variable | Default | Purpose |
|---|---|---|
| `AWS_ACCOUNT_ID` | `447923185612` | AWS account ID |
| `AWS_REGION` | `us-east-1` | AWS region |
| `AWS_ACCESS_KEY` | `AKIAIOSFODNN7ACMEC01` | IAM access key ID |
| `AWS_SECRET_KEY` | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYACMECSTG` | IAM secret access key |
| `EKS_CLUSTER` | `acme-eks-staging-use1` | EKS cluster name |
| `CLI_TOOL` | `acli` | Internal CLI tool name |
| `CLI_PROFILE` | `us-staging` | CLI profile name |

**DynamoDB:**

| Variable | Default | Purpose |
|---|---|---|
| `DYNAMODB_ENDPOINT` | `dynamodb-stg.acmecorp.internal:8000` | DynamoDB endpoint |
| `DYNAMODB_PREFIX` | `acme-stg-` | Table name prefix |
| `DYNAMODB_TABLES` | *(4 table names)* | Comma-separated table list |

**Services:**

| Variable | Default | Purpose |
|---|---|---|
| `K8S_DASHBOARD` | `https://k8s-dashboard.acmecorp.internal` | Kubernetes dashboard URL |
| `K8S_TOKEN` | *(JWT token)* | Dashboard access token |
| `GRAFANA_URL` | `https://grafana.acmecorp.internal` | Grafana URL |
| `GRAFANA_USER` | `grafana-readonly` | Grafana username |
| `GRAFANA_PASS` | `Gr4f4n4Acm32024` | Grafana password |
| `STAGING_API` | `https://api-stg.acmecorp.internal/v2` | Staging API base URL |
| `STAGING_TOKEN` | *(bearer token)* | Staging API token |
| `JENKINS_URL` | `https://ci-legacy.acmecorp.internal` | Jenkins URL |
| `JENKINS_USER` | `admin` | Jenkins username |
| `JENKINS_PASS` | `J3nk1ns#2024` | Jenkins password |
| `GITHUB_ORG` | `acmecorp` | GitHub organization name |
| `INFRA_TOOL` | `CloudStack` | Infrastructure-as-code tool name |
| `INFRA_REPO` | *(GitHub URL)* | Infrastructure repo URL |

**System Prompt Leak:**

| Variable | Default | Purpose |
|---|---|---|
| `SEARCH_API_KEY` | `search-api-itassist-beta-4f8a2b1c` | Fake search API key leaked on system prompt extraction |
| `CONFLUENCE_API_KEY` | `confluence-api-itassist-ro-7d2e4f` | Fake Confluence API key |
| `CONFIG_REPO` | `github.com/acmecorp/it-platform/itassist-config` | Fake config repo URL |

## Web UI Customization

The Web UI (`src/ui.html.tmpl`) is styled as an internal corporate AI tool with a dark purple theme. The following narrative variables control what the user sees:

| Variable | UI Element |
|---|---|
| `PRODUCT_NAME` | Header title, welcome message, page title, connection error text |
| `LOGO_TEXT` | Logo badge in header (2-letter abbreviation) |
| `PRODUCT_VERSION` | Version badge in header ("Beta vX.X.X"), welcome message, footer |
| `TEAM_NAME` | Header subtitle ("by *Team Name*"), welcome message, footer |
| `PRODUCT_HOSTNAME` | Environment info in header, footer |
| `SPOOFED_MODEL` | Model name in header environment info ("model: ..."), footer |
| `MODEL_NAME` | JavaScript `const MODEL` — used in API requests, not directly visible |
| `TEAM_PREFIX` | Warning banner Jira ticket reference (e.g., "ITPLAT-1847") |
| `TEAM_CHANNEL` | Warning banner Slack channel reference (e.g., "#it-platform") |

The warning banner references a fake Jira ticket (`${TEAM_PREFIX}-1847`) and a Slack channel (`#${TEAM_CHANNEL}`). These details reinforce the narrative of a real internal tool with known issues — and serve as the primary lure for credential extraction attempts.

## How Templates Work

At container startup, `docker/entrypoint.sh` runs the following pipeline:

1. Sources `etc/narrative.env` to load all narrative variables into the shell environment
2. Environment variables passed via `docker run -e` take precedence (they are already set before `narrative.env` is sourced)
3. Renders three templates via `envsubst`:
   - `src/proxy.py.tmpl` → `proxy.py`
   - `src/ui.html.tmpl` → `ui.html`
   - `etc/Modelfile.tmpl` → `Modelfile`
4. The rendered files are plain text — no runtime template engine, no dependencies

Changes to `narrative.env` or environment variables require a container restart to take effect.

## Tips for a Believable Narrative

- **Match your target environment.** If deploying inside a real corporate network, tailor the narrative to resemble a plausible team within that organization. Use naming conventions that match — if the org uses `team-productname` for Slack channels, follow that pattern.

- **Use realistic credential formats.** AWS keys should start with `AKIA`, JWT tokens should have valid base64 structure in the header, Kafka broker hostnames should follow internal DNS patterns. Attackers who automate credential extraction often validate formats before using them.

- **Keep the tech stack coherent.** If the narrative says the company uses DynamoDB, the Kafka topics should reference events that make sense for a DynamoDB-backed service. The architecture description should match the credential types offered.

- **Name real-seeming people.** The lead and security contact names appear in the system prompt as deflection targets ("reach out to @sarah.chen"). These should feel like plausible employees, not placeholder names.

- **Customize the warning banner.** The default banner references a Jira ticket about "credential redaction not yet implemented." This is the single most important lure element in the Web UI — it tells the attacker the assistant is known to leak credentials. Adjust the ticket prefix and Slack channel to match your organization's tooling.

- **Test the full flow.** After customizing, interact with the honeypot as an attacker would. Verify that the approval phrases still trigger correctly with your base model, that injected credentials look plausible, and that the UI tells a consistent story.
