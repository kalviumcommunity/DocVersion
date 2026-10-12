import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = ROOT / "outputs"

load_dotenv(ROOT / ".env")

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("API_BASE_URL")
MODEL = os.getenv("CHAT_MODEL")

QUESTION = (
    "According to this policy, how many annual leave days "
    "does an employee receive, and can unused leave be carried over?"
)

POLICY_CONTEXT = """
Company leave policy:
Employees receive 20 days of annual leave per calendar year.
The provided policy does not specify whether unused leave
can be carried over.
"""

SYSTEM_PROMPT = """
You are an internal company policy assistant.
Answer only using the policy information provided.
Do not invent missing rules or facts.
If the policy does not contain the answer, say so clearly.
Keep the answer concise and factual.
"""


def run_experiment(client, label, parameters):
    """Run one chat completion experiment."""
    print(f"\n{'=' * 55}")
    print(label)
    print(f"Parameters: {parameters}")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"{POLICY_CONTEXT}\nQuestion: {QUESTION}",
            },
        ],
        **parameters,
    )

    answer = response.choices[0].message.content or ""
    print(f"Response:\n{answer}")

    usage = response.usage
    if usage:
        print(f"Completion tokens: {usage.completion_tokens}")

    return answer


def main():
    if not API_KEY or not BASE_URL or not MODEL:
        print("API configuration is missing.")
        print("Set API_KEY, API_BASE_URL, and CHAT_MODEL in .env.")
        print("No API experiments were run.")
        return

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    experiments = [
        (
            "Temperature: low",
            {"temperature": 0.0, "max_tokens": 100},
        ),
        (
            "Temperature: high",
            {"temperature": 1.0, "max_tokens": 100},
        ),
        (
            "Max tokens: short",
            {"temperature": 0.0, "max_tokens": 10},
        ),
        (
            "Max tokens: longer",
            {"temperature": 0.0, "max_tokens": 100},
        ),
        (
            "Top-p: unrestricted nucleus",
            {"temperature": 0.7, "top_p": 1.0, "max_tokens": 100},
        ),
        (
            "Top-p: narrower nucleus",
            {"temperature": 0.7, "top_p": 0.3, "max_tokens": 100},
        ),
    ]

    results = []

    for label, parameters in experiments:
        answer = run_experiment(client, label, parameters)
        results.append((label, parameters, answer))

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS_DIR / "parameter_comparison.md"

    with output_path.open("w", encoding="utf-8") as file:
        file.write("# Generation Parameter Experiments\n\n")
        file.write(f"**Model:** `{MODEL}`\n\n")
        file.write(f"**Question:** {QUESTION}\n\n")
        file.write(f"**Policy context:**\n\n{POLICY_CONTEXT}\n\n")

        for label, parameters, answer in results:
            file.write(f"## {label}\n\n")
            file.write(f"Parameters: `{parameters}`\n\n")
            file.write(f"{answer}\n\n")

    print(f"\nSaved actual API responses to {output_path}")


if __name__ == "__main__":
    main()