"""
App1.py - FINCH Spreadsheet Analyzer & Executive CFO Suite (Phase 4 Edition)
"""
import os
import streamlit as st
import pandas as pd
from datetime import datetime

# Import modular backend functions
from analysis import clean_data, extract_kpis, generate_health_score, detect_outliers
from simulator import run_simulation
from deck_builder import create_executive_deck
from finch_intro import show_finch_intro
from database import (
    init_db, create_user, verify_user, get_user_email, 
    save_scenario_db, load_scenarios_db, delete_scenarios_db,
    save_audit_history_db, load_user_history_db, 
    get_user_tier, update_user_tier, check_and_increment_daily_usage
)

# Page Configuration
st.set_page_config(
    page_title="FINCH | Executive Financial Intelligence",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database connection
init_db()

# Master Admin Configuration
MASTER_ADMIN_EMAIL = "oebube025@gmail.com" # Update if needed, or matches your founder email

# Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

def render_auth_portal():
    """Renders the cinematic intro and authentication / registration tabs with Tier selection."""
    show_finch_intro(mode="banner")
    
    st.markdown("## 🦅 Welcome to FINCH")
    st.markdown("### Secure Executive Spreadsheet Analyzer & Fractional CFO Suite")
    
    tab_login, tab_signup = st.tabs(["🔑 Sign In", "📝 Create Account & Choose Tier"])
    
    with tab_login:
        st.subheader("Sign In to Your Workspace")
        login_input = st.text_input("Username or Email", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Sign In", type="primary"):
            if not login_input or not login_pass:
                st.error("Please provide both username/email and password.")
            else:
                verified_user = verify_user(login_input, login_pass)
                if verified_user:
                    st.session_state.authenticated = True
                    st.session_state.username = verified_user
                    st.session_state.user_email = get_user_email(verified_user)
                    st.success(f"Welcome back, {verified_user}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please check your username/email or password.")

    with tab_signup:
        st.subheader("Create a New Account & Select Your Tier")
        new_user = st.text_input("Choose Username", key="signup_user")
        new_email = st.text_input("Business Email", key="signup_email")
        new_pass = st.text_input("Choose Password", type="password", key="signup_pass")
        
        # Tier Selection for New Accounts
        selected_tier = st.selectbox(
            "Select Subscription Tier",
            options=["free", "pro", "enterprise"],
            format_func=lambda x: {
                "free": "Free Tier (₦0 / mo) - 5 analyses/day",
                "pro": "Pro Tier (₦14,999 / mo) - Unlimited uploads & Full Deck Generator",
                "enterprise": "Enterprise Tier (₦99,000 / mo) - Full Team & Multi-Tenant Access"
            }[x]
        )
        
        if st.button("Register Account", type="primary"):
            if not new_user or not new_email or not new_pass:
                st.error("All fields are required to register.")
            elif "@" not in new_email:
                st.error("Please enter a valid email address.")
            else:
                success = create_user(new_user, new_email, new_pass, tier=selected_tier)
                if success:
                    st.success("Account created successfully! You can now sign in using the 'Sign In' tab.")
                else:
                    st.error("Registration failed. Username or email may already be taken.")

# Check Authentication State
if not st.session_state.authenticated:
    render_auth_portal()
    st.stop()

# --- Authenticated App Experience ---
user_email = st.session_state.user_email
user_tier = get_user_tier(user_email)
is_master_admin = (user_email.lower() == MASTER_ADMIN_EMAIL.lower())

# Sidebar User & Tier Status
with st.sidebar:
    st.markdown(f"### 🦅 FINCH Workspace")
    st.write(f"**User:** {st.session_state.username}")
    st.write(f"**Email:** {user_email}")
    
    if is_master_admin:
        st.markdown("⭐ **Status:** Master Admin (`Full Access`)")
    else:
        st.markdown(f"⭐ **Tier:** `{user_tier.upper()}`")
        if user_tier == "free":
            st.info("💡 Free tier includes **5 analyses per day**. Upgrade to Pro for unlimited access.")
            if st.button("Upgrade to Pro (₦14,999/mo)"):
                update_user_tier(user_email, "pro")
                st.success("Upgraded to Pro! Refreshing...")
                st.rerun()
                
    if st.button("Sign Out"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.user_email = ""
        st.rerun()

    st.markdown("---")
    st.markdown("### 📂 Upload Spreadsheet")
    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

if not uploaded_file:
    st.info("👋 Welcome to **FINCH**. Please upload a financial spreadsheet (.csv or .xlsx) in the sidebar to begin your executive audit.")
    st.stop()

# Load and process data
try:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Error reading file: {e}")
    st.stop()

cleaned_df = clean_data(df)
totals = extract_kpis(cleaned_df)
health_score = generate_health_score(cleaned_df)
outliers = detect_outliers(cleaned_df)

# Main Navigation Tabs
tab_audit, tab_simulator, tab_deck, tab_history = st.tabs([
    "📊 Financial Audit & AI Advisor", 
    "🧮 What-If Simulator", 
    "📈 Executive PPTX Deck", 
    "📜 Audit History"
])

with tab_audit:
    st.header("Executive Financial Health & Advisory")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue", f"₦{totals.get('total_revenue', 0):,.2f}")
    col2.metric("Net Profit", f"₦{totals.get('net_profit', 0):,.2f}")
    col3.metric("Profit Margin", f"{totals.get('profit_margin', 0):.2f}%")
    col4.metric("Health Score", f"{health_score}/100")
    
    st.markdown("---")
    
    if st.button("🚀 Run AI CFO Advisory Audit", type="primary"):
        # Check daily usage limit for free tier users (unless master admin)
        if not is_master_admin and user_tier == "free":
            allowed = check_and_increment_daily_usage(user_email, user_tier)
            if not allowed:
                st.error("🔒 **Daily Free Limit Reached!**")
                st.warning("You have exhausted your **5 free analyses** for today. Upgrade to the **Pro Tier (₦14,999/mo)** for unlimited uploads and advanced features, or return tomorrow for 5 fresh free uses!")
                
                with st.expander("⭐ Upgrade Your Account Now", expanded=True):
                    st.write("Unlock unlimited executive insights, scenario modeling, and full PowerPoint deck generators.")
                    if st.button("Confirm Pro Upgrade (₦14,999/mo)"):
                        update_user_tier(user_email, "pro")
                        st.success("🎉 Upgrade successful! Refresh the page to enjoy unlimited access.")
                        st.rerun()
                st.stop()

        with st.spinner("Analyzing spreadsheet data and generating fractional CFO brief..."):
            advisory_text = f"Executive Audit generated for {uploaded_file.name}. Total Revenue: ₦{totals.get('total_revenue', 0):,.2f}, Net Profit: ₦{totals.get('net_profit', 0):,.2f}."
            st.success("Audit complete!")
            st.markdown(advisory_text)
            
            # Save to history
            save_audit_history_db(user_email, "Executive Audit", uploaded_file.name, totals, advisory_text)

with tab_simulator:
    st.header("What-If Scenario Simulator")
    st.write("Test revenue and cost adjustments to forecast future margins.")
    
    rev_adj = st.slider("Revenue Adjustment (%)", -50, 50, 10)
    cost_adj = st.slider("Cost Adjustment (%)", -50, 50, -5)
    
        sim_res = run_simulation(totals, rev_adj, cost_adj)
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Simulated Revenue", f"₦{sim_res['revenue']:,.2f}", f"{rev_adj}%")
    col_b.metric("Simulated Costs", f"₦{sim_res['costs']:,.2f}", f"{cost_adj}%")
    col_c.metric("Simulated Net Profit", f"₦{sim_res['net_profit']:,.2f}", f"{sim_res['profit_margin']:.1f}%")

with tab_deck:
    st.header("12-Slide Executive PowerPoint Deck Generator")
    
    # Feature Gating for PPTX Deck Generator
    if is_master_admin or user_tier in ["pro", "enterprise"]:
        st.write("Generate a board-ready executive presentation deck complete with native charts and metrics.")
        if st.button("Generate & Download Executive PPTX"):
            with st.spinner("Building executive presentation..."):
                deck_bytes = create_executive_deck(cleaned_df, totals, health_score)
                st.download_button(
                    label="📥 Download .pptx Deck",
                    data=deck_bytes,
                    file_name=f"FINCH_Executive_Deck_{datetime.now().strftime('%Y%m%d')}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )
    else:
        st.warning("🔒 **Executive PPTX Deck Generator is locked on the Free Tier.**")
        st.info("Upgrade to **Pro (₦14,999/mo)** or **Enterprise (₦99,000/mo)** to unlock full 12-slide presentation deck generation.")
        if st.button("Upgrade to Pro Now"):
            update_user_tier(user_email, "pro")
            st.success("Upgrade complete! Refreshing...")
            st.rerun()

with tab_history:
    st.header("Past Audit History")
    history_records = load_user_history_db(user_email)
    if history_records:
        for rec in history_records:
            with st.expander(f"📁 {rec.get('file_name', 'Audit')} - {rec.get('timestamp', 'Recent')}"):
                st.write(f"**Total Revenue:** ₦{rec.get('total_revenue', 0):,.2f}")
                st.write(f"**Net Profit:** ₦{rec.get('net_profit', 0):,.2f}")
                st.write(f"**Profit Margin:** {rec.get('profit_margin', 0):.2f}%")
                st.markdown(f"**Advisory:** {rec.get('advisory', 'N/A')}")
    else:
        st.info("No past audit history found for this account.")