"""Prism Academy — Session Calendar (Streamlit).

Run locally to validate:  streamlit run app.py
No Google setup needed to check it — data persists to data_store.json and you
can export .ics. Add secrets later to turn on live Google Calendar sync.
"""

import datetime as dt
import json

import streamlit as st
import streamlit.components.v1 as components

import seed_data
import store
import calendar_sync as gc

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


def render_calendar_html(sessions, colors, fulls):
    """A self-contained, Prism-branded month calendar (renders in an iframe)."""
    tmpl = _CAL_TEMPLATE
    tmpl = tmpl.replace("__SESSIONS__", json.dumps(sessions))
    tmpl = tmpl.replace("__COLORS__", json.dumps(colors))
    tmpl = tmpl.replace("__FULLS__", json.dumps(fulls))
    return tmpl


_CAL_TEMPLATE = r"""
<style>
  :root{--forest:#4A6741;--cream:#EDFFE1;--gold:#F5B942;--muted:#66705C;--warm:#F5F8EF;--tint:#E7EEDB;--border:#DDE4CF;--text:#23291d}
  *{box-sizing:border-box}
  body{margin:0;font-family:'Segoe UI',system-ui,Arial,sans-serif;color:var(--text);background:#fff}
  .bar{display:flex;align-items:center;gap:8px;padding:10px 4px}
  .bar .ic{width:32px;height:32px;border:1px solid #C9D3BA;background:#fff;border-radius:6px;cursor:pointer;color:var(--forest);font-size:15px}
  .bar .lbl{font-weight:800;color:var(--forest);min-width:150px;text-align:center;font-size:16px}
  .bar .sp{flex:1}
  .bar .seg button{border:1px solid #C9D3BA;background:#fff;padding:7px 13px;font-weight:700;font-size:12px;color:var(--muted);cursor:pointer}
  .bar .seg button[aria-pressed=true]{background:var(--forest);color:#fff}
  .bar .seg button:first-child{border-radius:6px 0 0 6px}.bar .seg button:last-child{border-radius:0 6px 6px 0;border-left:0}
  .cal{border:1px solid var(--border);border-radius:12px;overflow:hidden}
  .head,.grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr))}
  .head{background:var(--warm);border-bottom:1px solid var(--border)}
  .head div{padding:8px 10px;font-size:10.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
  .cell{border-right:1px solid var(--border);border-bottom:1px solid var(--border);min-height:104px;min-width:0;padding:5px 6px;display:flex;flex-direction:column;gap:3px}
  .cell:nth-child(7n){border-right:0}
  .cell.out{background:#FAFBF6}.cell.out .dn{color:#c1c6b6}
  .cell.today .dn{background:var(--forest);color:var(--cream);width:22px;height:22px;border-radius:50%;display:grid;place-items:center}
  .dn{font-size:12.5px;font-weight:700}
  .pill{border:0;border-radius:5px;padding:3px 6px;font-size:10.5px;line-height:1.2;color:#fff;cursor:pointer;text-align:left;width:100%;min-width:0;border-left:3px solid rgba(0,0,0,.22)}
  .pill.proposed{background-image:repeating-linear-gradient(45deg,transparent,transparent 5px,rgba(255,255,255,.28) 5px,rgba(255,255,255,.28) 10px)}
  .pill b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .pill span{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;opacity:.9;font-size:9.5px}
  .more{font-size:10.5px;color:var(--forest);background:none;border:0;cursor:pointer;text-align:left;font-weight:700}
  .list .day{border-top:1px solid var(--border)}.list .day:first-child{border-top:0}
  .list .dh{background:var(--warm);padding:8px 14px;font-weight:800;color:var(--forest);font-size:11.5px;text-transform:uppercase;letter-spacing:.04em}
  .row{display:grid;grid-template-columns:84px 1fr 130px 100px;gap:10px;padding:9px 14px;border-top:1px solid var(--border);font-size:13px;align-items:center;cursor:pointer}
  .row:hover{background:var(--tint)}.row .t{font-weight:700;color:var(--forest)}.row .m{font-weight:700}
  .sw{width:9px;height:9px;border-radius:2px;display:inline-block;margin-right:5px}
  .bdg{font-size:10px;font-weight:800;padding:2px 8px;border-radius:999px;text-transform:uppercase}
  .bdg.confirmed{background:#E5EFDC;color:var(--forest)}.bdg.proposed{background:#FBEDCF;color:#9A6A10}
  .legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;font-size:11.5px;color:var(--muted)}
  .legend .k{width:18px;height:11px;border-radius:3px;display:inline-block;vertical-align:-1px;margin-right:5px}
  .ov{position:fixed;inset:0;background:rgba(28,40,22,.5);display:none;align-items:flex-start;justify-content:center;padding:34px 14px;z-index:9}
  .ov.open{display:flex}.modal{background:#fff;border-radius:12px;max-width:460px;width:100%}
  .mh{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid var(--border)}
  .mh h2{margin:0;font-size:16px;color:var(--forest)}.mh button{border:0;background:none;font-size:19px;cursor:pointer;color:var(--muted)}
  .mb{padding:16px 18px;display:grid;gap:10px;font-size:13.5px}
  .kv .k{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
  .kv .v{font-weight:700;margin-top:1px}
</style>
<div class="bar">
  <button class="ic" id="prev">&lsaquo;</button>
  <div class="lbl" id="lbl">—</div>
  <button class="ic" id="next">&rsaquo;</button>
  <button class="ic" id="today" style="width:auto;padding:0 12px;font-size:12px;font-weight:700">Today</button>
  <div class="sp"></div>
  <div class="seg"><button id="vM" aria-pressed="true">Month</button><button id="vL" aria-pressed="false">List</button></div>
</div>
<div id="calView" class="cal"><div class="head" id="head"></div><div class="grid" id="grid"></div></div>
<div id="listView" class="cal list" style="display:none"></div>
<div class="legend" id="legend"></div>
<div class="ov" id="ov"><div class="modal"><div class="mh"><h2 id="dT">Session</h2><button onclick="closeOv()">&times;</button></div><div class="mb" id="dB"></div></div></div>
<script>
  const S=__SESSIONS__, COLORS=__COLORS__, FULLS=__FULLS__;
  const DOW=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
  const MO=["January","February","March","April","May","June","July","August","September","October","November","December"];
  let cur=new Date(2026,5,1), view="month";
  function esc(s){return (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
  function ft(t){if(!t)return"";let[h,m]=t.split(":");h=+h;let ap=h<12?"AM":"PM",hh=h%12||12;return hh+":"+m+" "+ap}
  function col(p){return COLORS[p]||"#4A6741"}
  function ct(hex){let c=hex.replace("#","");let r=parseInt(c.substr(0,2),16),g=parseInt(c.substr(2,2),16),b=parseInt(c.substr(4,2),16);return (r*299+g*587+b*114)/1000>150?"#23291d":"#fff"}
  function inM(s){let d=new Date(s.date+"T00:00:00");return d.getFullYear()===cur.getFullYear()&&d.getMonth()===cur.getMonth()}
  function legend(){document.getElementById("legend").innerHTML='<span><span class="k" style="background:#4A6741"></span>Confirmed</span><span><span class="k" style="background:#4A6741;background-image:repeating-linear-gradient(45deg,transparent,transparent 4px,rgba(255,255,255,.4) 4px,rgba(255,255,255,.4) 8px)"></span>Proposed</span>&nbsp;'+Object.keys(COLORS).map(p=>`<span title="${esc(FULLS[p]||p)}"><span class="k" style="background:${col(p)}"></span>${esc(p)}</span>`).join("")}
  function render(){document.getElementById("calView").style.display=view==="month"?"":"none";document.getElementById("listView").style.display=view==="list"?"":"none";view==="month"?month():list()}
  function month(){
    document.getElementById("lbl").textContent=MO[cur.getMonth()]+" "+cur.getFullYear();
    document.getElementById("head").innerHTML=DOW.map(d=>`<div>${d}</div>`).join("");
    const g=document.getElementById("grid");g.innerHTML="";
    const first=new Date(cur.getFullYear(),cur.getMonth(),1),off=(first.getDay()+6)%7,start=new Date(first);start.setDate(1-off);
    const by={};S.forEach(s=>{(by[s.date]=by[s.date]||[]).push(s)});
    const dim=new Date(cur.getFullYear(),cur.getMonth()+1,0).getDate(),cells=Math.ceil((off+dim)/7)*7;
    const tIso=new Date().toISOString().slice(0,10);
    for(let i=0;i<cells;i++){
      const d=new Date(start);d.setDate(start.getDate()+i);
      const iso=d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");
      const out=d.getMonth()!==cur.getMonth();
      const cell=document.createElement("div");cell.className="cell"+(out?" out":"")+(iso===tIso?" today":"");
      cell.innerHTML=`<div><span class="dn">${d.getDate()}</span></div>`;
      const items=(by[iso]||[]).sort((a,b)=>a.start.localeCompare(b.start));
      items.slice(0,3).forEach(s=>cell.appendChild(pill(s)));
      if(items.length>3){const b=document.createElement("button");b.className="more";b.textContent="+"+(items.length-3)+" more";b.onclick=()=>{view="list";sync();render()};cell.appendChild(b)}
      g.appendChild(cell);
    }
  }
  function pill(s){const b=document.createElement("button"),c=col(s.pod);b.className="pill "+s.status;if(s.status==="confirmed")b.style.background=c;else b.style.backgroundColor=c;b.style.color=ct(c);b.innerHTML=`<b>${ft(s.start)} ${esc(s.title)}</b><span>${esc(s.faculty)} · ${s.mode==="virtual"?"Virtual":"In person"}</span>`;b.onclick=()=>openD(s);return b}
  function list(){
    document.getElementById("lbl").textContent=MO[cur.getMonth()]+" "+cur.getFullYear();
    const m=S.filter(inM).sort((a,b)=>a.date.localeCompare(b.date)||a.start.localeCompare(b.start)),box=document.getElementById("listView");
    if(!m.length){box.innerHTML='<div style="padding:40px;text-align:center;color:#66705C">No sessions this month.</div>';return}
    const g={};m.forEach(s=>{(g[s.date]=g[s.date]||[]).push(s)});let h="";
    Object.keys(g).sort().forEach(dt=>{const d=new Date(dt+"T00:00:00");h+=`<div class="day"><div class="dh">${DOW[(d.getDay()+6)%7]}, ${d.getDate()} ${MO[d.getMonth()]}</div>`;g[dt].forEach((s,i)=>{h+=`<div class="row" data-k="${dt}|${i}"><div class="t">${ft(s.start)}</div><div class="m">${esc(s.title)}</div><div><span class="sw" style="background:${col(s.pod)}"></span>${esc(s.pod)}</div><div><span class="bdg ${s.status}">${s.status}</span></div></div>`});h+="</div>"});
    box.innerHTML=h;box.querySelectorAll(".row").forEach(r=>{const[dt,i]=r.getAttribute("data-k").split("|");r.onclick=()=>openD(g[dt][+i])})
  }
  function openD(s){const c=col(s.pod);document.getElementById("dT").textContent=s.title;
    document.getElementById("dB").innerHTML=`<div style="border-left:5px solid ${c};padding-left:11px"><div class="v" style="font-size:15px">${esc(FULLS[s.pod]||s.pod)}</div><span class="bdg ${s.status}">${s.status}</span> ${s.type&&s.type!=="module"?"· "+s.type:""}</div>
    <div class="kv"><div class="k">Faculty</div><div class="v">${esc(s.faculty)} (${s.fkind||"internal"})</div></div>
    <div class="kv"><div class="k">Date &amp; time</div><div class="v">${s.date} · ${ft(s.start)}${s.end?" – "+ft(s.end):""}</div></div>
    <div class="kv"><div class="k">Mode</div><div class="v">${s.mode==="virtual"?"Virtual":"In person"}</div></div>
    <div class="kv"><div class="k">${s.mode==="virtual"?"Meeting link":"Venue"}</div><div class="v">${s.loc?esc(s.loc):"—"}</div></div>
    ${s.note?`<div style="background:var(--warm);border-radius:6px;padding:9px 11px;font-size:13px">${esc(s.note)}</div>`:""}`;
    document.getElementById("ov").classList.add("open")}
  function closeOv(){document.getElementById("ov").classList.remove("open")}
  document.getElementById("ov").addEventListener("click",e=>{if(e.target.id==="ov")closeOv()});
  function sync(){document.getElementById("vM").setAttribute("aria-pressed",view==="month");document.getElementById("vL").setAttribute("aria-pressed",view==="list")}
  document.getElementById("prev").onclick=()=>{cur=new Date(cur.getFullYear(),cur.getMonth()-1,1);render()};
  document.getElementById("next").onclick=()=>{cur=new Date(cur.getFullYear(),cur.getMonth()+1,1);render()};
  document.getElementById("today").onclick=()=>{const t=new Date();cur=new Date(t.getFullYear(),t.getMonth(),1);render()};
  document.getElementById("vM").onclick=()=>{view="month";sync();render()};
  document.getElementById("vL").onclick=()=>{view="list";sync();render()};
  legend();render();
</script>
"""


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
    components.html(render_calendar_html(sessions, POD_COLORS, POD_FULL), height=780, scrolling=True)

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
