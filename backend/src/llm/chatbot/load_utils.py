import traceback
from pathlib import Path


from pathlib import Path

def load_prompt(filename) -> str:
    """
    Load a system prompt with the following strategy:
      1. Try package resources (if prompts are packaged with the module)
      2. Fallback to a path relative to this file: ../../prompts/<filename>
      3. Raise a combined exception if all attempts fail
    """
    import importlib.resources as importlib_resources

    # 1) Try package resources
    try:
        return importlib_resources.read_text("src.llm.prompts", filename)
    except Exception as e:
        traceback.print_exc()

    # 2) Try local fallback path
    candidate = Path(__file__).resolve().parent / "prompts" / filename
    try:
        return candidate.read_text(encoding="utf-8")
    except Exception as e:
        traceback.print_exc()

    # 3) Combine both errors if both failed
    raise RuntimeError(f"Failed to load prompt '{filename}'")



if __name__ == '__main__':
    print(load_prompt("patient_chatbot_system.txt"))