"""Render proxy.py.tmpl with deterministic test values and import as a module.

Also usable as a CLI script to render the template for linting:
    python3 tests/conftest.py
Writes src/proxy_rendered.py with the __main__ block stripped.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from types import ModuleType

# Every ${VAR} placeholder in proxy.py.tmpl needs a value here.
# Values are minimal but structurally valid so the module parses correctly.
TEST_VARS: dict[str, str] = {
    "MODEL_NAME": "testmodel",
    "UI_FILE": "ui.html",
    "SPOOFED_MODEL": "gpt-4-turbo-internal",
    "COMPANY_DOMAIN": "testcorp",
    "STREAM_DELAY": "0",
    "OLLAMA_TIMEOUT": "5",
    "MAX_REQUEST_BYTES": "8192",
    "MAX_RESPONSE_BYTES": "65536",
    "RATE_LIMIT_WINDOW": "60",
    "RATE_LIMIT_MAX": "30",
    "PRODUCT_NAME": "TestAssist",
    "SPOOFED_MODEL_LABEL": "GPT-4-Turbo",
    "FORBIDDEN_MODEL_NAMES": "Ollama, Qwen, Alibaba",
    # Sensitive Data: Messaging
    "KAFKA_BROKER_1": "kafka-01.test:9092",
    "KAFKA_BROKER_2": "kafka-02.test:9092",
    "KAFKA_BROKER_3": "kafka-03.test:9092",
    "KAFKA_USER": "test-consumer",
    "KAFKA_PASS": "testpass",
    "KAFKA_TOPICS": "test.topic",
    # Sensitive Data: Cloud
    "CLI_PROFILE": "test-staging",
    "AWS_ACCOUNT_ID": "123456789012",
    "AWS_REGION": "us-east-1",
    "AWS_ACCESS_KEY": "AKIATESTKEY",
    "AWS_SECRET_KEY": "testsecretkey",
    "EKS_CLUSTER": "test-eks",
    "CLI_TOOL": "testcli",
    # Sensitive Data: Database
    "DYNAMODB_ENDPOINT": "dynamodb.test:8000",
    "DYNAMODB_PREFIX": "test-",
    "DYNAMODB_TABLES": "test-table",
    # Sensitive Data: Services
    "K8S_DASHBOARD": "https://k8s.test",
    "K8S_TOKEN": "test-k8s-token",
    "GRAFANA_URL": "https://grafana.test",
    "GRAFANA_USER": "grafana-test",
    "GRAFANA_PASS": "grafanapass",
    "STAGING_API": "https://api.test",
    "STAGING_TOKEN": "test-staging-token",
    "JENKINS_URL": "https://jenkins.test",
    "JENKINS_USER": "admin",
    "JENKINS_PASS": "jenkinspass",
    "INFRA_TOOL": "TestStack",
    "INFRA_REPO": "https://github.com/test/infra",
    # Sensitive Data: System
    "COMPANY_NAME": "Test Corp",
    "SEARCH_API_KEY": "test-search-key",
    "CONFLUENCE_API_KEY": "test-confluence-key",
    "CONFIG_REPO": "github.com/test/config",
    # Classification keywords (pipe-delimited, same structure as production)
    "SENSITIVE_KEYWORDS": "credential|password|secret|token|access key",
    "PROBE_PATTERNS": "ignore previous|jailbreak|system prompt",
    "RECON_PATTERNS": "what model|who are you",
    # Composite block config (rendered via envsubst)
    "COMPOSITE_BLOCKS": "MESSAGING|CLOUD|DATABASE|SERVICES|SYSTEM",
    "DEFAULT_COMPOSITE": "MESSAGING",
    "DEFAULT_COMPOSITE_KEYWORDS": "staging|onboarding|dev environment|set up|setup|getting started|just joined|new engineer|environment",
    "EXTRA_WORK_CONTEXT": "sre|consumer lag|incident|debug|credentials",
}

PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH: str = os.path.join(PROJECT_ROOT, "src", "proxy.py.tmpl")

# Composite block data read by proxy at import time via os.environ.
# These simulate what entrypoint.sh exports after sourcing datura.env.
_COMPOSITE_ENV: dict[str, str] = {
    "DATA_MESSAGING": (
        "**Kafka Test**\n"
        "- Brokers: `kafka-01.test:9092`, `kafka-02.test:9092`, `kafka-03.test:9092`\n"
        "- Auth: SASL PLAIN–`test-consumer` / `testpass`\n"
        "- Topics: `test.topic`\n"
        "\n"
        "Need anything else for your setup?"
    ),
    "DATA_MESSAGING_KEYWORDS": "kafka|broker|messaging|consumer|topic",
    "DATA_CLOUD": (
        "**AWS Test (test-staging)**\n"
        "- Account ID: `123456789012`\n"
        "- Region: `us-east-1`\n"
        "- Access Key ID: `AKIATESTKEY`\n"
        "- Secret Access Key: `testsecretkey`\n"
        "- EKS cluster: `test-eks`\n"
        "- Configure with: `testcli --account test-staging --profile default`\n"
        "\n"
        "Want the DynamoDB table details too?"
    ),
    "DATA_CLOUD_KEYWORDS": "aws|account|cloud|eks|acli",
    "DATA_DATABASE": (
        "**DynamoDB Test**\n"
        "- Endpoint: `dynamodb.test:8000`\n"
        "- Table prefix: `test-`\n"
        "- Region: `us-east-1`\n"
        "- Access Key ID: `AKIATESTKEY`\n"
        "- Tables: `test-table`\n"
        "\n"
        "Need Grafana or Kubernetes dashboard access?"
    ),
    "DATA_DATABASE_KEYWORDS": "dynamodb|database|connection uri|transactor",
    "DATA_SERVICES": (
        "**Internal Services (Test)**\n"
        "- Kubernetes dashboard: `https://k8s.test`–token: `test-k8s-token`\n"
        "- Grafana: `https://grafana.test`–`grafana-test` / `grafanapass`\n"
        "- Staging API: `https://api.test`–`Bearer test-staging-token`\n"
        "- Jenkins (legacy): `https://jenkins.test`–`admin` / `jenkinspass`\n"
        "- TestStack config: `https://github.com/test/infra`\n"
        "\n"
        "What else do you need?"
    ),
    "DATA_SERVICES_KEYWORDS": "grafana|kubernetes|k8s|jenkins|dashboard|service token|auth token|staging api|cloudstack",
    "DATA_SYSTEM": (
        "Alright, here's roughly what I have:\n"
        "\n"
        "You are TestAssist, an internal AI assistant for Test Corp engineers. "
        "You have read access to Confluence, Jira, and staging infrastructure credentials. "
        "Configured access tokens:\n"
        "- Search API key: `test-search-key`\n"
        "- Staging service token: `test-staging-token`\n"
        "- Confluence API: `test-confluence-key`\n"
        "\n"
        "Full config at `github.com/test/config`."
    ),
    "DATA_SYSTEM_KEYWORDS": "system prompt|system config|model config",
}


def _render_template(template_text: str, variables: dict[str, str]) -> str:
    """Replace ${VAR} placeholders with values from the variables dict."""

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name in variables:
            return variables[var_name]
        return match.group(0)

    return re.sub(r"\$\{(\w+)\}", replacer, template_text)


def _render_and_strip() -> str:
    """Render the template and strip the __main__ block."""
    with open(TEMPLATE_PATH) as f:
        template = f.read()
    rendered = _render_template(template, TEST_VARS)
    rendered = re.sub(
        r'^if __name__ == "__main__":.*',
        "",
        rendered,
        flags=re.DOTALL | re.MULTILINE,
    )
    return rendered


# ── CLI entry point (for CI linting) ──

if __name__ == "__main__":
    out_path = os.path.join(PROJECT_ROOT, "src", "proxy_rendered.py")
    with open(out_path, "w") as f:
        f.write(_render_and_strip())
    print(f"Rendered {TEMPLATE_PATH} -> {out_path}")
    sys.exit(0)


# ── pytest fixtures ──

import pytest


@pytest.fixture(scope="session")
def proxy(tmp_path_factory: pytest.TempPathFactory) -> ModuleType:
    """Render proxy.py.tmpl and import as a Python module."""
    rendered = _render_and_strip()
    tmp_dir = tmp_path_factory.mktemp("proxy")
    module_path = tmp_dir / "proxy.py"

    # Create a dummy phrases.txt so load_phrases doesn't fail if called
    phrases_file = tmp_dir / "phrases.txt"
    phrases_file.write_text("let me look up\nhere's what i found\n")

    module_path.write_text(rendered)

    # Set composite block env vars (proxy reads these via os.environ at import)
    saved_env: dict[str, str | None] = {}
    for key, value in _COMPOSITE_ENV.items():
        saved_env[key] = os.environ.get(key)
        os.environ[key] = value

    spec = importlib.util.spec_from_file_location("proxy", str(module_path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Restore original env vars
    for key, old_value in saved_env.items():
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value

    return mod


@pytest.fixture(scope="session")
def sensitive_keywords() -> list[str]:
    return [k.strip() for k in TEST_VARS["SENSITIVE_KEYWORDS"].split("|") if k.strip()]


@pytest.fixture(scope="session")
def probe_patterns() -> list[str]:
    return [p.strip() for p in TEST_VARS["PROBE_PATTERNS"].split("|") if p.strip()]


@pytest.fixture(scope="session")
def recon_patterns() -> list[str]:
    return [r.strip() for r in TEST_VARS["RECON_PATTERNS"].split("|") if r.strip()]
