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
  def agent(self, task, available_tools=None, max_steps=8, confirm=None, verbose=True, system=None):
    validator = self.validator
    schema = registry.schema(available_tools)

    msgs = [{"role": "system", "content": (system or SYSTEM).format(catalog=registry.document(available_tools))},
            {"role": "user", "content": task}]

    curr_tool = None
    last_tool = None
    repeat = 0
    answer = None
    
    # last_tool, repeat = None, 0 # guarda contra repetição de chamadas de ferramenta idênticas
    for t in range(1, max_steps + 1):

      if validator.current == fsm.State.START:
        validator.start_to_received()
        raw = self.chat(msgs, response_format={"type": "json_schema", "json_schema": {"name": "action", "schema": schema}})
        msgs += [{"role": "assistant", "content": raw}]
        
        if verbose: print(f" <o>! {raw}")

      if validator.current == fsm.State.RECEIVED:
        # especificar a tarefa
        msgs += [{"role": "assistant", "content": "Preciso fazer uma especificação do desejo do usuário, " +
                "colhendo requisitos, parâmetros e possíveis operações que terei de realizar."}]
        raw = self.chat(msgs, response_format={"type": "json_schema", "json_schema": {"name": "action", "schema": schema}})
        msgs += [{"role": "assistant", "content": raw}]
        validator.received_to_specified()

        if verbose: print(f" <o>! {raw}")
        # TODO verificar se ele não chama ferramentas erradas aqui
        # TODO pedir mais informação deveria ser uma tool, pra parar o fluxo de execução e ler um input

      if validator.current == fsm.State.SPECIFIED:
        msgs += [{"role": "assistant", "content": "Preciso bolar um passo a passo ANTES de agir, explicando minha linha de pensamento em detalhes."}]
        raw = self.chat(msgs, response_format={"type": "json_schema", "json_schema": {"name": "action", "schema": schema}})
        msgs += [{"role": "assistant", "content": raw}]
        validator.specified_to_planned()

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

        print(f"[{t}] <o> {action["thought"]}")
        # Verifica se o agente está pronto para responder e retorna se for de fato a resposta final
        if action["tool"] == "answer":
          answer = action["arguments"].get("text", "")
          validator.implementing_to_verifying()

        obs = tools.execute(action, available_tools, confirm)
        if verbose: print(f" <o>! {action["tool"]}({action["arguments"]})\n < o>: {tools.short(obs, 260)}")

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
                {"role": "user", "content": "Observação: " + tools.short(obs) + warning}]

      if validator.current == fsm.State.VERIFYING:
        validator.verifying_to_done()

      if validator.current == fsm.State.DONE:
        return answer

        
      
      # IMPLEMENTING: executar a implementação planejada após uma certificação do usuário

      # VERIFYING: testar o código feito

      # REPAIRING:

      # FAILED? provavelmente vai ser um erro, não um estado de fato, embora esteja no código para permitir transições.
      # outra opção é devolver que o modelo não é capaz de resolver tal tarefa. É, provavelmente isso.

    raise RuntimeError(f"Número máximo de iterações alcançado {max_steps}.")
