"""Offline contract tests: real function bodies, simulated cloud dependencies."""
import ast
import asyncio
import contextlib
import io
import json
import logging
from pathlib import Path
from textwrap import dedent
import unittest
from unittest.mock import AsyncMock, patch
import uuid


class FakeMCPClient:
    def __init__(self, *args, **kwargs):
        self.transport = args

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def list_tools_sync(self):
        return []

    async def call_tool_async(self, *args, **kwargs):
        return {"status": "success", "content": [{"text": "order found"}]}


def load_subject():
    # Avoid importing main.py's AWS clients or making cloud calls during tests.
    tree = ast.parse((Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8"))
    names = {"GatewayError", "SupportGatewayClient", "calculate_loyalty_discount", "invoke"}
    nodes = [node for node in tree.body if getattr(node, "name", None) in names]
    for node in nodes:
        node.decorator_list = []
    logger = logging.getLogger("offline-review-tests")
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    ns = dict(MCPClient=FakeMCPClient, json=json, dedent=dedent, logger=logger,
              REGION="us-east-1", uuid=uuid)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "main.py", "exec"), ns)
    return ns


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_subject()

    def test_calculation_contract_success_and_fallback(self):
        class Interpreter:
            def invoke(inner, action, payload):
                self.assertEqual(action, "executeCode")
                self.assertTrue(payload["clearContext"])
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exec(compile(payload["code"], "calculation", "exec"), {})
                return {"stream": [{"result": {"isError": False, "structuredContent": {
                    "stdout": output.getvalue(), "exitCode": 0}}}]}

        @contextlib.contextmanager
        def session(region):
            yield Interpreter()

        self.ns["code_session"] = session
        calculate = self.ns["calculate_loyalty_discount"]
        normal = json.loads(calculate(4250, "Gold", 150))
        self.assertEqual((normal["points_redeemed"], normal["tier_discount_pct"],
                          normal["final_total"], normal["remaining_points"]), (4000, 10.0, 99.0, 349))
        with patch.object(Interpreter, "invoke", side_effect=TimeoutError("private upstream detail")):
            fallback = json.loads(calculate(4250, "Gold", 150))
        self.assertEqual(set(normal), set(fallback))
        self.assertEqual((fallback["points_redeemed"], fallback["tier_discount_pct"],
                          fallback["final_total"], fallback["remaining_points"]), (0, 10.0, 135.0, 4250))
        for key in normal:
            self.assertIs(type(normal[key]), type(fallback[key]), key)
        with patch.object(Interpreter, "invoke", return_value={"stream": [{"result": {"isError": True}}]}):
            self.assertTrue(json.loads(calculate(4250, "Gold", 150))["fallback"])
        print("NORMAL:", json.dumps(normal))
        print("FALLBACK:", json.dumps(fallback))

    def test_gateway_connection_and_discovery(self):
        cls = self.ns["SupportGatewayClient"]
        for method in ("__enter__", "list_tools_sync"):
            with patch.object(FakeMCPClient, method, side_effect=TimeoutError("secret-token")):
                with self.assertRaises(self.ns["GatewayError"]) as raised:
                    getattr(cls(lambda: None), method)()
                self.assertNotIn("secret-token", str(raised.exception))
                self.assertIn("Gateway", str(raised.exception))

    def test_gateway_tool_failure_and_recovery(self):
        client = self.ns["SupportGatewayClient"](lambda: None)
        for failure in (ConnectionError("secret-token"), TimeoutError("secret-token"), RuntimeError("secret-token")):
            with patch.object(FakeMCPClient, "call_tool_async", new=AsyncMock(side_effect=failure)):
                result = asyncio.run(client.call_tool_async("id", "order-tracker___get_order"))
                self.assertEqual(result["status"], "error")
                self.assertIn("order lookup", result["content"][0]["text"])
                self.assertNotIn("secret-token", str(result))
        with patch.object(FakeMCPClient, "call_tool_async", new=AsyncMock(return_value={"status": "error", "content": [{"text": "secret-token"}]})):
            result = asyncio.run(client.call_tool_async("id", "refund-processor___initiate_refund"))
            self.assertIn("before retrying", result["content"][0]["text"])
            self.assertNotIn("secret-token", str(result))
        self.assertEqual(asyncio.run(client.call_tool_async("id", "order-tracker___get_order"))["status"], "success")

    def test_invoke_controlled_failure_then_responsive(self):
        ns = self.ns
        class Agent:
            def __init__(self, **kwargs):
                self.options = kwargs
            async def invoke_async(self, prompt):
                return "Agent remains responsive."
        class Browser:
            browser = "browser-tool"
            def __init__(self, **kwargs):
                self.options = kwargs
        ns.update(GATEWAY_URL="https://example.invalid/mcp", MEMORY_ID="test", memory_client=object(),
                  MemoryHook=lambda **kwargs: object(), AgentCoreBrowser=Browser,
                  streamable_http_client=lambda url: None, Agent=Agent, model=object(),
                  search_knowledge_base=lambda query: "catalog")
        with patch.object(FakeMCPClient, "__enter__", side_effect=ConnectionError("secret-token")):
            failed = asyncio.run(ns["invoke"]({"prompt": "Track my order"}))
        self.assertEqual(failed["status"], "error")
        self.assertNotIn("secret-token", str(failed))
        recovered = asyncio.run(ns["invoke"]({"prompt": "Track my order"}))
        self.assertEqual(recovered["status"], "ok")
        print("CONTROLLED GATEWAY FAILURE:", json.dumps(failed))
        print("NEXT REQUEST:", json.dumps(recovered))


if __name__ == "__main__":
    unittest.main(verbosity=2)
