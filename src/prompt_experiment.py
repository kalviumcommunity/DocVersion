from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"
OUTPUTS_DIR = ROOT / "outputs"

policy_context = """
Company leave policy:
Employees receive 20 days of annual leave per calendar year.
Unused leave carryover rules are not specified.
"""

user_question = (
    f"Policy information:\n{policy_context}\n"
    "Employee question: Can I carry over unused annual leave "
    "into next year?"
)

prompts = {
    "Vague prompt": PROMPTS_DIR / "vague_prompt.txt",
    "Constrained prompt": PROMPTS_DIR / "constrained_prompt.txt",
}

print("PROMPT COMPARISON DEMO")
print("=" * 50)

for label, prompt_path in prompts.items():
    system_prompt = prompt_path.read_text(encoding="utf-8").strip()

    print(f"\n{label}")
    print("-" * 50)
    print("System message:")
    print(system_prompt)
    print("\nUser message:")
    print(user_question)

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

print("\nDemo completed.")
print("Both prompts and the shared user question were loaded.")
print("No API call was made.")