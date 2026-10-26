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
  State.DONE: {State.START},
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
  def __init__(self, client:OpenAI):
    self.current = State.START
    self.last = None
    self.client = client
    self.specification = None
    self.plan = None

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
  def transition(self, target: State) -> bool:
    if target not in ALLOWED_TRANSITIONS[self.current]:
      proceed = False
      raise ValueError("Transição inválida: "f"{self.current.value} -> {target.value}")

    self.last = self.current
    self.current = target
    proceed = True
    #return self.current
    return proceed

  def start_to_received(self) -> bool:
    if self.current != State.START:
      return False # o agente já passou por esse estágio e está em outra iteração do loop de execução

    health = self.check_api_health()

    if health != HealthStatus.HEALTHY:
      self.current = State.FAILED
      raise RuntimeError(f"Não foi possível validar a API: {health.value}")

    return self.transition(State.RECEIVED)

  def received_to_specified(self, specification=None) -> bool:
    if self.current != State.RECEIVED:
      return False
    if not specification:
      raise ValueError("Não é possível especificar sem uma especificação válida.")
    self.specification = specification
    return self.transition(State.SPECIFIED)

  def specified_to_planned(self, plan=None) -> bool:
    if self.current != State.SPECIFIED:
      return False
    if not plan:
      raise ValueError("Não é possível planejar sem um plano válido.")
    self.plan = plan
    return self.transition(State.PLANNED)

  def planned_to_implementing(self) -> bool:
    if self.current != State.PLANNED:
      return False

    return self.transition(State.IMPLEMENTING)

  def implementing_to_verifying(self) -> bool:
    if self.current != State.IMPLEMENTING:
      return False
    
    return self.transition(State.VERIFYING)

  def verifying_to_done(self) -> bool:
    if self.current != State.VERIFYING:
      return False
    
    return self.transition(State.DONE)

  def verifying_to_repairing(self) -> bool:
    if self.current != State.VERIFYING:
      return False
    
    return self.transition(State.REPAIRING)

  def repairing_to_verifying(self) -> bool:
    if self.current != State.REPAIRING:
      return False

    return self.transition(State.VERIFYING)

  def to_failed(self) -> bool:
    if self.current == State.FAILED:
      return False

    return self.transition(State.FAILED)

  def done(self):
    if self.current == State.DONE:
      return True
    else:
      return False

  def done_to_start(self) -> bool:
    if self.current != State.DONE:
      return False

    return self.transition(State.START)

  def ask_to_continue(self) -> bool:
    while True:
      response = input("Deseja encerrar a conversa? [S/n] ").strip().lower()
      
      if response in {"", "s", "sim"}:
        return False
      elif response in {"n", "nao", "não"}:
        return True

      print("\nResposta inválida. Digite S ou N: ")