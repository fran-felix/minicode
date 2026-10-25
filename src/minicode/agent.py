from openai import OpenAI
import json, re, inspect

from minicode.orchestrator import fsm
from minicode.tools import registry, tools
# requests
# from datetime import datetime
# from zoneinfo import ZoneInfo, available_timezones

SYSTEM = """Você é um agente desenvolvido para auxiliar com código por meio de conselhos, leitura de código e implementação. Você
resolve resolve tarefas passo a passo usando ferramentas.

Ferramentas disponíveis:
{catalog}

Regras:
- Ao receber uma mensagem, entenda e desenvolva o problema
- Se faltar informação, use ask_for_information antes de executar ações dependentes dela.
- Faça um plano de ação passo a passo antes de executar ferramentas
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

  # ----- AGENT LOOP -----
  def agent(self, task, available_tools=None, max_steps=8, confirm=None, ask=None, verbose=True, system=None):
    task = task or ""

    validator = self.validator
    schema = registry.schema(available_tools)
    specification_schema = registry.specification_schema()
    planning_schema = registry.planning_schema(available_tools)

    msgs = [{"role": "system", "content": (system or SYSTEM).format(catalog=registry.document(available_tools))}]

    answer = None
    task_in = None
    keep_chat = True

    while keep_chat:
      curr_tool = None
      last_tool = None
      repeat = 0
    
      # last_tool, repeat = None, 0 # guarda contra repetição de chamadas de ferramenta idênticas
      for t in range(1, max_steps + 1):

        if validator.current == fsm.State.START:
          task_in = input("Converse com Minicode: ").strip()

          if not task_in:
            msgs.append({
                "role": "user",
                "content": "O usuário não forneceu uma tarefa. Apenas se apresente."
            })

            greeting = self.chat_simple(msgs)
            if not greeting:
                raise RuntimeError("O modelo não retornou uma apresentação.")

            msgs.append({"role": "assistant", "content": greeting})
            print(f"\n{greeting}")
            keep_chat = validator.ask_to_continue()
            
            if not keep_chat:
                break
            continue

          task += task_in
          msgs.append({"role": "user", "content": task})
          validator.start_to_received()

        if validator.current == fsm.State.RECEIVED:
          # especificar a tarefa
          msgs += [{"role": "user", "content": (
            "Produza somente uma especificação estruturada da tarefa. "
            "Não chame ferramentas e não invente informações. "
            "Liste em unknowns tudo que for necessário mas não estiver disponível."
          )}]
          for attempt in range(1, 4):
            raw = self.chat(
              msgs,
              response_format={
                "type": "json_schema",
                "json_schema": {"name": "specification", "schema": specification_schema}
              }
            )
            msgs += [{"role": "assistant", "content": raw}]
            try:
              specification = self._load_json_object(raw, "especificação")
              self._validate_specification(specification)
              break
            except ValueError as error:
              if attempt == 3:
                raise
              msgs += [{"role": "user", "content": (
                "A especificação anterior é inválida. Corrija-a e responda somente "
                f"com o JSON da especificação. Erro de validação: {error}"
              )}]
          validator.received_to_specified(specification)

          if verbose: print(f" <o>! {raw}")

        if validator.current == fsm.State.SPECIFIED:
          msgs += [{"role": "user", "content": (
            "Com base na especificação anterior, produza somente um plano de ação "
            "executável. Cada passo deve usar no máximo uma ferramenta registrada, "
            "declarar sua observação esperada e como será verificado. "
            "Não revele raciocínio interno detalhado."
          )}]
          raw = self.chat(
            msgs,
            response_format={
              "type": "json_schema",
              "json_schema": {"name": "action_plan", "schema": planning_schema}
            }
          )
          msgs += [{"role": "assistant", "content": raw}]
          plan = self._load_json_object(raw, "plano")
          self._validate_plan(plan, available_tools)
          validator.specified_to_planned(plan)

          if verbose: print(f" <o>! {raw}")

        if validator.current == fsm.State.PLANNED:
          msgs += [{"role": "assistant", "content": "Agora que tenho um plano, vou começar a implementação."}]
          validator.planned_to_implementing()

        if validator.current == fsm.State.IMPLEMENTING:
          raw = self.chat(msgs, response_format={"type": "json_schema", "json_schema": {"name": "action", "schema": schema}})
          
          if raw is None:
            raise RuntimeError("O modelo não retornou uma resposta.")
          else:
            action = json.loads(raw)

          print(f"[{t}] <o> {action['thought']}")
          # Verifica se o agente está pronto para responder e retorna se for de fato a resposta final
          if action["tool"] == "answer":
            answer = action["arguments"].get("text", "")
            validator.implementing_to_verifying()

          obs = tools.execute(action, available_tools, confirm, ask)
          if verbose: print(f" <o>! {action['tool']}({action['arguments']})\n < o>: {tools.short(obs, 260)}")

          # Controle de repetição de chamadas de ferramenta
          curr_tool = (action['tool'], json.dumps(action['arguments'], sort_keys=True))
          repeat = repeat + 1 if curr_tool == last_tool else 0
          last_tool = curr_tool

          # Erro e retorno de aviso ao agente, informando que ele provavelmente está se repetindo erroneamente
          if repeat >= 2:
            raise RuntimeError("Agente interrompido: repetição excessiva de chamadas de função (mais de 3 vezes).")
          warning = ("\nATENÇÃO: você repetiu a chamada de ferramenta anterior, que falhou. "
                    "Não repita a mesma chamada, mude os argumentos ou use outra ferramenta.") if repeat else ""
          msgs += [{"role": "assistant", "content": raw},
                  {"role": "user", "content": "Observação: " + tools.short(obs) + warning}]

        if validator.current == fsm.State.VERIFYING:
          validator.verifying_to_done()

        if validator.current == fsm.State.DONE:
          print(f"\n{answer}")
          keep_chat = validator.ask_to_continue()
          if not keep_chat:
            validator.done_to_start()

        if not keep_chat:
          break

      else:
        raise RuntimeError(
            f"Número máximo de iterações alcançado {max_steps}."
        )
    
    print("\n<o> Espero ter ajudado!")

  # ----- MÉTODOS ESTÁTICOS GERADOS COM COPILOT -----

  @staticmethod
  def _load_json_object(raw, label):
    if not raw:
      raise ValueError(f"O modelo não retornou uma {label}.")
    try:
      value = json.loads(raw)
    except json.JSONDecodeError as error:
      raise ValueError(f"A {label} não é JSON válido: {error}") from error
    if not isinstance(value, dict):
      raise ValueError(f"A {label} deve ser um objeto JSON.")
    return value

  @staticmethod
  def _validate_specification(specification):
    if not specification["goal"].strip():
      raise ValueError("A especificação deve conter um objetivo.")
    if specification["needs_clarification"] != bool(specification["unknowns"]):
      raise ValueError(
        "needs_clarification deve ser true quando unknowns não estiver vazio."
      )
    if not specification["acceptance_criteria"]:
      raise ValueError("A especificação deve conter critérios de aceitação.")

  @staticmethod
  def _validate_plan(plan, available_tools):
    if not plan["objective"].strip():
      raise ValueError("O plano deve conter um objetivo.")
    tools = set(available_tools or {})
    tools.add("answer")
    ids = [step["id"] for step in plan["steps"]]
    if len(ids) != len(set(ids)):
      raise ValueError("O plano contém IDs de passos duplicados.")
    known_ids = set(ids)
    for step in plan["steps"]:
      if step["tool"] not in tools:
        raise ValueError(f"Ferramenta não disponível no plano: {step['tool']}")
      if any(dependency not in known_ids for dependency in step["depends_on"]):
        raise ValueError(f"Dependência desconhecida no passo {step['id']}.")
    if not plan["steps"]:
      raise ValueError("O plano deve conter pelo menos um passo.")
    if not plan["verification_steps"]:
      raise ValueError("O plano deve conter passos de verificação.")
