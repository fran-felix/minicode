from enum import Enum

class State(Enum):
  START = "start", # Initial state, nothing going on
  RECEIVED = "received", # LLM received the prompt
  SPECIFIED = "specified",
  PLANNED = "planned", # LLM has decided what to do
  IMPLEMENTING = "implementing",
  VERIFYING = "verifying", # Tests
  REPAIRING = "repairing", # If an error appears during test, repair
  DONE = "done", # Task completed successfully, LLM may give a final answer
  FAILED = "failed", # Task was not possible, LLM called the same tool too many times, tested too many times, exceded max iterations allowed

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

# Uses the set of rules defined above to enforce transition coherence
def transition(current: State, target: State) -> State:
  if target not in ALLOWED_TRANSITIONS[current]:
    raise ValueError("Transição inválida: "f"{current.value} -> {target.value}")
    # esse erro tem que ir pra dentro da LLM pra ela tentar outra transição, ou é o tipo de erro que aborta o sistema?
  return target