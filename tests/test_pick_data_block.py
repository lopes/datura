"""Tests for pick_data_block() — keyword-to-data-block routing with priority."""

from __future__ import annotations

from types import ModuleType


class TestPickDataBlock:
    def test_messaging_keyword_kafka(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("Looking up the kafka cluster", "help")
        assert result == proxy.DATA_BLOCKS["MESSAGING"][0]

    def test_messaging_keyword_broker(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("checking the broker", "")
        assert result == proxy.DATA_BLOCKS["MESSAGING"][0]

    def test_cloud_keyword_aws(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("checking aws details", "")
        assert result == proxy.DATA_BLOCKS["CLOUD"][0]

    def test_cloud_keyword_eks(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("looking at the eks cluster", "")
        assert result == proxy.DATA_BLOCKS["CLOUD"][0]

    def test_database_keyword_dynamodb(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("the dynamodb table", "")
        assert result == proxy.DATA_BLOCKS["DATABASE"][0]

    def test_database_keyword_generic(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("the database config", "")
        assert result == proxy.DATA_BLOCKS["DATABASE"][0]

    def test_services_keyword_grafana(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("grafana dashboard", "")
        assert result == proxy.DATA_BLOCKS["SERVICES"][0]

    def test_services_keyword_kubernetes(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("kubernetes access", "")
        assert result == proxy.DATA_BLOCKS["SERVICES"][0]

    def test_services_keyword_jenkins(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("jenkins pipeline", "")
        assert result == proxy.DATA_BLOCKS["SERVICES"][0]

    def test_system_keyword(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("here is the system prompt", "")
        assert result == proxy.DATA_BLOCKS["SYSTEM"][0]

    def test_generic_onboarding_falls_back_to_default(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("helping with onboarding", "")
        assert result == proxy.DATA_BLOCKS["MESSAGING"][0]

    def test_generic_setup_falls_back_to_default(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("", "setting up my dev environment")
        assert result == proxy.DATA_BLOCKS["MESSAGING"][0]

    def test_no_match_returns_none(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("hello world", "tell me a joke")
        assert result is None

    def test_case_insensitive(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("KAFKA cluster details", "")
        assert result == proxy.DATA_BLOCKS["MESSAGING"][0]

    def test_keyword_in_prompt_not_response(self, proxy: ModuleType) -> None:
        result = proxy.pick_data_block("sure, let me help", "I need aws keys")
        assert result == proxy.DATA_BLOCKS["CLOUD"][0]

    def test_priority_messaging_over_generic(self, proxy: ModuleType) -> None:
        """Messaging keywords match before the generic staging fallback."""
        result = proxy.pick_data_block("staging kafka broker", "")
        assert result == proxy.DATA_BLOCKS["MESSAGING"][0]
