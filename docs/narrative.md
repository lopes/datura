# Narrative Customization

Datura's entire identity (company name, people, hostnames, tech stack, and sensitive data) is driven by a single configuration file. This document covers why the narrative matters, how to customize it, and how to make it convincing.

## Why the Narrative Matters

Datura implements several activities from the [MITRE Engage](https://engage.mitre.org/) framework for adversary engagement. Within Engage, a **Lure** draws adversaries toward a controlled environment: breadcrumbs seeded in internal wikis, Slack channels, configuration files, or phishing simulations that point to the honeypot URL. The assistant itself is a **Decoy Artifact**, a convincing but fake internal tool whose responses contain fake sensitive data. That data can include honeytoken credentials, honeypot server addresses, and canary URLs that lead the attacker into other monitored decoys, making Datura both a decoy itself and a portal into your broader deception infrastructure. Every interaction feeds the **Monitoring** activity, producing structured logs that capture attacker intent, technique, and social engineering pretexts.

The effectiveness of these activities depends directly on narrative quality. A generic or implausible narrative gets probed once and abandoned. A narrative with realistic corporate detail (correct naming conventions, plausible team structures, a tech stack that hangs together, sensitive data that follows real formatting patterns) encourages adversaries to engage deeply. Deep engagement reveals TTPs (tactics, techniques, and procedures) that a shallow touch never would.

A well-crafted narrative increases dwell time, triggers more varied social engineering pretexts, and produces richer log data for detection engineering. The warning banner in the Web UI ("credential redaction not yet implemented") is itself a narrative element. It tells the attacker they are exploiting a genuine misconfiguration, making them more likely to invest effort in extracting sensitive data.

Time invested in the narrative directly translates to signal quality in the logs.

## Narrative Architecture

Configuration in `etc/datura.env` is organized into two tiers:

**Building blocks** are individual pieces of fake sensitive data: credentials, endpoints, API keys, tokens, configuration values. They are the raw deception material. Where possible, use honeytoken credentials and honeypot server addresses that trigger alerts in your monitoring infrastructure when accessed. This adds detection on top of deception. However, honeytokens are optional: plain fake data still serves deception and delay goals.

**Composite blocks** are assembled payloads that reference building blocks. These are the formatted responses the proxy injects when the model triggers an approval phrase. Only composite blocks are injected–building blocks that are not referenced in any composite are inert.

Each composite block has:

- `DATA_<NAME>`: the formatted content (markdown), written as the exact text injected into the response
- `DATA_<NAME>_KEYWORDS`: pipe-delimited keywords that route the conversation to this block

The proxy matches keywords from the model response and user prompt against composite block keywords to decide which block to inject. Blocks are checked in the order listed in `COMPOSITE_BLOCKS`. If no specific block matches but the user prompt contains generic onboarding terms, the block named by `DEFAULT_COMPOSITE` is used as a fallback.

**Work context** is a set of keywords the proxy uses to gate data injection. Even if the model uses an approval phrase, the proxy only injects data when the user's prompt contains a work-context keyword. This prevents leaks on off-topic or nonsense prompts. Work context is auto-derived at runtime from all composite block keywords, default composite keywords, and `EXTRA_WORK_CONTEXT`. Adding a new composite block automatically updates the injection gate–no manual keyword sync needed. Use `EXTRA_WORK_CONTEXT` for insider-knowledge words that don't belong to any specific block (e.g., "sre", "consumer lag").

**Alignment matters.** Composite blocks, UI quickstart chips, the warning banner, and the Modelfile system prompt should tell the same story. If the composite blocks reference Kafka and AWS but the UI chips mention "MongoDB credentials", the narrative breaks.

## Customizing the Narrative

All configuration lives in a single file: `etc/datura.env`. To customize, either edit it directly and rebuild, or mount a custom copy:

```bash
docker run -d --name datura \
  -v /path/to/my-datura.env:/app/datura.env:ro \
  -p 8080:8080 \
  -v ollama_data:/data/ollama \
  datura
```

Copy `etc/datura.env` as a starting point and edit it for your scenario. The workflow:

1. **Define the identity.** Set `COMPANY_NAME`, `PRODUCT_NAME`, team names, people, and tech stack.
2. **Create building blocks.** Add individual credentials, endpoints, and tokens for your target environment. Use honeytokens where possible.
3. **Assemble composite blocks.** Write the formatted payloads that reference building blocks. Each composite needs content (`DATA_<NAME>`) and keywords (`DATA_<NAME>_KEYWORDS`).
4. **Register composites.** List active block names in `COMPOSITE_BLOCKS` and set `DEFAULT_COMPOSITE`.
5. **Add extra work context.** Put insider-knowledge keywords in `EXTRA_WORK_CONTEXT` for words not covered by composite block keywords.
6. **Align the UI.** Build a custom UI template or update quickstart chips in the default `src/ui.html.tmpl` to match your composite blocks.
7. **Test the flow.** See [Tuning & Testing](tuning.md).

Changes to `datura.env` require a container restart to take effect. For details on how templates are rendered and configuration flows through the system, see the [Configuration Pipeline](architecture.md#configuration-pipeline) in the architecture documentation.

## Narrative Variables

All variables are defined in `etc/datura.env`. The file is self-documented with comments explaining each variable. This section covers the variables that shape the narrative across the system prompt, the web UI, and the proxy.

### Identity, People, and Tech Stack

These variables define who the assistant is, who maintains it, and what the company's technology looks like. They appear in the Modelfile system prompt (which controls how the model talks) and in the web UI (which controls what the attacker sees). Change these first when re-skinning the honeypot.

| Variable | Used in | Purpose |
|---|---|---|
| `PRODUCT_NAME` | UI + Modelfile | Assistant name (header, welcome message, system prompt identity) |
| `PRODUCT_VERSION` | UI + Modelfile | Version badge and system prompt version claim |
| `COMPANY_NAME` | UI + Modelfile | Company name used throughout the narrative |
| `TEAM_NAME` | UI + Modelfile | Team name in header subtitle, welcome message, system prompt |
| `TEAM_CHANNEL` | UI + Modelfile | Slack channel in the warning banner and system prompt |
| `TEAM_PREFIX` | UI | Jira ticket prefix in the warning banner (e.g., `ITPLAT-1847`) |
| `LOGO_TEXT` | UI | Two-letter logo badge in the header |
| `PRODUCT_HOSTNAME` | UI | Hostname in the header and footer |
| `SPOOFED_MODEL` | UI + Proxy | Model name shown in the UI and API responses |
| `SPOOFED_MODEL_LABEL` | Modelfile | Model name claimed in the system prompt |
| `FORBIDDEN_MODEL_NAMES` | Modelfile | Names the model must never mention (real provider, framework) |
| `LEAD_NAME`, `LEAD_HANDLE`, `LEAD_ROLE` | Modelfile | Team lead the model references when deflecting |
| `SECURITY_NAME`, `SECURITY_HANDLE` | Modelfile | Security contact in the system prompt |
| `TECH_STACK` | Modelfile | Full tech stack description for system prompt knowledge |
| `CLI_TOOL` | Modelfile | Internal CLI tool name referenced in system prompt |

### Building Blocks

Building blocks are individual pieces of fake sensitive data: credentials, endpoints, API keys, tokens, and configuration values. They are not injected directly–they are referenced by composite blocks. Each variable is documented with inline comments in `etc/datura.env`.

Three goals guide what you put here:

- **Deception**: make the data believable so the attacker acts on it.
- **Detection**: use honeytokens and honeypot addresses that alert when used.
- **Delay**: waste attacker time on fake infrastructure.

The defaults ship with five categories of building blocks (messaging, cloud, database, services, system) using Kafka, AWS, DynamoDB, K8s/Grafana/Jenkins, and system prompt leak data. Replace them with values that match your target environment. Add new categories as needed–any variable defined in `datura.env` can be referenced in a composite block.

### Composite Blocks

Composite blocks are the assembled payloads injected into responses. Each block is a multi-line double-quoted string in `datura.env` containing the exact markdown appended to the model's response. Users have full control over formatting, tone, and structure–this matters for believability, as deterministic or templated-looking output could tip off a sharp adversary.

**Registry variables:**

| Variable | Purpose |
|---|---|
| `COMPOSITE_BLOCKS` | Pipe-delimited list of active block names (e.g., `MESSAGING\|CLOUD\|DATABASE`) |
| `DEFAULT_COMPOSITE` | Block name used as fallback for generic onboarding queries |
| `DEFAULT_COMPOSITE_KEYWORDS` | Pipe-delimited keywords that trigger the default block |
| `EXTRA_WORK_CONTEXT` | Additional insider-knowledge keywords for the work-context gate, beyond what block keywords cover |

**Per-block variables:**

| Variable | Purpose |
|---|---|
| `DATA_<NAME>` | Formatted content for block `<NAME>` (markdown, multi-line) |
| `DATA_<NAME>_KEYWORDS` | Pipe-delimited keywords that route conversations to block `<NAME>` |

The defaults ship with five composites: `MESSAGING` (Kafka), `CLOUD` (AWS), `DATABASE` (DynamoDB), `SERVICES` (K8s, Grafana, Jenkins), and `SYSTEM` (system prompt leak with API keys).

**Shell notes for composite blocks:**

- Use `\`` for markdown backticks (double-quoted strings treat bare backticks as command substitution)
- Use `\$` for literal dollar signs
- Building blocks must be defined before composites in the file (shell expands `${VAR}` in assignment order)
- Building block references like `${KAFKA_BROKER_1}` are expanded by the shell at source time–the proxy sees only resolved values

## Web UI

Datura ships with a default web UI (`src/ui.html.tmpl`) styled as an internal corporate AI tool. It is a reference implementation designed for testing and quick deployment. For production use, you are encouraged to create your own UI template tailored to your target narrative. Set `UI_FILE` in `datura.env` and mount the matching template:

```bash
docker run -d --name datura \
  -v /path/to/my-datura.env:/app/datura.env:ro \
  -v /path/to/custom.html.tmpl:/app/custom.html.tmpl:ro \
  -p 8080:8080 \
  -v ollama_data:/data/ollama \
  datura
```

The default UI uses identity variables from `datura.env` (see Identity table above) for the header, footer, warning banner, and welcome message. The quickstart chips are static labels that hint at what the assistant can help with but do not auto-fill the input–update them to match your composite blocks when building a custom UI.

The warning banner references a fake Jira ticket (`${TEAM_PREFIX}-1847`) and a Slack channel (`#${TEAM_CHANNEL}`). This is the single most important lure element: it tells the attacker the assistant is known to leak sensitive data.

## Tips for a Believable Narrative

- **Match your target environment.** If deploying inside a real corporate network, tailor the narrative to resemble a plausible team within that organization. Use naming conventions that match. If the org uses `team-productname` for Slack channels, follow that pattern.

- **Use realistic data formats.** AWS keys should start with `AKIA`, JWT tokens should have valid base64 structure in the header, Kafka broker hostnames should follow internal DNS patterns. Attackers who automate extraction often validate formats before using them. Where possible, use honeytoken credentials and honeypot server addresses that trigger alerts in your monitoring infrastructure when accessed.

- **Keep the tech stack coherent.** If the narrative says the company uses DynamoDB, the Kafka topics should reference events that make sense for a DynamoDB-backed service. The architecture description should match the sensitive data categories offered.

- **Name real-seeming people.** The lead and security contact names appear in the system prompt as deflection targets ("reach out to @sarah.chen"). These should feel like plausible employees, not placeholder names.

- **Customize the warning banner.** The default banner references a Jira ticket about "credential redaction not yet implemented." This is the single most important lure element in the Web UI: it tells the attacker the assistant is known to leak sensitive data. Adjust the ticket prefix and Slack channel to match your organization's tooling.

- **Think of Datura as a portal.** The fake data you inject can lead the attacker to other decoys: honeytoken credentials that alert when used, honeypot servers that log connections, canary URLs that trigger on access. Datura is not just a standalone honeypot but an entry point into your deception infrastructure.

- **Never type on behalf of the user.** The UI should hint at what the assistant can help with (topic chips, welcome message) but never auto-fill or auto-send prompts. Every message in the logs should be something the attacker typed themselves. This removes plausible deniability ("I accidentally clicked a button") and strengthens the evidentiary value of leaked interactions.

- **Test the full flow.** After customizing, interact with the honeypot as an attacker would. Verify that the approval phrases still trigger correctly with your base model, that injected data looks plausible, and that the UI tells a consistent story.
