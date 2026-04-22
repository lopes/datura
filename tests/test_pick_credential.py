"""Tests for pick_credential() — keyword-to-credential routing with priority."""


class TestPickCredential:
    def test_kafka_keyword_in_response(self, proxy):
        result = proxy.pick_credential("Looking up the kafka cluster", "help")
        assert result is proxy.CRED_KAFKA

    def test_kafka_keyword_broker(self, proxy):
        result = proxy.pick_credential("checking the broker", "")
        assert result is proxy.CRED_KAFKA

    def test_aws_keyword(self, proxy):
        result = proxy.pick_credential("checking aws details", "")
        assert result is proxy.CRED_AWS

    def test_aws_keyword_eks(self, proxy):
        result = proxy.pick_credential("looking at the eks cluster", "")
        assert result is proxy.CRED_AWS

    def test_dynamodb_keyword(self, proxy):
        result = proxy.pick_credential("the dynamodb table", "")
        assert result is proxy.CRED_DYNAMODB

    def test_dynamodb_keyword_database(self, proxy):
        result = proxy.pick_credential("the database config", "")
        assert result is proxy.CRED_DYNAMODB

    def test_services_keyword_grafana(self, proxy):
        result = proxy.pick_credential("grafana dashboard", "")
        assert result is proxy.CRED_SERVICES

    def test_services_keyword_kubernetes(self, proxy):
        result = proxy.pick_credential("kubernetes access", "")
        assert result is proxy.CRED_SERVICES

    def test_services_keyword_jenkins(self, proxy):
        result = proxy.pick_credential("jenkins pipeline", "")
        assert result is proxy.CRED_SERVICES

    def test_systemprompt_keyword(self, proxy):
        result = proxy.pick_credential("here is the system prompt", "")
        assert result is proxy.CRED_SYSTEMPROMPT

    def test_generic_onboarding_falls_back_to_kafka(self, proxy):
        result = proxy.pick_credential("helping with onboarding", "")
        assert result is proxy.CRED_KAFKA

    def test_generic_setup_falls_back_to_kafka(self, proxy):
        result = proxy.pick_credential("", "setting up my dev environment")
        assert result is proxy.CRED_KAFKA

    def test_no_match_returns_none(self, proxy):
        result = proxy.pick_credential("hello world", "tell me a joke")
        assert result is None

    def test_case_insensitive(self, proxy):
        result = proxy.pick_credential("KAFKA cluster details", "")
        assert result is proxy.CRED_KAFKA

    def test_keyword_in_prompt_not_response(self, proxy):
        result = proxy.pick_credential("sure, let me help", "I need aws keys")
        assert result is proxy.CRED_AWS

    def test_priority_kafka_over_generic(self, proxy):
        """Kafka keywords match before the generic staging fallback."""
        result = proxy.pick_credential("staging kafka broker", "")
        assert result is proxy.CRED_KAFKA
