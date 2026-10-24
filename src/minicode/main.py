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

def main() -> None:
    # Definindo o agente e os segmentos da harness
    client = OpenAI(base_url=url, api_key=key)
    validator = fsm.Validator(client)
    minicode = agent.MyAgent(model, client, validator)

    print(minicode.agent(task="O que tem no arquivo ai_teste.py ? Me devolva o conteúdo do arquivo, apenas isso.", available_tools=tools.CODETOOLS))

if __name__ == "__main__":
    main()