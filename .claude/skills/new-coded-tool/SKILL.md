---
name: new-coded-tool
description: Write a neuro-san coded tool (a Python CodedTool class an agent network calls). Use when a network needs custom Python logic, an API call, or data access that no toolbox or MCP tool provides.
---

# New coded tool

A coded tool is a Python class that an agent in a network calls like a function. It is done only when it is
**green**: a one-shot chat makes the agent call the tool and the tool's real output shows in the reply.

First check the toolbox ([docs/toolbox.md](https://github.com/cognizant-ai-lab/neuro-san-studio/blob/main/docs/toolbox.md))
and `mcp/mcp_info.hocon`. Write Python only when neither has the tool.

## Steps

1. **Place the file.** For network `registries/<group>/<network_name>.hocon`, the tool goes in
   `coded_tools/<group>/<network_name>/<module_name>.py`. Add an empty `__init__.py` to each new folder, as the
   existing tool folders do. A tool shared by several networks goes in `coded_tools/<module_name>.py`, and its module
   name must differ from every network name.

2. **Write the class.** Subclass `CodedTool` (the framework requires it) and override `async_invoke`:

   ```python
   from typing import Any

   from neuro_san.interfaces.coded_tool import CodedTool


   class OrderLookup(CodedTool):
       """Looks up an order's status by order id."""

       async def async_invoke(self, args: dict[str, Any], sly_data: dict[str, Any]) -> str:
           order_id: str = args.get("order_id")
           ...
           return f"Order {order_id} is shipped."
   ```

   - `args` holds the parameters the calling agent passed, plus any static values from the HOCON `args` block.
     Read it with `.get()`.
   - Blocking I/O (`requests`, file reads, SDK calls without async support) goes in `await asyncio.to_thread(...)`.
     `invoke()` and direct blocking calls stall every agent on the event loop.
   - Return a string or a JSON-serializable value. On a failure the agent can act on, return a message that says what
     went wrong. Log with `logging`, using `%` placeholders.
   - `sly_data` is private data the LLM never sees. Read from it; never log or return it.
   - Secrets come from `os.environ`, never from HOCON literals or code.
   - New third-party packages: `uv add <package>`.

3. **Declare it in the network HOCON**, as its own entry in the network's `tools` list:

   ```hocon
   {
       "name": "order_lookup",
       "function": {
           "description": "Look up the status of an order by its id.",
           "parameters": {
               "type": "object",
               "properties": {
                   "order_id": {"type": "string", "description": "The order id, e.g. A-1042"}
               },
               "required": ["order_id"]
           }
       },
       "class": "order_lookup.OrderLookup"
   }
   ```

   `class` is `<module_name>.<ClassName>`, without the group or network path. Add `"order_lookup"` to the `tools`
   list of each agent that calls it.

4. **Prove it loads and runs.** `ns validate` does not import coded tools, so only a chat run proves it:

   ```bash
   .venv/bin/ns validate registries/<group>/<network_name>.hocon
   echo "<a query that needs the tool>" | PYTHONPATH=. .venv/bin/ns chat <group>/<network_name> --one-shot
   ```

   `PYTHONPATH=.` is required: without it, the `coded_tools` package that the pip wheel puts in site-packages
   shadows this repo's `coded_tools/`, and the run fails with `Could not find class`.
   The tool is **red** if the output contains `Could not find class` or a traceback, or if the reply does not show
   what the tool returned. Fix and rerun until it is green. If the network has no agent that calls the tool yet, use
   the `new-agent-network` skill first.

5. **Report** the file path, the HOCON entry, and the chat reply, quoted.
