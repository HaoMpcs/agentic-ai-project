# Author: Jingyu Huang (CNetID: jyhuang28).
"""SDK-backed, request-scoped MCP server over in-process memory streams.

Each request constructs a fresh server. No initialize exchange, global server,
connection affinity, Roots, Sampling or Logging capability is used.
"""
from __future__ import annotations

import asyncio
import contextvars
import json
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import anyio
from mcp import types
from mcp.server.lowlevel import Server
from mcp.shared.message import SessionMessage


def request(method, *, definitions, handler, name=None, arguments=None, metadata=None):
    if method not in ("tools/list", "tools/call") or (method == "tools/call" and name not in {d["name"] for d in definitions}):
        return {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Unknown MCP method or tool."}}
    if method == "tools/call" and not isinstance(arguments, dict):
        return {"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "Tool arguments must be an object."}}
    async def exchange():
        server = Server("course-tools")

        @server.list_tools()
        async def listing():
            return [types.Tool(name=d["name"], description=d["description"], inputSchema=d["input_schema"])
                    for d in definitions]

        @server.call_tool(validate_input=False)
        async def calling(tool_name, tool_arguments):
            try:
                data = handler(tool_name, tool_arguments)
                payload, failed = data, False
            except Exception as exc:
                payload = {"error": str(exc)[:450], "exception": type(exc).__name__,
                           "exhausted": getattr(exc, "exhausted", False)}
                failed = True
            return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(payload))],
                                        isError=failed, _meta=metadata or {})

        to_server, incoming = anyio.create_memory_object_stream(1)
        outgoing, from_server = anyio.create_memory_object_stream(1)
        params = {"name": name, "arguments": arguments, "_meta": metadata or {}} if method == "tools/call" else {}
        message = types.JSONRPCRequest(jsonrpc="2.0", id=1, method=method, params=params)
        async with anyio.create_task_group() as group:
            group.start_soon(partial(server.run, incoming, outgoing,
                                     server.create_initialization_options(), stateless=True))
            await to_server.send(SessionMessage(types.JSONRPCMessage(message)))
            with anyio.fail_after(10):
                reply = await from_server.receive()
            group.cancel_scope.cancel()
        for stream in (to_server, incoming, outgoing, from_server):
            await stream.aclose()
        return reply.message.model_dump(by_alias=True, exclude_none=True)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return anyio.run(exchange)
    # The public service is synchronous; also support callers already in a loop.
    context = contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(context.run, anyio.run, exchange).result()


def call(name, arguments, *, key, definitions, handler, metadata):
    envelope = request("tools/call", definitions=definitions, handler=handler, name=name,
                       arguments=arguments, metadata={**metadata, "action_key": key})
    if "error" in envelope:
        raise LookupError("MCP protocol error; choose an offered tool and a valid request.")
    result = envelope["result"]
    data = json.loads(result["content"][0]["text"])
    if result.get("isError"):
        from agent.critique import DraftRejected
        errors = {"ValueError": ValueError, "PermissionError": PermissionError, "LookupError": LookupError,
                  "TimeoutError": TimeoutError, "ConnectionError": ConnectionError,
                  "BlockingIOError": BlockingIOError, "RuntimeError": RuntimeError}
        if data["exception"] == "DraftRejected":
            raise DraftRejected(data["error"], exhausted=data["exhausted"])
        raise errors.get(data["exception"], RuntimeError)(data["error"])
    return data
