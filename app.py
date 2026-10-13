import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
from pathlib import Path

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "scrs_attendance.db"

st.set_page_config(page_title="SCRS Attendance", page_icon="📋", layout="wide")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                email TEXT,
                course TEXT,
                year TEXT,
                section TEXT,
                role TEXT DEFAULT 'Member',
                active INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT NOT NULL,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late', 'Excused')),
                session TEXT NOT NULL DEFAULT 'Regular Meeting',
                marked_by TEXT NOT NULL DEFAULT 'SCRS Admin',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(roll_no, attendance_date, session),
                FOREIGN KEY(roll_no) REFERENCES students(roll_no)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()

def query_df(sql, params=()):
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)

def execute(sql, params=()):
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid

init_db()

# ---------- UI ----------
st.markdown("""
<style>
    .stApp { background: #f5f7fb; }
    .block-container { padding-top: 1.5rem; max-width: 1400px; }
    .hero { background: linear-gradient(120deg, #102a43, #1f5a7a); padding: 1.5rem 1.8rem;
            border-radius: 18px; color: white; margin-bottom: 1rem; }
    .hero h1 { color: white; margin: 0; font-size: 2.15rem; }
    .hero p { color: #e5f1f8; margin: .35rem 0 0 0; }
    div[data-testid="stMetric"] { background: white; padding: 1rem; border-radius: 14px;
                                  border: 1px solid #e3eaf2; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>📋 SCRS Attendance Management</h1>
  <p>Student Committee Records System · Meetings, events and committee participation</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("SCRS Portal")
    page = st.radio("Navigate", [
        "Dashboard", "Mark Attendance", "Attendance Records",
        "Members", "Reports & Export", "About / Setup"
    ])
    st.caption("Local prototype · SQLite database")

# Seed data from the provided SCRS Student Committee PDF (page 1).
# The PDF lists 18 committee members. Names/emails/roll numbers/course/year/section/role
# are preloaded; contact numbers are intentionally not imported to reduce unnecessary exposure.
SEED_MEMBERS = [
    ("1240439426","Shreshtha Verma","shreasth2005@gmail.com","B.Tech CSE AI","Third","AI3B","Head"),
    ("1240432512","Virat Rai","viratrai255075@gmail.com","B.Tech CSE","Third","CS3F","Associate Head"),
    ("1240439401","Shafiquurrahman Ansari","shafiqurrahmanansari0786@gmail.com","B.Tech CSE AI","Third","AI3B","Technical Head"),
    ("1250439002","Anya Massey","aanyamassey05@gmail.com","B.Tech CSE AI","Second","AI2B","Social Media Head"),
    ("1240432233","Kishan Rai","raikishan109@gmail.com","B.Tech CSE","Third","CS3F","Event Head"),
    ("1240439247","Laxmiish Shukla","laxmiishshukla@bbdu.ac.in","B.Tech CSE AI","Third","AI3B","Member"),
    ("1240439308","Piyush Dubey","piyushdubey947@bbdu.ac.in","B.Tech CSE AI","Third","AI3B","Member"),
    ("1240439414","Shiva Kumar Tiwari","tiwarinishant543@bbdu.ac.in","B.Tech CSE AI","Third","AI3B","Member"),
    ("1240439216","Kamakhya Singh Yadav","kamakhyayadav05@gmail.com","B.Tech CSE AI","Third","AI3D","Member"),
    ("1240439295","Nitin Gupta","rahulkaundha@bbdu.ac.in","B.Tech CSE AI","Third","AI3D","Member"),
    ("1240432222","Jay Anshul","anshul30042005@gmail.com","B.Tech CSE","Third","CS3C","Member"),
    ("1240432458","Sonam Yadav","sonamyadav72005@gmail.com","B.Tech CSE","Third","CS3C","Member"),
    ("1240432466","Sumit Kumar","sk1786668@gmail.com","B.Tech CSE","Third","CS3C","Member"),
    ("1240432410","Shivam Gupta","22shivamgupta05@gmail.com","B.Tech CSE","Third","CS3F","Member"),
    ("1240432300","Nitin Verma","nv531965@gmail.com","B.Tech CSE","Third","CS3F","Member"),
    ("1240432497","Utsav Sharma","u1823452@gmail.com","B.Tech CSE","Third","CS3F","Member"),
    ("1250439396","Shivam Mishra","s.mishra4421@bbdu.ac.in","B.Tech CSE AI","Second","AI2E","Member"),
    ("1250439358","Rudransh Kumar Singh","rudranshsingh57112@gmail.com","B.Tech CSE AI","Second","AI2B","Member"),
]

with get_connection() as conn:
    count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if count == 0:
        conn.executemany("""INSERT OR IGNORE INTO students
            (roll_no,name,email,course,year,section,role) VALUES (?,?,?,?,?,?,?)""", SEED_MEMBERS)
        conn.commit()

def get_members(active_only=True):
    sql = "SELECT roll_no, name, email, course, year, section, role, active FROM students"
    if active_only:
        sql += " WHERE active=1"
    return query_df(sql + " ORDER BY name")

def attendance_summary(day=None, session=None):
    filters, params = [], []
    if day:
        filters.append("attendance_date=?"); params.append(str(day))
    if session:
        filters.append("session=?"); params.append(session)
    where = (" WHERE " + " AND ".join(filters)) if filters else ""
    return query_df("SELECT status, COUNT(*) AS total FROM attendance" + where + " GROUP BY status", params)

# Dashboard
if page == "Dashboard":
    today = date.today().isoformat()
    members = get_members()
    todays = query_df("SELECT status, COUNT(*) total FROM attendance WHERE attendance_date=? GROUP BY status", (today,))
    status_counts = dict(zip(todays["status"], todays["total"])) if not todays.empty else {}
    total_today = sum(status_counts.values())
    present_today = status_counts.get("Present", 0)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Active Members", len(members))
    c2.metric("Present Today", present_today)
    c3.metric("Attendance Entries Today", total_today)
    c4.metric("Overall Attendance Rows", int(query_df("SELECT COUNT(*) n FROM attendance").iloc[0]["n"]))
    st.subheader("Today's snapshot")
    if total_today:
        st.progress(present_today / total_today, text=f"{present_today} present out of {total_today} recorded entries")
        st.dataframe(todays.rename(columns={"status":"Status","total":"Count"}), use_container_width=True, hide_index=True)
    else:
        st.info("No attendance has been marked for today yet. Open **Mark Attendance** to begin.")
    st.subheader("Committee overview")
    if not members.empty:
        section_counts = members.groupby(["section","year"]).size().reset_index(name="Members")
        st.dataframe(section_counts, use_container_width=True, hide_index=True)
    recent = query_df("""SELECT attendance_date AS Date, session AS Session, roll_no AS 'Roll No',
                         status AS Status, marked_by AS 'Marked By'
                         FROM attendance ORDER BY attendance_date DESC, id DESC LIMIT 8""")
    st.subheader("Recent attendance activity")
    st.dataframe(recent, use_container_width=True, hide_index=True)

# Mark attendance
elif page == "Mark Attendance":
    st.subheader("Mark attendance")
    members = get_members()
    if members.empty:
        st.warning("Add members first.")
    else:
        with st.form("attendance_form"):
            col1,col2,col3 = st.columns(3)
            chosen_date = col1.date_input("Meeting / event date", value=date.today())
            session = col2.text_input("Meeting / event name", value="Regular Meeting")
            marked_by = col3.text_input("Marked by", value="SCRS Admin")
            sections = ["All sections"] + sorted(members["section"].dropna().unique().tolist())
            chosen_section = st.selectbox("Filter by section", sections)
            filtered = members if chosen_section == "All sections" else members[members["section"] == chosen_section]
            st.caption(f"{len(filtered)} members in this marking list. Set each status manually.")
            statuses = {}
            cols = st.columns(2)
            for i, row in enumerate(filtered.itertuples(index=False)):
                with cols[i % 2]:
                    statuses[row.roll_no] = st.selectbox(
                        f"{row.name} · {row.roll_no} · {row.section}",
                        ["Present", "Absent", "Late", "Excused"],
                        index=0, key=f"status_{row.roll_no}"
                    )
            notes = st.text_input("Optional note for this session")
            submitted = st.form_submit_button("Save attendance", type="primary", use_container_width=True)
        if submitted:
            if not session.strip() or not marked_by.strip():
                st.error("Meeting name and 'Marked by' are required.")
            else:
                saved, errors = 0, []
                for roll_no, status in statuses.items():
                    try:
                        execute("""INSERT INTO attendance
                            (roll_no,attendance_date,status,session,marked_by,notes,created_at)
                            VALUES (?,?,?,?,?,?,?)
                            ON CONFLICT(roll_no,attendance_date,session) DO UPDATE SET
                            status=excluded.status, marked_by=excluded.marked_by,
                            notes=excluded.notes, created_at=excluded.created_at""",
                            (roll_no, chosen_date.isoformat(), status, session.strip(),
                             marked_by.strip(), notes.strip(), datetime.now().isoformat(timespec="seconds")))
                        saved += 1
                    except Exception as e:
                        errors.append(f"{roll_no}: {e}")
                st.success(f"Saved/updated attendance for {saved} members.")
                if errors:
                    st.error("; ".join(errors))

# Records
elif page == "Attendance Records":
    st.subheader("Attendance records")
    records = query_df("""SELECT a.attendance_date AS Date, a.session AS Session,
        s.roll_no AS 'Roll No', s.name AS Name, s.section AS Section, a.status AS Status,
        a.marked_by AS 'Marked By', a.notes AS Notes
        FROM attendance a JOIN students s ON s.roll_no=a.roll_no
        ORDER BY a.attendance_date DESC, s.name""")
    if records.empty:
        st.info("No records yet. Mark attendance first.")
    else:
        col1,col2,col3 = st.columns(3)
        start = col1.date_input("From", value=date.today().replace(day=1), key="rec_from")
        end = col2.date_input("To", value=date.today(), key="rec_to")
        all_statuses = ["All"] + sorted(records["Status"].unique().tolist())
        status_filter = col3.selectbox("Status", all_statuses)
        filtered = records[(records["Date"] >= start.isoformat()) & (records["Date"] <= end.isoformat())]
        if status_filter != "All":
            filtered = filtered[filtered["Status"] == status_filter]
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        st.caption(f"{len(filtered)} record(s) match your filters.")

# Members
elif page == "Members":
    st.subheader("Committee members")
    with st.expander("Add a member"):
        with st.form("add_member"):
            a,b = st.columns(2)
            roll = a.text_input("University roll number *")
            name = b.text_input("Student name *")
            email = a.text_input("Email")
            course = b.text_input("Course", value="B.Tech CSE")
            year = a.selectbox("Year", ["First","Second","Third","Fourth"])
            section = b.text_input("Section")
            role = a.selectbox("SCRS role", ["Member","Head","Associate Head","Technical Head","Event Head","Social Media Head"])
            add = st.form_submit_button("Add member")
        if add:
            if not roll.strip() or not name.strip():
                st.error("Roll number and name are required.")
            else:
                try:
                    execute("INSERT INTO students (roll_no,name,email,course,year,section,role) VALUES (?,?,?,?,?,?,?)",
                            (roll.strip(),name.strip(),email.strip(),course.strip(),year,section.strip(),role))
                    st.success(f"Added {name}.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("That roll number already exists.")
    members = get_members(active_only=False)
    st.dataframe(members.rename(columns={"roll_no":"Roll No","name":"Name","email":"Email",
        "course":"Course","year":"Year","section":"Section","role":"Role","active":"Active"}),
        use_container_width=True, hide_index=True)
    with st.expander("Deactivate a member"):
        active = get_members()
        if not active.empty:
            choice = st.selectbox("Member", active["roll_no"] + " — " + active["name"])
            roll_to_disable = choice.split(" — ")[0]
            if st.button("Deactivate selected member"):
                execute("UPDATE students SET active=0 WHERE roll_no=?", (roll_to_disable,))
                st.success("Member deactivated. Existing attendance history is preserved.")
                st.rerun()

# Reports
elif page == "Reports & Export":
    st.subheader("Reports & export")
    members = get_members()
    if members.empty:
        st.info("No active members.")
    else:
        records = query_df("""SELECT s.roll_no AS 'Roll No', s.name AS Name, s.section AS Section,
            COUNT(a.id) AS 'Sessions Recorded',
            SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS Present,
            SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS Absent,
            SUM(CASE WHEN a.status='Late' THEN 1 ELSE 0 END) AS Late,
            SUM(CASE WHEN a.status='Excused' THEN 1 ELSE 0 END) AS Excused
            FROM students s LEFT JOIN attendance a ON a.roll_no=s.roll_no
            WHERE s.active=1 GROUP BY s.roll_no,s.name,s.section ORDER BY s.name""")
        records["Attendance %"] = records.apply(
            lambda r: round((r["Present"] / r["Sessions Recorded"] * 100), 1) if r["Sessions Recorded"] else 0.0, axis=1)
        st.dataframe(records, use_container_width=True, hide_index=True)
        st.download_button("Download summary CSV", records.to_csv(index=False).encode("utf-8"),
                           "scrs_attendance_summary.csv", "text/csv", use_container_width=True)
        full = query_df("""SELECT a.attendance_date AS Date, a.session AS Session, s.roll_no AS 'Roll No',
            s.name AS Name, s.section AS Section, a.status AS Status, a.marked_by AS 'Marked By', a.notes AS Notes
            FROM attendance a JOIN students s ON s.roll_no=a.roll_no
            ORDER BY a.attendance_date DESC,s.name""")
        st.download_button("Download detailed attendance CSV", full.to_csv(index=False).encode("utf-8"),
                           "scrs_attendance_details.csv", "text/csv", use_container_width=True)

# About
else:
    st.subheader("About this project")
    st.markdown("""
    **SCRS Attendance Management System** is a student-built prototype for manually tracking committee attendance.

    **Features**
    - Preloaded committee roster from the supplied one-page SCRS Student Committee PDF
    - Manual Present / Absent / Late / Excused marking
    - Date and meeting/event name tracking
    - Sections and roles, member management, and deactivation
    - Dashboard, searchable date/status filters, summary and detailed CSV exports
    - SQLite storage in a local database file

    **Important:** This is a local prototype, not a production-secured college system. Before real deployment, add login/authentication, role-based permissions, backups, audit logs, and a privacy review. The source PDF includes phone numbers; this app deliberately does not import them because attendance does not require them.
    """)
    st.info("Run locally with:  `python -m streamlit run app.py`")
