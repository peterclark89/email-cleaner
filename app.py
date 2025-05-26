import os
import streamlit as st
from mail_scanner import scan_senders, load_json
from action_cleanup import unsubscribe_and_delete_sender as cleanup_sender
import json

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Email Cleanup Dashboard", layout="wide")
# ──────────────────────────────────────────────────────────────────────────────

# ─── Persistent safelist files ───────────────────────────────────────────────
WHITELIST_FILE  = "whitelist.json"
APPROVED_FILE   = "approved_senders.json"
ONEOFF_FILE     = "oneoff.json"

# Ensure the one-off file exists in a list form
if not os.path.exists(ONEOFF_FILE):
    with open(ONEOFF_FILE, "w") as f:
        json.dump({"senders": []}, f)

# Load existing safelists
whitelist = load_json(WHITELIST_FILE,   {"emails": [], "domains": []})["emails"]
approved  = load_json(APPROVED_FILE,    [])  # list of senders
oneoff    = load_json(ONEOFF_FILE,      [])  # list of senders
# ──────────────────────────────────────────────────────────────────────────────

# ─── Session state setup ─────────────────────────────────────────────────────
if "unknown" not in st.session_state:
    # first load: get all unknown senders
    _, unk = scan_senders(limit=None)
    st.session_state.unknown = {s: unk[s] for s in unk
                                if s not in whitelist
                                and s not in approved
                                and s not in oneoff}
    st.session_state.choices = {}  # sender -> choice
# ──────────────────────────────────────────────────────────────────────────────

st.title("📧 Email Cleanup Dashboard")
st.markdown("""
Click **Whitelist**, **Auto-Cleanup**, or **One-Off** for each sender.  
Rows color-code as you classify. When you’re done, hit **Run Cleanup**.
""")

# ─── Table header ────────────────────────────────────────────────────────────
cols = st.columns([4,1,1,1])
cols[0].markdown("**Sender (count)**")
cols[1].markdown("**Whitelist**")
cols[2].markdown("**Auto-Cleanup**")
cols[3].markdown("**One-Off**")
# ──────────────────────────────────────────────────────────────────────────────

# ─── Per-sender rows ─────────────────────────────────────────────────────────
for sender, count in st.session_state.unknown.items():
    # determine row color
    choice = st.session_state.choices.get(sender, None)
    if choice == "whitelist":
        bg = "#d4edda"
    elif choice == "approved":
        bg = "#d1ecf1"
    elif choice == "oneoff":
        bg = "#f8d7da"
    else:
        bg = "transparent"

    cols = st.columns([4,1,1,1])
    cols[0].markdown(
        f'<div style="background:{bg};padding:6px;border-radius:4px">'
        f"{sender} ({count})</div>",
        unsafe_allow_html=True
    )

    # Whitelist button
    if cols[1].button("Whitelist", key=f"wl_{sender}"):
        st.session_state.choices[sender] = "whitelist"
        # persist
        wl = load_json(WHITELIST_FILE, {"emails": [], "domains": []})
        if sender not in wl["emails"]:
            wl["emails"].append(sender)
            with open(WHITELIST_FILE, "w") as f:
                json.dump(wl, f, indent=2)

    # Auto-Cleanup (approved_senders)
    if cols[2].button("Cleanup", key=f"ac_{sender}"):
        st.session_state.choices[sender] = "approved"
        apr = load_json(APPROVED_FILE, [])
        if sender not in apr:
            apr.append(sender)
            with open(APPROVED_FILE, "w") as f:
                json.dump(apr, f, indent=2)

    # One-Off
    if cols[3].button("One-Off", key=f"oo_{sender}"):
        st.session_state.choices[sender] = "oneoff"
        oo = load_json(ONEOFF_FILE, [])
        if sender not in oo:
            oo.append(sender)
            with open(ONEOFF_FILE, "w") as f:
                json.dump(oo, f, indent=2)
# ──────────────────────────────────────────────────────────────────────────────

# ─── Run Cleanup ─────────────────────────────────────────────────────────────
if st.button("🧹 Run Cleanup for Approved & One-Off"):
    to_cleanup = [s for s,ch in st.session_state.choices.items()
                  if ch in ("approved","oneoff")]
    if to_cleanup:
        with st.spinner("Unsubscribing & deleting…"):
            for s in to_cleanup:
                cleanup_sender(s)
        st.success(f"✅ Completed cleanup for {len(to_cleanup)} senders!")
    else:
        st.info("No senders marked for cleanup.")
# ──────────────────────────────────────────────────────────────────────────────
