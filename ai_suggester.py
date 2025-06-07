import os
import json
import openai
import yaml
from collections import defaultdict
from datetime import datetime

# ─── Load OpenAI API key from config.yaml ───────────────────────────────
def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

config_path = os.path.expanduser("~/yt_summarizer/config.yaml")
config = load_config(config_path)
openai.api_key = config["openai_api_key"]

# ─── File paths ─────────────────────────────────────────────────────────
WHITELIST_FILE = "whitelist.json"
APPROVED_FILE  = "approved_senders.json"
ONEOFF_FILE    = "oneoff.json"
SUGGESTIONS_FILE = "sender_suggestions.json"

# ─── JSON Helpers ───────────────────────────────────────────────────────
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ─── AI Classification Logic ────────────────────────────────────────────
def suggest_classification(sender, subjects, whitelist, approved, oneoff):
    """
    Uses ChatGPT to classify sender based on past safelist patterns + subject lines.
    Returns {suggestion, reason, timestamp}.
    """

    system_prompt = (
        "You are an email classification assistant.\n"
        "You help sort unknown email senders into one of three buckets:\n"
        "- 'whitelist': personal contacts, important human messages\n"
        "- 'approved': newsletters, alerts, accounts you want to auto-clean\n"
        "- 'oneoff': emails you want cleaned once (like surveys, ticket links)\n"
        "\n"
        "You are provided example safelists and asked to classify new senders."
    )

    user_prompt = f"""
Known whitelisted emails/domains:
{whitelist['emails'] + whitelist['domains']}

Known approved senders:
{approved}

Known oneoff senders:
{oneoff}

New sender to classify: {sender}

Recent email subjects:
{subjects}

What is the most likely classification? Respond with:
- suggestion: one of 'whitelist', 'approved', or 'oneoff'
- reason: short explanation of your reasoning
""".strip()

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=150
    )

    raw = response["choices"][0]["message"]["content"]

    suggestion = None
    reason = ""
    for line in raw.splitlines():
        if "suggestion" in line.lower():
            suggestion = line.split(":")[-1].strip().lower()
        elif "reason" in line.lower():
            reason = line.split(":", 1)[-1].strip()

    return {
        "suggestion": suggestion,
        "reason": reason,
        "timestamp": datetime.now().isoformat()
    }

# ─── Batch Runner ───────────────────────────────────────────────────────
def run_batch_suggestions(unknown_senders, subjects_by_sender):
    whitelist = load_json(WHITELIST_FILE, {"emails": [], "domains": []})
    approved  = load_json(APPROVED_FILE, [])
    oneoff    = load_json(ONEOFF_FILE, [])
    suggestions = load_json(SUGGESTIONS_FILE, {})

    for sender in unknown_senders:
        if sender in suggestions:
            print(f"✅ Cached: {sender}")
            continue
        subjects = subjects_by_sender.get(sender, [])[:5]
        result = suggest_classification(sender, subjects, whitelist, approved, oneoff)
        suggestions[sender] = result
        print(f"🧠 {sender} → {result['suggestion']} ({result['reason']})")

    save_json(SUGGESTIONS_FILE, suggestions)

# ─── CLI Mode ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("⚙️  This script is meant to be called from batch runner.")
    print("Import run_batch_suggestions() from another script.")
