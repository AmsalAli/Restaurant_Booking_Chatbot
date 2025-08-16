# Restaurant Booking Chatbot – Deployment Pack

This pack gives you a one-click-ready structure to deploy your Streamlit restaurant booking chatbot **for free** on **Streamlit Community Cloud** or **Hugging Face Spaces**, and a polished, Colab-free `streamlit_app.py`.

---

## Repo Layout

```
restaurant-booking-chatbot/
├─ streamlit_app.py
├─ requirements.txt
├─ README.md
├─ .streamlit/
│  └─ config.toml
└─ .gitignore
```

---

## File: `streamlit_app.py`

```python
# file: streamlit_app.py
"""
Restaurant Booking Chatbot (Streamlit)
- Colab-free version (no pyngrok/google.colab)
- Uses a local SQLite DB at data/reservations.db (ephemeral on free hosts)
- Includes download via st.download_button
"""

import streamlit as st
import datetime
import re
import sqlite3
import os
from datetime import time, timedelta

# Set the page title and favicon
st.set_page_config(
    page_title="Restaurant Booking Chatbot",
    page_icon="🍽️",
    layout="centered"
)

# Custom CSS for nicer UI
st.markdown(
    """
    <style>
    /* Background styling */
    .stApp {
        background-color: #f8f9fa;
        padding: 20px;
    }

    /* Header styling */
    h1 {
        color: #4A4A4A;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: bold;
        padding-bottom: 15px;
        border-bottom: 2px solid #FF5A5F;
        margin-bottom: 30px;
    }

    /* Chat message styling */
    .stChatMessage[data-testid="user-stChatMessage"] {
        background-color: #E6F7FF;
        border: 1px solid #B3E5FC;
        border-radius: 12px;
        padding: 12px;
        margin: 10px 0;
    }

    .stChatMessage[data-testid="assistant-stChatMessage"] {
        background-color: #F5F5F5;
        border: 1px solid #E0E0E0;
        border-radius: 12px;
        padding: 12px;
        margin: 10px 0;
    }

    /* Buttons */
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
    }
    .stButton>button:hover { transform: translateY(-1px); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Utilities ----------

def ensure_db():
    """Create 'data' dir and reservations table if not present."""
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect('data/reservations.db')
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY,
            name TEXT,
            guests INTEGER,
            date TEXT,
            time TEXT,
            email TEXT,
            phone TEXT,
            special_requests TEXT
        )
        """
    )
    conn.commit()
    conn.close()

# Database operations

def get_next_reservation_id():
    conn = sqlite3.connect('data/reservations.db')
    c = conn.cursor()
    c.execute("SELECT MAX(id) FROM reservations")
    max_id = c.fetchone()[0]
    conn.close()
    return 1 if max_id is None else max_id + 1


def save_reservation(reservation_data):
    conn = sqlite3.connect('data/reservations.db')
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO reservations (id, name, guests, date, time, email, phone, special_requests)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reservation_data['id'],
            reservation_data['name'],
            reservation_data['guests'],
            reservation_data['date'],
            reservation_data['time'],
            reservation_data['email'],
            reservation_data['phone'],
            reservation_data.get('special_requests', '')
        )
    )
    conn.commit()
    conn.close()


def get_all_reservations():
    conn = sqlite3.connect('data/reservations.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM reservations ORDER BY date, time")
    result = [dict(row) for row in c.fetchall()]
    conn.close()
    return result


def update_reservation(reservation):
    conn = sqlite3.connect('data/reservations.db')
    c = conn.cursor()
    c.execute(
        "UPDATE reservations SET name=?, guests=?, date=?, time=?, email=?, phone=?, special_requests=? WHERE id=?",
        (
            reservation['name'],
            reservation['guests'],
            reservation['date'],
            reservation['time'],
            reservation['email'],
            reservation['phone'],
            reservation.get('special_requests', ''),
            reservation['id'],
        ),
    )
    conn.commit()
    conn.close()


def delete_reservation(reservation_id):
    conn = sqlite3.connect('data/reservations.db')
    c = conn.cursor()
    c.execute("DELETE FROM reservations WHERE id=?", (reservation_id,))
    conn.commit()
    conn.close()


# ---------- Validation Helpers ----------

def is_valid_email(email: str) -> bool:
    return re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", email) is not None


def is_valid_phone(phone: str) -> bool:
    return re.match(r"^[+\d][\d\s()-]{6,}$", phone) is not None


# ---------- Chat State ----------

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'reservation_data' not in st.session_state:
    st.session_state.reservation_data = {}

if 'current_step' not in st.session_state:
    st.session_state.current_step = 'greeting'

if 'editing_id' not in st.session_state:
    st.session_state.editing_id = None


# ---------- Chat Flow ----------

def add_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})


def reset_chat():
    st.session_state.messages = []
    st.session_state.reservation_data = {}
    st.session_state.current_step = 'greeting'
    st.session_state.editing_id = None


def process_input(user_input: str):
    user_input = user_input.strip()
    if not user_input:
        return

    add_message("user", user_input)

    # Simple intent detection
    text = user_input.lower()
    intents = {
        'book': any(k in text for k in ["book", "reserve", "reservation", "table"]),
        'manage': any(k in text for k in ["manage", "update", "change", "edit", "cancel"]),
        'help': any(k in text for k in ["help", "how", "instructions"]),
    }

    if st.session_state.current_step == 'greeting':
        add_message(
            "assistant",
            "Hello! I'm your booking assistant. Would you like to **book a table** or **manage reservations**?",
        )
        st.session_state.current_step = 'await_intent'
        return

    if st.session_state.current_step == 'await_intent':
        if intents['book']:
            st.session_state.reservation_data = {}
            add_message("assistant", "Great! How many people?")
            st.session_state.current_step = 'guests'
        elif intents['manage']:
            add_message("assistant", "Please enter your reservation ID to manage it.")
            st.session_state.current_step = 'manage_id'
        else:
            add_message("assistant", "Please say **book** or **manage**.")
        return

    # Booking steps
    if st.session_state.current_step == 'guests':
        try:
            guests = int(re.findall(r"\d+", user_input)[0])
            st.session_state.reservation_data['guests'] = max(1, min(20, guests))
            add_message("assistant", "Select the **date** for your reservation.")
            st.session_state.current_step = 'date'
        except Exception:
            add_message("assistant", "Please provide a valid number of guests (e.g., 2, 4, 6).")

    elif st.session_state.current_step == 'date':
        # Handled via date picker; we still accept textual YYYY-MM-DD.
        try:
            datetime.date.fromisoformat(user_input[:10])
            st.session_state.reservation_data['date'] = user_input[:10]
            add_message("assistant", "Now choose a **time** (e.g., 19:30).")
            st.session_state.current_step = 'time'
        except Exception:
            add_message("assistant", "Use the date picker or type as YYYY-MM-DD.")

    elif st.session_state.current_step == 'time':
        try:
            hh, mm = [int(x) for x in user_input.split(":")]
            t = time(hh, mm)
            # simple opening hours guard
            open_t, close_t = time(11, 0), time(22, 0)
            if not (open_t <= t <= close_t):
                add_message("assistant", "We are open 11:00–22:00. Pick a time within hours.")
                return
            st.session_state.reservation_data['time'] = f"{hh:02d}:{mm:02d}"
            add_message("assistant", "What's your **name**?")
            st.session_state.current_step = 'name'
        except Exception:
            add_message("assistant", "Please type time like HH:MM (e.g., 18:45).")

    elif st.session_state.current_step == 'name':
        st.session_state.reservation_data['name'] = user_input.title()
        add_message("assistant", "Your **email**?")
        st.session_state.current_step = 'email'

    elif st.session_state.current_step == 'email':
        if is_valid_email(user_input):
            st.session_state.reservation_data['email'] = user_input
            add_message("assistant", "Your **phone number**?")
            st.session_state.current_step = 'phone'
        else:
            add_message("assistant", "That email looks invalid. Try again.")

    elif st.session_state.current_step == 'phone':
        if is_valid_phone(user_input):
            st.session_state.reservation_data['phone'] = user_input
            add_message("assistant", "Any **special requests**? If none, say 'no'.")
            st.session_state.current_step = 'special'
        else:
            add_message("assistant", "Please provide a valid phone number.")

    elif st.session_state.current_step == 'special':
        if user_input.lower() not in ("no", "none", "n/a"):
            st.session_state.reservation_data['special_requests'] = user_input
        else:
            st.session_state.reservation_data['special_requests'] = ""

        # Summarize & confirm
        r = st.session_state.reservation_data
        add_message(
            "assistant",
            (
                f"Please confirm:\n\n"
                f"• Name: {r['name']}\n"
                f"• Guests: {r['guests']}\n"
                f"• Date: {r['date']}\n"
                f"• Time: {r['time']}\n"
                f"• Email: {r['email']}\n"
                f"• Phone: {r['phone']}\n"
                f"• Special: {r.get('special_requests','')}\n\n"
                "Type **confirm** to save or **edit** to make changes."
            ),
        )
        st.session_state.current_step = 'confirm'

    elif st.session_state.current_step == 'confirm':
        if user_input.lower().strip() == 'confirm':
            ensure_db()
            new_id = get_next_reservation_id()
            st.session_state.reservation_data['id'] = new_id
            save_reservation(st.session_state.reservation_data)
            add_message("assistant", f"✅ Reservation saved! Your ID is **{new_id}**. Need anything else?")
            st.session_state.current_step = 'post_confirmation'
        elif user_input.lower().strip() == 'edit':
            add_message("assistant", "What would you like to change? (guests, date, time, name, email, phone, special)")
            st.session_state.current_step = 'correction'
        else:
            add_message("assistant", "Please type **confirm** or **edit**.")

    elif st.session_state.current_step == 'correction':
        field = user_input.lower()
        mapping = {
            'guests': 'guests',
            'people': 'guests',
            'party': 'guests',
            'date': 'date',
            'day': 'date',
            'time': 'time',
            'hour': 'time',
            'name': 'name',
            'email': 'email',
            'phone': 'phone',
            'number': 'phone',
            'special': 'special_requests',
            'requests': 'special_requests',
        }
        key = mapping.get(field)
        if not key:
            add_message("assistant", "Specify one of: guests, date, time, name, email, phone, special.")
            return
        st.session_state.reservation_data.pop(key, None)
        add_message("assistant", f"Okay, please provide new value for **{key}**.")
        st.session_state.current_step = key

    # Editing individual fields after correction intent
    elif st.session_state.current_step == 'guests' and 'guests' not in st.session_state.reservation_data:
        try:
            guests = int(re.findall(r"\d+", user_input)[0])
            st.session_state.reservation_data['guests'] = max(1, min(20, guests))
            add_message("assistant", "Continue: type **confirm** to save or edit another field.")
            st.session_state.current_step = 'confirm'
        except Exception:
            add_message("assistant", "Please provide a valid number of guests (e.g., 2, 4, 6).")

    elif st.session_state.current_step == 'date' and 'date' not in st.session_state.reservation_data:
        try:
            datetime.date.fromisoformat(user_input[:10])
            st.session_state.reservation_data['date'] = user_input[:10]
            add_message("assistant", "Continue: type **confirm** to save or edit another field.")
            st.session_state.current_step = 'confirm'
        except Exception:
            add_message("assistant", "Use the date picker or type as YYYY-MM-DD.")

    elif st.session_state.current_step == 'time' and 'time' not in st.session_state.reservation_data:
        try:
            hh, mm = [int(x) for x in user_input.split(":")]
            t = time(hh, mm)
            open_t, close_t = time(11, 0), time(22, 0)
            if not (open_t <= t <= close_t):
                add_message("assistant", "We are open 11:00–22:00. Pick a time within hours.")
                return
            st.session_state.reservation_data['time'] = f"{hh:02d}:{mm:02d}"
            add_message("assistant", "Continue: type **confirm** to save or edit another field.")
            st.session_state.current_step = 'confirm'
        except Exception:
            add_message("assistant", "Please type time like HH:MM (e.g., 18:45).")

    elif st.session_state.current_step == 'name' and 'name' not in st.session_state.reservation_data:
        st.session_state.reservation_data['name'] = user_input.title()
        add_message("assistant", "Continue: type **confirm** to save or edit another field.")
        st.session_state.current_step = 'confirm'

    elif st.session_state.current_step == 'email' and 'email' not in st.session_state.reservation_data:
        if is_valid_email(user_input):
            st.session_state.reservation_data['email'] = user_input
            add_message("assistant", "Continue: type **confirm** to save or edit another field.")
            st.session_state.current_step = 'confirm'
        else:
            add_message("assistant", "That email looks invalid. Try again.")

    elif st.session_state.current_step == 'phone' and 'phone' not in st.session_state.reservation_data:
        if is_valid_phone(user_input):
            st.session_state.reservation_data['phone'] = user_input
            add_message("assistant", "Continue: type **confirm** to save or edit another field.")
            st.session_state.current_step = 'confirm'
        else:
            add_message("assistant", "Please provide a valid phone number.")

    elif st.session_state.current_step == 'special_requests' and 'special_requests' not in st.session_state.reservation_data:
        st.session_state.reservation_data['special_requests'] = user_input
        add_message("assistant", "Continue: type **confirm** to save or edit another field.")
        st.session_state.current_step = 'confirm'

    # Manage reservation path
    elif st.session_state.current_step == 'manage_id':
        try:
            rid = int(re.findall(r"\d+", user_input)[0])
            st.session_state.editing_id = rid
            ensure_db()
            rows = [r for r in get_all_reservations() if r['id'] == rid]
            if not rows:
                add_message("assistant", f"I couldn't find reservation ID {rid}. Try again.")
            else:
                r = rows[0]
                add_message(
                    "assistant",
                    (
                        "Found it! What would you like to do?\n"
                        "• Type **update** to edit fields\n"
                        "• Type **cancel** to delete\n"
                        "• Type **show** to display details"
                    ),
                )
                st.session_state.current_step = 'manage_action'
        except Exception:
            add_message("assistant", "Please enter a valid numeric reservation ID.")

    elif st.session_state.current_step == 'manage_action':
        act = user_input.lower()
        if act == 'cancel':
            delete_reservation(st.session_state.editing_id)
            add_message("assistant", "Reservation cancelled.")
            st.session_state.current_step = 'greeting'
        elif act == 'show':
            rows = [r for r in get_all_reservations() if r['id'] == st.session_state.editing_id]
            if rows:
                r = rows[0]
                add_message(
                    "assistant",
                    (
                        f"Reservation **{r['id']}**: {r['name']}, {r['guests']} guests, {r['date']} {r['time']}, "
                        f"{r['email']}, {r['phone']}, Special: {r.get('special_requests','')}"
                    ),
                )
            else:
                add_message("assistant", "Reservation not found anymore.")
        elif act == 'update':
            add_message("assistant", "Which field to update? (guests, date, time, name, email, phone, special)")
            st.session_state.current_step = 'correction'
        else:
            add_message("assistant", "Please type one of: update, cancel, show.")


# ---------- UI ----------

st.title("🍽️ Restaurant Booking Chatbot")

with st.expander("How it works", expanded=True):
    st.write(
        "Use the chat below to book or manage a reservation. You can also use the sidebar to quick-fill date/time.")

# Sidebar quick inputs (optional UX sugar)
with st.sidebar:
    st.header("Quick Inputs")
    today = datetime.date.today()
    date_pick = st.date_input("Date", value=today)
    time_pick = st.time_input("Time", value=time(19, 0))
    if st.button("Use date/time"):
        # why: enable mouse-only users to fill fields quickly
        if st.session_state.current_step in {"date", "time"}:
            if st.session_state.current_step == 'date':
                process_input(date_pick.isoformat())
            else:
                process_input(time_pick.strftime("%H:%M"))
            st.rerun()

# Existing reservations viewer
with st.expander("All Reservations"):
    ensure_db()
    rows = get_all_reservations()
    if rows:
        st.table(rows)
    else:
        st.info("No reservations yet.")

# Render messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])  # why: use markdown for bold/lines

# Quick action buttons
with st.container():
    col1, col2 = st.columns(2)
    if col1.button("Book a Table", key="action_book"):
        process_input("I want to book a table")
        st.rerun()
    if col2.button("Manage Reservations", key="action_manage"):
        process_input("I want to manage my reservations")
        st.rerun()

# Chat input
user_input = st.chat_input("Type your message here...")
if user_input:
    process_input(user_input)
    st.rerun()

# Reset
if st.button("Reset Chat"):
    reset_chat()
    st.rerun()

# Download the database
try:
    with open('data/reservations.db', 'rb') as f:
        db_bytes = f.read()
    st.download_button(
        label="Download Database",
        data=db_bytes,
        file_name="reservations.db",
        mime="application/octet-stream",
        help="Download the current SQLite database"
    )
except FileNotFoundError:
    st.info("No database found yet. Create a reservation first.")
except Exception as e:
    st.error(f"Error preparing database download: {e}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; padding: 20px 0;">
        <p><strong>Fine Dining Restaurant</strong></p>
        <p>123 Gourmet Avenue, Foodie District</p>
        <p>Opening Hours: 11:00 AM - 10:00 PM, 7 days a week</p>
        <p>For special events and large parties, please call us directly at (555) 123-4567</p>
        <small>Powered by Streamlit Chatbot</small>
    </div>
    """,
    unsafe_allow_html=True,
)
```

---

## File: `requirements.txt`

```txt
streamlit>=1.35.0
```

> If your original notebook used extra libraries, add them here.

---

## File: `.streamlit/config.toml`

```toml
[theme]
base = "light"
primaryColor = "#FF5A5F"
textColor = "#262730"
font = "sans serif"
```

---

## File: `.gitignore`

```gitignore
# Python
__pycache__/
*.pyc

# Streamlit
.streamlit/secrets.toml

# OS
.DS_Store
Thumbs.db

# DB (optional ignore if you don’t want to commit it)
data/*.db
```

---

## File: `README.md`

````markdown
# 🍽️ Restaurant Booking Chatbot (Streamlit)

Colab-free Streamlit app with a local SQLite database. Deployable for **free** on Streamlit Community Cloud or Hugging Face Spaces.

## Demo Locally
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
````

## Deploy – Option A: Streamlit Community Cloud (Free)

1. Push this folder to a **public GitHub repo**.
2. Go to [https://share.streamlit.io/](https://share.streamlit.io/) (Community Cloud) → **New app**.
3. Select your repo, branch, and set **Main file path** to `streamlit_app.py`.
4. Click **Deploy**. Your app gets a stable URL you can put on your CV.

### Notes

- The SQLite file (`data/reservations.db`) is **ephemeral**. It's fine for demos.
- You can add a custom subdomain in Community Cloud settings.

## Deploy – Option B: Hugging Face Spaces (Free)

1. Create a new **Space** → **Streamlit** → Public.
2. Upload `streamlit_app.py`, `requirements.txt`, `.streamlit/config.toml`, and `.gitignore`.
3. In **Settings → App File**, set `streamlit_app.py`.
4. The Space will build and give you a stable URL.

## Persistence Options (Optional)

For long-term storage across restarts, use a free external DB:

- **Deta Base**, **Supabase (free tier)**, or **TinyDB (file in HF Space)**. Replace SQLite calls accordingly.

## Common Issues

- *Module not found*: Add it to `requirements.txt` and redeploy.
- *App sleeps when idle*: Free tiers may cold-start; just reload – the URL stays stable.

```

---

## What changed vs. your Colab notebook?
- Removed `pyngrok` and `google.colab` dependencies.
- Replaced `files.download(...)` with `st.download_button(...)`.
- Ensured the `data/` directory is created automatically.

---

## How to use this pack
1. Copy these files into a new GitHub repo.
2. Deploy with **Streamlit Community Cloud** or **Hugging Face Spaces** using the steps above.
3. Put the resulting URL on your CV.

```
