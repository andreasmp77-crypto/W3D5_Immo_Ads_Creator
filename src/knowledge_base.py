from pathlib import Path

SECONDARY_KB_DIR = Path("knowledge_base/secondary")

def get_secondary_kb_context() -> str:
    """
    Reads all secondary knowledge base markdown files 
    and combines them into a single string for LLM context.
    """
    context_blocks = []
    
    for file_path in SECONDARY_KB_DIR.glob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8")
            context_blocks.append(content)
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            
    return "\n\n---\n\n".join(context_blocks)