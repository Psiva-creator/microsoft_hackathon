from app.agent.tools import TOOL_SCHEMAS
from app.config import get_settings


def test_allow_actions_is_false():
    settings = get_settings()
    assert settings.ALLOW_ACTIONS is False


def test_tools_are_strictly_read_only():
    # Verify no tool schema allows mutation (restart, delete, rollback, write, execute_action)
    mutating_keywords = [
        "restart",
        "rollback",
        "reboot",
        "delete",
        "drop",
        "kill",
        "terminate",
        "write_infrastructure",
    ]
    for tool in TOOL_SCHEMAS:
        name = tool["name"].lower()
        desc = tool.get("description", "").lower()
        for kw in mutating_keywords:
            assert kw not in name, f"Forbidden mutating tool found: {name}"
            # Verify description does not state mutating action
            if name != "submit_analysis":
                assert f"execute {kw}" not in desc
