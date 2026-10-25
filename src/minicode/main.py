from openai import OpenAI
from minicode import agent
from dotenv import load_dotenv
import os

from minicode.orchestrator import fsm
from minicode.tools import tools


load_dotenv()
model = 'Qwen/Qwen2.5-14B-Instruct-AWQ'
url = os.getenv('MINICODE_URL')
key = os.getenv('MINICODE_KEY')

def confirm_action(name, args):
    print(f"\nO agente quer executar: {name}({tools.short(args)})")
    answer = input("Permitir? [s/N] ").strip().lower()
    return answer in {"s", "sim"}


def ask_for_information(question):
    return input(f"\nO agente precisa saber: {question}\nResposta: ").strip()


def main() -> None:
    # Definindo o agente e os segmentos da harness
    client = OpenAI(base_url=url, api_key=key)
    validator = fsm.Validator(client)
    minicode = agent.MyAgent(model, client, validator)

    minicode.agent(
        task=None,
        available_tools=tools.CODETOOLS,
        confirm=confirm_action,
        ask=ask_for_information,
    )

if __name__ == "__main__":
    main()