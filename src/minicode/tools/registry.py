def json_type(t):
    return {"type": t} if isinstance(t, str) else t


def name_type(t):
    return t if isinstance(t, str) else f"lista de {t['items']['type']}s"


def document(fs):
    return "\n".join(
        f"- {n}({', '.join(f'{p}: {name_type(t)}' for p, t in f['params'].items())}) -> {f['doc']}"
        for n, f in fs.items()
    )


def schema(fs):
    """Schema for tool calls and the existing final answer action."""
    props = {}
    for f in fs.values():
        for p, t in f["params"].items():
            props[p] = json_type(t)

    props["text"] = {"type": "string"}
    return {
        "type": "object",
        "properties": {
            "thought": {"type": "string"},
            "tool": {"type": "string", "enum": list(fs) + ["answer"]},
            "arguments": {
                "type": "object",
                "properties": props,
                "additionalProperties": False,
            },
        },
        "required": ["thought", "tool", "arguments"],
        "additionalProperties": False,
    }


# ---- ESQUEMAS ABAIXO GERADOS COM COPILOT -----

def specification_schema():
    """Schema for the model's normalized description of the user's task."""
    return {
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "context": {"type": "array", "items": {"type": "string"}},
            "constraints": {"type": "array", "items": {"type": "string"}},
            "acceptance_criteria": {
                "type": "array",
                "items": {"type": "string"},
            },
            "affected_files": {"type": "array", "items": {"type": "string"}},
            "unknowns": {"type": "array", "items": {"type": "string"}},
            "needs_clarification": {"type": "boolean"},
        },
        "required": [
            "goal",
            "context",
            "constraints",
            "acceptance_criteria",
            "affected_files",
            "unknowns",
            "needs_clarification",
        ],
        "additionalProperties": False,
    }


def planning_schema(fs):
    """Schema for an executable plan based on a validated specification."""
    tool_names = list(fs or {})
    tool_names.append("answer")
    step = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "description": {"type": "string"},
            "tool": {"type": "string", "enum": tool_names},
            "arguments": {"type": "object", "additionalProperties": True},
            "depends_on": {"type": "array", "items": {"type": "string"}},
            "expected_observation": {"type": "string"},
            "verification": {"type": "string"},
            "risk": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
        },
        "required": [
            "id",
            "description",
            "tool",
            "arguments",
            "depends_on",
            "expected_observation",
            "verification",
            "risk",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "objective": {"type": "string"},
            "steps": {"type": "array", "items": step},
            "verification_steps": {
                "type": "array",
                "items": {"type": "string"},
            },
            "rollback": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["objective", "steps", "verification_steps", "rollback"],
        "additionalProperties": False,
    }
