import os

PATH_CODE = "/home/francisco/minicode/agent_code"

# Lista todos os arquivos no diretório acessível ao agente
def list_files():
  # files = [f for f in os.listdir(PATH_CODE) if f.endswith('py')]
  files = [f for f in os.listdir(PATH_CODE)]
  if files:
    return files
  raise LookupError("Não há arquivos implementados.")

# Retorna o conteúdo de um arquivo
def read_file(file_name: str):
  if file_name not in os.listdir(PATH_CODE):
    raise FileNotFoundError(f"Não há um arquivo como nome: {file_name}. Use {list_files} para ver os arquivos disponíveis.")

  with open(os.path.join(PATH_CODE, file_name), 'r') as f:
    data = f.read()

  return data

# Escreve num arquivo existente na posição "position" e devolve uma string dizendo onde escreveu, a partir de qual posição e qual foi a última posição escrita
def write_file(file_name: str, position: int, write):
  if file_name not in os.listdir(PATH_CODE):
    raise FileNotFoundError(f"Não há um arquivo como nome: {file_name}. Use {list_files} para ver os arquivos disponíveis.")

  with open(os.path.join(PATH_CODE, file_name), 'w') as f:
    f.seek(position)
    end = f.write(write)

  return {f"Escrito em {file_name}, da posição {position} até {position + end}."}

# Reposta final do agente, saída do loop
#def answer(text):
#  return text

CODETOOLS = {
  "list_files":     {"fn": list_files, "doc": "lista dos nomes dos arquivos no diretório de desenvolvimento", "params": {}},
  "read_file":      {"fn": read_file, "doc": "conteúdo de um arquivo no diretório de desenvolvimento, apenas leitura",
                    "params": {"file_name": "string"}},
  "write_file":     {"fn": write_file, "doc": "escreve num arquivo do diretório de desenvolvimento",
                    "params": {"file_name": "string", "position": "number", "write": "string"}},
  # TODO "run_tests":    {"fn": run_tests, "doc": "", "params": {}},

  # Recomendações do Takashi
  #search_code
  #replace_text
  #create_file
  #git_diff
  #run_command
  #"answer":         {"fn": answer, "doc": "resposta final do agente", "params": {"text": "string"}}
}