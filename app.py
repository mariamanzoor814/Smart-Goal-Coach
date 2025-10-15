# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta
import time
import utils
import streamlit.components.v1 as components


CATEGORY_OPTIONS = ["All", "Personal", "Work", "Study"]

def safe_rerun():
    """
    Try to force a Streamlit rerun in a way that works across versions.
    1) Prefer st.experimental_rerun when available.
    2) Fallback: change query params (this triggers a rerun).
    3) Final fallback: toggle a session_state flag (less immediate).
    """
    fn = getattr(st, "experimental_rerun", None)
    if callable(fn):
        try:
            fn()
            return
        except Exception:
            pass

    try:
        st.query_params(_rerun=int(time.time()))
        return
    except Exception:
        pass

    st.session_state["_needs_rerun_toggle"] = not st.session_state.get("_needs_rerun_toggle", False)


# add this after st.set_page_config(...)
st.markdown(
"""
<style>
:root{
  --page-padding: 200px; /* change this value to taste */
}

/* Target Streamlit's main block container */
div[data-testid="stApp"] div.block-container {
  padding-left: var(--page-padding) !important;
  padding-right: var(--page-padding) !important;
  max-width: none !important; /* keep full wide-layout width but with padding */
  box-sizing: border-box !important;
}

/* Make it responsive on small screens */
@media (max-width: 900px) {
  :root { --page-padding: 16px; }
  div[data-testid="stApp"] div.block-container {
    padding-left: var(--page-padding) !important;
    padding-right: var(--page-padding) !important;
  }
}

/* If you have components rendered via components.html, it's often safer to add padding inside them too:
   .my-component-wrapper { padding-left: var(--page-padding); padding-right: var(--page-padding); }
*/
</style>
""",
unsafe_allow_html=True,
)

# ---------- PAGE CONFIG & STYLING ----------
st.set_page_config(page_title="🎯 Smart Goal Coach", layout="wide")
st.markdown("""
<style>
:root {
  --primary: #6C63FF;
  --bg: #F9FAFB;
  --card: #FFFFFF;
  --text: #222222;
  --muted: #6B7280;
}
body { background-color: var(--bg); color: var(--text); }
.card { background: var(--card); padding:16px; border-radius:12px; box-shadow:0 6px 20px rgba(17,24,39,0.06); margin-bottom:16px; }
.goal-title { font-weight:700; color:var(--text); font-size:18px; }
.muted { color:var(--muted); font-size:13px; }
.progress-pill { background:#EEF2FF; color:var(--primary); padding:6px 10px; border-radius:999px; font-weight:600; }
.small { font-size:13px; color:var(--muted); }
</style>
""", unsafe_allow_html=True)

# ---------- SESSION STATE ----------
if "page" not in st.session_state:
    st.session_state.page = "home"
if "user" not in st.session_state:
    st.session_state.user = None
if "current_monday" not in st.session_state:
    st.session_state.current_monday = utils.iso(utils.monday_of_week(date.today()))
if "carry_prompt_shown_for_week" not in st.session_state:
    st.session_state.carry_prompt_shown_for_week = None  # to avoid repeated prompts

st.markdown("""
<style>
:root{
  --primary: #6C63FF;
  --bg: #F9FAFB;
  --card: #FFFFFF;
  --text: #222222;
  --muted: #6B7280;
}

/* base */
body{ background-color:var(--bg); color:var(--text); }
.card{ background:var(--card); padding:16px; border-radius:12px; box-shadow:0 6px 20px rgba(17,24,39,0.06); margin-bottom:16px; }
.goal-title{ font-weight:700; color:var(--text); font-size:18px; }
.muted{ color:var(--muted); font-size:13px; }
.progress-pill{ background:#EEF2FF; color:var(--primary); padding:6px 10px; border-radius:999px; font-weight:600; }
.small{ font-size:13px; color:var(--muted); }

/* Global Streamlit button styling */
.stButton>button,
div.stButton>button{
  background: var(--primary) !important;
  color: #fff !important;
  border: 0 !important;
  border-radius: 8px !important;
  padding: 8px 12px !important;
  font-weight:600 !important;
  box-shadow:none !important;
  min-height:40px !important;
  white-space:nowrap !important;
}

/* Sidebar buttons full width */
[data-testid="stSidebar"] .stButton>button{
  width:100% !important;
  display:block !important;
  text-align:left !important;
  padding-left:14px !important;
}


/* Action column wrapper */
.action-col{
  display:flex;
  flex-direction:column;
  align-items:flex-end; /* right-align the buttons/alert */
  gap:8px;
}

/* confirm row: buttons side-by-side, same width */
.confirm-row{ display:flex; gap:8px; align-items:center; justify-content:flex-end; flex-wrap:nowrap; }
.confirm-row .stButton>button{ width:150px !important; }

/* action buttons uniform width inside action-col */
.action-col .stButton>button{ width:150px !important; }

/* confirm alert box */
.confirm-alert{
  background:#fff7d6;
  border-left:4px solid #f59e0b;
  padding:10px 12px;
  border-radius:8px;
  max-width:260px;
  text-align:left;
  font-size:13px;
}
                        .stForm {
  background: var(--card, #FFFFFF) !important;    /* card color from your root */
  padding: 2.25rem !important;
  border-radius: 14px !important;
  box-shadow: 0 10px 30px rgba(17,24,39,0.06) !important;
  margin: 3.25rem auto !important;               /* center horizontally with top spacing */
  max-width: 520px !important;                   /* compact width on desktop */
  width: calc(100% - 32px) !important;           /* responsive on mobile */
  font-size: 15px !important;
  color: var(--text) !important;
}

/* responsive fallback */
@media (max-width:520px){
  .confirm-row{ flex-wrap:wrap; }
  .confirm-row .stButton>button{ width:100% !important; }
  .action-col .stButton>button{ width:100% !important; }
}
</style>
""", unsafe_allow_html=True)



def go_to(page):
    st.session_state.page = page
    st.rerun()

def render_sidebar_for(key_prefix="sb"):
    """
    Unified sidebar. Call from pages with a unique key_prefix
    so widgets get unique keys across pages/reruns.
    """
    if st.session_state.user:
        st.sidebar.markdown(f"👋 Hello, **{st.session_state.user['name']}**")

        # Navigation buttons (use unique keys via key_prefix)
        if st.sidebar.button("🏠 Home", key=f"{key_prefix}_home"):
            go_to("home")
        if st.sidebar.button("🎯 Dashboard", key=f"{key_prefix}_dashboard"):
            go_to("dashboard")
        if st.sidebar.button("📊 Visualizer", key=f"{key_prefix}_visualizer"):
            go_to("visualizer")
        if st.sidebar.button("🕑 Focus Mode", key=f"{key_prefix}_focus"):
            go_to("focus")


        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Logout", key=f"{key_prefix}_logout"):
            st.session_state.user = None
            st.session_state.carry_prompt_shown_for_week = None
            go_to("home")
    else:
        # Not logged in: only auth actions shown
        if st.sidebar.button("🔐 Login", key=f"{key_prefix}_login"):
            go_to("login")
        if st.sidebar.button("📝 Create account", key=f"{key_prefix}_signup"):
            go_to("signup")

# ---------- AUTH UI ----------
def login_ui():
    st.markdown("<h2> Login</h2>", unsafe_allow_html=True)
    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        user = utils.login_user(email.strip(), password)
        if user:
            st.session_state.user = user
            # clear carry prompt state when user logs in
            st.session_state.carry_prompt_shown_for_week = None
            go_to("dashboard")
        else:
            st.error("Invalid email or password.")
    st.write("Don't have an account? ")
    if st.button("Create account", key="login_create_account"):
        go_to("signup")

def signup_ui():
    st.markdown("<h2> Create Account</h2>", unsafe_allow_html=True)
    with st.form("signup"):
        name = st.text_input("Full name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create account")
    if submitted:
        if password != confirm:
            st.error("Passwords do not match.")
        elif len(password) < 6:
            st.warning("Password must be at least 6 characters.")
        else:
            ok = utils.create_user(name.strip(), email.strip(), password)
            if ok:
                st.success("Account created — please log in.")
                go_to("login")
            else:
                st.error("Email already exists or an error occurred.")
    if st.button("Back to login", key="signup_back_to_login"):
        go_to("login")


# ---------- CARRY-OVER PROMPT ----------
def prompt_carry_over_if_needed(user_id, new_week_iso):
    """
    Check previous week for missed but uncarried tasks.
    Show a user prompt (one-time per week per session).
    """
    # avoid repeating prompt multiple times per week
    if st.session_state.carry_prompt_shown_for_week == new_week_iso:
        return None

    prev_monday = datetime.strptime(new_week_iso, "%Y-%m-%d").date() - timedelta(days=7)
    prev_week_iso = utils.iso(prev_monday)

    # Identify missed/uncompleted tasks from prev week due before new_week_iso
    missed_df = utils.detect_missed_tasks_from_week(user_id, prev_week_iso, new_week_iso)
    if missed_df.empty:
        st.session_state.carry_prompt_shown_for_week = new_week_iso
        return None

    st.warning(f"You have {len(missed_df)} unfinished task(s) from the week of {prev_week_iso}.")
    st.markdown("Select tasks to carry over (or skip). You can also edit tasks before carrying them.")
    # present multiselect
    options = [f"{row['title']}  — due {row['due_date']} (Goal: {row['goal_title']})" for _, row in missed_df.iterrows()]
    mapping = {options[i]: int(missed_df.iloc[i]["id"]) for i in range(len(options))}
    selected = st.multiselect("Select tasks", options)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Carry selected"):
            sel_ids = [mapping[s] for s in selected]
            carried_count = utils.carry_over_selected_tasks(sel_ids, prev_week_iso, new_week_iso, user_id)
            st.success(f"Carried {carried_count} task(s) to this week.")
            st.session_state.carry_prompt_shown_for_week = new_week_iso
            st.rerun()
    with col2:
        if st.button("🚫 Mark selected as missed (archive)"):
            sel_ids = [mapping[s] for s in selected]
            utils.mark_tasks_missed(sel_ids)
            st.info(f"Marked {len(sel_ids)} task(s) as missed.")
            st.session_state.carry_prompt_shown_for_week = new_week_iso
            st.rerun()
    with col3:
        if st.button("✏️ Edit selected (open task editor)"):
            # set flags in session to open editors on the dashboard for selected tasks
            sel_ids = [mapping[s] for s in selected]
            for tid in sel_ids:
                st.session_state[f"edit_task_{tid}"] = True
            st.session_state.carry_prompt_shown_for_week = new_week_iso
            st.rerun()

def render_add_goal_form(container, user_id, week_iso, key_prefix="quick_goal", expanded=False):
    """
    Render a small Add Goal form inside any container (st.sidebar or main).
    `container` must be a Streamlit container (st.sidebar or st).
    """
    # Use an expander so it can be placed in sidebar or main area
    with container.expander("➕ Add Goal", expanded=expanded):
        # create a form inside the container
        with container.form(f"{key_prefix}_form"):
            title = container.text_input("Goal title", key=f"{key_prefix}_title")
            desc = container.text_area("Description (optional)", key=f"{key_prefix}_desc", height=80)
            category = container.selectbox("Category", options=["Personal","Work","Study"], index=0, key=f"{key_prefix}_category")
            use_cd = container.checkbox("Set custom deadline", key=f"{key_prefix}_use_cd")
            cd_val = None
            if use_cd:
                cd_val = container.date_input("Custom deadline", key=f"{key_prefix}_cd")
            submit = st.form_submit_button("Add Goal", key=f"{key_prefix}_submit")


        # handle submission outside the `with` so container methods still work
        if submit:
            if not title or not title.strip():
                container.error("Title required.")
            else:
                # if user set a custom deadline use it; otherwise default to week end (Monday + 6 days)
                if cd_val:
                    cd_iso = cd_val.strftime("%Y-%m-%d")
                else:
                    try:
                        week_monday = datetime.strptime(week_iso, "%Y-%m-%d").date()
                        week_end = week_monday + timedelta(days=6)
                        cd_iso = week_end.strftime("%Y-%m-%d")
                    except Exception:
                        cd_iso = None

                utils.create_goal(user_id, title.strip(), desc.strip(), week_iso, cd_iso, category=category.lower())
                container.success("Goal added.")
                # flag to pre-clear inputs on next run (keeps UI tidy)
                st.session_state[f"{key_prefix}_just_added"] = True
                st.rerun()


def home_ui():
    """
    Home / marketing page for SMART Goal Coach rendered in Streamlit.
    Replaces raw HTML printing and wires CTA buttons to go_to().
    """

    # Remove Streamlit’s default container padding
    st.markdown("""
        <style>
        div[data-testid="stApp"] div.block-container {
            padding-left: 0 !important;
            padding-right: 0 !important;
            padding-top: 0 !important;
            max-width: none !important;
            box-sizing: border-box !important;
        }

        @media (max-width: 900px) {
            div[data-testid="stApp"] div.block-container {
                padding-left: 12px !important;
                padding-right: 12px !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)

    render_sidebar_for(key_prefix="sb_home")

    # ✅ FIXED CSS BLOCK — properly closed
    css = """
    <style>
    :root{
      --primary: #6C63FF;
      --bg: #F9FAFB;
      --card: #FFFFFF;
      --text: #0f172a;
      --muted: #6B7280;
      --accent: linear-gradient(90deg,#6C63FF,#9D97FF);
      --border: #E6E9F0;
    }

    .hero {
      padding:56px 20px;
      text-align:center;
      background: linear-gradient(180deg, rgba(108,99,255,0.06), rgba(249,250,251,0));
    }
    .hero h1 {
      font-size:clamp(28px, 5vw, 56px);
      margin:0 0 12px;
      line-height:1.02;
      font-weight:800;
    }
    .hero p {
      color:var(--muted);
      font-size:clamp(14px, 1.6vw, 20px);
      max-width:900px;
      margin:0 auto 22px;
    }

    .cta-row { display:flex; gap:12px; justify-content:center; margin-top:18px; flex-wrap:wrap; }
    .btn-primary { background:var(--primary); color:white; padding:14px 28px; border-radius:999px; text-decoration:none; font-weight:700; box-shadow:0 8px 30px rgba(108,99,255,0.12); }
    .btn-outline { border:2px solid var(--primary); color:var(--primary); padding:12px 26px; border-radius:999px; text-decoration:none; font-weight:700; background:transparent; }


    /* --- Testimonials --- */
    .testimonials { padding:48px 20px; background:linear-gradient(180deg, rgba(108,99,255,0.03), transparent); }
    .test-grid { display:grid; gap:20px; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); max-width:1100px; margin:0 auto; }
    .testimonial { background:var(--card); border-radius:12px; padding:20px; border:1px solid var(--border); }
    .avatar { width:48px; height:48px; border-radius:999px; display:flex; align-items:center; justify-content:center; color:white; font-weight:700; }


    </style>
    """  # ✅ this was missing before!

    st.markdown(css, unsafe_allow_html=True)


    st.markdown(css, unsafe_allow_html=True)

    # Hero
    st.markdown(
        """
        <section class="hero">
          <h1>Achieve Your Goals with <span style="color:var(--primary)">SMART</span> Planning</h1>
          <p> Our Smart Goal Coach helps you set Specific, Measurable, Achievable, Relevant, and Time-bound goals.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # CTA buttons (use Streamlit native buttons for routing)
    left, c1, c2, right = st.columns([2, 1, 1, 2])
    with c1:
        if st.button("Get Started Free", key="cta_start"):
            if st.session_state.get("user"):
                go_to("dashboard")
            else:
                go_to("signup")
    with c2:
        if st.button("Watch Demo", key="cta_demo"):
            if st.session_state.get("user"):
                go_to("visualizer")
            else:
                st.info("Demo: Sign up or log in to see the interactive demo.")


    st.markdown("<br/>", unsafe_allow_html=True)

    
    # --- ADD this block instead ---
    import streamlit.components.v1 as components
    components.html("""
    <style>
    :root{
    --primary: #6C63FF;
    --bg: #F9FAFB;
    --card: #FFFFFF;
    --text: #0f172a;
    --muted: #6B7280;
    --accent: linear-gradient(90deg,#6C63FF,#9D97FF);
    --border: #E6E9F0;
    }

    .features {
    padding: 72px 0;
    background: transparent;
    }

    .features .inner {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 60px;
    box-sizing: border-box;
    }

    .features-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 32px;
    }

    @media (max-width: 1100px) {
    .features-grid { grid-template-columns: repeat(2, 1fr); gap: 24px; }
    }

    @media (max-width: 700px) {
    .features-grid { grid-template-columns: 1fr; gap: 16px; }
    }

    .feature-card {
    background: var(--card, #fff);
    border: 1px solid var(--border, #e6e9f0);
    padding: 28px;
    border-radius: 14px;
    box-shadow: 0 6px 22px rgba(2, 6, 23, 0.05);
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .feature-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 28px rgba(2, 6, 23, 0.08);
    }

    .feature-icon {
    width: 56px;
    height: 56px;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(108,99,255,0.08);
    margin-bottom: 14px;
    font-size: 22px;
    }

    .feature-card h3 {
    margin: 0 0 8px 0;
    font-size: 20px;
    font-weight: 700;
    }

    .feature-card p {
    color: var(--muted, #6B7280);
    margin: 0;
    line-height: 1.5;
    }

    .muted { color: var(--muted); }
    </style>

    <section class="features">
    <div class="inner">
        <div style="text-align:center; margin:0 auto 28px; max-width:900px;">
        <h2 style="margin:0 0 10px; font-size:32px;">The SMART Way to Success</h2>
        <p class="muted">Our proven methodology breaks down your goals into manageable, achievable steps</p>
        </div>

        <div class="features-grid">
        <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <h3>Specific</h3>
            <p>Define clear and precise goals that give you direction and focus on what matters most.</p>
        </div>

        <div class="feature-card">
            <div class="feature-icon">📈</div>
            <h3>Measurable</h3>
            <p>Track your progress with quantifiable metrics and celebrate milestones along the way.</p>
        </div>

        <div class="feature-card">
            <div class="feature-icon">✔️</div>
            <h3>Achievable</h3>
            <p>Set realistic goals that challenge you while remaining within your capabilities.</p>
        </div>

        <div class="feature-card">
            <div class="feature-icon">🏆</div>
            <h3>Relevant</h3>
            <p>Align your goals with your values and long-term objectives for meaningful progress.</p>
        </div>

        <div class="feature-card">
            <div class="feature-icon">📅</div>
            <h3>Time-bound</h3>
            <p>Set deadlines and timelines to create urgency and maintain momentum toward success.</p>
        </div>

        <div class="feature-card">
            <div class="feature-icon">👥</div>
            <h3>Focus Mode</h3>
            <p>A simple, distraction-free timer to get you into work quickly. Minutes matter more than motivation — use short, focused sessions to build rhythm and finish tasks without drama.</p>
        </div>
        </div>
    </div>
    </section>
    """, height=850, scrolling=False)


    # --- END ADD ---


    # Testimonials
    st.markdown('<section class="testimonials" style="padding-top:28px;"><div style="text-align:center; max-width:900px; margin:0 auto 24px;"><h2 style="margin:0 0 10px; font-size:28px;">Success Stories</h2><p class="muted">See how our SMART Goal Coach has transformed lives</p></div>', unsafe_allow_html=True)

    test_html = """
    <div class="test-grid">
      <div class="testimonial">
        <div style="display:flex; gap:12px; align-items:center; margin-bottom:8px;">
          <div class="avatar" style="background:linear-gradient(90deg,#6C63FF,#9D97FF);">SJ</div>
          <div>
            <div style="font-weight:700;">Sarah Johnson</div>
            <div class="muted" style="font-size:13px;">Entrepreneur</div>
          </div>
        </div>
        <p class="muted">"This platform helped me launch my business in 6 months. The SMART framework kept me focused and accountable every step of the way."</p>
        <div style="margin-top:10px; color:var(--primary)">★★★★★</div>
      </div>

      <div class="testimonial">
        <div style="display:flex; gap:12px; align-items:center; margin-bottom:8px;">
          <div class="avatar" style="background:linear-gradient(90deg,#6C63FF,#9D97FF);">MC</div>
          <div>
            <div style="font-weight:700;">Michael Chen</div>
            <div class="muted" style="font-size:13px;">Fitness Coach</div>
          </div>
        </div>
        <p class="muted">"I've tried many goal-setting apps, but this one stands out. The AI coaching adapts to my needs and keeps me motivated."</p>
        <div style="margin-top:10px; color:var(--primary)">★★★★★</div>
      </div>

      <div class="testimonial">
        <div style="display:flex; gap:12px; align-items:center; margin-bottom:8px;">
          <div class="avatar" style="background:linear-gradient(90deg,#6C63FF,#9D97FF);">EP</div>
          <div>
            <div style="font-weight:700;">Emily Parker</div>
            <div class="muted" style="font-size:13px;">Software Developer</div>
          </div>
        </div>
        <p class="muted">"Finally achieved my career goals! The time-bound approach and progress tracking made all the difference."</p>
        <div style="margin-top:10px; color:var(--primary)">★★★★★</div>
      </div>
    </div>
    </section>
    """
    st.markdown(test_html, unsafe_allow_html=True)


    # ---------- FIXED FOOTER ----------
    footer_html = """
    <style>
    footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: #f9f9f9;
    color: #555;
    text-align: center;
    padding: 10px 0;
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    border-top: 1px solid #e6e6e6;
    z-index: 9999;
    }
    </style>

    <footer>
    Built with ❤️ in Streamlit
    </footer>
    """

    # Render footer
    components.html(footer_html, height=60, scrolling=False)





# ---------- DASHBOARD ----------
def dashboard_ui():
    # top controls: prev/next week and Start New Week (carry prompt)
    left, mid, right = st.columns([1,2,1])
    with left:
        if st.button("⟵ Prev Week"):
            current = datetime.strptime(st.session_state.current_monday, "%Y-%m-%d").date()
            st.session_state.current_monday = utils.iso(current - timedelta(days=7))
            st.session_state.carry_prompt_shown_for_week = None
            st.rerun()
    with mid:
    # Heading slightly nudged left (inline approach)
        st.markdown(
            f"<div style='text-align:center; margin:8px 0 8px;'>"
            f"<h1 style='margin:0; display:inline-block; transform: translateX(-55px);'>"
            f"Goals — Week of {st.session_state.current_monday}</h1></div>",
            unsafe_allow_html=True
        )

        # Center + constrain the selectbox below the heading
        inner_left, inner_center, inner_right = st.columns([1, 2, 1])
        with inner_center:
            st.markdown("<div style='max-width:420px; margin:0 auto;'>", unsafe_allow_html=True)
            cat_filter = st.selectbox(
                "Filter category",
                options=CATEGORY_OPTIONS,
                index=0,
                key="dashboard_filter_category"
            )
            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.user:
        render_add_goal_form(st, st.session_state.user["id"], st.session_state.current_monday,
                         key_prefix="dashboard_quick_goal", expanded=False)
    with right:
        if st.button("Next Week ⟶"):
            current = datetime.strptime(st.session_state.current_monday, "%Y-%m-%d").date()
            st.session_state.current_monday = utils.iso(current + timedelta(days=7))
            st.session_state.carry_prompt_shown_for_week = None
            st.rerun()
            

    # Sidebar: user info, logout and create quick goal
    
    # if st.session_state.user:
    #     st.sidebar.markdown(f"👋 Hello, **{st.session_state.user['name']}**")
    #     if st.sidebar.button("🏠 Home"):
    #         go_to("home")
    #     if st.sidebar.button("🎯 Dashboard"):
    #         go_to("dashboard")
    #     if st.sidebar.button("📊 Visualizer"):
    #         go_to("visualizer")
    #     st.sidebar.markdown("---")
    #     if st.sidebar.button("🚪 Logout"):
    #         st.session_state.user = None
    #         st.session_state.carry_prompt_shown_for_week = None
    #         go_to("home")

        render_sidebar_for(key_prefix="dashboard")



    # ✅ CLEAR SIDEBAR INPUTS SAFELY ON NEXT RERUN
    if st.session_state.get("clear_quick_goal", False):
        st.session_state.quick_goal_title = ""
        st.session_state.quick_goal_desc = ""
        st.session_state.quick_goal_custom_dead = False
        st.session_state.pop("quick_goal_dead", None)
        st.session_state.clear_quick_goal = False


    # Reusable sidebar quick-add
    if st.session_state.user:
        render_add_goal_form(st.sidebar, st.session_state.user["id"], st.session_state.current_monday,
                            key_prefix="sidebar_quick_goal", expanded=True)


    # with st.sidebar.expander("➕ Quick Add Goal", expanded=True):
    #     g_title = st.text_input("Goal title", key="quick_goal_title")
    #     g_desc = st.text_area("Description (optional)", key="quick_goal_desc", height=80)
    #     use_custom_deadline = st.checkbox("Set custom deadline", key="quick_goal_custom_dead")
    #     custom_dead = None
    #     if use_custom_deadline:
    #         custom_dead = st.date_input("Custom deadline", key="quick_goal_dead")
    #     if st.button("Add Goal to this week"):
    #         if not g_title.strip():
    #             st.sidebar.error("Title required.")
    #         else:
    #             week_iso = st.session_state.current_monday
    #             cd_iso = custom_dead.strftime("%Y-%m-%d") if custom_dead else None
    #             utils.create_goal(st.session_state.user["id"], g_title.strip(), g_desc.strip(), week_iso, cd_iso)
    #             st.sidebar.success("Goal added.")
    #             st.session_state.clear_quick_goal = True
    #             st.rerun()

    # BEFORE RENDERING GOALS: prompt carry-over if needed (only once per selected week)
    prompt_carry_over_if_needed(st.session_state.user["id"], st.session_state.current_monday)

    # load goals for the week
    cat_arg = None if cat_filter == "All" else cat_filter.lower()
    goals = utils.get_goals_for_week(st.session_state.user["id"], st.session_state.current_monday, category=cat_arg)
    summary = utils.weekly_summary(st.session_state.user["id"], st.session_state.current_monday, category=cat_arg)
    # -------------------------
    # PRE-CLEAR: ensure any "just added" task form keys are removed BEFORE building widgets
    # (this is essential so text inputs are built empty)
    # -------------------------
    if goals is not None and not goals.empty:
        for g in goals.itertuples():
            gid = g.id
            just_added_flag = f"just_added_task_{gid}"
            expander_key = f"add_task_form_{gid}_expanded"
            title_key = f"t_title_{gid}"
            notes_key = f"t_notes_{gid}"
            due_key = f"t_due_{gid}"
            if st.session_state.get(just_added_flag, False):
                # remove the saved widget values before creating widgets
                for k in (title_key, notes_key, due_key):
                    st.session_state.pop(k, None)
                st.session_state.pop(just_added_flag, None)
                st.session_state[expander_key] = False

    # Top metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Goals", summary["goals"])
    c2.metric("Tasks", summary["tasks"])
    c3.metric("Carried", summary["carried"])
    c4.metric("Completion", f"{summary['completion']}%")

    st.markdown("---")
    if goals.empty:
        st.info("No goals for this week. Use the sidebar to add one.")
    else:
        # iterate goals and render cards
        for g in goals.itertuples():
            goal_id = g.id
            tasks = utils.get_tasks_for_goal(goal_id)
            progress = utils.goal_progress(tasks)

            st.markdown("<div class='card'>", unsafe_allow_html=True)

            # layout: tiny checkbox column, main content, actions column
            cb_col, main_col, action_col = st.columns([0.04, 3.0, 1.0])
            def _make_goal_toggle_cb(gid):
                def _cb():
                    state_key = f"goal_cb_{gid}"
                    checked_val = st.session_state.get(state_key, False)

                    # Update all tasks in DB
                    utils.mark_goal_completed(gid, completed=checked_val)

                    # Fetch child tasks to update UI state
                    tasks_df = utils.get_tasks_for_goal(gid)
                    for tid in tasks_df["id"].tolist():
                        st.session_state[f"task_cb_{tid}"] = checked_val

                    st.session_state["_last_change"] = f"goal:{gid}"
                    st.rerun()
                return _cb
            # --- left: goal-level checkbox ---
            with cb_col:
                is_goal_complete = (progress == 100)
                st.checkbox(
                    " ",
                    value=is_goal_complete,
                    key=f"goal_cb_{goal_id}",
                    label_visibility="collapsed",
                    on_change=_make_goal_toggle_cb(goal_id)
                )

                # def _make_goal_toggle_cb(gid):
                #     def _cb():
                #         state_key = f"goal_cb_{gid}"
                #         checked_val = st.session_state.get(state_key, False)

                #         # Update all tasks in DB
                #         utils.mark_goal_completed(gid, completed=checked_val)

                #         # Fetch child tasks to update UI state
                #         tasks_df = utils.get_tasks_for_goal(gid)
                #         for tid in tasks_df["id"].tolist():
                #             st.session_state[f"task_cb_{tid}"] = checked_val

                #         st.session_state["_last_change"] = f"goal:{gid}"
                #         st.rerun()
                #     return _cb


            # --- center: goal info + tasks list ---
            with main_col:
                st.markdown(f"<div class='goal-title'>{g.title}</div>", unsafe_allow_html=True)

                # show description if present
                if g.description:
                    st.markdown(f"<div class='muted'>{g.description}</div>", unsafe_allow_html=True)

                # always show category badge (fall back to 'personal' if missing)
                cat = getattr(g, "category", None) or "personal"
                st.markdown(
                    f"<div class='small' style='margin-top:6px'><b>Category:</b> "
                    f"<span style='padding:4px 8px;border-radius:6px;border:1px solid #e5e7eb'>{cat.title()}</span></div>",
                    unsafe_allow_html=True
                )




                # ---------------- GOAL DEADLINE ALERT ----------------
                deadline = g.custom_deadline if getattr(g, "custom_deadline", None) else (
                    (datetime.strptime(g.week_start, "%Y-%m-%d").date() + timedelta(days=6)).strftime("%Y-%m-%d")
                )
                deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
                days_left = (deadline_date - date.today()).days
                if days_left < 0:
                    alert_html = "<span style='color:#DC2626; font-weight:600;'>⚠️ Overdue</span>"
                elif days_left == 0:
                    alert_html = "<span style='color:#EA580C; font-weight:600;'>⏰ Deadline Today!</span>"
                elif 1 <= days_left <= 3:
                    alert_html = f"<span style='color:#CA8A04; font-weight:600;'>🕐 {days_left} days left</span>"
                else:
                    alert_html = f"<span style='color:#16A34A;'>✅ {days_left} days remaining</span>"

                st.markdown(f"<div class='small'>Deadline: <b>{deadline}</b> — {alert_html}</div>", unsafe_allow_html=True)

                st.markdown("<br/>", unsafe_allow_html=True)


                st.markdown("<br/>", unsafe_allow_html=True)

                # tasks listing
                if tasks.empty:
                    st.info("No tasks for this goal yet.")
                else:
                    for t in tasks.itertuples():
                        cols = st.columns([0.04, 0.72, 0.18, 0.06])
                        def _make_task_toggle_cb(task_id, title, notes, due_date, goal_id):
                            def _cb():
                                state_key = f"task_cb_{task_id}"
                                checked_val = st.session_state.get(state_key, False)
                                utils.update_task(task_id, title, notes or "", due_date or st.session_state.current_monday, checked_val)

                                # Check if all tasks under this goal are now complete
                                tasks_df = utils.get_tasks_for_goal(goal_id)
                                all_checked = bool(tasks_df["completed"].sum() == len(tasks_df))
                                st.session_state[f"goal_cb_{goal_id}"] = all_checked

                                st.session_state["_last_change"] = f"task:{task_id}"
                                st.rerun()
                            return _cb


                        cols = st.columns([0.04, 0.72, 0.18, 0.06])

                        # --- Checkbox in first column ---
                        with cols[0]:
                            st.checkbox(
                                " ",
                                value=bool(t.completed),
                                key=f"task_cb_{t.id}",
                                label_visibility="collapsed",
                                on_change=_make_task_toggle_cb(
                                    t.id,
                                    t.title,
                                    t.notes,
                                    t.due_date,
                                    goal_id
                                ),
                            )

                        # --- Task info ---
                        title_html = f"**{t.title}**"
                        if getattr(t, "carried_over", 0):
                            title_html += " <span style='color:var(--primary); font-size:12px;'>🔁 carried</span>"
                        cols[1].markdown(f"{title_html}  \n<small class='muted'>{t.notes or ''}</small>", unsafe_allow_html=True)

                        # --- Due date ---
                        cols[2].markdown(f"<div class='small'>Due: {t.due_date or '-'}</div>", unsafe_allow_html=True)
                        # ---------------- TASK DEADLINE ALERT ----------------
                        if t.due_date:
                            try:
                                due_dt = datetime.strptime(t.due_date, "%Y-%m-%d").date()
                                t_days_left = (due_dt - date.today()).days
                                if t_days_left < 0:
                                    due_badge = "⚠️ Overdue"
                                    badge_color = "#DC2626"
                                elif t_days_left == 0:
                                    due_badge = "⏰ Today"
                                    badge_color = "#EA580C"
                                elif 1 <= t_days_left <= 3:
                                    due_badge = f"⏳ {t_days_left}d left"
                                    badge_color = "#CA8A04"
                                else:
                                    due_badge = f"{t_days_left}d left"
                                    badge_color = "#16A34A"
                            except:
                                due_badge, badge_color = "", "#6B7280"
                        else:
                            due_badge, badge_color = "", "#6B7280"

                        cols[2].markdown(
                            f"<div class='small' style='color:{badge_color}; font-weight:600;'>{due_badge}</div>",
                            unsafe_allow_html=True
                        )
                        # -----------------------------------------------------


                        # Edit button toggles inline editor
                        if cols[3].button("✏️", key=f"edit_task_btn_{t.id}"):
                            st.session_state[f"edit_task_{t.id}"] = True

                        # inline editor if flagged
                        if st.session_state.get(f"edit_task_{t.id}", False):
                            # EDIT FORM
                            with st.form(f"edit_task_form_{t.id}"):
                                new_title = st.text_input("Task title", value=t.title, key=f"et_{t.id}")
                                new_notes = st.text_area("Notes", value=t.notes or "", key=f"en_{t.id}", height=80)
                                try:
                                    if t.due_date:
                                        default_due = datetime.strptime(t.due_date, "%Y-%m-%d").date()
                                    else:
                                        # default to the week end of current_monday
                                        week_monday = datetime.strptime(st.session_state.current_monday, "%Y-%m-%d").date()
                                        default_due = week_monday + timedelta(days=6)
                                except Exception:
                                    default_due = date.today()

                                new_due = st.date_input("Due date", value=default_due, key=f"ed_{t.id}")

                                save = st.form_submit_button("Save")
                                delete = st.form_submit_button("Delete")

                            if save:
                                utils.update_task(t.id, new_title.strip(), new_notes.strip(), new_due.strftime("%Y-%m-%d"), bool(t.completed))
                                st.success("Task updated.")
                                st.session_state.pop(f"edit_task_{t.id}", None)
                                st.rerun()

                            if delete:
                                # mark a confirmation flag; actual delete is done by separate confirm button outside the form
                                st.session_state[f"confirm_delete_task_{t.id}"] = True
                                st.session_state[f"edit_task_{t.id}"] = True
                                st.rerun()

                            # Confirmation UI (outside the form)
                            st.warning("Are you sure you want to DELETE this task? This cannot be undone.")
                            # wrapper div so CSS .confirm-row can control layout
                            st.markdown("<div class='confirm-row'>", unsafe_allow_html=True)
                            if st.button("Confirm", key=f"confirm_del_task_btn_{t.id}"):
                                utils.delete_task(t.id)
                                st.success("Task deleted.")
                                st.session_state.pop(f"edit_task_{t.id}", None)
                                st.session_state.pop(f"confirm_delete_task_{t.id}", None)
                                st.rerun()

                            if st.button("Cancel", key=f"cancel_del_task_btn_{t.id}"):
                                st.session_state.pop(f"confirm_delete_task_{t.id}", None)
                                st.session_state.pop(f"edit_task_{t.id}", None)
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)


                # -----------------------
                # Add Task Section (auto-clear + closed by default)
                # -----------------------
                expander_key = f"add_task_form_{goal_id}_expanded"
                title_key = f"t_title_{goal_id}"
                notes_key = f"t_notes_{goal_id}"
                due_key = f"t_due_{goal_id}"
                just_added_flag = f"just_added_task_{goal_id}"

                # ensure we always have a session state flag to control expander open/closed
                if expander_key not in st.session_state:
                    st.session_state[expander_key] = False

                # show expander (collapsed by default unless session requests otherwise)
                with st.expander("➕ Add Task", expanded=st.session_state[expander_key]):
                    with st.form(f"add_task_form_{goal_id}"):
                        t_title = st.text_input("Task title", key=title_key)
                        t_notes = st.text_area("Notes (optional)", key=notes_key, height=80)

                        # default due = end of current week (Monday + 6 days)
                        try:
                            week_monday = datetime.strptime(st.session_state.current_monday, "%Y-%m-%d").date()
                            default_due = week_monday + timedelta(days=6)
                        except Exception:
                            default_due = date.today()

                        t_due = st.date_input("Due date", value=default_due, key=due_key)
                        add_btn = st.form_submit_button("Add Task")

                    if add_btn:
                        if not t_title or not t_title.strip():
                            st.error("Title required.")
                        else:
                            utils.create_task(goal_id, t_title.strip(), t_notes.strip(), t_due.strftime("%Y-%m-%d"))
                            st.success("✅ Task added!")
                            # set flag for the next run: pre-clear inputs and collapse the expander
                            st.session_state[just_added_flag] = True
                            st.session_state[expander_key] = False
                            st.rerun()


            # --- right: actions and progress pill ---
            with action_col:
                st.markdown(f"<div style='text-align:right'><span class='progress-pill'>{progress}%</span></div>", unsafe_allow_html=True)
                st.markdown("<br/>", unsafe_allow_html=True)

                # Edit goal button
                if st.button("✏️ Edit Goal", key=f"edit_goal_btn_{goal_id}"):
                    st.session_state[f"edit_goal_{goal_id}"] = True
                if st.session_state.get(f"edit_goal_{goal_id}", False):
                    with st.form(f"edit_goal_form_{goal_id}"):
                        new_title = st.text_input("Goal title", value=g.title, key=f"gt_{goal_id}")
                        new_desc = st.text_area("Description", value=g.description or "", key=f"gd_{goal_id}", height=80)
                        cur_cat = getattr(g, "category", "personal").title()
                        new_cat = st.selectbox("Category", options=["Personal","Work","Study"], index=["Personal","Work","Study"].index(cur_cat), key=f"gc_{goal_id}")

                        try:
                            current_week_start = datetime.strptime(g.week_start, "%Y-%m-%d").date()
                        except Exception:
                            current_week_start = utils.monday_of_week(date.today())
                        new_week = st.date_input("Week start (Monday)", value=current_week_start, key=f"gw_{goal_id}")
                        use_cd = st.checkbox("Set custom deadline", key=f"gcd_flag_{goal_id}")
                        cd_val = None
                        if use_cd:
                            cd_val = st.date_input("Custom deadline", value=datetime.strptime(g.custom_deadline, "%Y-%m-%d").date() if g.custom_deadline else current_week_start + timedelta(days=6), key=f"gcd_{goal_id}")
                        save = st.form_submit_button("Save")
                        cancel = st.form_submit_button("Cancel")
                    if save:
                        cd_iso = cd_val.strftime("%Y-%m-%d") if cd_val else None
                        utils.update_goal(goal_id, new_title.strip(), new_desc.strip(), utils.iso(utils.monday_of_week(new_week)), cd_iso, category=new_cat.lower())
                        st.success("Goal updated.")
                        st.session_state.pop(f"edit_goal_{goal_id}", None)
                        st.rerun()
                    if cancel:
                        st.session_state.pop(f"edit_goal_{goal_id}", None)

                # Delete goal with confirm
                if st.button("🗑 Delete Goal", key=f"del_goal_btn_{goal_id}"):
                    st.session_state[f"confirm_del_goal_{goal_id}"] = True
                if st.session_state.get(f"confirm_del_goal_{goal_id}", False):
                    st.warning("Delete this goal and ALL its tasks? This cannot be undone.")
                    st.markdown("<div class='confirm-row'>", unsafe_allow_html=True)
                    if st.button("Confirm delete", key=f"confirm_del_goal_btn_{goal_id}"):
                        utils.delete_goal(goal_id)
                        st.success("Goal deleted.")
                        st.session_state.pop(f"confirm_del_goal_{goal_id}", None)
                        st.rerun()

                    if st.button("Cancel", key=f"cancel_del_goal_btn_{goal_id}"):
                        st.session_state.pop(f"confirm_del_goal_{goal_id}", None)
                    st.markdown("</div>", unsafe_allow_html=True)


            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br/>", unsafe_allow_html=True)

    utils.render_smart_insight_engine(
    st.session_state.user["id"],
    st.session_state.current_monday,
    summary
)

    
    # weekly charts + insights
    st.markdown("---")
    st.subheader("Weekly Progress")
    goals_list = utils.get_goals_for_week(st.session_state.user["id"], st.session_state.current_monday)
    rows = []
    for gg in goals_list.itertuples():
        tt = utils.get_tasks_for_goal(gg.id)
        rows.append({"goal": gg.title, "progress": utils.goal_progress(tt)})
    if rows:
        df = pd.DataFrame(rows)
        fig = px.bar(df, x="goal", y="progress", title="Progress by Goal", range_y=[0,100])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No goal progress to show for this week.")



# def graphs_ui():
#     st.title("📊 Analytics")
#     st.markdown("Overview of goals & task progress.")

#     # Example 1: Progress by goal (same as mini chart on dashboard)
#     goals = utils.get_goals_for_week(st.session_state.user["id"], st.session_state.current_monday)
#     rows = []
#     for g in goals.itertuples():
#         tasks = utils.get_tasks_for_goal(g.id)
#         rows.append({"goal": g.title, "progress": utils.goal_progress(tasks)})
#     if rows:
#         df = pd.DataFrame(rows)
#         fig = px.bar(df, x="goal", y="progress", title="Progress by Goal", range_y=[0,100])
#         st.plotly_chart(fig, use_container_width=True)
#     else:
#         st.info("No goals/tasks to visualize for this week.")

#     # Example 2: Basic tasks table for current week
#     all_rows = []
#     for g in goals.itertuples():
#         tdf = utils.get_tasks_for_goal(g.id)
#         for r in tdf.to_dict(orient="records"):
#             all_rows.append({"goal": g.title, "task": r["title"], "due": r.get("due_date", ""), "completed": r.get("completed", 0)})
#     if all_rows:
#         st.subheader("Tasks (table)")
#         st.dataframe(pd.DataFrame(all_rows))


def graphs_ui():

    # if st.session_state.user:
    #     st.sidebar.markdown(f"👋 Hello, **{st.session_state.user['name']}**")
    #     # use buttons (same style as dashboard) — include unique keys
    #     if st.sidebar.button("🏠 Home", key="sb_home_from_graphs"):
    #         go_to("home")
    #     if st.sidebar.button("🎯 Dashboard", key="sb_dashboard_from_graphs"):
    #         go_to("dashboard")
    #     if st.sidebar.button("📊 Visualizer", key="sb_visualizer_from_graphs"):
    #         go_to("visualizer")
    #     st.sidebar.markdown("---")
    #     if st.sidebar.button("🚪 Logout", key="sb_logout_from_graphs"):
    #         st.session_state.user = None
    #         st.session_state.carry_prompt_shown_for_week = None
    #         go_to("login")
    render_sidebar_for(key_prefix="graphs")
    
    st.title("📊 Weekly Progress & Smart Insights")
    st.markdown(f"<div class='small'>Week of {st.session_state.current_monday}</div>", unsafe_allow_html=True)

    cat_filter = st.selectbox("Filter category", options=CATEGORY_OPTIONS, index=0, key="graphs_filter_category")
    cat_arg = None if cat_filter == "All" else cat_filter.lower()

    # ---------- Progress Visualization ----------
    goals = utils.get_goals_for_week(st.session_state.user["id"], st.session_state.current_monday, category=cat_arg)

    rows = []
    for g in goals.itertuples():
        tasks = utils.get_tasks_for_goal(g.id)
        rows.append({"Goal": g.title, "Progress": utils.goal_progress(tasks)})

    if rows:
        df = pd.DataFrame(rows)
        st.subheader("Progress by Goal")
        fig = px.bar(df, x="Goal", y="Progress", range_y=[0,100],
                     color="Progress", color_continuous_scale="Blues",
                     title="Goal Completion (%)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No goals or tasks to visualize for this week.")

    # ---------- Summary Metrics ----------
    summary = utils.weekly_summary(st.session_state.user["id"], st.session_state.current_monday)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Goals", summary["goals"])
    c2.metric("Tasks", summary["tasks"])
    c3.metric("Carried", summary["carried"])
    c4.metric("Completion", f"{summary['completion']}%")
    # ---------------- DASHBOARD SUMMARY ALERT ----------------
    urgent_goals = []
    for g in goals.itertuples():
        d = g.custom_deadline or (datetime.strptime(g.week_start, "%Y-%m-%d").date() + timedelta(days=6)).strftime("%Y-%m-%d")
        d_date = datetime.strptime(d, "%Y-%m-%d").date()
        left = (d_date - date.today()).days
        if left <= 1:
            urgent_goals.append(f"{g.title} — due {d}")

    if urgent_goals:
        st.warning("⚠️ Upcoming Deadlines:\n" + "\n".join(f"- {x}" for x in urgent_goals))
    
    utils.render_smart_insight_engine(
    st.session_state.user["id"],
    st.session_state.current_monday,
    summary
)

# ----------------------------------------------------------

def focus_ui():
    import streamlit as st
    import streamlit.components.v1 as components
    import time
    render_sidebar_for(key_prefix="focus")

    st.markdown("<h1 style='text-align:center'>🕑 Focus Mode</h1>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; max-width:800px; margin:0 auto;'>Choose Countdown or Stopwatch. Controls run in your browser for smooth realtime updates.</div>", unsafe_allow_html=True)
    st.markdown("---")

    presets = {"Pomodoro (25m)": 25, "Deep Work (50m)": 50, "Short (5m)": 5}
    preset_keys = list(presets.keys()) + ["Custom"]

    left, right = st.columns([2, 1])
    with left:
        mode = st.selectbox("Mode", options=["Countdown", "Stopwatch"], index=0, key="focus_mode")
        if mode == "Countdown":
            choice = st.selectbox("Choose preset", options=preset_keys, index=0, key="focus_choice")
            if choice == "Custom":
                minutes = int(st.number_input("Minutes", min_value=1, max_value=240, value=25, key="focus_custom_minutes"))
            else:
                minutes = presets[choice]
        else:
            # for stopwatch we still allow setting an optional display cap (not required)
            minutes = int(st.number_input("Optional display cap minutes (0 = no cap)", min_value=0, max_value=1440, value=0, key="focus_stopwatch_cap"))
    with right:
        st.write("")  # spacer

    # prepare values to inject into JS
    initial_seconds = int(minutes * 60) if mode == "Countdown" else 0
    mode_js = "countdown" if mode == "Countdown" else "stopwatch"
    cap_seconds = int(minutes * 60) if (mode == "Stopwatch" and minutes > 0) else 0

    html = f"""
    <div style="font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; text-align:center; padding:8px;">
      <div id="display" style="font-size:72px; font-weight:700; margin:8px 0;">00:00</div>

      <div style="display:flex; gap:8px; justify-content:center; margin-bottom:12px; flex-wrap:wrap;">
        <button id="startBtn" style="padding:10px 14px; font-size:16px;">▶️ Start</button>
        <button id="pauseBtn" style="padding:10px 14px; font-size:16px; display:none;">⏸ Pause</button>
        <button id="resumeBtn" style="padding:10px 14px; font-size:16px; display:none;">▶️ Resume</button>
        <button id="resetBtn" style="padding:10px 14px; font-size:16px;">🔁 Reset</button>
        <button id="lapBtn" style="padding:10px 14px; font-size:16px; display:none;">📌 Lap</button>
      </div>

      <div style="width:90%; max-width:720px; margin:0 auto;">
        <div style="height:12px; background:#e6e6e6; border-radius:999px; overflow:hidden;">
          <div id="progress" style="height:12px; width:0%; background:linear-gradient(90deg,#6C63FF,#4F46E5);"></div>
        </div>
      </div>

      <div id="sub" style="color:#6B7280; font-size:13px; margin-top:8px;"></div>

      <div id="laps" style="margin-top:12px; max-height:120px; overflow:auto; text-align:left; display:none;">
        <b>Laps:</b>
        <ol id="lapList"></ol>
      </div>
    </div>

    <script>
    (function(){{
      // injected values
      const initialSeconds = {initial_seconds};   // for countdown only
      const mode = "{mode_js}";                  // "countdown" or "stopwatch"
      const capSeconds = {cap_seconds};          // optional cap for stopwatch (0 = no cap)

      // DOM refs
      const display = document.getElementById("display");
      const startBtn = document.getElementById("startBtn");
      const pauseBtn = document.getElementById("pauseBtn");
      const resumeBtn = document.getElementById("resumeBtn");
      const resetBtn = document.getElementById("resetBtn");
      const lapBtn = document.getElementById("lapBtn");
      const progress = document.getElementById("progress");
      const sub = document.getElementById("sub");
      const laps = document.getElementById("laps");
      const lapList = document.getElementById("lapList");

      // shared timer state (ms)
      let state = {{
        totalMs: mode === "countdown" ? initialSeconds * 1000 : 0,
        remainingMs: mode === "countdown" ? initialSeconds * 1000 : 0,
        elapsedMs: 0,            // used by stopwatch
        running: false,
        lastPerfStart: null,
        rafId: null,
        lapsArr: []
      }};

      function formatMs(ms) {{
        const totalSec = Math.max(0, Math.round(ms / 1000));
        const h = Math.floor(totalSec / 3600);
        const m = Math.floor((totalSec % 3600) / 60);
        const s = totalSec % 60;
        if (h > 0) {{
          return `${{String(h).padStart(2,'0')}}:${{String(m).padStart(2,'0')}}:${{String(s).padStart(2,'0')}}`;
        }}
        return `${{String(m).padStart(2,'0')}}:${{String(s).padStart(2,'0')}}`;
      }}

      function updateUI() {{
        if (mode === "countdown") {{
          display.textContent = formatMs(state.remainingMs);
          const pct = state.totalMs ? Math.round(((state.totalMs - state.remainingMs) / state.totalMs) * 100) : 0;
          progress.style.width = pct + "%";
        }} else {{
          display.textContent = formatMs(state.elapsedMs);
          if (capSeconds > 0) {{
            const pct = Math.min(100, Math.round((state.elapsedMs / (capSeconds * 1000)) * 100));
            progress.style.width = pct + "%";
          }} else {{
            // make progress a subtle pulse for stopwatch (or clear)
            progress.style.width = "100%";
          }}
        }}
      }}

      function tick() {{
        if (!state.running) return;
        const now = performance.now();
        if (mode === "countdown") {{
          const elapsed = now - state.lastPerfStart;
          state.remainingMs = Math.max(0, state.totalMs - elapsed);
          updateUI();
          if (state.remainingMs <= 0) {{
            state.running = false;
            sub.textContent = "✅ Session complete!";
            pauseBtn.style.display = "none";
            resumeBtn.style.display = "none";
            startBtn.style.display = "inline-block";
            cancelAnimationFrame(state.rafId);
            return;
          }}
        }} else {{
          // stopwatch mode: elapsedMs = priorElapsed + (now - lastPerfStart)
          state.elapsedMs = state.priorElapsed + (now - state.lastPerfStart);
          // optional cap handling:
          if (capSeconds > 0 && state.elapsedMs >= capSeconds * 1000) {{
            state.elapsedMs = capSeconds * 1000;
            state.running = false;
            sub.textContent = "⏹ Reached cap";
            pauseBtn.style.display = "none";
            resumeBtn.style.display = "none";
            startBtn.style.display = "inline-block";
            cancelAnimationFrame(state.rafId);
            updateUI();
            return;
          }}
          updateUI();
        }}
        state.rafId = requestAnimationFrame(tick);
      }}

      // Button behaviors
      startBtn.onclick = function() {{
        if (mode === "countdown") {{
          state.totalMs = initialSeconds * 1000;
          state.remainingMs = state.totalMs;
          state.lastPerfStart = performance.now();
          state.running = true;
          startBtn.style.display = "none";
          pauseBtn.style.display = "inline-block";
          resumeBtn.style.display = "none";
          sub.textContent = "";
          updateUI();
          state.rafId = requestAnimationFrame(tick);
        }} else {{
          // stopwatch: start from zero
          state.priorElapsed = 0;
          state.elapsedMs = 0;
          state.lastPerfStart = performance.now();
          state.running = true;
          startBtn.style.display = "none";
          pauseBtn.style.display = "inline-block";
          resumeBtn.style.display = "none";
          lapBtn.style.display = "inline-block";
          laps.style.display = "block";
          state.lapsArr = [];
          lapList.innerHTML = "";
          sub.textContent = "";
          updateUI();
          state.rafId = requestAnimationFrame(tick);
        }}
      }};

      pauseBtn.onclick = function() {{
        if (!state.running) return;
        state.running = false;
        cancelAnimationFrame(state.rafId);
        if (mode === "countdown") {{
          // freeze remaining based on elapsed
          const elapsed = performance.now() - state.lastPerfStart;
          state.remainingMs = Math.max(0, state.totalMs - elapsed);
        }} else {{
          // record priorElapsed
          state.priorElapsed = state.elapsedMs;
        }}
        pauseBtn.style.display = "none";
        resumeBtn.style.display = "inline-block";
        sub.textContent = "⏸ Paused";
      }};

      resumeBtn.onclick = function() {{
        if (state.running) return;
        state.lastPerfStart = performance.now();
        state.running = true;
        pauseBtn.style.display = "inline-block";
        resumeBtn.style.display = "none";
        sub.textContent = "";
        state.rafId = requestAnimationFrame(tick);
      }};

      resetBtn.onclick = function() {{
        // stop and reset everything
        state.running = false;
        cancelAnimationFrame(state.rafId);
        if (mode === "countdown") {{
          state.totalMs = initialSeconds * 1000;
          state.remainingMs = state.totalMs;
        }} else {{
          state.priorElapsed = 0;
          state.elapsedMs = 0;
          state.lapsArr = [];
          lapList.innerHTML = "";
          laps.style.display = "none";
          lapBtn.style.display = "none";
        }}
        pauseBtn.style.display = "none";
        resumeBtn.style.display = "none";
        startBtn.style.display = "inline-block";
        sub.textContent = "";
        updateUI();
      }};

      lapBtn.onclick = function() {{
        if (mode !== "stopwatch") return;
        // record a lap using current elapsed time
        const label = formatMs(state.elapsedMs);
        state.lapsArr.push(label);
        const li = document.createElement("li");
        li.textContent = label;
        lapList.insertBefore(li, lapList.firstChild);
      }};

      // UI init depending on mode
      if (mode === "countdown") {{
        lapBtn.style.display = "none";
        laps.style.display = "none";
        pauseBtn.style.display = "none";
        resumeBtn.style.display = "none";
        startBtn.style.display = "inline-block";
        state.totalMs = initialSeconds * 1000;
        state.remainingMs = state.totalMs;
        updateUI();
      }} else {{
        // stopwatch init
        lapBtn.style.display = "none";
        laps.style.display = "none";
        pauseBtn.style.display = "none";
        resumeBtn.style.display = "none";
        startBtn.style.display = "inline-block";
        state.priorElapsed = 0;
        state.elapsedMs = 0;
        updateUI();
      }}
    }})();
    </script>
    """

    # render component
    components.html(html, height=460, scrolling=False)

# ---------- ROUTER ----------
if st.session_state.page == "home":
    home_ui()
elif st.session_state.page == "login":
    login_ui()
elif st.session_state.page == "signup":
    signup_ui()
elif st.session_state.page == "dashboard":
    if st.session_state.user:
        dashboard_ui()
    else:
        go_to("home")
elif st.session_state.page == "visualizer":
    if st.session_state.user:
        graphs_ui()
    else:
        go_to("home")
elif st.session_state.page == "focus":
    if st.session_state.user:
        focus_ui()
    else:
        go_to("home")

