from dataclasses import asdict, dataclass
from statistics import mean
from typing import Iterable


@dataclass
class AgentMetrics:
  success: bool = False
  first_attempt_success: bool = False
  iterations: int = 0
  llm_calls: int = 0
  tool_calls: int = 0
  repair_count: int = 0
  failure_reason: str | None = None

  def as_dict(self):
    return asdict(self)


@dataclass
class EvaluationSummary:
  total_tasks: int
  task_success_rate: float
  first_attempt_success: float
  average_iterations: float
  average_llm_calls: float

  def as_dict(self):
    return asdict(self)


def summarize(runs: Iterable[AgentMetrics]) -> EvaluationSummary:
  results = list(runs)
  if not results:
    raise ValueError("Não é possível calcular métricas sem execuções.")

  return EvaluationSummary(
    total_tasks=len(results),
    task_success_rate=sum(run.success for run in results) / len(results),
    first_attempt_success=sum(run.first_attempt_success for run in results) / len(results),
    average_iterations=mean(run.iterations for run in results),
    average_llm_calls=mean(run.llm_calls for run in results),
  )
