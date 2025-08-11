import streamlit as st
import datetime
import re
import sqlite3
import os
from datetime import time, timedelta
from google.colab import files  # Import for Colab integration

# Set the page title and favicon
st.set_page_config(
    page_title="Restaurant Booking Chatbot",
    page_icon="🍽️",
    layout="centered"
)

# Inject custom CSS styles into the Streamlit application for better styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
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
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 15px;
    }

    /* User message styling */
    .stChatMessage[data-testid="user-stChatMessage"] {
        background-color: #E7F5FF;
    }

    /* Assistant message styling */
    .stChatMessage[data-testid="assistant-stChatMessage"] {
        background-color: #F5F5F5;
    }

    /* Button styling */
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }

    /* Primary button styling */
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }

    /* Date picker styling */
    .stDateInput>div>div {
        border-radius: 10px;
    }

    /* Chat input styling */
    .stChatInputContainer {
        border-top: 1px solid #e0e0e0;
        padding-top: 15px;
    }

    /* Footer styling */
    footer {
        text-align: center;
        margin-top: 50px;
        color: #888;
        font-size: 0.8em;
    }
</style>
""", unsafe_allow_html=True)

# Database setup
def init_db():
    # Create database directory if it doesn't exist
    os.makedirs('data', exist_ok=True)

    # Connect to SQLite database (it will be created if it doesn't exist)
    conn = sqlite3.connect('data/reservations.db')
    c = conn.cursor()

    # Create reservations table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            guests INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            special_requests TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# Call database initialization
init_db()

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
        "INSERT INTO reservations (id, name, guests, date, time, email, phone, special_request) VALUES (?,?, ?, ?, ?, ?, ?, ?)",
        (
            reservation_data['id'],
            reservation_data['name'],
            reservation_data['guests'],
            reservation_data['date'],
            reservation_data['time'],
            reservation_data['email'],
            reservation_data['phone'],
            reservation_data.get('special_requests', '') #why .get?
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
        "UPDATE reservations SET name=?, guests=?, date=?, time=?, email=?, phone=? WHERE id=?",
        (
            reservation['name'],
            reservation['guests'],
            reservation['date'],
            reservation['time'],
            reservation['email'],
            reservation['phone'],
            reservation['id'],
            reservation.get('special_requests', '')
        )
    )
    conn.commit()
    conn.close()

def delete_reservation(reservation_id):
    conn = sqlite3.connect('data/reservations.db')
    c = conn.cursor()
    c.execute("DELETE FROM reservations WHERE id=?", (reservation_id,))
    conn.commit()
    conn.close()

# Define session state variables if they don't exist
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'current_step' not in st.session_state:
    st.session_state.current_step = 'greeting'

if 'reservation_data' not in st.session_state:
    st.session_state.reservation_data = {}

# Load reservations from database instead of session state
if 'reservations' not in st.session_state:
    st.session_state.reservations = get_all_reservations()

if 'reservation_id' not in st.session_state:
    st.session_state.reservation_id = get_next_reservation_id()

# Helper functions
def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.[a-z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    pattern = r'^\+?\d{10,15}$'
    return re.match(pattern, phone) is not None

def add_message(role, message):
    st.session_state.chat_history.append({"role": role, "message": message})

def reset_chat():
    st.session_state.chat_history = []
    st.session_state.current_step = 'greeting'
    st.session_state.reservation_data = {}
    # Reload reservations from database
    st.session_state.reservations = get_all_reservations()
    # Reset reservation ID
    st.session_state.reservation_id = get_next_reservation_id()
    add_message("assistant", "👋 Welcome to our Restaurant Booking Chatbot! I can help you book a new table or manage your existing reservations. How can I help you today?")

# Process user input based on current step
def process_input(user_input):
    # Add user message to chat history
    add_message("user", user_input)

    # Process based on current step
    if st.session_state.current_step == 'greeting':
        if ('book' in user_input.lower() or 'table' in user_input.lower()) and not ('manage' in user_input.lower() or 'cancel' in user_input.lower() or 'modify' in user_input.lower()):
            add_message("assistant", "Great! I'll help you book a table. Please follow the prompts and I'll guide you through the reservation process.")
            add_message("assistant", "How many people will be dining?")
            st.session_state.current_step = 'guests'
        elif 'manage' in user_input.lower() or 'cancel' in user_input.lower() or 'modify' in user_input.lower():
            if len(st.session_state.reservations) > 0:
                reservation_list = "Here are your reservations:\n"
                for i, res in enumerate(st.session_state.reservations):
                    # Display the index + 1 for user-friendly numbering, but also show reservation ID
                    reservation_list += f"{i+1}. Reservation #{res['id']} - {res['name']} - {res['date']} at {res['time']} - {res['guests']} guests\n"
                reservation_list += "\nPlease type the number (1, 2, 3, etc.) of the reservation you want to manage."
                add_message("assistant", reservation_list)
                st.session_state.current_step = 'select_reservation'
            else:
                add_message("assistant", "You don't have any reservations yet. Would you like to make a new booking?")
                st.session_state.current_step = 'greeting'
        else:
            add_message("assistant", "I can help you book a table or manage existing reservations. What would you like to do?")

    elif st.session_state.current_step == 'guests':
        try:
            num_guests = int(user_input)
            if num_guests > 0 and num_guests <= 20:
                st.session_state.reservation_data['guests'] = num_guests
                add_message("assistant", f"Great! A table for {num_guests} guests. Now, please select a date for your reservation.")
                st.session_state.current_step = 'date'
            else:
                add_message("assistant", "Please enter a valid number between 1 and 20.")
        except ValueError:
            add_message("assistant", "Please enter a valid number.")

    elif st.session_state.current_step == 'date':
        # We'll handle date selection in the main UI flow
        pass

    elif st.session_state.current_step == 'time':
        # We'll handle time selection in the main UI flow
        pass

    elif st.session_state.current_step == 'name':
        if len(user_input.strip()) >= 2:
            st.session_state.reservation_data['name'] = user_input
            add_message("assistant", "Thank you! Please provide your email address for the reservation confirmation.")
            st.session_state.current_step = 'email'
        else:
            add_message("assistant", "Please enter a valid name.")

    elif st.session_state.current_step == 'email':
        if validate_email(user_input):
            st.session_state.reservation_data['email'] = user_input
            add_message("assistant", "Great! Lastly, may I have your phone number?")
            st.session_state.current_step = 'phone'
        else:
            add_message("assistant", "Please enter a valid email address.")

    elif st.session_state.current_step == 'phone':
        if validate_phone(user_input):
            st.session_state.reservation_data['phone'] = user_input

            # Instead of just showing a text summary, we'll show it in the next step
            add_message("assistant", "Great! Please review your reservation details.")
            st.session_state.current_step = 'confirmation'
        else:
            add_message("assistant", "Please enter a valid phone number.")

    elif st.session_state.current_step == 'confirmation':
        if user_input.lower() in ['yes', 'y', 'correct', 'right', 'yeah']:
            # Add the reservation to the database with an ID
            reservation = st.session_state.reservation_data.copy()
            reservation['id'] = st.session_state.reservation_id

            # Save to database
            save_reservation(reservation)

            # Refresh reservations list from database
            st.session_state.reservations = get_all_reservations()

            # Update next ID
            st.session_state.reservation_id = get_next_reservation_id()

            add_message("assistant", f"Perfect! Your reservation has been confirmed. Your reservation ID is #{reservation['id']}. We look forward to seeing you on {reservation['date']} at {reservation['time']}. Would you like to make another reservation or manage existing ones?")
            st.session_state.reservation_data = {}
            # Change to a new step for the confirmation response
            st.session_state.current_step = 'post_confirmation'
        else:
            add_message("assistant", "Let's make corrections. What information would you like to change? (guests, date, time, name, email, phone)")
            st.session_state.current_step = 'correction'

    elif st.session_state.current_step == 'correction':
        correction_field = user_input.lower()
        if correction_field in ['guests', 'people', 'party size', 'party']:
            add_message("assistant", "How many people will be dining?")
            st.session_state.current_step = 'guests'
        elif correction_field in ['date', 'day']:
            add_message("assistant", "Please select a new date for your reservation.")
            st.session_state.current_step = 'date'
        elif correction_field in ['time', 'hour']:
            add_message("assistant", "Please select a new time for your reservation.")
            st.session_state.current_step = 'time'
        elif correction_field in ['name']:
            add_message("assistant", "What is your name?")
            st.session_state.current_step = 'name'
        elif correction_field in ['email']:
            add_message("assistant", "What is your email address?")
            st.session_state.current_step = 'email'
        elif correction_field in ['phone', 'number', 'telephone', 'contact']:
            add_message("assistant", "What is your phone number?")
            st.session_state.current_step = 'phone' #Here
        else:
            add_message("assistant", "I didn't understand which field you want to correct. Please specify: guests, date, time, name, email, or phone.")

    elif st.session_state.current_step == 'select_reservation':
        try:
            selection = int(user_input)

            if 1 <= selection <= len(st.session_state.reservations):
                # Get the reservation at the selected index (adjusting for 0-based indexing)
                selected_reservation = st.session_state.reservations[selection-1]
                # Store the index for later use
                st.session_state.selected_res_index = selection-1

                # Get the actual reservation ID from the selected entry
                reservation_id = selected_reservation['id']

                add_message("assistant", f"You selected reservation #{reservation_id}. Would you like to cancel or modify this reservation?")
                st.session_state.current_step = 'manage_reservation'
            else:
                add_message("assistant", "Please enter a valid reservation number.")
        except ValueError:
            add_message("assistant", "Please enter a valid reservation number.")

    elif st.session_state.current_step == 'manage_reservation':
        if 'cancel' in user_input.lower():
            add_message("assistant", "Are you sure you want to cancel this reservation? (yes/no)")
            st.session_state.current_step = 'confirm_cancel'
        elif 'modify' in user_input.lower() or 'change' in user_input.lower() or 'edit' in user_input.lower():
            add_message("assistant", "What would you like to modify? (guests, date, time, name, email, phone)")
            st.session_state.current_step = 'select_modification'
        else:
            add_message("assistant", "Please specify if you want to cancel or modify this reservation.")

    elif st.session_state.current_step == 'confirm_cancel':
        if user_input.lower() in ['yes', 'y', 'yeah']:
            canceled_res = st.session_state.reservations[st.session_state.selected_res_index]

            # Delete from database
            delete_reservation(canceled_res['id'])

            # Refresh reservations list
            st.session_state.reservations = get_all_reservations()

            add_message("assistant", f"Reservation #{canceled_res['id']} has been canceled successfully. We appreciate your promptness in letting us know. Is there anything else I can help you with?")
            st.session_state.current_step = 'greeting'
        else:
            add_message("assistant", "Your reservation has not been canceled and remains active. Thank you for keeping your reservation with us. Is there anything else I can help you with today?")
            st.session_state.current_step = 'greeting'

    elif st.session_state.current_step == 'select_modification':
        field = user_input.lower()
        st.session_state.modification_field = field

        if field in ['guests', 'people', 'party size', 'party']:
            add_message("assistant", "How many people will be dining?")
            st.session_state.current_step = 'modify_field'
        elif field in ['date', 'day']:
            add_message("assistant", "Please select a new date for your reservation.")
            # Special step for modifying date with date picker
            st.session_state.current_step = 'modify_date'
        elif field in ['time', 'hour']:
            add_message("assistant", "Please select a new time for your reservation.")
            # Special step for modifying time with time picker
            st.session_state.current_step = 'modify_time'
        elif field in ['name']:
            add_message("assistant", "What is your name?")
            st.session_state.current_step = 'modify_field'
        elif field in ['email']:
            add_message("assistant", "What is your email address?")
            st.session_state.current_step = 'modify_field'
        elif field in ['phone', 'number', 'telephone', 'contact']:
            add_message("assistant", "What is your phone number?")
            st.session_state.current_step = 'modify_field'
        else:
            add_message("assistant", "I didn't understand which field you want to modify. Please specify: guests, date, time, name, email, or phone.")

    elif st.session_state.current_step == 'modify_field':
        field = st.session_state.modification_field

        # Map the user friendly terms to actual field names
        field_mapping = {
            'guests': 'guests', 'people': 'guests', 'party size': 'guests', 'party': 'guests',
            'date': 'date', 'day': 'date',
            'time': 'time', 'hour': 'time',
            'name': 'name',
            'email': 'email',
            'phone': 'phone', 'number': 'phone', 'telephone': 'phone', 'contact': 'phone'
        }

        actual_field = next((field_mapping[key] for key in field_mapping if key == field), None)

        # Validate the input based on the field
        is_valid = False
        error_message = ""

        if actual_field == 'guests':
            try:
                num_guests = int(user_input)
                if num_guests > 0 and num_guests <= 20:
                    is_valid = True
                    st.session_state.reservations[st.session_state.selected_res_index]['guests'] = num_guests
                else:
                    error_message = "Please enter a valid number between 1 and 20."
            except ValueError:
                error_message = "Please enter a valid number."

        elif actual_field == 'date':
            try:
                date_obj = datetime.datetime.strptime(user_input, '%Y-%m-%d').date()
                today = datetime.date.today()
                if date_obj >= today:
                    is_valid = True
                    st.session_state.reservations[st.session_state.selected_res_index]['date'] = user_input
                else:
                    error_message = "Please enter a future date."
            except ValueError:
                error_message = "Please enter a valid date in the format YYYY-MM-DD."

        elif actual_field == 'time':
            try:
                time_obj = datetime.datetime.strptime(user_input, '%H:%M').time()
                open_time = datetime.time(11, 0)
                close_time = datetime.time(22, 0)
                if open_time <= time_obj <= close_time:
                    is_valid = True
                    st.session_state.reservations[st.session_state.selected_res_index]['time'] = user_input
                else:
                    error_message = "Our restaurant is open from 11:00 to 22:00. Please select a time within this range."
            except ValueError:
                error_message = "Please enter a valid time in the format HH:MM."

        elif actual_field == 'name':
            if len(user_input.strip()) >= 2:
                is_valid = True
                st.session_state.reservations[st.session_state.selected_res_index]['name'] = user_input
            else:
                error_message = "Please enter a valid name."

        elif actual_field == 'email':
            if validate_email(user_input):
                is_valid = True
                st.session_state.reservations[st.session_state.selected_res_index]['email'] = user_input
            else:
                error_message = "Please enter a valid email address."

        elif actual_field == 'phone':
            if validate_phone(user_input):
                is_valid = True
                st.session_state.reservations[st.session_state.selected_res_index]['phone'] = user_input
            else:
                error_message = "Please enter a valid phone number."

        if is_valid:
            # Get the updated reservation
            res = st.session_state.reservations[st.session_state.selected_res_index]

            # Update the database
            update_reservation(res)

            # Create summary for user
            summary = f"Your reservation has been updated. Here's the new information:\n\n" + \
                     f"Name: {res['name']}\n" + \
                     f"Number of guests: {res['guests']}\n" + \
                     f"Date: {res['date']}\n" + \
                     f"Time: {res['time']}\n" + \
                     f"Email: {res['email']}\n" + \
                     f"Phone: {res['phone']}\n\n" + \
                     "Would you like to make any other changes to this reservation?"

            add_message("assistant", summary)
            st.session_state.current_step = 'additional_changes'
        else:
            add_message("assistant", error_message)

    elif st.session_state.current_step == 'modify_date':
        # We'll handle date modification in the main UI flow
        pass

    elif st.session_state.current_step == 'modify_time':
        # We'll handle time modification in the main UI flow
        pass

    elif st.session_state.current_step == 'post_confirmation':
        # Handle the response after confirming a new reservation
        if user_input.lower() in ['yes', 'y', 'yeah']:
            add_message("assistant", "Thank you for your interest in our restaurant! I'd be delighted to assist you with another reservation or help you manage your existing ones.")
            add_message("assistant", "I can help you book a table or manage existing reservations. What would you like to do?")
            st.session_state.current_step = 'greeting'
        else:
            add_message("assistant", "Thank you for using our reservation system! We're looking forward to serving you at our restaurant. If you need any assistance in the future, don't hesitate to come back to this chat.")
            add_message("assistant", "Is there anything else I can help you with today?")
            st.session_state.current_step = 'greeting'

    elif st.session_state.current_step == 'additional_changes':
        if user_input.lower() in ['yes', 'y', 'yeah']:
            add_message("assistant", "What else would you like to modify? (guests, date, time, name, email, phone)")
            st.session_state.current_step = 'select_modification'
        else:
            # Refresh the reservation list from database
            st.session_state.reservations = get_all_reservations()

            add_message("assistant", "Your reservation has been updated successfully. Thank you for letting us know about the changes. We have adjusted your booking accordingly.")
            add_message("assistant", "Is there anything else I can help you with today?")
            st.session_state.current_step = 'greeting'

# Initialize chat if empty
if len(st.session_state.chat_history) == 0:
    add_message("assistant", "👋 Welcome to our Restaurant Booking Chatbot! I can help you book a new table or manage your existing reservations. How can I help you today?")

# Main title
st.title("🍽️ Restaurant Booking Chatbot")

# Display chat history
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.chat_message("user").write(message["message"])
    else:
        st.chat_message("assistant").write(message["message"])

# Display a nice reservation confirmation screen
if st.session_state.current_step == 'confirmation':
    with st.chat_message("assistant"):
        st.markdown("### Reservation Summary")

        # Create a nice container for the reservation details
        review_container = st.container(border=True)

        with review_container:
            # Get reservation data for easier access
            res_data = st.session_state.reservation_data

            # Format the date nicely
            try:
                date_obj = datetime.datetime.strptime(res_data['date'], '%Y-%m-%d').date()
                friendly_date = date_obj.strftime('%A, %B %d, %Y')
            except:
                friendly_date = res_data['date']

            # Format the time nicely 'Here
            try:
                time_parts = res_data['time'].split(':')
                hour = int(time_parts[0])
                minute = time_parts[1]
                ampm = "PM" if hour >= 12 else "AM"
                hour = hour if hour <= 12 else hour - 12
                hour = 12 if hour == 0 else hour
                friendly_time = f"{hour}:{minute} {ampm}"
            except:
                friendly_time = res_data['time']

            # Display main reservation details in a nicer format
            st.markdown(f"""
            <div style="text-align: center; padding: 20px 0;">
                <h2 style="color: #333;">Reservation for {res_data.get('name', 'Guest')}</h2>
                <p style="font-size: 1.2em; margin: 5px;">🗓️ {friendly_date}</p>
                <p style="font-size: 1.2em; margin: 5px;">🕒 {friendly_time}</p>
                <p style="font-size: 1.2em; margin: 5px;">👥 {res_data.get('guests', '1')} Guests</p>
            </div>
            """, unsafe_allow_html=True)

            # Add a separator
            st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)

            # Contact information
            st.markdown("#### Contact Information")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Email**: {res_data.get('email', 'Not provided')}")
            with col2:
                st.markdown(f"**Phone**: {res_data.get('phone', 'Not provided')}")

            # Restaurant information and policies
            st.markdown("#### Restaurant Information")
            st.markdown("- Please arrive 10 minutes before your reservation time")
            st.markdown("- Reservation will be held for 15 minutes after the scheduled time")
            st.markdown("- Special requests should be made at least 24 hours in advance")

            # Add confirm/edit buttons
            st.markdown("<br>", unsafe_allow_html=True)
            confirm_col, edit_col = st.columns(2)

            if confirm_col.button("✅ Confirm Reservation", use_container_width=True, type="primary"):
                # Add the reservation to the database with an ID
                reservation = st.session_state.reservation_data.copy()
                reservation['id'] = st.session_state.reservation_id

                # Save to database
                save_reservation(reservation)

                # Refresh reservations list from database
                st.session_state.reservations = get_all_reservations()

                # Update next ID
                st.session_state.reservation_id = get_next_reservation_id()

                # Get dates for confirmation message
                date_for_message = friendly_date if friendly_date else reservation['date']
                time_for_message = friendly_time if friendly_time else reservation['time']

                # Show confirmation message
                add_message("assistant", f"Perfect! Your reservation has been confirmed. Your reservation ID is #{reservation['id']}. We look forward to seeing you on {date_for_message} at {time_for_message}. Would you like to make another reservation or manage existing ones?")
                st.session_state.reservation_data = {}

                # Change to a new step for the confirmation response
                st.session_state.current_step = 'post_confirmation'
                st.rerun()

            if edit_col.button("✏️ Edit Details", use_container_width=True):
                add_message("assistant", "Let's make corrections. What information would you like to change? (guests, date, time, name, email, phone)")
                st.session_state.current_step = 'correction'
                st.rerun()

# Display the date picker if we're on the date selection step
elif st.session_state.current_step == 'date':
    with st.chat_message("assistant"):
        st.markdown("### Please select your reservation date")

        # Create a nice container for date selection
        date_container = st.container(border=True)

        with date_container:
            # Set the minimum date to today
            min_date = datetime.date.today()
            # Set the maximum date to 3 months from today
            max_date = min_date + datetime.timedelta(days=90)

            # Show calendar in a tabbed interface
            cal_tabs = st.tabs(["Calendar View", "Quick Selection"])

            with cal_tabs[0]:
                # Create the standard date picker widget
                selected_date = st.date_input(
                    "Select a date",
                    min_value=min_date,
                    max_value=max_date,
                    value=min_date,
                    key="date_picker"
                )

                # Display any special dates or availability info
                today = datetime.date.today()
                weekend = selected_date.weekday() >= 5  # 5 is Saturday, 6 is Sunday

                # Show different messages based on date selection
                if selected_date == today:
                    st.info("⚠️ Same-day reservations are subject to availability. We'll do our best to accommodate you!")
                elif weekend:
                    st.warning("🔔 You've selected a weekend date which tends to be busier. Early booking is recommended!")

                # Format date for display
                formatted_date = selected_date.strftime('%Y-%m-%d')
                st.success(f"Selected date: {selected_date.strftime('%A, %B %d, %Y')}")

            with cal_tabs[1]:
                # Quick date selection options
                st.markdown("#### Choose a date:")
                quick_options = [
                    ("Today", min_date),
                    ("Tomorrow", min_date + datetime.timedelta(days=1)),
                    ("This Weekend", min_date + datetime.timedelta((5 - min_date.weekday()) % 7)),
                    ("Next Week", min_date + datetime.timedelta(days=7)),
                ]

                # Create 2 columns for the quick selection buttons
                quick_cols = st.columns(2)

                # Keep track of which date is selected with these buttons
                if 'quick_selected_date' not in st.session_state:
                    st.session_state.quick_selected_date = None

                # Create buttons for each quick option
                for i, (label, date) in enumerate(quick_options):
                    col_idx = i % 2
                    if quick_cols[col_idx].button(label, key=f"quick_date_{i}", use_container_width=True):
                        st.session_state.quick_selected_date = date
                        # Update the date picker in the other tab to stay in sync
                        st.session_state.date_picker = date

                # Show the selected date if any quick option was chosen
                if st.session_state.quick_selected_date:
                    selected_date = st.session_state.quick_selected_date
                    st.success(f"Selected date: {selected_date.strftime('%A, %B %d, %Y')}")
                else:
                    st.info("Please select a date option above, or use the Calendar View tab.")

            # Add a confirm button with more prominence
            if st.button("✅ Confirm Date", use_container_width=True, type="primary"):
                # Use either the calendar-selected date or quick-selected date
                if st.session_state.get('quick_selected_date'):
                    selected_date = st.session_state.quick_selected_date

                # Format date as YYYY-MM-DD string
                formatted_date = selected_date.strftime('%Y-%m-%d')
                # Store the date in the reservation data
                st.session_state.reservation_data['date'] = formatted_date

                # Add a confirmation message to the chat
                friendly_date = selected_date.strftime('%A, %B %d, %Y')
                add_message("assistant", f"Thank you! Your selected date is {friendly_date}. Now, please select a time for your reservation.")

                # Move to the time selection step
                st.session_state.current_step = 'time'
                # Force a rerun to update the UI
                st.rerun()

# Display the time picker if we're on the time selection step
elif st.session_state.current_step == 'time':
    with st.chat_message("assistant"):
        st.markdown("### Please select a time for your reservation")

        # Create a nice container for time selection
        time_container = st.container(border=True)

        with time_container:
            # Define restaurant opening hours
            open_time = time(11, 0)  # 11:00 AM
            close_time = time(22, 0)  # 10:00 PM

            # Create tabs for lunch and dinner periods
            meal_tabs = st.tabs(["Lunch (11:00 - 15:00)", "Dinner (17:00 - 22:00)"])

            # Define a function to display time slots with a visual indication of peak hours
            def display_time_slots(filtered_slots):
                # Group slots into rows of 4 for better display
                cols = st.columns(4)

                for i, slot in enumerate(filtered_slots):
                    col_idx = i % 4

                    # Determine if this is a peak hour (e.g., 12-2 for lunch, 7-9 for dinner)
                    hour = int(slot["value"].split(":")[0])
                    is_peak = (12 <= hour <= 13) or (19 <= hour <= 20)

                    # Use different button styling for peak hours
                    if is_peak:
                        # Add peak indicator
                        cols[col_idx].markdown(f"<div style='text-align:center;'><small>⭐ Peak</small></div>", unsafe_allow_html=True)
                        if cols[col_idx].button(slot["display"], key=f"time_slot_{slot['value']}", type="primary"):
                            # Store the selected time
                            select_time(slot)
                    else:
                        # Regular styling for non-peak hours
                        if cols[col_idx].button(slot["display"], key=f"time_slot_{slot['value']}"):
                            # Store the selected time
                            select_time(slot)

            # Function to handle time selection
            def select_time(slot):
                # Store the selected time in the reservation data
                st.session_state.reservation_data['time'] = slot["value"]

                # Format time for display (convert to 12-hour format with AM/PM)
                hour, minute = map(int, slot["value"].split(":"))
                ampm = "PM" if hour >= 12 else "AM"
                hour_12 = hour if hour <= 12 else hour - 12
                hour_12 = 12 if hour_12 == 0 else hour_12
                friendly_time = f"{hour_12}:{minute:02d} {ampm}"

                # Add a confirmation message to the chat
                add_message("assistant", f"Thank you! You've selected {friendly_time} for your reservation. May I have your name, please?")

                # Move to the name input step
                st.session_state.current_step = 'name'
                # Force a rerun to update the UI
                st.rerun()

            # Generate time slots every 30 minutes
            all_time_slots = []
            current_time = open_time
            while current_time <= close_time:
                hour = current_time.hour
                minute = current_time.minute

                # Format time as HH:MM for storage
                time_str = f"{hour:02d}:{minute:02d}"

                # Format time with AM/PM for display
                ampm = "PM" if hour >= 12 else "AM"
                hour_12 = hour if hour <= 12 else hour - 12
                hour_12 = 12 if hour_12 == 0 else hour_12
                display_time = f"{hour_12}:{minute:02d} {ampm}"

                all_time_slots.append({"value": time_str, "display": display_time})

                # Move to next 30-minute slot
                if minute == 30:
                    current_time = time(hour + 1, 0)
                else:
                    current_time = time(hour, 30)#here

            # Filter for lunch time slots (11:00 AM - 3:00 PM)
            lunch_slots = [slot for slot in all_time_slots if 11 <= int(slot["value"].split(":")[0]) < 15]

            # Filter for dinner time slots (5:00 PM - 10:00 PM)
            dinner_slots = [slot for slot in all_time_slots if 17 <= int(slot["value"].split(":")[0]) <= 22]

            # Show appropriate time slots in each tab
            with meal_tabs[0]:
                st.markdown("#### Lunch Reservation Times")
                st.info("🍽️ Our lunch service runs from 11:00 AM to 3:00 PM.")
                display_time_slots(lunch_slots)

            with meal_tabs[1]:
                st.markdown("#### Dinner Reservation Times")
                st.info("🌙 Our dinner service runs from 5:00 PM to 10:00 PM.")
                display_time_slots(dinner_slots)

            # Show a help text at the bottom
            st.markdown("---")
            st.markdown("⭐ **Peak hours** are typically busier times with higher demand.")
            st.markdown("🕒 **Last seating** for lunch is at 2:30 PM and for dinner at 9:30 PM.")

# Display date modification widget if we're on the modify_date step
elif st.session_state.current_step == 'modify_date':
    with st.chat_message("assistant"):
        st.write("Please select a new date for this reservation:")

        # Set the minimum date to today
        min_date = datetime.date.today()
        # Set the maximum date to 3 months from today
        max_date = min_date + datetime.timedelta(days=90)

        # Get current reservation date to set as default
        current_res = st.session_state.reservations[st.session_state.selected_res_index]
        current_date = datetime.datetime.strptime(current_res['date'], '%Y-%m-%d').date()

        # Use the current date if it's valid, otherwise use today
        default_date = current_date if current_date >= min_date else min_date

        # Create the date picker widget
        selected_date = st.date_input(
            "New Reservation Date",
            min_value=min_date,
            max_value=max_date,
            value=default_date,
            key="modify_date_picker"
        )

        # Add a button to confirm date selection
        if st.button("Confirm New Date"):
            # Format date as YYYY-MM-DD string
            formatted_date = selected_date.strftime('%Y-%m-%d')
            # Update the reservation with new date
            st.session_state.reservations[st.session_state.selected_res_index]['date'] = formatted_date

            # Update the database
            update_reservation(st.session_state.reservations[st.session_state.selected_res_index])

            # Create a confirmation message
            res = st.session_state.reservations[st.session_state.selected_res_index]
            summary = f"Your reservation date has been updated. Here's the updated information:\n\n" + \
                     f"Name: {res['name']}\n" + \
                     f"Number of guests: {res['guests']}\n" + \
                     f"Date: {res['date']}\n" + \
                     f"Time: {res['time']}\n" + \
                     f"Email: {res['email']}\n" + \
                     f"Phone: {res['phone']}\n\n" + \
                     "Would you like to make any other changes to this reservation?"

            add_message("assistant", summary)
            st.session_state.current_step = 'additional_changes'
            st.rerun()

# Display time modification widget if we're on the modify_time step
elif st.session_state.current_step == 'modify_time':
    with st.chat_message("assistant"):
        st.write("Please select a new time for this reservation:")

        # Define restaurant opening hours
        open_time = time(11, 0)  # 11:00 AM
        close_time = time(22, 0)  # 10:00 PM

        # Generate time slots every 30 minutes
        time_slots = []
        current_time = open_time
        while current_time <= close_time:
            hour = current_time.hour
            minute = current_time.minute
            # Format time as HH:MM
            time_str = f"{hour:02d}:{minute:02d}"
            # Add AM/PM for display
            display_time = f"{hour:02d}:{minute:02d}"
            time_slots.append({"value": time_str, "display": display_time})

            # Move to next 30-minute slot
            if minute == 30:
                current_time = time(hour + 1, 0)
            else:
                current_time = time(hour, 30)

        # Display time slots as buttons in 4 columns
        st.write("Available time slots:")
        cols = st.columns(4)
        for i, slot in enumerate(time_slots):
            col_idx = i % 4
            if cols[col_idx].button(slot["display"], key=f"modify_time_slot_{i}"):
                # Update the reservation with the selected time
                st.session_state.reservations[st.session_state.selected_res_index]['time'] = slot["value"]

                # Update the database
                update_reservation(st.session_state.reservations[st.session_state.selected_res_index])

                # Create a confirmation message
                res = st.session_state.reservations[st.session_state.selected_res_index]
                summary = f"Your reservation time has been updated. Here's the updated information:\n\n" + \
                         f"Name: {res['name']}\n" + \
                         f"Number of guests: {res['guests']}\n" + \
                         f"Date: {res['date']}\n" + \
                         f"Time: {res['time']}\n" + \
                         f"Email: {res['email']}\n" + \
                         f"Phone: {res['phone']}\n\n" + \
                         "Would you like to make any other changes to this reservation?"

                add_message("assistant", summary)
                st.session_state.current_step = 'additional_changes'
                st.rerun()

# Show action buttons if we're at the greeting step
if st.session_state.current_step == 'greeting':
    with st.chat_message("assistant"):
        st.write("What would you like to do?")

        col1, col2 = st.columns(2)

        if col1.button("Book a Table", key="action_book"):
            # Simulate user input
            process_input("I want to book a table")
            st.rerun()

        if col2.button("Manage Reservations", key="action_manage"):
            # Simulate user input
            process_input("I want to manage my reservations")
            st.rerun()

# User input section
user_input = st.chat_input("Type your message here...")
if user_input:
    process_input(user_input)
    st.rerun()

# Reset button
if st.button("Reset Chat"):
    reset_chat()
    st.rerun()

# Button to download the database for Colab
if st.button("Download Database"):
    try:
        # Read the database file
        with open('data/reservations.db', 'rb') as f:
            data = f.read()

        # Download through Colab
        # files.download('reservations.db')
        with open("data/reservations.db", "rb") as f:
          st.download_button(
            label="Download Reservations DB",
            data=f,
            file_name="reservations.db",
            mime="application/octet-stream"
          )

        st.success("Database downloaded successfully!")
    except Exception as e:
        st.error(f"Error downloading database: {e}")

# Add a nice footer with restaurant information
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px 0;">
    <p><strong>Fine Dining Restaurant</strong></p>
    <p>123 Gourmet Avenue, Foodie District</p>
    <p>Opening Hours: 11:00 AM - 10:00 PM, 7 days a week</p>
    <p>For special events and large parties, please call us directly at (555) 123-4567</p>
    <small>Powered by Streamlit Chatbot</small>
</div>
""", unsafe_allow_html=True)
