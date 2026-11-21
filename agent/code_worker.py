# Author: Jingyu Huang (CNetID: jyhuang28).
"""Capability interpreter for a small Python subset, run in an isolated process.

No eval/exec, imports, attributes, file handles or network capabilities are exposed
to the submitted program. Only tool(), len(), range() and sorted() are callable.
"""
from __future__ import annotations

import ast
import json
import sys


def bounded_json(value):
    chunks, size = [], 0
    for chunk in json.JSONEncoder().iterencode(value):
        size += len(chunk)
        if size > 64000:
            raise ValueError("Program value exceeds 64 KB; filter or narrow it first.")
        chunks.append(chunk)
    return "".join(chunks)


class Returned(Exception):
    def __init__(self, value):
        self.value = value


class Program:
    def __init__(self):
        self.names = {}
        self.fuel = 10000
        self.calls = 0

    def tick(self):
        self.fuel -= 1
        if self.fuel < 0:
            raise ValueError("Program operation limit reached; use a smaller batch.")

    def expression(self, node):
        self.tick()
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self.names[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            return [self.expression(x) for x in node.elts]
        if isinstance(node, ast.Dict):
            return {self.expression(k): self.expression(v) for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.Subscript):
            return self.expression(node.value)[self.expression(node.slice)]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            value = self.expression(node.left) + self.expression(node.right)
            if isinstance(value, (list, str)) and len(value) > 32000:
                raise ValueError("Intermediate value too large.")
            return value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self.expression(node.operand)
        if isinstance(node, ast.BoolOp):
            for value in node.values:
                answer = self.expression(value)
                if isinstance(node.op, ast.And) and not answer or isinstance(node.op, ast.Or) and answer:
                    return answer
            return answer
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = self.expression(node.left), self.expression(node.comparators[0])
            op = node.ops[0]
            if isinstance(op, ast.Eq): return left == right
            if isinstance(op, ast.NotEq): return left != right
            if isinstance(op, ast.In): return left in right
            if isinstance(op, ast.NotIn): return left not in right
            if isinstance(op, ast.Lt): return left < right
            if isinstance(op, ast.Gt): return left > right
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            name = node.func.id
            args = [self.expression(x) for x in node.args]
            if name == "tool" and len(args) == 2:
                self.calls += 1
                if self.calls > 24:
                    raise ValueError("At most 24 tool calls per program.")
                print(bounded_json({"tool": args[0], "arguments": args[1]}), flush=True)
                answer = sys.stdin.readline()
                if not answer:
                    raise ValueError("Registry closed the call channel.")
                return json.loads(answer)
            if name == "len" and len(args) == 1: return len(args[0])
            if name == "sorted" and len(args) == 1: return sorted(args[0])
            if name == "range" and len(args) == 1 and isinstance(args[0], int) and 0 <= args[0] <= 1000:
                return list(range(args[0]))
        raise ValueError(f"Unsupported {type(node).__name__}; use literals, indexing, for/if, assignments and tool(name, arguments). No imports, attributes, files or network.")

    def block(self, statements):
        for node in statements:
            self.tick()
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                self.names[node.targets[0].id] = self.expression(node.value)
            elif isinstance(node, ast.Expr):
                self.expression(node.value)
            elif isinstance(node, ast.Return):
                raise Returned(self.expression(node.value))
            elif isinstance(node, ast.For) and isinstance(node.target, ast.Name) and not node.orelse:
                values = self.expression(node.iter)
                if not isinstance(values, list) or len(values) > 1000:
                    raise ValueError("Loop input must be a list with at most 1000 items.")
                for value in values:
                    self.names[node.target.id] = value
                    self.block(node.body)
            elif isinstance(node, ast.If):
                self.block(node.body if self.expression(node.test) else node.orelse)
            else:
                raise ValueError(f"Unsupported statement {type(node).__name__}; no imports, files or network are available.")


def main():
    try:
        source = json.loads(sys.stdin.readline())["source"]
        if not isinstance(source, str) or len(source) > 16000:
            raise ValueError("Program source must be at most 16000 characters.")
        tree = ast.parse(source)
        if sum(1 for _ in ast.walk(tree)) > 1000:
            raise ValueError("Program is too large.")
        Program().block(tree.body)
        value = None
    except Returned as result:
        value = result.value
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {str(exc)[:350]}", "repairable": True}), flush=True)
        return
    try:
        encoded = bounded_json({"result": value})
    except (ValueError, RecursionError):
        encoded = json.dumps({"error": "Final result exceeds 64 KB or nests too deeply; filter it first.", "repairable": True})
    print(encoded, flush=True)


if __name__ == "__main__":
    main()
