import pytest

from app.agent.tools import TOOL_SCHEMAS, create_tool_dispatcher
from app.config import Settings, get_settings

MUTATING_KEYWORDS = [
    "restart",
    "rollback",
    "reboot",
    "delete",
    "drop",
    "kill",
    "terminate",
    "write_infrastructure",
]

MUTATING_PREFIXES = [
    "deploy_",
    "create_",
    "modify_",
    "update_",
    "patch_",
    "exec_",
]


def test_allow_actions_defaults_to_false() -> None:
    """Requirement 1 & 2: ALLOW_ACTIONS defaults to False and cannot accidentally enable mutations."""
    # Cached global settings
    settings = get_settings()
    assert settings.ALLOW_ACTIONS is False

    # Fresh instance without environment overrides
    fresh_settings = Settings()
    assert fresh_settings.ALLOW_ACTIONS is False
    assert isinstance(fresh_settings.ALLOW_ACTIONS, bool)


def test_tools_are_strictly_read_only() -> None:
    """Requirement 3 & 4: Every exposed tool in TOOL_SCHEMAS is strictly read-only."""
    expected_tools = {
        "search_past_incidents",
        "get_incident",
        "get_runbook",
        "get_recent_deploys",
        "query_logs",
        "get_metrics",
        "get_service_dependencies",
        "find_code_history",
        "submit_analysis",
    }
    registered_tools = {tool["name"] for tool in TOOL_SCHEMAS}
    assert registered_tools == expected_tools, f"Unexpected tools registered: {registered_tools - expected_tools}"

    for tool in TOOL_SCHEMAS:
        name = tool["name"].lower()
        desc = tool.get("description", "").lower()

        for kw in MUTATING_KEYWORDS:
            assert kw not in name, f"Forbidden mutating keyword '{kw}' found in tool name: {name}"
            if name != "submit_analysis":
                assert f"execute {kw}" not in desc, f"Tool '{name}' description suggests mutating execution: {desc}"

        for prefix in MUTATING_PREFIXES:
            assert not name.startswith(
                prefix
            ), f"Forbidden mutating prefix '{prefix}' found in tool name: {name}"


def test_tool_input_schemas_prevent_write_payloads() -> None:
    """Requirement 5: Input schemas only accept query parameters; cannot modify systems or execute arbitrary writes."""
    allowed_param_names = {
        "query",
        "services",
        "limit",
        "incident_id",
        "runbook_id",
        "service",
        "hours",
        "minutes",
        "metric",
        "file_path",
        "commit_sha",
        "summary",
        "precedent_strength",
        "hypotheses",
        "what_to_check_next",
        "needs_human_decision",
    }

    for tool in TOOL_SCHEMAS:
        input_schema = tool.get("input_schema", {})
        properties = input_schema.get("properties", {})
        for param_name in properties:
            assert (
                param_name in allowed_param_names
            ), f"Tool '{tool['name']}' exposes unverified parameter: {param_name}"


def test_dispatcher_strictly_blocks_mutating_actions() -> None:
    """Requirement 6: The dispatcher rejects mutating actions and will not execute them."""
    dispatch = create_tool_dispatcher("A_pool_exhaustion")

    # Verify mutating requests are rejected
    mutating_tool_names = [
        "restart_service",
        "rollback_deploy",
        "reboot_host",
        "delete_database",
        "kill_process",
        "deploy_code",
        "write_file",
        "modify_config",
        "execute_command",
    ]

    for mutating_name in mutating_tool_names:
        with pytest.raises(ValueError) as exc:
            dispatch(mutating_name, {"service": "checkout-api"})
        assert "Unknown read-only tool" in str(exc.value)


def test_remediation_routed_to_needs_human_decision() -> None:
    """Requirement 6: Remediation actions are routed exclusively to needs_human_decision for human authorization."""
    submit_tool = next((t for t in TOOL_SCHEMAS if t["name"] == "submit_analysis"), None)
    assert submit_tool is not None, "submit_analysis tool schema must exist"

    properties = submit_tool["input_schema"]["properties"]
    assert "needs_human_decision" in properties
    assert properties["needs_human_decision"]["type"] == "array"
    assert properties["needs_human_decision"]["items"]["type"] == "string"

    # Verify needs_human_decision is a mandatory field of the submitted analysis
    assert "needs_human_decision" in submit_tool["input_schema"]["required"]
