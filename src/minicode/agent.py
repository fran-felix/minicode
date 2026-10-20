from openai import OpenAI
from dotenv import load_dotenv
import os, json, re, inspect

from minicode.orchestrator import fsm
# requests
# from datetime import datetime
# from zoneinfo import ZoneInfo, available_timezones

load_dotenv()

# ----- DEFININDO O MODELO -----
client = OpenAI(base_url=os.getenv('MINICODE_URL'), api_key=os.getenv('MINICODE_KEY'))
# message = [{'role': 'user', 'content': 'Hi'}]

# Envia uma mensagem para o modelo de retorna a resposta
def chat(messages, tools, temperature=0, **kw):
  resp = client.chat.completions.create(
    model='Qwen/Qwen2.5-14B-Instruct-AWQ',
    messages=messages,
    temperature=temperature,
    tools=tools
  )
  return resp.choices[0].message.content

def chat_simple(messages):
  resp = client.chat.completions.create(
    model='Qwen/Qwen2.5-14B-Instruct-AWQ',
    messages=messages,
    temperature=0
    )
  return resp.choices[0].message.content


# ----- DEFININDO CONTROLADORES -----
validator = fsm.Validator(client)


# ----- AGENT LOOP -----
SYSTEM = """You are an agent designed for coding assistance through counseling, code
reading and tool calling."""

def agent(task, tools=None, max_steps=8, confirm=None, verbose=None, system=None):
  # tool schema
  msgs = [{"role": "system", "content": (system or SYSTEM)},
          {"role": "user", "content": task}]
  inst = None
  
  # last_tool, repeat = None, 0 # guarda contra repetição de chamadas de ferramenta idênticas
  for t in range(1, max_steps + 1):
    
    if validator.current == fsm.State.START:
    # raw = chat(msgs, tools) # more to add, response format
    # first step of communication, collect response in "raw"
      validator.start_to_received()
      raw = chat_simple(msgs)
      msgs += [{"role": "assistant", "content": raw}] # add said response to the whole context

    elif validator.current != fsm.State.START and validator.current in fsm.State:
      validator.received_to_specified()
      inst = "Agora que sei o que devo fazer, preciso planejar um passo a passo para concluir a solução com base nas ferramentas que tenho á disposição."
      msgs += [{"role": "assistant", "content": inst}]


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

print(agent("Who are you?"))
