import inspect
import json
import os
import tempfile

PATH_CODE = "/home/francisco/minicode/agent_code"
os.makedirs(PATH_CODE, exist_ok=True)

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

# Insere texto em um arquivo existente sem descartar o conteúdo que já está nele.
# Incrementado com uso de ferramenta generativa (Copilot)
def write_file(file_name: str, position: int, write: str):
  if not isinstance(file_name, str) or not file_name:
    raise ValueError("file_name deve ser um nome de arquivo não vazio.")
  if not isinstance(position, int) or isinstance(position, bool) or position < 0:
    raise ValueError("position deve ser um inteiro não negativo.")
  if not isinstance(write, str):
    raise TypeError("write deve ser uma string.")

  root = os.path.realpath(PATH_CODE)
  path = os.path.realpath(os.path.join(root, file_name))
  if os.path.commonpath((root, path)) != root:
    raise ValueError("file_name deve apontar para dentro do diretório de desenvolvimento.")
  if not os.path.isfile(path):
    raise FileNotFoundError(
      f"Não há um arquivo com esse nome: {file_name}. Use list_files para "
      "ver os arquivos disponíveis."
    )

  with open(path, "r", encoding="utf-8", newline="") as file:
    original = file.read()

  if position > len(original):
    raise ValueError(
      f"position ({position}) está além do fim do arquivo ({len(original)})."
    )

  updated = original[:position] + write + original[position:]
  directory = os.path.dirname(path)
  mode = os.stat(path).st_mode
  temporary_path = None
  try:
    with tempfile.NamedTemporaryFile(
      mode="w",
      encoding="utf-8",
      newline="",
      dir=directory,
      prefix=f".{os.path.basename(path)}.",
      delete=False,
    ) as temporary:
      temporary_path = temporary.name
      temporary.write(updated)
      temporary.flush()
      os.fsync(temporary.fileno())
    os.chmod(temporary_path, mode)
    os.replace(temporary_path, path)
  except Exception:
    if temporary_path is not None:
      try:
        os.unlink(temporary_path)
      except FileNotFoundError:
        pass
    raise

  return {
    "arquivo": file_name,
    "posição_inicial": position,
    "posição_final": position + len(write),
    "caracteres_escritos": len(write),
  }

# Cria um arquivo novo no diretório de desenvolvimento. Implementado com ajuda de IA (Copilot)
def create_file(file_name: str, content: str):
  if not isinstance(file_name, str) or not file_name:
    raise ValueError("file_name deve ser um nome de arquivo não vazio.")
  if not isinstance(content, str):
    raise TypeError("content deve ser uma string.")

  root = os.path.realpath(PATH_CODE)
  path = os.path.realpath(os.path.join(root, file_name))
  if os.path.commonpath((root, path)) != root:
    raise ValueError("file_name deve apontar para dentro do diretório de desenvolvimento.")
  if os.path.exists(path):
    raise FileExistsError(f"Já existe um arquivo ou diretório com esse nome: {file_name}.")

  try:
    file_descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
  except FileNotFoundError as error:
    raise FileNotFoundError(
      f"O diretório pai não existe para o arquivo: {file_name}."
    ) from error

  with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as file:
    file.write(content)

  return {
    "arquivo": file_name,
    "caracteres_escritos": len(content),
  }

# Reposta final do agente, saída do loop
def answer(text):
  return text

CODETOOLS = {
  "list_files":     {"fn": list_files, "doc": "lista dos nomes dos arquivos no diretório de desenvolvimento", "params": {}},
  "read_file":      {"fn": read_file, "doc": "conteúdo de um arquivo no diretório de desenvolvimento, apenas leitura",
                    "params": {"file_name": "string"}},
  "write_file":     {"fn": write_file, "doc": "insere texto em um arquivo existente do diretório de desenvolvimento",
                    "params": {"file_name": "string", "position": "number", "write": "string"},
                    "efeito_colateral": True},
  "create_file":    {"fn": create_file, "doc": "cria um arquivo novo no diretório de desenvolvimento",
                    "params": {"file_name": "string", "content": "string"},
                    "efeito_colateral": True},
  "answer":         {"fn": answer, "doc": "resposta final do agente", "params": {"text": "string"}}
  # TODO "run_tests":    {"fn": run_tests, "doc": "", "params": {}},

  # Recomendações do Takashi
  #search_code
  #replace_text
  #create_file
  #git_diff
  #run_command
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