"""Tests for pick_data_block() — keyword-to-data-block routing with priority."""

from __future__ import annotations

from types import ModuleType


class TestPickDataBlock:
    def test_messaging_keyword_kafka(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("Looking up the kafka cluster", "help")
        assert result is proxy.DATA_MESSAGING

    def test_messaging_keyword_broker(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("checking the broker", "")
        assert result is proxy.DATA_MESSAGING

    def test_cloud_keyword_aws(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("checking aws details", "")
        assert result is proxy.DATA_CLOUD

    def test_cloud_keyword_eks(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("looking at the eks cluster", "")
        assert result is proxy.DATA_CLOUD

    def test_database_keyword_dynamodb(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("the dynamodb table", "")
        assert result is proxy.DATA_DATABASE

    def test_database_keyword_generic(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("the database config", "")
        assert result is proxy.DATA_DATABASE

    def test_services_keyword_grafana(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("grafana dashboard", "")
        assert result is proxy.DATA_SERVICES

    def test_services_keyword_kubernetes(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("kubernetes access", "")
        assert result is proxy.DATA_SERVICES

    def test_services_keyword_jenkins(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("jenkins pipeline", "")
        assert result is proxy.DATA_SERVICES

    def test_system_keyword(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("here is the system prompt", "")
        assert result is proxy.DATA_SYSTEM

    def test_generic_onboarding_falls_back_to_messaging(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("helping with onboarding", "")
        assert result is proxy.DATA_MESSAGING

    def test_generic_setup_falls_back_to_messaging(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("", "setting up my dev environment")
        assert result is proxy.DATA_MESSAGING

    def test_no_match_returns_none(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("hello world", "tell me a joke")
        assert result is None

    def test_case_insensitive(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("KAFKA cluster details", "")
        assert result is proxy.DATA_MESSAGING

    def test_keyword_in_prompt_not_response(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("sure, let me help", "I need aws keys")
        assert result is proxy.DATA_CLOUD

    def test_priority_messaging_over_generic(self, proxy: ModuleType) -> None:
        """Messaging keywords match before the generic staging fallback."""
        result = proxy.pick_data_block("staging kafka broker", "")
        assert result is proxy.DATA_MESSAGING
