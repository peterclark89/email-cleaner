from mail_scanner import scan_senders
from ai_suggester import run_batch_suggestions
import json

def main():
    print("🔍 Scanning mailbox for unknown senders and subject lines...")

    # Limit how many messages per folder are scanned (None = all)
    corp, unknown_dict, skipped_dict, subjects_by_sender = scan_senders(limit=500)

    unknown_senders = list(unknown_dict.keys())
    print(f"📬 Found {len(unknown_senders)} unknown senders total.")

    # Limit how many senders to send to AI (to control cost)
    MAX_SENDERS = 100
    unknown_senders = unknown_senders[:MAX_SENDERS]
    print(f"🎯 Limiting to first {MAX_SENDERS} senders for this AI batch.")

    if not unknown_senders:
        print("✅ No new unknowns — nothing to classify.")
        return

    print("🤖 Running AI classification suggestions...")
    run_batch_suggestions(unknown_senders, subjects_by_sender)

    print("✅ Suggestions saved to sender_suggestions.json")

    # Optional: Show preview
    try:
        with open("sender_suggestions.json", "r") as f:
            suggestions = json.load(f)
    except Exception:
        print("⚠️ Failed to read sender_suggestions.json")
        return

    print("\n📊 Sample suggestions:")
    for s in unknown_senders[:10]:
        if s in suggestions:
            print(f" - {s}: {suggestions[s]['suggestion']} ({suggestions[s]['reason']})")

if __name__ == "__main__":
    main()
