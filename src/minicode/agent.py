from openai import OpenAI
from dotenv import load_dotenv
import os, json, re, inspect, requests
# from datetime import datetime
# from zoneinfo import ZoneInfo, available_timezones

load_dotenv()

# Definindo o modelo
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


# ----- AGENT LOOP -----
SYSTEM = """You are an agent designed for coding assistance through counselign, code
reading and tool calling."""

def agent(task, tools, max_steps=8, confirm=None, verbose=None, system=None):
  # tool schema
  msgs = [{"role": "system", "content": (system or SYSTEM)},
          {"role": "user", "content": task}]
  # last_tool, repeat = None, 0 # guarda contra repetição de chamadas de ferramenta idênticas
  for t in range(1, max_steps + 1):
    raw = chat(msgs, tools) # more to add, response format

  return raw
#    action = json.loads(raw)
#    if verbose

def teste():
  return 1

TESTE = {"teste": {"fn": teste, "doc": "just a test tool", "params": "nothing"}}

print(agent("What time is it?", TESTE))
