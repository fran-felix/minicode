from openai import OpenAI
import json, re, inspect

from minicode.orchestrator import fsm
from minicode.tools import registry
# requests
# from datetime import datetime
# from zoneinfo import ZoneInfo, available_timezones

SYSTEM = """Você é um agente desenvolvido para auxiliar com código por meio de conselhos, leitura de código e implementação. Você
resolve resolve tarefas passo a passo usando ferramentas.

Ferramentas disponíveis:
{catalog}

Regras:
- Chame UMA ferramenta por vez e espere a observação antes do próximo passo.
- Nunca invente dados que uma ferramenta pode fornecer, e nunca calcule de cabeça o que uma ferramenta calcula.
- Se uma observação trouxer "erro", leia a mensagem e corrija a chamada.
- Quando tiver tudo, use tool="answer" com arguments={{"text": "<resposta final em português>"}}."""

# ----- DEFININDO O MODELO -----
class MyAgent:
  def __init__(self, model, client:OpenAI, validator:fsm.Validator):
    self.model = model
    self.client = client
    self.validator = validator

  # Envia uma mensagem para o modelo de retorna a resposta
  def chat(self, messages, temperature=0, **kw):
    resp = self.client.chat.completions.create(
      model=self.model,
      messages=messages,
      temperature=temperature,
    )
    return resp.choices[0].message.content

  def chat_simple(self, messages):
    resp = self.client.chat.completions.create(
      model=self.model,
      messages=messages,
      temperature=0
      )
    return resp.choices[0].message.content

  # Método que controla o uso de ferramentas
  def execute(self, fs, confirm=None):
    # TODO
    ...

  # ----- AGENT LOOP -----
  def agent(self, task, tools=None, max_steps=8, confirm=None, verbose=None, system=None):
    validator = self.validator
    schema = registry.schema(tools)

    msgs = [{"role": "system", "content": (system or SYSTEM).format(catalog=registry.document(tools))},
            {"role": "user", "content": task}]
    inst = "Esperando instruções, não faça nada."
    plan = "Não há um plano de ação, aguarde."
    answer = None
    
    # last_tool, repeat = None, 0 # guarda contra repetição de chamadas de ferramenta idênticas
    for t in range(1, max_steps + 1):
      
      #if validator.current == fsm.State.START:
      if validator.start_to_received(): # RECEIVED: mensagem chegou ao servidor e o modelo está funcional
      # first step of communication, collect response in "raw"
        raw = self.chat(msgs, response_format={"type": "json_schema", "json_schema": {"name": "action", "schema": schema}})

        msgs += [{"role": "assistant", "content": raw}] # retroalimentar a resposta ao modelo

      elif validator.received_to_specified(): # SPECIFIED: modelo recebeu a tarefa e devolveu a primeira resposta, proceder com raciocínio e planejar
        # instrução adicional para direcionar o modelo
        inst = ("Agora que sei o que devo fazer, preciso planejar um passo a passo para concluir a solução com base nas ferramentas que tenho á disposição."
          +"Posso pedir mais informação se achar necessário.")
        # TODO pedir mais informação deveria ser uma tool, pra parar o fluxo de execução e ler um input
        msgs += [{"role": "assistant", "content": inst}]
        raw = self.chat_simple(msgs)

      elif validator.specified_to_planned(): # PLANNED: modelo devolveu um plano válido, começar a implementação
        plan = self.chat_simple(msgs)

        return plan # resposta final

      # IMPLEMENTING: executar a implementação planejada após uma certificação do usuário

      # VERIFYING: testar o código feito

      # REPAIRING:

      # FAILED? provavelmente vai ser um erro, não um estado de fato, embora esteja no código para permitir transições.
      # outra opção é devolver que o modelo não é capaz de resolver tal tarefa. É, provavelmente isso.

      elif validator.done(): # DONE: modelo concluiu a tarefa com sucesso, a resposta pode ser devolvida ao usuário
        return answer

      else:
        raise RuntimeError("Estado inválido.")
      # if not, continue processing, retro-feeding the model
      # feedback = chat_simple(msgs)
      
        # determine the action taken by the model, and return if said action is the final answer to the problem
            #if action["tool"] == "answer":
            #  return action["arguments"].get("text", "")'''
      
    raise RuntimeError("Max number of iterations reached.")
  #    action = json.loads(raw)
  #    if verbose
