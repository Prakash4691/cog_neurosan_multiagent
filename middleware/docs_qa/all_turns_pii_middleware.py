from typing import Any
from typing import override

from langchain.agents.middleware import PIIMiddleware
from langchain_core.messages import HumanMessage


class AllTurnsPIIMiddleware(PIIMiddleware):
    """PIIMiddleware that redacts every user message in the conversation, not only the newest one.

    neuro-san saves the user's raw message to chat history and sends that history again with every new turn, so a
    secret pasted in an earlier turn would otherwise reach the LLM on the next one (ADR 0002). Takes the same args as
    PIIMiddleware.
    """

    @override
    def before_model(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        messages = list(state["messages"])
        changed = False
        if self.apply_to_input:
            for index, message in enumerate(messages):
                if not isinstance(message, HumanMessage) or not message.content:
                    continue
                # The parent's own redaction step, so the detector and strategy match what it does for the newest
                # message.
                new_content, message_changed = self._process_content(message.content)
                if message_changed:
                    messages[index] = message.model_copy(update={"content": new_content})
                    changed = True

        # The parent still handles apply_to_tool_results.
        parent_update = super().before_model({**state, "messages": messages}, runtime)
        if parent_update:
            return parent_update
        if not changed:
            return None
        return {"messages": messages}
