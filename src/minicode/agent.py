from openai import OpenAI
import json, re, inspect

from minicode.orchestrator import fsm
# requests
# from datetime import datetime
# from zoneinfo import ZoneInfo, available_timezones

SYSTEM = """You are an agent designed for coding assistance through counseling, code
reading and tool calling."""

# ----- DEFININDO O MODELO -----
class MyAgent:
  def __init__(self, model, client:OpenAI, validator:fsm.Validator):
    self.model = model
    self.client = client
    self.validator = validator

  # Envia uma mensagem para o modelo de retorna a resposta
  def chat(self, messages, tools, temperature=0, **kw):
    resp = self.client.chat.completions.create(
      model=self.model,
      messages=messages,
      temperature=temperature,
      tools=tools
    )
    return resp.choices[0].message.content

  def chat_simple(self, messages):
    resp = self.client.chat.completions.create(
      model=self.model,
      messages=messages,
      temperature=0
      )
    return resp.choices[0].message.content

  # ----- AGENT LOOP -----
  def agent(self, task, tools=None, max_steps=8, confirm=None, verbose=None, system=None):
    # tool schema
    validator = self.validator
    msgs = [{"role": "system", "content": (system or SYSTEM)},
            {"role": "user", "content": task}]
    inst = "Esperando instruções, não faça nada."
    plan = "Não há um plano de ação, aguarde."
    
    # last_tool, repeat = None, 0 # guarda contra repetição de chamadas de ferramenta idênticas
    for t in range(1, max_steps + 1):
      
      #if validator.current == fsm.State.START:
      if validator.start_to_received():
      # first step of communication, collect response in "raw"
      # raw = self.chat(msgs, tools) # more to add, response format
        raw = self.chat_simple(msgs)
        msgs += [{"role": "assistant", "content": raw}] # retroalimentar a resposta ao modelo

      #elif validator.current != fsm.State.START and validator.current in fsm.State:
      elif validator.received_to_specified():
        # instrução adicional para direcionar o modelo
        inst = "Agora que sei o que devo fazer, preciso planejar um passo a passo para concluir a solução com base nas ferramentas que tenho á disposição."
        msgs += [{"role": "assistant", "content": inst}]
        plan = self.chat_simple(msgs)

      elif validator.specified_to_planned():
        
        return raw # resposta final


      else:
        raise RuntimeError("Estado inválido.")
      # if not, continue processing, retro-feeding the model
      # feedback = chat_simple(msgs)

      '''elif state == fsm.State.RECEIVED:
        # state = 
      elif state == fsm.State.SPECIFIED:
        # state = create_and_validate_plan()

      elif state == fsm.State.PLANNED:
        # state = begin_implementation()

      elif state == fsm.State.IMPLEMENTING:
        # state = execute_implementation()

      elif state == fsm.State.VERIFYING:
        # state = verify_or_repair()
      # REPAIR e FAILED?
      elif state = fsm.State.DONE: # Qual a abordagem correta? Como misturar as duas?
        # determine the action taken by the model, and return if said action is the final answer to the problem
            #if action["tool"] == "answer":
            #  return action["arguments"].get("text", "")'''
    raise RuntimeError("Max number of iterations reached.")
  #    action = json.loads(raw)
  #    if verbose
