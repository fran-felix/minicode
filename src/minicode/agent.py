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
    return self.client.chat.completions.create(
        model=self.model,
        messages=messages,
        temperature=temperature,
        **kw,
    ).choices[0].message.content

  def chat_simple(self, messages):
    resp = self.client.chat.completions.create(
      model=self.model,
      messages=messages,
      temperature=0
      )
    return resp.choices[0].message.content

  # ----- CONTROLE DE FERRAMENTAS -----
  def mandatory(self, fn):
    return [p.name for p in inspect.signature(fn).parameters.values() if p.default is inspect.Parameter.empty]

  def execute(self, action, fs, confirm=None):
    name = action.get("tool")
    if name not in fs:
      return {"erro": f"ferramenta desconhecida: {name}"}

    spec = fs[name]
    args = {k: v for k, v in (action.get("arguments") or {}).items() if k in spec["params"]}
    missing = [p for p in self.mandatory(spec["fn"]) if p not in args]

    if missing:
      return {"erro": f"faltam argumentos: {missing}"}
    if spec.get("efeito_colateral"):
      if confirm is None or not confirm(name, args):
        return {"erro": "ação com efeito externo NEGADA pelo operador humano; nada foi executado"}

    try:
      return {"resultado": spec["fn"](**args)}
    except Exception as e:
      return {"erro": f"{type(e).__name__}: {e}"}    

  def short(self, obj, limit=900):
      s = json.dumps(obj, ensure_ascii=False)
      return s if len(s) <= limit else s[:limit] + f"... (truncado, {len(s)} caracteres)"

  # ----- AGENT LOOP -----
  def agent(self, task, tools=None, max_steps=8, confirm=None, verbose=True, system=None):
    validator = self.validator
    schema = registry.schema(tools)

    msgs = [{"role": "system", "content": (system or SYSTEM).format(catalog=registry.document(tools))},
            {"role": "user", "content": task}]
    inst = "Esperando instruções, não faça nada."

    curr_tool = None
    last_tool = None
    repeat = 0
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
        raw = self.chat(msgs)

      elif validator.specified_to_planned(): # PLANNED: modelo devolveu um plano válido, começar a implementação
        plan = self.chat(msgs)


        #return json.loads(plan) # resposta final

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
      
      # isso aqui tem que ser o primeiro check
      if raw is None:
        raise RuntimeError("O modelo não retornou uma resposta.")
      else:
        action = json.loads(raw)
      print(f"[{t}] <o>? {action["thought"]}")
      # Verifica se o agente está pronto para responder e retorna se for de fato a resposta final
      if action["tool"] == "answer":
        return action["arguments"].get("text", "")

      obs = self.execute(action, tools, confirm)

      if verbose: print(f" <o>! {action["tool"]}({action["arguments"]})\n < o>: {self.short(obs, 260)}")

      # Controle de repetição de chamadas de ferramenta
      curr_tool = (action["tool"], json.dumps(action["arguments"], sort_keys=True))
      repeat = repeat + 1 if curr_tool == last_tool else 0
      last_tool = curr_tool

      # Erro e retorno de aviso ao agente, informando que ele provavelmente está se repetindo erroneamente
      if repeat >= 2:
        raise RuntimeError("Agente interrompido: repetição excessiva de chamadas de função (mais de 3 vezes).")
      warning = ("\nATENÇÃO: você repetiu a chamada de ferramenta anterior, que falhou. "
                 "Não repita a mesma chamada, mude os argumentos ou use outra ferramenta.") if repeat else ""
      msgs += [{"role": "assistant", "content": raw},
              {"role": "user", "content": "Observação: " + self.short(obs) + warning}]
      
    raise RuntimeError(f"Número máximo de iterações alcançado {max_steps}.")
