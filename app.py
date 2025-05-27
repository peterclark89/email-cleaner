import os
import streamlit as st
import json
from mail_scanner import scan_senders, load_json
from action_cleanup import unsubscribe_and_delete_sender as cleanup_sender
from collections import Counter

# ─── Config & safelist files ──────────────────────────────────────────────
WHITELIST_FILE = "whitelist.json"
APPROVED_FILE  = "approved_senders.json"
ONEOFF_FILE    = "oneoff.json"
BLACKLIST_FILE = "blacklist.json"
# Ensure files exist
for f, default in [
    (WHITELIST_FILE,   {"emails": [], "domains": []}),
    (APPROVED_FILE,    []),
    (ONEOFF_FILE,      []),
    (BLACKLIST_FILE,   {"domains": []})
]:
    if not os.path.exists(f):
        with open(f, "w") as fp:
            json.dump(default, fp)

# ─── Load persistent safelists ─────────────────────────────────────────────
wl = load_json(WHITELIST_FILE,   {"emails": [], "domains": []})
approved = load_json(APPROVED_FILE, [])
oneoff   = load_json(ONEOFF_FILE,   [])
bl_dom   = load_json(BLACKLIST_FILE, {"domains": []})["domains"]

# ─── Initial scan & session state ─────────────────────────────────────────
if "unknown" not in st.session_state:
    _, unk = scan_senders(limit=None)
    # filter out already classified or domain-blacklisted
    st.session_state.unknown = {
        s: c for s, c in unk.items()
        if s not in wl["emails"]
        and s not in approved
        and s not in oneoff
        and s.split("@")[-1] not in bl_dom
    }
    # staging areas (no file writes yet)
    st.session_state.sel_senders = set()   # checked senders
    st.session_state.sel_domains = set()   # checked domains
    st.session_state.choices      = {}     # sender -> "whitelist"/"approved"/"oneoff"
# ────────────────────────────────────────────────────────────────────────────

st.set_page_config(layout="wide")
st.title("📧 Email Cleanup Dashboard")

# ─── Domain Summary Panel ──────────────────────────────────────────────────
st.subheader("Domain Summary")
domains = [s.split("@")[-1] for s in st.session_state.unknown]
dom_counts = Counter(domains)
col1, col2 = st.columns([3,1])
with col1:
    st.table(
        [{"Domain": d, "Senders": dom_counts[d], "Msgs": sum(
            count for s,count in st.session_state.unknown.items() if s.endswith(f"@{d}")
        )} for d in sorted(dom_counts)]
    )
with col2:
    # bulk-select domains for cleanup
    selected = st.multiselect(
        "Auto-Cleanup Domains",
        options=sorted(dom_counts),
        default=list(st.session_state.sel_domains),
        key="domains_multiselect"
    )
    st.session_state.sel_domains = set(selected)

# ─── Bulk-select senders ────────────────────────────────────────────────────
st.subheader("Senders")
sender_list = sorted(st.session_state.unknown)
checked = st.multiselect(
    "Select senders to classify",
    options=sender_list,
    default=list(st.session_state.sel_senders),
    key="senders_multiselect"
)
st.session_state.sel_senders = set(checked)

# ─── Choose action for selected senders ────────────────────────────────────
action = st.selectbox(
    "Action for selected senders",
    options=["Whitelist", "Auto-Cleanup", "One-Off"],
    key="action_select"
)

# ─── Save Classifications (deferred write!) ────────────────────────────────
if st.button("💾 Save Classifications"):
    # Domains → app.auto-cleanup
    bl = load_json(BLACKLIST_FILE, {"domains":[]})
    for d in st.session_state.sel_domains:
        if d not in bl["domains"]:
            bl["domains"].append(d)
    with open(BLACKLIST_FILE, "w") as fp:
        json.dump(bl, fp, indent=2)

    # Senders → chosen action
    if action == "Whitelist":
        data = load_json(WHITELIST_FILE, {"emails": [], "domains": []})
        for s in st.session_state.sel_senders:
            if s not in data["emails"]:
                data["emails"].append(s)
        with open(WHITELIST_FILE, "w") as fp:
            json.dump(data, fp, indent=2)
    elif action == "Auto-Cleanup":
        data = load_json(APPROVED_FILE, [])
        for s in st.session_state.sel_senders:
            if s not in data:
                data.append(s)
        with open(APPROVED_FILE, "w") as fp:
            json.dump(data, fp, indent=2)
    else:  # One-Off
        data = load_json(ONEOFF_FILE, [])
        for s in st.session_state.sel_senders:
            if s not in data:
                data.append(s)
        with open(ONEOFF_FILE, "w") as fp:
            json.dump(data, fp, indent=2)

    st.success(f"✅ Saved {len(st.session_state.sel_senders)} senders + {len(st.session_state.sel_domains)} domains")
    # clear staging
    st.session_state.sel_senders = set()
    st.session_state.sel_domains = set()
    st.experimental_rerun()

# ─── Run Cleanup ────────────────────────────────────────────────────────────
if st.button("🧹 Run Cleanup for Auto-Cleanup & One-Off"):
    # read full approved & oneoff
    to_cleanup = load_json(APPROVED_FILE, []) + load_json(ONEOFF_FILE, [])
    if to_cleanup:
        with st.spinner("Unsubscribing & deleting…"):
            for s in to_cleanup:
                cleanup_sender(s)
        st.success(f"✅ Completed cleanup for {len(to_cleanup)} senders!")
    else:
        st.info("No senders marked for cleanup.")