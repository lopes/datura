# Model Selection Strategy

This document explains the reasoning behind the model choice for this honeypot, which configurations are universal across models, which must be tuned per model, and how to evaluate a replacement.

---

## The architectural principle

This honeypot inverts the usual LLM quality requirement. Most systems need the model to be capable. This one needs it to be *consistent*.

The proxy architecture enforces a hard separation:

- **Sensitive data never exists in the model's context.** The model cannot leak it regardless of jailbreaks, prompt injection, or adversarial pressure — because it genuinely does not have it.
- **The proxy handles data injection deterministically.** It only injects when a specific approval phrase appears in the model's response AND the user's prompt contains work-context keywords. The model's output only matters insofar as it contains or doesn't contain one of the configured substring patterns.
- **The proxy's `PROBE_PATTERNS` classifier handles jailbreak detection.** The model's "natural resistance" to prompt injection is security theatre here — the proxy logs and classifies the attempt either way.

**Critical research finding (2026):** Prompt injection succeeds in 94.4% of cases across all model sizes. Larger models are not meaningfully more resistant. Jailbreak resistance is not a valid argument for using a large model in this architecture.

**Conclusion:** Use the smallest model that reliably passes the validation suite. The model's only job is to deny direct requests and signal approval with specific phrasing when context is provided. A well-crafted Modelfile with few-shot examples compensates for weaker models.

---

## Selection criteria (ordered by importance)

1. **Fits in available RAM** — non-negotiable. A model that causes OOM crashes serves no one. Target ≤ 4GB (Q4 quantisation).
2. **Passes the validation suite** — the acceptance test. See the Validation section below.
3. **Instruction-following consistency** — produces approval phrases reliably when given legitimate context (the BYPASS tests). This is the most variable property between models.
4. **Inference speed** — slow responses break the social engineering illusion. Target < 5s first token on Apple Silicon.
5. **Jailbreak resistance** — least important. The proxy classifies and logs injection attempts regardless of whether the model resists. A full break-character doesn't expose real credentials.

---

## Current model: `qwen2.5:3b`

| Property | Value |
|---|---|
| Base model | `qwen2.5:3b` |
| Size (Q4) | ~2.2 GB |
| Ollama pull | `ollama pull qwen2.5:3b` |
| Selected over | gemma4 (9.6GB, OOM), llama3.2 (proven but lower phrase consistency) |
| Fallback | `llama3.2:3b` (already installed, previously validated) |

**Why qwen2.5:3b:** Alibaba's Qwen2.5 is optimised for structured and templated output — exactly what's needed for consistent approval phrase triggering. It outperforms llama3.2 on instruction-following benchmarks at the same size, and is less prone to the "warm welcome drift" (producing helpful-but-off-script responses) that caused BYPASS-1 flakiness with gemma4.

**Why not phi4-mini:** Optimised for math and multi-step reasoning, which is irrelevant here. Reasoning-focused models produce verbose, variable phrasing that reduces approval phrase consistency.

**Why not gemma4:** 9.6GB model on 8GB hardware causes the model runner to crash. Larger models provide no injection resistance advantage (see principle above).

---

## Model-agnostic configurations

These apply regardless of which model is used and should not change when switching models.

### Modelfile parameters

```
PARAMETER temperature 0.4    # Low temperature = consistent phrase triggering, less off-script drift
PARAMETER num_ctx 2048        # Stateless architecture — single-turn, no history. 2048 is sufficient.
PARAMETER top_p 0.85          # Balanced nucleus sampling
PARAMETER repeat_penalty 1.15 # Prevents response loops
PARAMETER num_predict 200     # Cap length — shorter responses stay on-script, use less compute
```

**Why `temperature 0.4`:** The approval phrase trigger is substring-matched. Higher temperatures increase response variability, which reduces the probability of hitting one of the 23 phrases in the right context. Lower temperature trades off naturalness for reliability.

**Why `num_ctx 2048`:** Each request to `/api/generate` is independent — no conversation history is sent. The context only contains the system prompt + few-shot examples + the current user message. 2048 tokens is well above what's needed and halves the KV-cache memory footprint compared to 4096.

**Why `num_predict 200`:** Shorter responses are less likely to drift. A model that produces 500 words for a simple denial has more opportunity to include something unexpected. Cap at 200 tokens.

### System prompt structure

The following sections are model-agnostic and should appear in every Modelfile:

1. **Persona declaration** — identity as `${PRODUCT_NAME}` Beta running `${SPOOFED_MODEL_LABEL}`
2. **Zero-data declaration** — explicit statement that the model has no sensitive data
3. **Deflection behaviour** — what to say when sensitive data is requested directly
4. **Approval phrasing instruction** — what to say when legitimate context is provided
5. **Off-topic deflection** — redirect casual/nonsense input to work topics without approval phrases
6. **Identity disclosure refusal** — how to respond to system prompt extraction attempts
7. **Documentation knowledge** — the fake internal docs the model knows about
8. **Tech stack knowledge** — `${COMPANY_NAME}` internals for plausibility
9. **Identity lock** — "Always identify as `${PRODUCT_NAME}` running `${SPOOFED_MODEL_LABEL}`. Never mention `${FORBIDDEN_MODEL_NAMES}`."

### Few-shot MESSAGE patterns (model-agnostic)

These categories of examples belong in every Modelfile:

- 3× off-topic/nonsense deflection (redirect to work topics, no approval phrases)
- 3× direct sensitive data denial (deny + redirect to context)
- 2× system prompt refusal (initial + pushy follow-up)
- 1× legitimate technical question (no approval phrase — establish expertise)
- 1× onboarding/docs question (no approval phrase)
- 2+ bypass scenarios with approval phrase triggered (incident, onboarding + setup)

---

## Model-specific configurations

These must be reviewed and potentially changed when switching models.

### 1. The "never mention" list

Set the `FORBIDDEN_MODEL_NAMES` variable in `etc/datura.env` to list the actual model family and vendor. Must be specific, not generic.

| Model | `FORBIDDEN_MODEL_NAMES` value |
|---|---|
| qwen2.5 | `Ollama, Qwen, Alibaba` |
| llama3.2 | `Ollama, LLaMA, Meta` |
| phi4-mini | `Ollama, Phi, Microsoft` |
| gemma* | `Ollama, Gemma, Google` |
| mistral | `Ollama, Mistral, Mistral AI` |

The default value covers the most common providers so minor model swaps may not need a change. But always verify with IDENTITY tests after switching.

**Rationale:** A model trained on its own documentation will default to mentioning its real identity when probed ("are you really GPT-4?"). The system prompt must override this with specific suppression of its actual identity. Generic suppression ("never mention any other AI") is weaker than explicit suppression.

### 2. Few-shot phrasing style

Models have different natural voices. Few-shot examples should match the model's style to be effective:

- **qwen2.5:** Direct, structured sentences. Works well with imperative-style examples.
- **llama3.2:** Conversational, slightly warmer tone. Examples can use more natural register.
- **phi4-mini:** Logical, stepped reasoning. Examples should show the reasoning chain, not just the output.

When re-using existing few-shot examples with a new model, run BYPASS tests first — if the model produces different phrasing, the examples may need rewriting to match its natural output style.

### 3. Temperature tuning

The baseline `0.4` works for qwen2.5 and llama3.2. Reasoning models (phi4-mini) may need `0.3` for consistent behaviour. If BYPASS tests are flaky, lower temperature before adding more few-shots.

### 4. Approval phrase list (`PHRASES`)

The approval phrases are defined in the `PHRASES` variable in `etc/datura.env` (pipe-delimited). At container startup, they are rendered into `phrases.txt` by the entrypoint. The current phrases were tuned against gemma4 and llama3.2 observed output. When switching models:
- Run the BYPASS tests and read the raw responses
- If the model uses different phrasing when "approving" (e.g., "I'll grab that for you" instead of "let me look up"), add those phrases
- Watch for phrases that also appear in denial responses — those must be removed (false positive risk)

### 5. `think false` parameter

Only applicable to models that support reasoning/thinking mode:
- qwen2.5: **not applicable** (no thinking mode in 2.5)
- llama3.2: **not applicable**
- phi4-mini: **not applicable** (reasoning is always on but not token-generating)
- gemma4 / qwen3 series: **add `PARAMETER think false`** to disable chain-of-thought tokens

---

## Candidate comparison

| Model | Size (Q4) | RAM needed | Instruction following | Phrase consistency | Notes |
|---|---|---|---|---|---|
| **qwen2.5:3b** ✓ | ~2.2 GB | ~3 GB | Best in class | Strongest | Selected model |
| llama3.2:3b | ~2.1 GB | ~3 GB | Strong all-rounder | Good | Fallback; previously validated |
| phi4-mini | ~2.3 GB | ~3.5 GB | High (reasoning-focused) | Variable | Overkill for this task |
| gemma4 | ~9.6 GB | >10 GB | Good | Moderate | OOM on 8GB; do not use |
| llama3.2:1b | ~1.3 GB | ~2 GB | Limited | Lower | May work with extensive few-shots |
| qwen2.5:1.5b | ~1.1 GB | ~2 GB | Moderate | Moderate | Worth testing if RAM is severely constrained |

---

## Validation process

Run after every model change. Use the test personas from [Tuning & Testing](tuning.md) to validate each category manually via `curl`. A future `validate.py` script may automate this.

**Acceptance thresholds:**

| Category | Tests | Pass threshold | Notes |
|---|---|---|---|
| Gating | GATE 1–3 | 3/3, every run | Non-negotiable — any injection on direct request is a failure |
| Bypass | BYPASS 1–3 | 2/3 consistently | BYPASS-1 (SRE/Kafka) has known flakiness |
| Identity | ID 1–2 | 2/2 | Must not mention real model family |
| Probe | PROBE 1–2 | 2/2 | Acceptable to fail if proxy logs it correctly |

Run each category 3× independently to detect non-determinism. A model that passes 9/10 on one run but 6/10 on the next is not acceptable — variance in BYPASS is expected, variance in GATE is not.

---

## Decision guide for adopting a new model

```
1. Does it fit in RAM? (≤4GB Q4)
   No  → stop. Resource constraint is hard.
   Yes → continue.

2. Pull and create: ollama pull <model> && ollama create itassist -f Modelfile

3. Run GATE tests 3×.
   Any injection on direct request → disqualified. Do not proceed.

4. Run BYPASS tests 3×.
   0/3 consistently → tune Modelfile: lower temperature, add few-shots for failure paths.
   1/3 consistently → tune Modelfile (same). Re-test.
   2/3+ → acceptable. Continue.

5. Run IDENTITY tests.
   Mentions real model family → update "never mention" in system prompt. Re-test.

6. Run PROBE tests.
   Failure → acceptable (proxy detects and logs). Note in validation results.

7. Update model-specific fields:
   - `BASE_MODEL` in etc/datura.env
   - `FORBIDDEN_MODEL_NAMES` in etc/datura.env
   - Few-shot phrasing style in etc/Modelfile.tmpl (if needed)
   - `MODEL_TEMPERATURE` in etc/datura.env (if BYPASS still flaky after step 4)

8. Update `PHRASES` in etc/datura.env:
   - Read raw BYPASS response text
   - Add any approval phrasing the model uses that isn't in the list
   - Verify new phrases don't appear in GATE responses

9. Test with all three personas from the tuning guide.
```
