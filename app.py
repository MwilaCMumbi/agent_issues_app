import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time, timedelta
import time
import uuid
from typing import Dict, List, Optional, TypedDict
import sqlite3
import json

# ============================================
# TYPE HINTS & CONSTANTS
# ============================================
class User(TypedDict):
    username: str
    password: str
    role: str
    region: str
    active: bool

class CaseReporter(TypedDict):
    name: str
    role: str
    agent_number: Optional[str]
    contact: str

class CaseIssue(TypedDict):
    type: str
    description: str
    attachments: List[str]

class CaseResolution(TypedDict):
    notes: str
    action_taken: str
    timestamp: str

class CaseTimestamps(TypedDict):
    received: Optional[str]
    logged: str
    resolved: Optional[str]

class Case(TypedDict):
    case_id: str
    channel: str
    timestamps: CaseTimestamps
    reporter: CaseReporter
    region: str
    issue: CaseIssue
    status: str
    resolution: Optional[CaseResolution]
    handled_by: str

# Constants
CHANNELS = ["WhatsApp", "Voice Call", "Email"]
ROLES = [
    "Agent", 
    "Sales and Service Assistant",
    "Agent Team Leader",
    "Regional Manager",
    "Assistant Regional Manager"
]
REGIONS = [
    "Lusaka", "Western", "North-Western", 
    "Northern", "Southern", "Central",
    "Luapula", "Eastern", "Copperbelt", 
    "Muchinga"
]
ISSUE_TYPES = [
    "Commissions", "Tokens", "Registration Failure", 
    "Float", "Stock", "Edit own account request",
    "Edit customer request", "Reporting New Fault",
    "Follow up on previously reported fault",
    "Balance inquiry", "Campaign related",
    "Call back request", "Call was dropped",
    "Customer feedback"
]
USER_ROLES = ["Admin", "Manager", "Agent"]

# ============================================
# DATABASE FUNCTIONS
# ============================================
DB_NAME = "vitalite_cases.db"

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Cases table (stores entire case as JSON for simplicity)
    c.execute('''CREATE TABLE IF NOT EXISTS cases
                 (case_id TEXT PRIMARY KEY,
                  case_data TEXT)''')
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY,
                  password TEXT,
                  role TEXT,
                  region TEXT,
                  active BOOLEAN)''')
    
    # Insert default admin user if not exists
    c.execute('''INSERT OR IGNORE INTO users VALUES 
              (?, ?, ?, ?, ?)''', 
              ("admin", "admin123", "Admin", "All", True))
    
    conn.commit()
    conn.close()

def save_case(case: Case):
    """Save a case to the database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO cases VALUES (?, ?)''', 
              (case['case_id'], json.dumps(case)))
    conn.commit()
    conn.close()

def get_all_cases() -> List[Case]:
    """Retrieve all cases from the database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT case_data FROM cases")
    cases = [json.loads(row[0]) for row in c.fetchall()]
    conn.close()
    return cases

def delete_case(case_id: str):
    """Delete a case from the database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM cases WHERE case_id=?", (case_id,))
    conn.commit()
    conn.close()

def save_user(user: User):
    """Save a user to the database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)''', 
              (user['username'], user['password'], user['role'], 
               user['region'], user['active']))
    conn.commit()
    conn.close()

def get_all_users() -> List[User]:
    """Retrieve all users from the database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = [{
        "username": row[0],
        "password": row[1],
        "role": row[2],
        "region": row[3],
        "active": bool(row[4])
    } for row in c.fetchall()]
    conn.close()
    return users

def delete_user(username: str):
    """Delete a user from the database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# ============================================
# SETUP & CONFIGURATION
# ============================================
def setup_page_config():
    """Configure the page settings and apply custom CSS."""
    try:
        st.set_page_config(
            page_title="VITALITE Agent Management Query Portal",
            page_icon="🆘",
            layout="wide"
        )
        
        # Modern, sleek CSS styling
        st.markdown("""
        <style>
            :root {
                --primary: #003366;
                --secondary: #ffcc00;
                --accent: #5cb85c;
                --danger: #d9534f;
                --warning: #f0ad4e;
                --light-bg: #f8f9fa;
            }
            
            .stButton>button {
                background-color: var(--primary);
                color: white;
                border-radius: 8px;
                padding: 0.5rem 1rem;
                border: none;
                font-weight: 500;
                transition: all 0.2s;
            }
            .stButton>button:hover {
                background-color: #004080;
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            .report-title {
                font-size: 28px;
                color: var(--primary);
                font-weight: 700;
                margin-bottom: 1.5rem;
                padding-bottom: 0.5rem;
                border-bottom: 2px solid var(--primary);
            }
            
            .case-card {
                border-left: 4px solid var(--primary);
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            }
            
            .status-badge {
                display: inline-block;
                padding: 0.25rem 0.75rem;
                border-radius: 12px;
                font-size: 0.85rem;
                font-weight: 600;
            }
            
            .status-open {
                background-color: rgba(217, 83, 79, 0.1);
                color: var(--danger);
            }
            
            .status-closed {
                background-color: rgba(92, 184, 92, 0.1);
                color: var(--accent);
            }
            
            .status-escalated {
                background-color: rgba(240, 173, 78, 0.1);
                color: var(--warning);
            }
            
            .required-field::after {
                content: " *";
                color: var(--danger);
            }
            
            .form-section {
                background-color: white;
                padding: 1.5rem;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                margin-bottom: 1.5rem;
            }
            
            .stTextArea textarea {
                min-height: 120px;
            }
            
            .stSelectbox, .stTextInput, .stDateInput, .stTimeInput {
                margin-bottom: 1rem;
            }
            
            .success-message {
                background-color: rgba(92, 184, 92, 0.1);
                padding: 1rem;
                border-radius: 8px;
                border-left: 4px solid var(--accent);
                margin-bottom: 1.5rem;
            }
            
            .portal-title {
                font-size: 24px;
                font-weight: bold;
                color: var(--primary);
                margin-bottom: 1rem;
                text-align: center;
            }
            
            .sidebar-title {
                font-size: 20px;
                font-weight: bold;
                color: var(--primary);
                margin-bottom: 1rem;
                text-align: center;
            }
            
            .user-card {
                background-color: white;
                padding: 1rem;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                margin-bottom: 1rem;
            }
        </style>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error in page setup: {str(e)}")

def initialize_session_state():
    """Initialize all required session state variables."""
    try:
        defaults = {
            'current_case': None,
            'logged_in': False,
            'current_page': "dashboard",
            'user': None,
            'case_filter': 'All',
            'new_case_submitted': False,
            'form_data': {},
            'users': get_all_users()
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    except Exception as e:
        st.error(f"Error initializing session state: {str(e)}")

# ============================================
# USER MANAGEMENT
# ============================================
def user_management():
    """User management interface for admins."""
    try:
        st.markdown('<div class="report-title">User Management</div>', unsafe_allow_html=True)
        
        if st.session_state.user['role'] != "Admin":
            st.warning("You don't have permission to access this page")
            return
        
        # Add new user form
        with st.expander("Add New User", expanded=True):
            with st.form("user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_username = st.text_input("Username")
                    new_role = st.selectbox("Role", USER_ROLES)
                with col2:
                    new_password = st.text_input("Password", type="password")
                    new_region = st.selectbox("Region", ["All"] + REGIONS)
                
                if st.form_submit_button("Add User"):
                    if new_username and new_password:
                        if any(user['username'] == new_username for user in get_all_users()):
                            st.error("Username already exists")
                        else:
                            new_user = {
                                "username": new_username,
                                "password": new_password,
                                "role": new_role,
                                "region": new_region,
                                "active": True
                            }
                            save_user(new_user)
                            st.session_state.users = get_all_users()
                            st.success("User added successfully!")
                            st.rerun()
                    else:
                        st.error("Please fill all fields")
        
        # User list with edit/delete options
        st.subheader("User List")
        for user in st.session_state.users:
            with st.container():
                st.markdown(f"""
                <div class="user-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4>{user['username']}</h4>
                        <span>{'Active' if user['active'] else 'Inactive'}</span>
                    </div>
                    <p><strong>Role:</strong> {user['role']}</p>
                    <p><strong>Region:</strong> {user['region']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button(f"Edit", key=f"edit_{user['username']}"):
                        st.session_state.editing_user = user
                        st.session_state.current_page = "edit_user"
                        st.rerun()
                with col2:
                    if st.button(f"Delete", key=f"delete_{user['username']}"):
                        delete_user(user['username'])
                        st.session_state.users = get_all_users()
                        st.success("User deleted successfully!")
                        time.sleep(1)
                        st.rerun()
    except Exception as e:
        st.error(f"Error in user management: {str(e)}")

def edit_user():
    """Edit user details."""
    try:
        if 'editing_user' not in st.session_state:
            st.error("No user selected for editing")
            st.session_state.current_page = "user_management"
            st.rerun()
        
        user = st.session_state.editing_user
        st.markdown(f'<div class="report-title">Edit User: {user["username"]}</div>', unsafe_allow_html=True)
        
        with st.form("edit_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_password = st.text_input("New Password", type="password", value=user['password'])
                new_role = st.selectbox("Role", USER_ROLES, index=USER_ROLES.index(user['role']))
            with col2:
                confirm_password = st.text_input("Confirm Password", type="password", value=user['password'])
                new_region = st.selectbox("Region", ["All"] + REGIONS, index=(["All"] + REGIONS).index(user['region']))
            
            active = st.checkbox("Active", value=user['active'])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Save Changes"):
                    if new_password == confirm_password:
                        updated_user = {
                            "username": user['username'],
                            "password": new_password,
                            "role": new_role,
                            "region": new_region,
                            "active": active
                        }
                        save_user(updated_user)
                        st.session_state.users = get_all_users()
                        st.success("User updated successfully!")
                        time.sleep(1)
                        st.session_state.current_page = "user_management"
                        st.rerun()
                    else:
                        st.error("Passwords don't match")
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.current_page = "user_management"
                    st.rerun()
    except Exception as e:
        st.error(f"Error editing user: {str(e)}")

# ============================================
# AUTHENTICATION
# ============================================
def login_page():
    """Render the login page and handle authentication."""
    try:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="portal-title">VITALITE Agent Management Query Portal</div>', unsafe_allow_html=True)
            with st.container():
                with st.form("login", clear_on_submit=True):
                    st.subheader("Agent Login")
                    username = st.text_input("Username", placeholder="Enter your username")
                    password = st.text_input("Password", type="password", placeholder="Enter your password")
                    submit = st.form_submit_button("Login", use_container_width=True)
                    
                    if submit:
                        if username and password:
                            user = next((u for u in get_all_users() if u['username'] == username and u['password'] == password and u['active']), None)
                            if user:
                                st.session_state.logged_in = True
                                st.session_state.user = user
                                st.session_state.current_page = "dashboard"
                                st.success("Login successful!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Invalid credentials or inactive account")
                        else:
                            st.error("Please enter both username and password")
    except Exception as e:
        st.error(f"Login error: {str(e)}")

# ============================================
# CASE MANAGEMENT
# ============================================
def generate_case_id() -> str:
    """Generate a unique case ID."""
    try:
        return f"VL-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
    except Exception as e:
        st.error(f"Error generating case ID: {str(e)}")
        return f"VL-{int(time.time())}"

def validate_case_form(name: str, role: str, region: str, issue_type: str, description: str) -> bool:
    """Validate required fields in the case form."""
    try:
        if not all([name, role, region, issue_type, description]):
            st.error("Please fill all required fields (*)")
            return False
        return True
    except Exception as e:
        st.error(f"Validation error: {str(e)}")
        return False

def create_new_case(form_data: Dict) -> Case:
    """Create a new case dictionary from form data."""
    try:
        case = {
            "case_id": generate_case_id(),
            "channel": form_data['channel'],
            "timestamps": {
                "received": form_data.get('received_time'),
                "logged": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "resolved": None
            },
            "reporter": {
                "name": form_data['name'],
                "role": form_data['role'],
                "agent_number": form_data.get('agent_num'),
                "contact": form_data.get('phone') or form_data.get('email')
            },
            "region": form_data['region'],
            "issue": {
                "type": form_data['issue_type'],
                "description": form_data['description'],
                "attachments": form_data.get('attachments', [])
            },
            "status": "Open",
            "resolution": None,
            "handled_by": st.session_state.user['username']
        }
        
        # Add resolution if provided in form
        if form_data.get('resolution_notes'):
            case['resolution'] = {
                "notes": form_data['resolution_notes'],
                "action_taken": "Initial notes",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        return case
    except Exception as e:
        st.error(f"Error creating case: {str(e)}")
        return None

def new_case_form():
    """Render the form for creating new cases."""
    try:
        st.markdown('<div class="report-title">New Case Entry</div>', unsafe_allow_html=True)
        
        # Initialize form data in session state if not exists
        if 'form_data' not in st.session_state:
            st.session_state.form_data = {}
        
        # Initialize attachments as empty list
        attachments = []
        
        with st.form("case_form", clear_on_submit=True):
            # Section 1: Channel Selection
            with st.expander("1. Contact Channel", expanded=True):
                channel = st.radio("How was this issue reported?", 
                                 CHANNELS,
                                 horizontal=True)
            
            # Section 2: Reporter Information
            with st.expander("2. Reporter Details", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Full Name", help="Enter the reporter's full name")
                with col2:
                    role = st.selectbox("Role", ROLES)
                    
                    if role == "Agent":
                        agent_num = st.text_input("Agent Number", help="Required for Agent role")
                
                # Dynamic contact field
                if channel in ["WhatsApp", "Voice Call"]:
                    phone = st.text_input("Phone Number")
                    
                    if channel == "WhatsApp":
                        col1, col2 = st.columns(2)
                        with col1:
                            received_date = st.date_input("Message Date")
                        with col2:
                            received_time = st.time_input("Message Time")
                        received_time_str = datetime.combine(received_date, received_time).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    email = st.text_input("Email Address")
            
            # Section 3: Location
            with st.expander("3. Location Details", expanded=True):
                region = st.selectbox("Region", REGIONS)
            
            # Section 4: Issue Description
            with st.expander("4. Issue Description", expanded=True):
                issue_type = st.selectbox("Issue Type", ISSUE_TYPES)
                description = st.text_area("Detailed Description", height=150,
                                         help="Provide as much detail as possible about the issue")
                
                # Resolution field immediately after description
                resolution_notes = st.text_area("Resolution Notes (Optional)", 
                                              height=100,
                                              help="You can add resolution notes now or later")
            
            # Section 5: Attachments
            if channel in ["WhatsApp", "Email"]:
                with st.expander("5. Attachments", expanded=False):
                    uploaded_files = st.file_uploader("Upload screenshots or documents", 
                                                   accept_multiple_files=True,
                                                   type=['png', 'jpg', 'jpeg', 'pdf'])
                    if uploaded_files:
                        attachments = [file.name for file in uploaded_files]
            
            # Form submission button
            submit_col1, submit_col2 = st.columns([3, 1])
            with submit_col1:
                submit = st.form_submit_button("Submit Case", use_container_width=True)
            
            if submit:
                # Store form data in session state
                st.session_state.form_data = {
                    'channel': channel,
                    'name': name,
                    'role': role,
                    'agent_num': agent_num if role == "Agent" else None,
                    'phone': phone if channel in ["WhatsApp", "Voice Call"] else None,
                    'email': email if channel == "Email" else None,
                    'received_time': received_time_str if channel == "WhatsApp" else None,
                    'region': region,
                    'issue_type': issue_type,
                    'description': description,
                    'resolution_notes': resolution_notes,
                    'attachments': attachments
                }
                
                if validate_case_form(name, role, region, issue_type, description):
                    if role == "Agent" and not agent_num:
                        st.error("Agent number is required for Agent role")
                        return
                    
                    if channel in ["WhatsApp", "Voice Call"] and not phone:
                        st.error("Phone number is required for this channel")
                        return
                    
                    if channel == "Email" and not email:
                        st.error("Email address is required for email cases")
                        return
                    
                    new_case = create_new_case(st.session_state.form_data)
                    if new_case:
                        save_case(new_case)
                        st.session_state.new_case_submitted = True
                        st.session_state.current_case = new_case
                        st.rerun()

        # Post-submission message
        if st.session_state.get('new_case_submitted') and st.session_state.current_case:
            case = st.session_state.current_case
            st.markdown(f"""
            <div class="success-message">
                <h3>Case {case['case_id']} created successfully!</h3>
                <p>Status: <span class="status-badge status-open">Open</span></p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Go to Dashboard", use_container_width=True):
                    st.session_state.current_page = "dashboard"
                    st.session_state.new_case_submitted = False
                    st.rerun()
            with col2:
                if st.button("Create Another Case", use_container_width=True):
                    st.session_state.new_case_submitted = False
                    st.rerun()
    except Exception as e:
        st.error(f"Error in case form: {str(e)}")

def display_case_details(case: Case):
    """Display detailed information about a case."""
    try:
        if not case:
            st.warning("No case data available")
            return
        
        status_class = f"status-{case['status'].lower()}" if case.get('status') else ""
        
        with st.container():
            st.markdown(f"""
            <div class="case-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>Case {case.get('case_id', 'N/A')}</h3>
                    <span class="status-badge {status_class}">{case.get('status', 'Unknown')}</span>
                </div>
                <div style="margin-top: 1rem;">
                    <p><strong>Reporter:</strong> {case['reporter'].get('name', 'N/A')} ({case['reporter'].get('role', 'N/A')})</p>
                    <p><strong>Contact:</strong> {case['reporter'].get('contact', 'N/A')}</p>
                    <p><strong>Region:</strong> {case.get('region', 'N/A')}</p>
                    <p><strong>Issue Type:</strong> {case['issue'].get('type', 'N/A')}</p>
                    <p><strong>Description:</strong> {case['issue'].get('description', 'N/A')}</p>
                    <p><strong>Logged by:</strong> {case.get('handled_by', 'N/A')} at {case['timestamps'].get('logged', 'N/A')}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if case.get('channel') == "WhatsApp" and case['timestamps'].get('received'):
                try:
                    received = datetime.strptime(case['timestamps']['received'], "%Y-%m-%d %H:%M:%S")
                    logged = datetime.strptime(case['timestamps']['logged'], "%Y-%m-%d %H:%M:%S")
                    response_mins = (logged - received).total_seconds() / 60
                    st.metric("WhatsApp Response Time", f"{response_mins:.1f} minutes")
                except:
                    pass
    except Exception as e:
        st.error(f"Error displaying case details: {str(e)}")

def resolve_case(case: Case):
    """Render the case resolution interface."""
    try:
        if not case:
            st.error("No case selected")
            st.session_state.current_case = None
            st.rerun()
            return
        
        st.markdown(f'<div class="report-title">Case Resolution</div>', unsafe_allow_html=True)
        
        # Display case details
        display_case_details(case)
        
        # Resolution form
        with st.form("resolution_form"):
            st.subheader("Resolution Details")
            
            # Pre-fill resolution notes if they exist
            existing_notes = ""
            if case.get('resolution'):
                existing_notes = case['resolution'].get('notes', "")
            resolution_notes = st.text_area("Resolution Notes", 
                                          value=existing_notes,
                                          height=150,
                                          help="Describe how the issue was resolved")
            
            # Form buttons
            col1, col2 = st.columns([1, 1])
            with col1:
                close = st.form_submit_button("✅ Close Case", use_container_width=True)
            with col2:
                escalate = st.form_submit_button("⚠️ Escalate", use_container_width=True)
            
            if close or escalate:
                if not resolution_notes:
                    st.error("Please provide resolution notes")
                else:
                    if close:
                        case['status'] = "Closed"
                        action = "closed"
                    else:
                        case['status'] = "Open"  # Treat escalated cases as Open
                        action = "escalated (marked as Open)"
                    
                    case['resolution'] = {
                        "notes": resolution_notes,
                        "action_taken": "Closed by agent" if close else "Escalated to senior support",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Save the updated case
                    save_case(case)
                    
                    st.success(f"Case has been {action} successfully!")
                    time.sleep(1)
                    st.session_state.current_case = None
                    st.rerun()
    except Exception as e:
        st.error(f"Error in case resolution: {str(e)}")

def filter_cases() -> List[Case]:
    """Filter cases based on the selected filter option."""
    try:
        cases = get_all_cases()
        if not cases:
            return []
        
        if st.session_state.case_filter == 'All':
            return cases
        elif st.session_state.case_filter == 'Open':
            # Include both Open and Escalated cases in Open filter
            return [case for case in cases if case.get('status') in ['Open', 'Escalated']]
        return [case for case in cases if case.get('status') == st.session_state.case_filter]
    except Exception as e:
        st.error(f"Error filtering cases: {str(e)}")
        return []

def display_case_list():
    """Display a list of cases with filtering options."""
    try:
        st.subheader("Case Management")
        
        # Filter and search controls
        col1, col2 = st.columns([1, 3])
        with col1:
            filter_option = st.selectbox(
                "Filter by status",
                ['All', 'Open', 'Closed'],
                key='case_filter'
            )
        
        cases = filter_cases()
        
        if not cases:
            st.info("No cases found matching the selected filter")
            return
        
        for case in cases:
            if not case:
                continue
                
            with st.container():
                display_case_details(case)
                
                # Action buttons
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    if st.button(f"View/Resolve", key=f"view_{case.get('case_id', '')}", use_container_width=True):
                        st.session_state.current_case = case
                        st.rerun()
                with col3:
                    if st.button(f"Delete", key=f"delete_{case.get('case_id', '')}", use_container_width=True):
                        delete_case(case.get('case_id'))
                        st.success("Case deleted successfully!")
                        time.sleep(1)
                        st.rerun()
                
                st.markdown("---")
    except Exception as e:
        st.error(f"Error displaying case list: {str(e)}")

def dashboard():
    """Render the analytics dashboard."""
    try:
        st.markdown('<div class="report-title">VITALITE Agent Management Query Portal</div>', unsafe_allow_html=True)
        
        cases = get_all_cases()
        if not cases:
            st.info("No cases logged yet")
            return
        
        # Create DataFrame
        try:
            df = pd.DataFrame(cases)
        except Exception as e:
            st.error(f"Error creating data table: {str(e)}")
            return
        
        # KPI Cards
        st.subheader("Performance Metrics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Cases", len(df))
        
        # Count Open cases (including Escalated)
        open_cases = len([case for case in cases if case.get('status') in ['Open', 'Escalated']])
        col2.metric("Open Cases", open_cases)
        
        # Resolution rate based on Closed cases only
        closed_cases = len([case for case in cases if case.get('status') == 'Closed'])
        resolution_rate = (closed_cases / len(cases)) * 100 if cases else 0
        col3.metric("Resolution Rate", f"{resolution_rate:.1f}%")
        
        # Charts
        tab1, tab2, tab3 = st.tabs(["Cases by Type", "Cases by Status", "Channel Distribution"])
        
        with tab1:
            try:
                issue_types = [case['issue'].get('type', 'Unknown') for case in cases]
                st.bar_chart(pd.Series(issue_types).value_counts())
            except:
                st.warning("Could not display cases by type")
        
        with tab2:
            try:
                # Group Escalated cases with Open for visualization
                statuses = [case.get('status', 'Unknown') for case in cases]
                status_counts = pd.Series(statuses).replace('Escalated', 'Open').value_counts()
                st.bar_chart(status_counts)
            except:
                st.warning("Could not display cases by status")
        
        with tab3:
            try:
                channels = [case.get('channel', 'Unknown') for case in cases]
                fig = px.pie(values=pd.Series(channels).value_counts().values,
                               names=pd.Series(channels).value_counts().index,
                               title='Case Channel Distribution')
                st.plotly_chart(fig)
            except:
                st.warning("Could not display channel distribution")
        
        # Case List
        display_case_list()
        
        # Data Export
        with st.expander("Export Options"):
            # Download CSV
            if cases:
                st.download_button(
                    label="Download All Cases as CSV",
                    data=df.to_csv(index=False),
                    file_name="vitalite_all_cases.csv",
                    mime="text/csv"
                )
                
                # Download KPI Report
                report = f"""
                VITALITE Agent Management Query Portal - KPI Report
                ===================================================
                
                Summary Metrics:
                - Total Cases: {len(cases)}
                - Open Cases: {open_cases}
                - Closed Cases: {closed_cases}
                - Resolution Rate: {resolution_rate:.1f}%
                
                Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                st.download_button(
                    label="Download KPI Report",
                    data=report,
                    file_name="vitalite_kpi_report.txt",
                    mime="text/plain"
                )
            else:
                st.warning("No cases to export")
    except Exception as e:
        st.error(f"Dashboard error: {str(e)}")

# ============================================
# MAIN APP FLOW
# ============================================
def main():
    """Main application flow controller."""
    try:
        # Sidebar Navigation
        st.sidebar.markdown('<div class="sidebar-title">VITALITE Agent Management</div>', unsafe_allow_html=True)
        st.sidebar.markdown(f"**Logged in as:** {st.session_state.user['username']} ({st.session_state.user['role']})")
        st.sidebar.markdown("---")
        
        nav_options = {
            "📊 Dashboard": "dashboard",
            "➕ New Case": "new_case",
        }
        
        # Add User Management for Admins
        if st.session_state.user['role'] == "Admin":
            nav_options["👥 User Management"] = "user_management"
        
        for label, page in nav_options.items():
            if st.sidebar.button(label, use_container_width=True):
                st.session_state.current_page = page
                st.session_state.current_case = None
                st.rerun()
        
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_case = None
            st.session_state.current_page = None
            st.rerun()
        
        # Main Content
        if st.session_state.current_case:
            resolve_case(st.session_state.current_case)
        elif st.session_state.current_page == "dashboard":
            dashboard()
        elif st.session_state.current_page == "user_management":
            user_management()
        elif st.session_state.current_page == "edit_user":
            edit_user()
        else:
            new_case_form()
    except Exception as e:
        st.error(f"Application error: {str(e)}")

# ============================================
# RUN THE APP
# ============================================
if __name__ == "__main__":
    try:
        setup_page_config()
        initialize_session_state()
        
        if not st.session_state.logged_in:
            login_page()
        else:
            main()
    except Exception as e:
        st.error(f"Fatal error: {str(e)}")