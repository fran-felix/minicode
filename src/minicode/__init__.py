from openai import OpenAI
from minicode import agent
from minicode.orchestrator import fsm
from dotenv import load_dotenv
import os


load_dotenv()
model = 'Qwen/Qwen2.5-14B-Instruct-AWQ'
url = os.getenv('MINICODE_URL')
key = os.getenv('MINICODE_KEY')

def main() -> None:
    # Definindo o agente e os segmentos da harness
    client = OpenAI(base_url=url, api_key=key)
    validator = fsm.Validator(client)
    minicode = agent.MyAgent(model, client, validator)

    print(minicode.agent("Hello."))