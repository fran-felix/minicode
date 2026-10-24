import os, json, inspect

PATH_CODE = "/home/francisco/minicode/agent_code"

# ----- FERRAMENTAS DO SISTEMA -----

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


# ----- CONTROLE DE USO DAS FERRAMENTAS -----

def mandatory(fn):
  return [p.name for p in inspect.signature(fn).parameters.values() if p.default is inspect.Parameter.empty]

def execute(action, fs, confirm=None):
  name = action.get("tool")
  if name not in fs:
    return {"erro": f"ferramenta desconhecida: {name}"}

  spec = fs[name]
  args = {k: v for k, v in (action.get("arguments") or {}).items() if k in spec["params"]}
  missing = [p for p in mandatory(spec["fn"]) if p not in args]

  if missing:
    return {"erro": f"faltam argumentos: {missing}"}
  if spec.get("efeito_colateral"):
    if confirm is None or not confirm(name, args):
      return {"erro": "ação com efeito externo NEGADA pelo operador humano; nada foi executado"}

  try:
    return {"resultado": spec["fn"](**args)}
  except Exception as e:
    return {"erro": f"{type(e).__name__}: {e}"}    

def short(obj, limit=900):
    s = json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= limit else s[:limit] + f"... (truncado, {len(s)} caracteres)"