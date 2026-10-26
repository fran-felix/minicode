# ----- GERADO POR IA (COPILOT) -----

import os
import unittest
from uuid import uuid4
from unittest.mock import patch
from openai import OpenAI
from dotenv import load_dotenv

from minicode.agent import MyAgent
from minicode import main
from minicode.metrics import AgentMetrics, summarize
from minicode.orchestrator.fsm import ALLOWED_TRANSITIONS, State, Validator
from minicode.tools import registry, tools

load_dotenv()


class ToolsTests(unittest.TestCase):
    def test_schema_contains_control_tools(self):
        schema = registry.schema(tools.CODETOOLS)
        names = schema["properties"]["tool"]["enum"]
        self.assertIn("ask_for_information", names)
        self.assertIn("run_command", names)
        self.assertIn("nenhuma", names)
        self.assertIn("answer", names)

    def test_ask_uses_injected_callback(self):
        result = tools.execute(
            action={"tool": "ask_for_information", "arguments": {"question": "qual?"}},
            fs=tools.CODETOOLS,
            ask=lambda question: "resposta",
        )
        self.assertEqual(result, {"resultado": "resposta"})

    def test_side_effect_requires_confirmation(self):
        result = tools.execute(
            {"tool": "run_command", "arguments": {"command": "printf ok"}},
            tools.CODETOOLS,
            confirm=lambda name, args: False,
        )
        self.assertIn("NEGADA", result["erro"])

    def test_run_command_captures_success_and_failure(self):
        success = tools.run_command("printf ok")
        failure = tools.run_command("printf erro >&2; exit 3")
        self.assertEqual(success["codigo_saida"], 0)
        self.assertEqual(success["stdout"], "ok")
        self.assertEqual(failure["codigo_saida"], 3)
        self.assertEqual(failure["stderr"], "erro")

    def test_no_action_is_returned_as_observation(self):
        result = tools.execute(
            {"tool": "nenhuma", "arguments": {"reason": "indisponível"}},
            tools.CODETOOLS,
        )
        self.assertEqual(result, {"resultado": {"motivo": "indisponível"}})


class FsmTests(unittest.TestCase):
    def test_repair_cycle_and_failure_are_allowed(self):
        self.assertIn(State.REPAIRING, ALLOWED_TRANSITIONS[State.VERIFYING])
        self.assertIn(State.VERIFYING, ALLOWED_TRANSITIONS[State.REPAIRING])
        self.assertIn(State.FAILED, ALLOWED_TRANSITIONS[State.IMPLEMENTING])
        self.assertNotIn(State.START, ALLOWED_TRANSITIONS[State.FAILED])

    def test_validator_can_enter_failed(self):
        validator = Validator(OpenAI(api_key="test-key"))
        validator.current = State.REPAIRING
        self.assertTrue(validator.to_failed())
        self.assertEqual(validator.current, State.FAILED)


class MetricsTests(unittest.TestCase):
    def test_summary_calculates_task_metrics(self):
        summary = summarize([
            AgentMetrics(success=True, first_attempt_success=True, iterations=4, llm_calls=3),
            AgentMetrics(success=False, iterations=8, llm_calls=6, repair_count=1),
        ])
        self.assertEqual(summary.total_tasks, 2)
        self.assertEqual(summary.task_success_rate, 0.5)
        self.assertEqual(summary.first_attempt_success, 0.5)
        self.assertEqual(summary.average_iterations, 6)
        self.assertEqual(summary.average_llm_calls, 4.5)

    def test_summary_rejects_empty_evaluation(self):
        with self.assertRaises(ValueError):
            summarize([])


class AgentPipelineTests(unittest.TestCase):
    runs = []

    @unittest.skipUnless(
        os.getenv("RUN_MINICODE_INTEGRATION") == "1"
        and os.getenv("MINICODE_URL")
        and os.getenv("MINICODE_KEY"),
        "testes de integração exigem RUN_MINICODE_INTEGRATION=1, MINICODE_URL e MINICODE_KEY",
    )
    def run_agent(self, task, cleanup=()):
        client = OpenAI(base_url=main.url, api_key=main.key)
        validator = Validator(client)
        agent = MyAgent(main.model, client, validator)
        try:
            with patch("builtins.input", side_effect=[task, "s"]):
                metrics = agent.agent(
                    task=None,
                    available_tools=tools.CODETOOLS,
                    confirm=lambda name, args: True,
                    ask=lambda question: "informação fornecida",
                    max_steps=12,
                    verbose=False,
                )
        finally:
            for file_name in cleanup:
                file_path = os.path.join(tools.PATH_CODE, file_name)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
        self.runs.append(metrics)
        print(f"\nMétricas da tarefa: {metrics.as_dict()}")
        return validator, metrics

    @classmethod
    def tearDownClass(cls):
        if cls.runs:
            print(f"\nMétricas agregadas: {summarize(cls.runs).as_dict()}")

    def test_successful_implementation_reaches_done_and_returns_to_start(self):
        file_name = f"integration_success_{uuid4().hex}.py"
        validator, metrics = self.run_agent(
            f"Crie um arquivo {file_name} contendo uma função hello que retorna 'ok'. "
            "Execute um teste simples para verificar o arquivo."
            , cleanup=(file_name,)
        )
        self.assertEqual(validator.current, State.START)
        self.assertTrue(metrics.success)

    def test_agent_can_request_additional_information(self):
        file_name = f"integration_information_{uuid4().hex}.py"
        validator, metrics = self.run_agent(
            f"Crie um arquivo {file_name} com uma função cujo nome e comportamento "
            "devem ser perguntados ao usuário antes da implementação."
            , cleanup=(file_name,)
        )
        self.assertEqual(validator.current, State.START)
        self.assertTrue(metrics.success)

    def test_failed_verification_enters_repair_and_verifies_again(self):
        file_name = f"integration_repair_{uuid4().hex}.py"
        validator, metrics = self.run_agent(
            f"Crie um arquivo {file_name} com um teste inicialmente falhando, "
            "execute o teste, corrija o erro e execute-o novamente."
            , cleanup=(file_name,)
        )
        self.assertEqual(validator.current, State.START)
        self.assertTrue(metrics.success)

    def test_no_action_reaches_failed(self):
        self.skipTest("cenário depende de o modelo reconhecer uma ação sem ferramenta")


if __name__ == "__main__":
    unittest.main()
