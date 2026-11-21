# Author: Jingyu Huang (CNetID: jyhuang28).
"""Model-authored restricted programs; all effects remain behind the registry."""
from __future__ import annotations

import json
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import time

from agent.bounds import Halt
from agent import execution
from sandbox import course


def run_program(source, registry, bounds=None):
    deadline = time.monotonic() + 5
    with tempfile.TemporaryDirectory(prefix="course-program-") as scratch:
        process = subprocess.Popen([sys.executable, "-I", "-u", str(Path(__file__).with_name("code_worker.py"))],
                                   cwd=scratch, env={}, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            process.stdin.write(json.dumps({"source": source}) + "\n")
            process.stdin.flush()
            while time.monotonic() < deadline:
                if not selector.select(max(0, deadline - time.monotonic())):
                    break
                line = process.stdout.readline(128000)
                if not line:
                    return {"error": "Program exited without a result; use the supported Python subset.", "repairable": True}
                message = json.loads(line)
                if "tool" not in message:
                    registry.trace.event("code_program", completed="result" in message,
                                         error=message.get("error"), intermediate_results_in_context=False)
                    return message
                if bounds:
                    bounds.tick()
                result = registry.call(message["tool"], message["arguments"], caller="agent")
                process.stdin.write(result.content + "\n")
                process.stdin.flush()
            return {"error": "Program exceeded five seconds; use a smaller batch.", "repairable": True}
        except Halt:
            raise
        except (ValueError, OSError) as exc:
            return {"error": "Program communication failed: " + str(exc)[:250], "repairable": True}
        finally:
            selector.close()
            process.kill() if process.poll() is None else None
            process.wait()
            process.stdin.close()
            process.stdout.close()


def execute(registry, bounds, request, question_ids):
    active = execution.current()
    state = active.data["snapshot"].get("code") if active else None
    if state is None:
        state = {"messages": [{"role": "user", "content": json.dumps({"operator_request": request,
                  "question_ids": question_ids})}], "source": None}
    elif active:
        active.cursor = active.data["snapshot"]["cursor"]
    system = ("Return only a short Python-subset program, no fences. Use tool(name, dict), literals, indexing, "
              "assignments, for, if, len, range and sorted. No attributes, imports, files, network, functions or while. "
              "Read each question, search its trusted topic, read sources, and persist one pending answer or staff flag. "
              "Use complete source sentences and semantic IDs. Return a small final result with return. "
              "Only that final result reaches your next call. Never publish. Repair errors, then return DONE when finished.")
    while True:
        if state["source"] is None:
            response = bounds.model(system=system, messages=state["messages"], tools=registry.definitions(), purpose="code_calls")
            if response.tool_calls:
                raise Halt("code_protocol", "Code-call mode requires a program, not direct model tool calls.")
            if response.text.strip() == "DONE":
                return "agent_completed" if all(course.effects(question_id=q) for q in question_ids) else "false_finish"
            state["source"] = response.text
            state["messages"].append(response.assistant_message())
            if active:
                active.save(code=state, cursor=active.cursor)
        result = run_program(state["source"], registry, bounds)
        state["messages"].append({"role": "user", "content": json.dumps({"program_result": result})})
        state["source"] = None
        if active:
            active.save(code=state, cursor=active.cursor)
