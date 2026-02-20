# ABOUTME: Goal coach agent package; exposes root_agent for adk web/run.
# ABOUTME: Use generate_smart_goal() from goal_coach.agent for API integration.

from goal_coach.agent import generate_smart_goal, root_agent

__all__ = ["generate_smart_goal", "root_agent"]
