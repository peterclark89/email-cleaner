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
    (WHITELIST_FILE,   {"emails": [], "domains": []}),
    (APPROVED_FILE,    []),
    (ONEOFF_FILE,      [])
]:
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)

# ─── Initial scan & session-state setup ──────────────────────────────────
if "unknown" not in st.session_state:
    _, unk = scan_senders(limit=None)
    # filter out already classified
    wl = load_json(WHITELIST_FILE,   {"emails": [], "domains": []})["emails"]
    apr = load_json(APPROVED_FILE,    [])
    oo = load_json(ONEOFF_FILE,      [])
    st.session_state.unknown = {
        s: unk[s]
        for s in unk
        if s not in wl and s not in apr and s not in oo
    }
    # initialize all choices to None
    st.session_state.choices = {s: None for s in st.session_state.unknown}

st.set_page_config(layout="wide")
st.title("📧 Email Cleanup Dashboard")

# ─── Header with Select-All buttons ────────────────────────────────────────
header_cols = st.columns([4,1,1,1])
header_cols[0].markdown("**Sender (count)**")
# Select All Whitelist
if header_cols[1].button("Select All", key="sel_all_wl"):
    for s in st.session_state.choices:
        st.session_state.choices[s] = "whitelist"
header_cols[1].markdown("**Whitelist**")
# Select All Cleanup
if header_cols[2].button("Select All", key="sel_all_ac"):
    for s in st.session_state.choices:
        st.session_state.choices[s] = "approved"
header_cols[2].markdown("**Cleanup**")
# Select All One-Off
if header_cols[3].button("Select All", key="sel_all_oo"):
    for s in st.session_state.choices:
        st.session_state.choices[s] = "oneoff"
header_cols[3].markdown("**One-Off**")

# ─── Per-sender inline buttons ────────────────────────────────────────────
for sender, count in st.session_state.unknown.items():
    choice = st.session_state.choices.get(sender)
    # row background
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
    if cols[1].button("●", key=f"wl_{sender}"):
        st.session_state.choices[sender] = "whitelist"
    # Cleanup button
    if cols[2].button("●", key=f"ac_{sender}"):
        st.session_state.choices[sender] = "approved"
    # One-Off button
    if cols[3].button("●", key=f"oo_{sender}"):
        st.session_state.choices[sender] = "oneoff"

# ─── Submit Classifications ───────────────────────────────────────────────
if st.button("💾 Submit Classifications"):
    # Load current safelists
    wl = load_json(WHITELIST_FILE, {"emails": [], "domains": []})
    apr = load_json(APPROVED_FILE, [])
    oo = load_json(ONEOFF_FILE, [])

    # Apply staged choices
    for sender, choice in st.session_state.choices.items():
        if choice == "whitelist" and sender not in wl["emails"]:
            wl["emails"].append(sender)
        if choice == "approved" and sender not in apr:
            apr.append(sender)
        if choice == "oneoff" and sender not in oo:
            oo.append(sender)

    # Write safelists
    with open(WHITELIST_FILE, "w") as f:
        json.dump(wl, f, indent=2)
    with open(APPROVED_FILE, "w") as f:
        json.dump(apr, f, indent=2)
    with open(ONEOFF_FILE, "w") as f:
        json.dump(oo, f, indent=2)

    st.success("✅ Classifications saved!")
    st.experimental_rerun()

# ─── Run Cleanup ───────────────────────────────────────────────────────────
if st.button("🧹 Run Cleanup for Approved & One-Off"):
    approved_list = load_json(APPROVED_FILE, [])
    oneoff_list   = load_json(ONEOFF_FILE, [])
    to_cleanup = approved_list + oneoff_list
    if to_cleanup:
        with st.spinner("Unsubscribing & deleting…"):
            for s in to_cleanup:
                cleanup_sender(s)
        st.success(f"✅ Completed cleanup for {len(to_cleanup)} senders.")
    else:
        st.info("No senders marked for cleanup.")
