"""Prism Academy — Session Calendar (Streamlit).

Run locally to validate:  streamlit run app.py
No Google setup needed to check it — data persists to data_store.json and you
can export .ics. Add secrets later to turn on live Google Calendar sync.
"""

import datetime as dt
import html as _html

import streamlit as st

import seed_data
import store
import calendar_sync as gc

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

st.set_page_config(page_title="Prism Academy — Session Calendar", page_icon="📅", layout="wide")

POD_COLORS = {p["short"]: p["color"] for p in seed_data.PODS}
POD_FULL = {p["short"]: p["name"] for p in seed_data.PODS}
POD_NAMES = list(POD_COLORS)
TYPES = ["module", "fireside", "assessment", "activity"]

# --- Prism brand styling for the Streamlit shell ---
st.markdown("""
<style>
  .stApp { background: #F1F5EA; }
  [data-testid="stSidebar"] { background: #F5F8EF; }
  .prism-hero { background:#4A6741; background-image:
      linear-gradient(135deg,rgba(255,255,255,.05) 25%,transparent 25%),
      linear-gradient(225deg,rgba(0,0,0,.06) 25%,transparent 25%);
      background-size:44px 44px; border-radius:14px; padding:20px 26px; margin-bottom:14px; }
  .prism-hero .tag { color:#F5B942; font-size:10.5px; font-weight:800; letter-spacing:.32em; }
  .prism-hero h1 { color:#EDFFE1; margin:4px 0 0; font-size:24px; font-weight:800; }
  .prism-hero p { color:rgba(237,255,225,.82); margin:6px 0 0; font-size:13.5px; }
  .stButton>button { border-radius:6px; font-weight:700; }
  .stTabs [data-baseweb="tab-list"] { gap:4px; }
  .stTabs [aria-selected="true"] { color:#4A6741 !important; }
</style>
""", unsafe_allow_html=True)


def _esc(s):
    return _html.escape(str(s or ""))


def _ft(t):
    if not t:
        return ""
    h, m = t.split(":")
    h = int(h)
    ap = "AM" if h < 12 else "PM"
    return f"{h % 12 or 12}:{m} {ap}"


def _contrast(hexc):
    c = hexc.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return "#23291d" if (r * 299 + g * 587 + b * 114) / 1000 > 150 else "#fff"


def _shift_month(base, delta):
    m = base.month - 1 + delta
    return dt.date(base.year + m // 12, m % 12 + 1, 1)


_GRID_STYLE = """
<style>
.pc-cal{border:1px solid #DDE4CF;border-radius:12px;overflow:hidden;background:#fff}
.pc-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr))}
.pc-head{background:#F5F8EF;border-bottom:1px solid #DDE4CF}
.pc-h{padding:8px 10px;font-size:10.5px;font-weight:700;color:#66705C;text-transform:uppercase;letter-spacing:.06em}
.pc-cell{border-right:1px solid #DDE4CF;border-bottom:1px solid #DDE4CF;min-height:104px;min-width:0;padding:5px 6px}
.pc-cell:nth-child(7n){border-right:0}
.pc-cell.out{background:#FAFBF6}
.pc-dn{font-size:12.5px;font-weight:700;color:#23291d}
.pc-cell.out .pc-dn{color:#c1c6b6}
.pc-cell.today .pc-dn{background:#4A6741;color:#EDFFE1;padding:1px 7px;border-radius:999px}
.pc-pill{border-radius:5px;padding:3px 6px;margin-top:3px;font-size:10.5px;line-height:1.2;border-left:3px solid rgba(0,0,0,.22);overflow:hidden}
.pc-pill b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pc-pill span{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;opacity:.9;font-size:9.5px}
.pc-more{font-size:10.5px;color:#4A6741;font-weight:700;margin-top:2px}
</style>
"""


def build_month_grid(cur, sessions, colors):
    """Server-rendered (no-iframe) Prism-branded month grid. Robust on any host."""
    import calendar as _cal
    by = {}
    for s in sessions:
        by.setdefault(s["date"], []).append(s)
    for k in by:
        by[k].sort(key=lambda x: x["start"])
    first = cur.replace(day=1)
    off = first.weekday()  # Monday = 0
    start = first - dt.timedelta(days=off)
    dim = _cal.monthrange(cur.year, cur.month)[1]
    cells = ((off + dim + 6) // 7) * 7
    today = dt.date.today().isoformat()
    head = "".join(f'<div class="pc-h">{d}</div>' for d in DOW)
    body = ""
    for i in range(cells):
        d = start + dt.timedelta(days=i)
        iso = d.isoformat()
        cls = "pc-cell" + (" out" if d.month != cur.month else "") + (" today" if iso == today else "")
        pills = ""
        items = by.get(iso, [])
        for s in items[:3]:
            c = colors.get(s["pod"], "#4A6741")
            if s["status"] == "confirmed":
                bg = f"background:{c};"
            else:
                bg = (f"background-color:{c};background-image:repeating-linear-gradient(45deg,"
                      "transparent,transparent 5px,rgba(255,255,255,.28) 5px,rgba(255,255,255,.28) 10px);")
            pills += (f'<div class="pc-pill" style="{bg}color:{_contrast(c)}">'
                      f'<b>{_esc(_ft(s["start"]))} {_esc(s["title"])}</b>'
                      f'<span>{_esc(s["faculty"])} · {"Virtual" if s["mode"] == "virtual" else "In person"}</span></div>')
        if len(items) > 3:
            pills += f'<div class="pc-more">+{len(items) - 3} more</div>'
        body += f'<div class="{cls}"><span class="pc-dn">{d.day}</span>{pills}</div>'
    return (_GRID_STYLE + '<div class="pc-cal">'
            f'<div class="pc-grid pc-head">{head}</div>'
            f'<div class="pc-grid">{body}</div></div>')


# ------------------------------------------------------------------ identity
def resolve_role(email):
    email = (email or "").lower()
    if email == seed_data.ADMIN_EMAIL.lower():
        return "admin"
    leads = store.get_pod_leads()
    owners = set()
    for v in leads.values():
        owners.add((v.get("owner") or "").lower())
        owners.add((v.get("lead") or "").lower())
    return "pod" if email in owners else "view"


# In real deployment, replace this block with st.login()/st.user (see README).
with st.sidebar:
    st.markdown("### Prism Academy")
    st.caption("Session calendar")
    mode = st.radio("Preview as", ["Program admin", "Pod owner", "Others"], key="rolepick")
    role = {"Program admin": "admin", "Pod owner": "pod", "Others": "view"}[mode]
    can_edit = role in ("admin", "pod")
    st.caption("Prototype: role is a simulator. Real login maps identity automatically.")
    st.divider()
    pod_filter = st.selectbox("Filter by pod", ["All pods"] + POD_NAMES)
    st.divider()
    st.caption(f"Data source: {store.BACKEND}")

_access = "Full access." if role == "admin" else "Edit access." if role == "pod" else "View only."
st.markdown(f"""
<div class="prism-hero">
  <div class="tag">PRISM ACADEMY · OF INTERIOR DESIGN</div>
  <h1>Session Calendar</h1>
  <p>Faculty sessions across pods, month on month. {_access}</p>
</div>
""", unsafe_allow_html=True)

sessions = store.get_sessions()
if pod_filter != "All pods":
    sessions = [s for s in sessions if s["pod"] == pod_filter]

tab_cal, tab_sessions, tab_people = st.tabs(["📅 Calendar", "📋 Sessions", "👥 Participants & leads"])

# ------------------------------------------------------------------ calendar
with tab_cal:
    st.session_state.setdefault("cur", dt.date(2026, 6, 1))
    nav = st.columns([1, 1, 1, 5])
    if nav[0].button("‹ Prev", use_container_width=True):
        st.session_state.cur = _shift_month(st.session_state.cur, -1)
    if nav[1].button("Today", use_container_width=True):
        _t = dt.date.today()
        st.session_state.cur = dt.date(_t.year, _t.month, 1)
    if nav[2].button("Next ›", use_container_width=True):
        st.session_state.cur = _shift_month(st.session_state.cur, 1)
    cur = st.session_state.cur
    nav[3].markdown(f"### {MONTHS[cur.month - 1]} {cur.year}")
    st.markdown(build_month_grid(cur, sessions, POD_COLORS), unsafe_allow_html=True)
    st.markdown(
        "**Programs:** " + "  ".join(f'<span style="color:{POD_COLORS[p]}">■</span> {p}' for p in POD_NAMES)
        + '  ·  <span style="opacity:.65">striped = proposed</span>', unsafe_allow_html=True)
    st.caption("Open the **Sessions** tab to see full details, add, or edit.")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if gc.is_configured():
            if st.button("🔄 Sync visible sessions to Google Calendar", disabled=not can_edit):
                ok = 0
                for s in sessions:
                    try:
                        gid = gc.upsert_event(s, store.invitees(s["pod"]))
                        store.set_gcal_id(s["id"], gid)
                        ok += 1
                    except Exception as e:  # noqa
                        st.warning(f'{s["title"]}: {e}')
                st.success(f"Synced {ok} session(s) to Google Calendar.")
        else:
            st.info("Google Calendar sync not configured yet — using .ics export. See README.")
    with c2:
        ics = gc.build_ics(sessions, store.invitees)
        st.download_button("⬇️ Export .ics (import to Google Calendar)", ics,
                           file_name="prism-sessions.ics", mime="text/calendar")

# ------------------------------------------------------------------ sessions
with tab_sessions:
    if can_edit:
        with st.expander("➕ Add a session", expanded=False):
            with st.form("add_session", clear_on_submit=True):
                a, b = st.columns(2)
                pod = a.selectbox("Pod", POD_NAMES)
                typ = b.selectbox("Type", TYPES)
                title = st.text_input("Title")
                fac = st.text_input("Faculty")
                fk = st.radio("Faculty type", ["internal", "external"],
                              index=0 if seed_data.FACULTY.get(fac, "internal") == "internal" else 1,
                              horizontal=True)
                d = st.date_input("Date", value=dt.date(2026, 6, 1))
                t1, t2 = st.columns(2)
                start = t1.time_input("Start", value=dt.time(11, 0))
                end = t2.time_input("End", value=dt.time(12, 0))
                mode_ = st.radio("Mode", ["virtual", "inperson"], horizontal=True)
                loc = st.text_input("Meeting link / venue")
                status = st.radio("Status", ["proposed", "confirmed"], horizontal=True)
                note = st.text_area("Notes")
                if st.form_submit_button("Save session"):
                    store.save_session({
                        "pod": pod, "type": typ, "title": title, "faculty": fac, "fkind": fk,
                        "date": str(d), "start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"),
                        "mode": mode_, "loc": loc, "status": status, "note": note, "gcal_id": "",
                    })
                    st.success("Saved.")
                    st.rerun()

    st.subheader("Sessions")
    for s in sorted(sessions, key=lambda x: (x["date"], x["start"])):
        badge = "✅" if s["status"] == "confirmed" else "🟡"
        tag = "" if s["type"] == "module" else f' · {s["type"].title()}'
        with st.expander(f'{badge} {s["date"]} {s["start"]}  |  {s["title"]}  ·  {s["pod"]}{tag}'):
            st.write(f'**Faculty:** {s["faculty"]} ({s["fkind"]})   |   **Mode:** {s["mode"]}'
                     f'   |   **Where:** {s.get("loc") or "—"}')
            if s.get("note"):
                st.caption(s["note"])
            inv = store.invitees(s["pod"])
            st.caption(f'Invitees on sync: {len(inv)} — {", ".join(inv[:5])}'
                       + (f' +{len(inv) - 5} more' if len(inv) > 5 else ""))
            if can_edit:
                cc1, cc2 = st.columns([1, 5])
                if cc1.button("Toggle status", key=f'tog{s["id"]}'):
                    s["status"] = "proposed" if s["status"] == "confirmed" else "confirmed"
                    store.save_session(s)
                    st.rerun()
                if cc2.button("Delete", key=f'del{s["id"]}'):
                    store.delete_session(s["id"])
                    st.rerun()

# ------------------------------------------------------------------ people
with tab_people:
    st.subheader("Participants & pod leads")
    if role == "admin":
        st.caption("You can reassign pod owner and content lead, and manage participants.")
    elif role == "pod":
        st.caption("You can manage participants. Pod owner / content lead are set by the program admin.")
    else:
        st.caption("View only.")

    leads = store.get_pod_leads()
    parts = store.get_participants()
    for pod in POD_NAMES:
        with st.expander(f'{pod}  ·  {len(parts.get(pod, []))} participant(s)'):
            st.caption(POD_FULL[pod])
            L = leads.get(pod, {"owner": "", "lead": ""})
            if role == "admin":
                oc, lc = st.columns(2)
                new_o = oc.text_input("Pod owner", L.get("owner", ""), key=f'o{pod}')
                new_l = lc.text_input("Content lead", L.get("lead", ""), key=f'l{pod}')
                if oc.button("Save owner", key=f'so{pod}'):
                    store.set_pod_lead(pod, "owner", new_o.strip().lower()); st.rerun()
                if lc.button("Save lead", key=f'sl{pod}'):
                    store.set_pod_lead(pod, "lead", new_l.strip().lower()); st.rerun()
            else:
                st.write(f'**Pod owner:** {L.get("owner") or "—"}   |   **Content lead:** {L.get("lead") or "—"}')

            st.write("**Participants**")
            for e in parts.get(pod, []):
                org = "DC" if e.lower().endswith("@designcafe.com") else "HL"
                row = st.columns([6, 1])
                row[0].write(f'`{org}`  {e}')
                if can_edit and row[1].button("✕", key=f'rm{pod}{e}'):
                    store.remove_participant(pod, e); st.rerun()
            if can_edit:
                nc = st.columns([6, 1])
                new_e = nc[0].text_input("Add participant email", key=f'add{pod}', label_visibility="collapsed",
                                         placeholder="name@homelane.com or name@designcafe.com")
                if nc[1].button("Add", key=f'addb{pod}') and new_e.strip():
                    store.add_participant(pod, new_e.strip().lower()); st.rerun()
