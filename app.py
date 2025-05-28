import os
import streamlit as st
import json
from mail_scanner import scan_senders, load_json
from action_cleanup import unsubscribe_and_delete_sender as cleanup_sender

# ─── Config & safelist files ──────────────────────────────────────────────
WHITELIST_FILE = "whitelist.json"
APPROVED_FILE  = "approved_senders.json"
ONEOFF_FILE    = "oneoff.json"

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
    # Load existing safelists
    wl = load_json(WHITELIST_FILE, {"emails": [], "domains": []})["emails"]
    apr = load_json(APPROVED_FILE, [])
    oo  = load_json(ONEOFF_FILE, [])
    # Scan for unknown senders
    _, unk = scan_senders(limit=None)
    # Filter out already classified
    st.session_state.unknown = {
        s: cnt for s, cnt in unk.items()
        if s not in wl and s not in apr and s not in oo
    }
    # Initialize all choices to None
    st.session_state.choices = {s: None for s in st.session_state.unknown}

# ─── Page setup ────────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Email Cleanup Dashboard")
st.title("📧 Email Cleanup Dashboard")

# ─── Header with Select-All buttons ────────────────────────────────────────
header_cols = st.columns([4,1,1,1])
header_cols[0].markdown("**Sender (count)**")

# Whitelist column
if header_cols[1].button("Select All", key="sel_all_wl"):
    for s in st.session_state.choices:
        st.session_state.choices[s] = "whitelist"
header_cols[1].markdown("**Whitelist**")

# Auto-Cleanup column
if header_cols[2].button("Select All", key="sel_all_ac"):
    for s in st.session_state.choices:
        st.session_state.choices[s] = "approved"
header_cols[2].markdown("**Cleanup**")

# One-Off column
if header_cols[3].button("Select All", key="sel_all_oo"):
    for s in st.session_state.choices:
        st.session_state.choices[s] = "oneoff"
header_cols[3].markdown("**One-Off**")

# ─── Per-sender inline buttons ────────────────────────────────────────────
for sender, count in st.session_state.unknown.items():
    choice = st.session_state.choices[sender]
    cols = st.columns([4,1,1,1])
    cols[0].markdown(f"**{sender}** ({count})")

    # Whitelist button (checkbox)
    icon = "☑️" if choice == "whitelist" else "☐"
    if cols[1].button(icon, key=f"wl_{sender}"):
        st.session_state.choices[sender] = "whitelist"

    # Auto-Cleanup button (checkbox)
    icon = "☑️" if choice == "approved" else "☐"
    if cols[2].button(icon, key=f"ac_{sender}"):
        st.session_state.choices[sender] = "approved"

    # One-Off button (checkbox)
    icon = "☑️" if choice == "oneoff" else "☐"
    if cols[3].button(icon, key=f"oo_{sender}"):
        st.session_state.choices[sender] = "oneoff"

# ─── Submit Classifications ───────────────────────────────────────────────
if st.button("💾 Submit Classifications"):
    # Load safelists
    wl = load_json(WHITELIST_FILE, {"emails": [], "domains": []})
    apr = load_json(APPROVED_FILE, [])
    oo  = load_json(ONEOFF_FILE, [])

    # Apply staged choices
    for sender, choice in st.session_state.choices.items():
        if choice == "whitelist" and sender not in wl["emails"]:
            wl["emails"].append(sender)
        elif choice == "approved" and sender not in apr:
            apr.append(sender)
        elif choice == "oneoff" and sender not in oo:
            oo.append(sender)

    # Write safelists
    with open(WHITELIST_FILE, "w") as f:
        json.dump(wl, f, indent=2)
    with open(APPROVED_FILE, "w") as f:
        json.dump(apr, f, indent=2)
    with open(ONEOFF_FILE, "w") as f:
        json.dump(oo, f, indent=2)

    st.success("✅ Classifications saved!")

    # Rebuild unknown list and reset choices
    _, unk = scan_senders(limit=None)
    wl = load_json(WHITELIST_FILE, {"emails": [], "domains": []})["emails"]
    apr = load_json(APPROVED_FILE, [])
    oo  = load_json(ONEOFF_FILE, [])
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
