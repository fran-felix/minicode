from enum import Enum
from openai import (
  APIConnectionError,
  APIStatusError,
  AuthenticationError,
  OpenAI
)


class State(Enum):
  START = "start" # Initial state, nothing going on
  RECEIVED = "received" # LLM received the prompt
  SPECIFIED = "specified"
  PLANNED = "planned" # LLM has decided what to do
  IMPLEMENTING = "implementing"
  VERIFYING = "verifying" # Tests
  REPAIRING = "repairing" # If an error appears during test, repair
  DONE = "done" # Task completed successfully, LLM may give a final answer
  FAILED = "failed" # Task was not possible, LLM called the same tool too many times, tested too many times, exceded max iterations allowed

# Defines what state transitions are allowed
ALLOWED_TRANSITIONS = {
  State.START: {State.RECEIVED, State.FAILED},
  State.RECEIVED: {State.SPECIFIED, State.FAILED},
  State.SPECIFIED: {State.PLANNED, State.FAILED},
  State.PLANNED: {State.IMPLEMENTING, State.FAILED},
  State.IMPLEMENTING: {State.VERIFYING, State.FAILED},
  State.VERIFYING: {
    State.DONE,
    State.REPAIRING,
    State.FAILED,
  },
  State.REPAIRING: {State.VERIFYING, State.FAILED},
  State.DONE: set(),
  State.FAILED: set(),
}

class HealthStatus(Enum):
  HEALTHY = "healthy"
  UNAUTHORIZED = "unauthorized"
  UNREACHABLE = "unreachable"
  RATE_LIMITED = "rate_limited"
  UNAVAILABLE = "unavailable"


# Responsável por verificar as ações do modelo e decidir se é permitido ou não dar seguimento com a execução
class Validator():
  def __init__(self, client: OpenAI):
    self.current = State.START
    self.client = client

  def check_api_health(self) -> HealthStatus:
    try:
      self.client.models.list()
      return HealthStatus.HEALTHY
    
    except AuthenticationError:
      return HealthStatus.UNAUTHORIZED
    
    except (APIConnectionError, APIStatusError) as error:
      status_code = getattr(error, "status_code", None)
      
      if status_code == 429:
        return HealthStatus.RATE_LIMITED
      elif status_code != None and status_code >= 500:
        return HealthStatus.UNAVAILABLE
      return HealthStatus.UNREACHABLE

  # Usa as regras definidas em ALLOWED_TRANSITIONS para verificar se uma transição e válida ou não
  def transition(self, target: State) -> State:
    if target not in ALLOWED_TRANSITIONS[self.current]:
      raise ValueError("Transição inválida: "f"{self.current.value} -> {target.value}")

    self.current = target
    return self.current

  def start_to_received(self) -> State:
    if self.current != State.START:
      raise RuntimeError(f"Estado atual inválido: {self.current.value}")

    health = self.check_api_health()

    if health != HealthStatus.HEALTHY:
      self.current = State.FAILED
      raise RuntimeError(f"Não foi possível validar a API: {health.value}")

    return self.transition(State.RECEIVED)

  def received_to_specified(self):
    
    return self.transition(State.SPECIFIED)

  def specified_to_planned(self):
    ...



# TODO métodos de validação pra cada transição