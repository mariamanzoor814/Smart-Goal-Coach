# utils.py
import sqlite3
import bcrypt
import pandas as pd
from datetime import date, datetime, timedelta
from db import get_connection
DB_PATH = "goals.db" 
import streamlit as st


# ---------- AUTH ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_user(name: str, email: str, password: str) -> bool:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, hash_password(password))
        )
        conn.commit()
        return True
    except Exception as e:
        print("create_user error:", e)
        return False
    finally:
        conn.close()

def login_user(email: str, password: str):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if row and verify_password(password, row["password"]):
            return {"id": row["id"], "name": row["name"], "email": row["email"]}
        return None
    finally:
        conn.close()

# ---------- WEEK HELPERS ----------
def monday_of_week(some_date: date) -> date:
    return some_date - timedelta(days=some_date.weekday())

def iso(d):
    if isinstance(d, (date, datetime)):
        return d.strftime("%Y-%m-%d")
    return d

# ---------- DB helpers ----------
def _coerce_task_df_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure task-related columns are numeric and present.
    """
    if df is None or df.empty:
        # ensure columns exist for downstream code
        return pd.DataFrame(columns=["id", "goal_id", "title", "notes", "due_date", "completed",
                                     "carried_over", "missed", "carried_from_week", "created_at"])
    df = df.copy()
    # Coerce to numeric for safety (SQLite sometimes gives strings)
    for col in ("completed", "carried_over", "missed"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = 0
    # Normalize due_date column (keep as string ISO or None)
    if "due_date" in df.columns:
        df["due_date"] = df["due_date"].fillna("")
    else:
        df["due_date"] = ""
    return df

def _normalize_category(cat):
    """Return normalized category key: 'personal', 'work', or 'study'."""
    if not cat:
        return "personal"
    cat = str(cat).strip().lower()
    if cat in ("work", "study", "personal"):
        return cat
    return "personal"

# ---------- GOAL CRUD ----------
def create_goal(user_id, title, description, week_start_iso, custom_deadline_iso=None, category='personal'):
    category = _normalize_category(category)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO goals (user_id, title, description, week_start, custom_deadline, category) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title, description, week_start_iso, custom_deadline_iso, category)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()



def update_goal(goal_id, title, description, week_start_iso, custom_deadline_iso, category='personal'):
    category = _normalize_category(category)
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE goals SET title=?, description=?, week_start=?, custom_deadline=?, category=? WHERE id=?
        """, (title, description, week_start_iso, custom_deadline_iso, category, goal_id))
        conn.commit()
    finally:
        conn.close()

def delete_goal(goal_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM tasks WHERE goal_id=?", (goal_id,))
        conn.execute("DELETE FROM goals WHERE id=?", (goal_id,))
        conn.commit()
    finally:
        conn.close()

def get_goals_for_week(user_id, week_start_iso, category=None):
    conn = get_connection()
    try:
        if category and str(category).lower() != "all":
            cat = _normalize_category(category)
            df = pd.read_sql(
                "SELECT * FROM goals WHERE user_id=? AND week_start=? AND category=? ORDER BY id DESC",
                conn, params=(user_id, week_start_iso, cat)
            )
        else:
            df = pd.read_sql(
                "SELECT * FROM goals WHERE user_id=? AND week_start=? ORDER BY id DESC",
                conn, params=(user_id, week_start_iso)
            )
        return df
    finally:
        conn.close()

# ---------- TASK CRUD ----------
def create_task(goal_id, title, notes, due_date_iso, carried_over=0, carried_from_week=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tasks (goal_id, title, notes, due_date, carried_over, carried_from_week)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (goal_id, title, notes, due_date_iso, 1 if carried_over else 0, carried_from_week))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def update_task(task_id, title, notes, due_date_iso, completed):
    """
    Update a task; store completed as 0/1 and return True on success.
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE tasks SET title=?, notes=?, due_date=?, completed=? WHERE id=?",
            (title, notes, due_date_iso, 1 if bool(completed) else 0, task_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print("update_task error:", e)
        return False
    finally:
        conn.close()

def get_missed_tasks(user_id, week_iso):
    """Return all missed (incomplete and past due) tasks up to current week."""
    query = """
        SELECT t.id, t.title, t.due_date, g.title as goal_title
        FROM tasks t
        JOIN goals g ON g.id = t.goal_id
        WHERE g.user_id = ? AND t.completed = 0
          AND date(t.due_date) < date(?)
    """
    return fetch_df(query, (user_id, week_iso))


def fetch_df(query, params=()):
    """Run a read-only SQL query and return results as a pandas DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def delete_task(task_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
    finally:
        conn.close()

def get_tasks_for_goal(goal_id):
    """
    Return tasks for a goal ordered so active & incomplete tasks appear first,
    then completed tasks, then missed tasks — all ordered by due_date inside those groups.
    Also coerce types for columns used in calculations.
    """
    conn = get_connection()
    try:
        # Order by missed (0 first), completed (0 first), then due_date asc
        df = pd.read_sql(
            "SELECT * FROM tasks WHERE goal_id=? ORDER BY missed ASC, completed ASC, due_date",
            conn, params=(goal_id,)
        )
        df = _coerce_task_df_types(df)
        return df
    finally:
        conn.close()

# ---------- PROGRESS & SUMMARY ----------
def _safe_sum(series):
    if series is None or len(series) == 0:
        return 0
    try:
        return int(pd.to_numeric(series, errors="coerce").fillna(0).sum())
    except Exception:
        s = 0
        for v in series:
            try:
                s += int(v)
            except Exception:
                continue
        return s

# paste into utils.py replacing existing goal_progress

# def _coerce_completed_val(v):
#     """
#     Turn many possible representations into 0 or 1.
#     """
#     if v is None:
#         return 0
#     if isinstance(v, (int, float)):
#         try:
#             return 1 if int(v) != 0 else 0
#         except Exception:
#             return 0
#     s = str(v).strip().lower()
#     if s in ("1", "true", "t", "yes", "y"):
#         return 1
#     return 0

# def goal_progress(tasks_df):
#     """
#     Robust progress calculation with server-side debug prints.

#     - Logs raw and normalized DataFrame.
#     - Ignores missed==1 tasks.
#     """
#     import pprint
#     # quick safety
#     if tasks_df is None:
#         print("goal_progress: tasks_df is None -> returning 0")
#         return 0
#     if isinstance(tasks_df, pd.DataFrame) and tasks_df.empty:
#         print("goal_progress: tasks_df empty -> returning 0")
#         return 0

#     df = tasks_df.copy()

#     # Ensure columns exist
#     for c in ("completed", "missed", "carried_over"):
#         if c not in df.columns:
#             df[c] = 0

#     # Normalize types for the three flags
#     df["completed_norm"] = df["completed"].apply(_coerce_completed_val)
#     df["missed_norm"] = df["missed"].apply(_coerce_completed_val)
#     df["carried_norm"] = df["carried_over"].apply(_coerce_completed_val)

#     # Log raw -> normalized to server log (visible in terminal where Streamlit runs)
#     print("=== goal_progress debug ===")
#     try:
#         # print raw rows (small)
#         print("raw rows:")
#         pprint.pprint(df[["id", "title", "completed", "missed", "carried_over", "due_date"]].to_dict(orient="records"))
#     except Exception as e:
#         print("error printing raw rows:", e)

#     # active tasks = not missed
#     active = df[df["missed_norm"] == 0].copy()
#     total_active = len(active)
#     sum_completed = int(active["completed_norm"].sum()) if total_active else 0

#     print(f"normalized (completed_sum, total_active) = ({sum_completed}, {total_active})")

#     if total_active == 0:
#         print("No active tasks (total_active == 0) -> returning 0")
#         return 0

#     pct = round((sum_completed / total_active) * 100)
#     pct = max(0, min(100, int(pct)))
#     print(f"CALCULATED PROGRESS: {pct}%")
#     print("=== end debug ===")
#     return pct

def goal_progress(tasks_df):
    """
    Compute goal completion percentage safely.
    Handles boolean, int, or string-completed fields.
    """
    if tasks_df is None or tasks_df.empty:
        return 0

    # Normalize the 'completed' column to booleans
    tasks_df["completed"] = tasks_df["completed"].apply(
        lambda x: True if str(x).lower() in ["1", "true", "yes"] else False
    )

    total = len(tasks_df)
    done = tasks_df["completed"].sum()

    if total == 0:
        return 0

    # Round to nearest whole number for cleaner display
    return round((done / total) * 100)


def inspect_goal_tasks(goal_id):
    """
    Debug helper: returns (raw_rows, normalized_df) and prints them.
    Use this to verify what's actually in the DB for a given goal_id.
    """
    conn = get_connection()
    try:
        import pprint
        q = "SELECT * FROM tasks WHERE goal_id=? ORDER BY id"
        cur = conn.execute(q, (goal_id,))
        rows = [dict(r) for r in cur.fetchall()]
        print(f"RAW DB rows for goal_id={goal_id}:")
        pprint.pprint(rows)

        df = pd.DataFrame(rows)
        if df.empty:
            print("inspect_goal_tasks: dataframe empty.")
            return rows, df

        # # coerce flags exactly as goal_progress does
        # df["completed_norm"] = df["completed"].apply(_coerce_completed_val) if "completed" in df.columns else 0
        # df["missed_norm"] = df["missed"].apply(_coerce_completed_val) if "missed" in df.columns else 0
        # df["carried_norm"] = df["carried_over"].apply(_coerce_completed_val) if "carried_over" in df.columns else 0

        print("NORMALIZED dataframe preview:")
        pprint.pprint(df[["id", "title", "completed", "completed_norm", "missed", "missed_norm", "carried_over", "carried_norm", "due_date"]].to_dict(orient="records"))
        return rows, df
    finally:
        conn.close()


def weekly_summary(user_id, week_start_iso, category=None):
    goals = get_goals_for_week(user_id, week_start_iso, category=category)
    total_goals = len(goals)
    total_active_tasks = 0
    completed_active_tasks = 0
    carried = 0
    missed = 0

    for g in goals.itertuples():
        tasks = get_tasks_for_goal(g.id)
        if tasks is None or tasks.empty:
            continue

        missed += _safe_sum(tasks["missed"])

        active = tasks[tasks["missed"] == 0]
        n_active = len(active)
        total_active_tasks += n_active

        if n_active:
            completed_active_tasks += _safe_sum(active["completed"])
            carried += _safe_sum(active["carried_over"])

    completion = int(round((completed_active_tasks / total_active_tasks * 100))) if total_active_tasks else 0
    completion = max(0, min(100, completion))

    return {
        "goals": total_goals,
        "tasks": total_active_tasks,
        "completed_tasks": completed_active_tasks,
        "completion": completion,
        "carried": carried,
        "missed": missed
    }


# ---------- CARRY-OVER LOGIC ----------
def detect_missed_tasks_from_week(user_id, from_week_iso, before_date_iso):
    conn = get_connection()
    try:
        q = """
        SELECT t.*, g.title as goal_title, g.week_start
        FROM tasks t
        JOIN goals g ON t.goal_id = g.id
        WHERE g.user_id = ? AND g.week_start = ? AND t.completed = 0 AND date(t.due_date) < date(?)
        AND t.carried_over = 0 AND t.missed = 0
        ORDER BY t.due_date
        """
        df = pd.read_sql(q, conn, params=(user_id, from_week_iso, before_date_iso))
        df = _coerce_task_df_types(df)
        return df
    finally:
        conn.close()

def mark_tasks_missed(task_ids):
    if not task_ids:
        return 0
    conn = get_connection()
    try:
        cur = conn.cursor()
        for tid in task_ids:
            cur.execute("UPDATE tasks SET missed=1 WHERE id=?", (tid,))
        conn.commit()
        return len(task_ids)
    finally:
        conn.close()

def mark_goal_completed(goal_id, completed=True):
    """
    Mark active tasks under a goal completed/uncompleted.
    Returns number of tasks updated (approx).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Update only active tasks (missed IS NULL OR missed=0)
        cur.execute("UPDATE tasks SET completed=? WHERE goal_id=? AND (missed IS NULL OR missed=0)",
                    (1 if completed else 0, goal_id))
        conn.commit()
        return cur.rowcount if hasattr(cur, "rowcount") else None
    finally:
        conn.close()

def carry_over_selected_tasks(task_ids, from_week_iso, to_week_iso, user_id):
    if not task_ids:
        return 0
    conn = get_connection()
    try:
        cur = conn.cursor()
        # try find existing 'Carried Over' goal for to_week_iso
        r = cur.execute("SELECT id, category FROM goals WHERE user_id=? AND week_start=? AND title='Carried Over'", (user_id, to_week_iso)).fetchone()
        if r:
            carried_goal_id, carried_cat = r[0], r[1] or "personal"
        else:
            cur.execute("INSERT INTO goals (user_id, title, description, week_start, category) VALUES (?, ?, ?, ?, ?)",
                        (user_id, "Carried Over", f"Tasks carried from {from_week_iso}", to_week_iso, "personal"))
            carried_goal_id = cur.lastrowid
            carried_cat = "personal"

        carried_count = 0
        for tid in task_ids:
            row = cur.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
            if not row:
                continue
            # original goal category
            orig_goal = cur.execute("SELECT category FROM goals WHERE id=?", (row["goal_id"],)).fetchone()
            orig_cat = orig_goal["category"] if orig_goal and orig_goal["category"] else "personal"

            orig_due = row["due_date"]
            try:
                orig_dt = datetime.strptime(orig_due, "%Y-%m-%d").date()
                weekday = orig_dt.weekday()
                to_monday = datetime.strptime(to_week_iso, "%Y-%m-%d").date()
                new_due = to_monday + timedelta(days=weekday)
                new_due_iso = new_due.strftime("%Y-%m-%d")
            except Exception:
                new_due_iso = to_week_iso

            target_goal_id = carried_goal_id
            # If categories differ, create/find a carried goal specific to this category
            if orig_cat != carried_cat:
                title_candidate = f"Carried Over - {orig_cat.title()}"
                r2 = cur.execute("SELECT id FROM goals WHERE user_id=? AND week_start=? AND title=?", (user_id, to_week_iso, title_candidate)).fetchone()
                if r2:
                    target_goal_id = r2[0]
                else:
                    cur.execute("INSERT INTO goals (user_id, title, description, week_start, category) VALUES (?, ?, ?, ?, ?)",
                                (user_id, title_candidate, f"Tasks carried from {from_week_iso}", to_week_iso, orig_cat))
                    target_goal_id = cur.lastrowid

            cur.execute("""
                INSERT INTO tasks (goal_id, title, notes, due_date, carried_over, carried_from_week)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (target_goal_id, row["title"], row["notes"], new_due_iso, from_week_iso))
            cur.execute("UPDATE tasks SET missed=1 WHERE id=?", (tid,))
            carried_count += 1

        conn.commit()
        return carried_count
    finally:
        conn.close()


def render_smart_insight_engine(user_id: str, week_start: str, summary: dict):
    """
    Reusable Smart Insight Engine UI block.
    Generates dynamic productivity insights for the given user/week.
    """

    # Section Header
    st.markdown("---")
    st.subheader("🧠 Smart Insight Engine")

    # Fetch missed tasks
    from datetime import datetime
    import utils  # safe circular import if inside same module

    missed_tasks = utils.get_missed_tasks(user_id, week_start)

    completion_rate = summary.get("completion", 0)
    total_goals = summary.get("goals", 0)
    total_tasks = summary.get("tasks", 0)
    carried = summary.get("carried", 0)
    overdue_count = len(missed_tasks) if missed_tasks is not None else 0

    insights = []

    # --- Insight Rules ---
    if total_goals == 0:
        insights.append("Start by setting at least one goal this week.")
    elif completion_rate == 0:
        insights.append("No tasks done yet — start small today.")
    elif completion_rate < 30:
        insights.append("Progress seems slow. Break goals into smaller parts.")
    elif 30 <= completion_rate < 70:
        insights.append("Nice! Stay consistent this week.")
    elif 70 <= completion_rate < 100:
        insights.append("Great work! You’re close to 100%. Keep it up.")
    elif completion_rate == 100:
        insights.append("Excellent! You’ve completed all your goals — set new ones for next week.")

    if overdue_count > 0:
        insights.append(f"{overdue_count} tasks are overdue — reschedule or mark as missed.")
    if carried > 0:
        insights.append(f"{carried} tasks were carried from last week — finish them early.")
    if total_tasks > 10 and completion_rate < 50:
        insights.append("Maybe too many tasks this week — focus on the essentials.")

    if not insights:
        insights.append("Everything looks balanced. Keep tracking regularly.")

    # --- Render insights as styled cards ---
    for i, tip in enumerate(insights, 1):
        st.markdown(
            f"""
            <div class='card' style='border-left:6px solid var(--primary); margin-bottom:8px;'>
                <b>💡 Insight {i}:</b> {tip}
            </div>
            """,
            unsafe_allow_html=True,
        )