import os
import streamlit as st
import json
from mail_scanner import scan_senders, load_json
from action_cleanup import unsubscribe_and_delete_sender as cleanup_sender
from github import Github   # PyGithub

# ─── CONFIG ────────────────────────────────────────────────────────────────
WHITELIST_FILE = "whitelist.json"
APPROVED_FILE  = "approved_senders.json"
ONEOFF_FILE    = "oneoff.json"
REPO_NAME      = "peterclark89/email-cleaner"
# ──────────────────────────────────────────────────────────────────────────

def push_to_github(local_path, repo_path, commit_message):
    """
    Push a local file to GitHub (create or update).
    """
    token = os.getenv("GITHUB_TOKEN")
    gh    = Github(token)
    repo  = gh.get_repo(REPO_NAME)
    with open(local_path, "r") as f:
        content = f.read()
    try:
        contents = repo.get_contents(repo_path)
        repo.update_file(repo_path, commit_message, content, contents.sha)
    except Exception:
        repo.create_file(repo_path, commit_message, content)

# Ensure safelist files exist
for path, default in [
    (WHITELIST_FILE, {"emails": [], "domains": []}),
    (APPROVED_FILE,  []),
    (ONEOFF_FILE,    [])
]:
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)

# ─── Initial scan & session-state setup ──────────────────────────────────
if "unknown" not in st.session_state or "choices" not in st.session_state:
    wl   = load_json(WHITELIST_FILE, {"emails": [], "domains": []})["emails"]
    apr  = load_json(APPROVED_FILE,  [])
    oo   = load_json(ONEOFF_FILE,    [])
    _, unk = scan_senders(limit=None)
    st.session_state.unknown = {
        s: cnt for s, cnt in unk.items()
        if s not in wl and s not in apr and s not in oo
    }
    st.session_state.choices = {s: None for s in st.session_state.unknown}

st.set_page_config(layout="wide", page_title="Email Cleanup Dashboard")
st.title("📧 Email Cleanup Dashboard")

# ─── Header with Select-All buttons ────────────────────────────────────────
header_cols = st.columns([4,1,1,1])
header_cols[0].markdown("**Sender (count)**")
if header_cols[1].button("Select All", key="sel_all_wl"):
    for s in st.session_state.choices:
        st.session_state.choices[s] = "whitelist"
header_cols[1].markdown("**Whitelist**")
if header_cols[2].button("Select All", key="sel_all_ac"):
    for s in st.session_state.choices:
        st.session_state.choices[s] = "approved"
header_cols[2].markdown("**Cleanup**")
if header_cols[3].button("Select All", key="sel_all_oo"):
    for s in st.session_state.choices:
        st.session_state.choices[s] = "oneoff"
header_cols[3].markdown("**One-Off**")

# ─── Per-sender inline buttons ────────────────────────────────────────────
for sender, count in st.session_state.unknown.items():
    choice = st.session_state.choices[sender]
    cols   = st.columns([4,1,1,1])
    cols[0].markdown(f"**{sender}** ({count})")

    # Whitelist (checkbox)
    icon = "☑️" if choice == "whitelist" else "☐"
    if cols[1].button(icon, key=f"wl_{sender}"):
        st.session_state.choices[sender] = "whitelist"

    # Auto-Cleanup (checkbox)
    icon = "☑️" if choice == "approved" else "☐"
    if cols[2].button(icon, key=f"ac_{sender}"):
        st.session_state.choices[sender] = "approved"

    # One-Off (checkbox)
    icon = "☑️" if choice == "oneoff" else "☐"
    if cols[3].button(icon, key=f"oo_{sender}"):
        st.session_state.choices[sender] = "oneoff"

# ─── Submit Classifications ───────────────────────────────────────────────
if st.button("💾 Submit Classifications"):
    wl  = load_json(WHITELIST_FILE, {"emails": [], "domains": []})
    apr = load_json(APPROVED_FILE,  [])
    oo  = load_json(ONEOFF_FILE,    [])

    for sender, choice in st.session_state.choices.items():
        if choice == "whitelist" and sender not in wl["emails"]:
            wl["emails"].append(sender)
        elif choice == "approved" and sender not in apr:
            apr.append(sender)
        elif choice == "oneoff" and sender not in oo:
            oo.append(sender)

    # Write locally
    with open(WHITELIST_FILE, "w") as f:
        json.dump(wl, f, indent=2)
    with open(APPROVED_FILE, "w") as f:
        json.dump(apr, f, indent=2)
    with open(ONEOFF_FILE, "w") as f:
        json.dump(oo, f, indent=2)

    # Push JSON files back to GitHub
    push_to_github(WHITELIST_FILE,  "whitelist.json",  "Update whitelist via UI")
    push_to_github(APPROVED_FILE,   "approved_senders.json", "Update approved list via UI")
    push_to_github(ONEOFF_FILE,     "oneoff.json",     "Update one-off list via UI")

    st.success("✅ Classifications saved and pushed to GitHub!")

    # Rebuild unknown list and reset choices
    _, unk = scan_senders(limit=None)
    wl   = load_json(WHITELIST_FILE,   {"emails": [], "domains": []})["emails"]
    apr  = load_json(APPROVED_FILE,    [])
    oo   = load_json(ONEOFF_FILE,      [])
    st.session_state.unknown = {
        s: cnt for s, cnt in unk.items()
        if s not in wl and s not in apr and s not in oo
    }
    st.session_state.choices = {s: None for s in st.session_state.unknown}

# ─── Run Cleanup ───────────────────────────────────────────────────────────
if st.button("🧹 Run Cleanup for Approved & One-Off"):
    to_cleanup = load_json(APPROVED_FILE, []) + load_json(ONEOFF_FILE, [])
    if to_cleanup:
        with st.spinner("Unsubscribing & deleting…"):
            for s in to_cleanup:
                cleanup_sender(s)
        st.success(f"✅ Completed cleanup for {len(to_cleanup)} senders.")
    else:
        st.info("No senders marked for cleanup.")
