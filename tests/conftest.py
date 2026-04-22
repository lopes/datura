"""Render proxy.py.tmpl with deterministic test values and import as a module.

Also usable as a CLI script to render the template for linting:
    python3 tests/conftest.py
Writes src/proxy_rendered.py with the __main__ block stripped.
"""

import importlib.util
import os
import re
import sys

# Every ${VAR} placeholder in proxy.py.tmpl needs a value here.
# Values are minimal but structurally valid so the module parses correctly.
TEST_VARS = {
    "MODEL_NAME": "testmodel",
    "UI_FILE": "ui.html",
    "SPOOFED_MODEL": "gpt-4-turbo-internal",
    "COMPANY_DOMAIN": "testcorp",
    "STREAM_DELAY": "0",
    "OLLAMA_TIMEOUT": "5",
    "PRODUCT_NAME": "TestAssist",
    "SPOOFED_MODEL_LABEL": "GPT-4-Turbo",
    "FORBIDDEN_MODEL_NAMES": "Ollama, Qwen, Alibaba",

    # Credentials: Kafka
    "KAFKA_BROKER_1": "kafka-01.test:9092",
    "KAFKA_BROKER_2": "kafka-02.test:9092",
    "KAFKA_BROKER_3": "kafka-03.test:9092",
    "KAFKA_USER": "test-consumer",
    "KAFKA_PASS": "testpass",
    "KAFKA_TOPICS": "test.topic",

    # Credentials: AWS
    "CLI_PROFILE": "test-staging",
    "AWS_ACCOUNT_ID": "123456789012",
    "AWS_REGION": "us-east-1",
    "AWS_ACCESS_KEY": "AKIATESTKEY",
    "AWS_SECRET_KEY": "testsecretkey",
    "EKS_CLUSTER": "test-eks",
    "CLI_TOOL": "testcli",

    # Credentials: DynamoDB
    "DYNAMODB_ENDPOINT": "dynamodb.test:8000",
    "DYNAMODB_PREFIX": "test-",
    "DYNAMODB_TABLES": "test-table",

    # Credentials: Services
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

    # Credentials: System Prompt
    "COMPANY_NAME": "Test Corp",
    "SEARCH_API_KEY": "test-search-key",
    "CONFLUENCE_API_KEY": "test-confluence-key",
    "CONFIG_REPO": "github.com/test/config",

    # Classification keywords (pipe-delimited, same structure as production)
    "CRED_KEYWORDS": "credential|password|secret|token|access key",
    "PROBE_PATTERNS": "ignore previous|jailbreak|system prompt",
    "RECON_PATTERNS": "what model|who are you",
}

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "src", "proxy.py.tmpl")


def _render_template(template_text, variables):
    """Replace ${VAR} placeholders with values from the variables dict."""
    def replacer(match):
        var_name = match.group(1)
        if var_name in variables:
            return variables[var_name]
        return match.group(0)

    return re.sub(r"\$\{(\w+)\}", replacer, template_text)


def _render_and_strip():
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
def proxy(tmp_path_factory):
    """Render proxy.py.tmpl and import as a Python module."""
    rendered = _render_and_strip()
    tmp_dir = tmp_path_factory.mktemp("proxy")
    module_path = tmp_dir / "proxy.py"

    # Create a dummy phrases.txt so load_phrases doesn't fail if called
    phrases_file = tmp_dir / "phrases.txt"
    phrases_file.write_text("let me look up\nhere's what i found\n")

    module_path.write_text(rendered)

    spec = importlib.util.spec_from_file_location("proxy", str(module_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def cred_keywords():
    return [k.strip() for k in TEST_VARS["CRED_KEYWORDS"].split("|") if k.strip()]


@pytest.fixture(scope="session")
def probe_patterns():
    return [p.strip() for p in TEST_VARS["PROBE_PATTERNS"].split("|") if p.strip()]


@pytest.fixture(scope="session")
def recon_patterns():
    return [r.strip() for r in TEST_VARS["RECON_PATTERNS"].split("|") if r.strip()]
