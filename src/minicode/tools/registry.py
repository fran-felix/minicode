def json_type(t): 
  return {"type": t} if isinstance(t, str) else t
#def nome_tipo(t):
#  return t if isinstance(t, str) else f"lista de {t['items']['type']}s"

def schema(fs):
    props = {}

    for f in fs.values():
        for p, t in f["params"].items():
            props[p] = json_type(t)  # Converts types into json formatting
            
    props["text"] = {"type": "string"}  # Allows the model to answer with plain text, which is used when it decides to give the final answer
    
    return {
        "type": "object",
        "properties": {
            "thought": {"type": "string"},
            "tool": {"type": "string", "enum": list(fs) + ["answer"]},  # The model can only use registered tools, or the response tool
            "arguments": {
                "type": "object",
                "properties": props,  # Inserts mapped arguments
                "additionalProperties": False
            }
        },
        "required": ["thought", "tool", "arguments"],
        "additionalProperties": False
    }