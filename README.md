## Live : https://mariamanzoor814-smart-goal-coach-app-rbfbwf.streamlit.app/

# Smart Goal-Setting & Productivity Coach

> A **Streamlit-based productivity app** that helps users set smarter goals, analyze habits, and stay consistent — without any paid AI APIs.

---

## 🧭 Overview

**Smart Goal-Setting & Productivity Coach** is your personal weekly productivity assistant.  
It allows you to:

- 🗓️ Create and track **weekly goals & subtasks**
- ✅ Monitor **deadlines and completion rates**
- 🔁 Automatically **carry forward unfinished goals** to the next week
- 🔍 Analyze **missed deadlines** and detect recurring issues
- 💬 Generate **AI-like motivational feedback** *(local rule-based logic)*
- 📊 Visualize your **progress and completion trends**

Everything runs **locally and free**, using only open-source tools — ideal for personal use or academic projects.

---

## ⚙️ Tech Stack

| Layer | Technology | Purpose |
|:------|:------------|:---------|
| **Frontend + Backend** | [Streamlit](https://streamlit.io/) | Unified UI + backend logic |
| **Database** | [SQLite](https://www.sqlite.org/) | Store goals, tasks, and progress records |
| **AI Simulation** | Rule-based Engine | Generate realistic motivational feedback |
| **Visualization** |  Streamlit Charts | Track progress and completion rates |
| **Deployment** | Streamlit Cloud | Free hosting, no setup required |

---

## ✨ Core Features

✅ **Add Weekly Goals & Subtasks**  
Plan structured, focused goals for each week.

✅ **Track Deadlines & Completion Status**  
Mark tasks as completed or overdue with simple UI controls.

✅ **Auto-Carry Forward Missed Goals**  
If a user misses a goal in one week, the app asks:  
> “Would you like to carry this goal forward into next week?”  
If the user chooses **Yes**, the goal is **cloned into the next week’s plan** and its **deadline is automatically extended**, keeping continuity and accountability intact.

✅ **Analyze Missed Tasks**  
The app prompts users to provide a reason for missed deadlines, helping identify recurring productivity blocks.

✅ **AI-like Motivational Feedback**  
Local rule-based “AI” generates motivational advice and improvement tips — no external API or internet dependency.

✅ **Progress Visualization Dashboard**  
Visual analytics showing completion trends, productivity score, and consistency streaks.

---

## show case

<img width="1920" height="953" alt="image" src="https://github.com/user-attachments/assets/7936ee14-96a0-4076-abad-f7be4a5d304a" />
<img width="1736" height="866" alt="image" src="https://github.com/user-attachments/assets/5e645019-9aa5-4f6b-80c7-6bdadf37d159" />
<img width="1742" height="867" alt="image" src="https://github.com/user-attachments/assets/7c01c589-e367-4fa8-9e3b-268bd9d8b864" />
<img width="1735" height="860" alt="image" src="https://github.com/user-attachments/assets/57f33fe3-72e4-42e6-8d5c-5493679c1655" />
<img width="1743" height="863" alt="image" src="https://github.com/user-attachments/assets/61e66754-844e-443f-b30e-889fafe6ca97" />
<img width="1742" height="864" alt="image" src="https://github.com/user-attachments/assets/557deba2-1d27-4e50-b3d3-eee938c8a1b3" />
<img width="1730" height="866" alt="image" src="https://github.com/user-attachments/assets/b0e8f367-1d1c-4b46-90e3-f7762b9278ad" />




## 🛠️ Installation & Setup

```bash
# 1️⃣ Clone this repository
git clone https://github.com/mariamanzoor814/Smart-Goal-Coach.git

# 2️⃣ Navigate to the project directory
cd smart-goal-coach

# 3️⃣ Install dependencies
pip install -r requirements.txt

# 4️⃣ Run the Streamlit app
streamlit run app.py
