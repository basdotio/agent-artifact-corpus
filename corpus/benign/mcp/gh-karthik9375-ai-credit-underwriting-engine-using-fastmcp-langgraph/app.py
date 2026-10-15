from graph import workflow
import asyncio
from state import ApplicantState, CreditState
from langchain_core.messages import HumanMessage
import streamlit as st
from auth_utils import register_user, load_users, verify_password

# Set page config
st.set_page_config(page_title="AI Credit Underwriting Engine", page_icon="🏦", layout="centered")

# Authentication in Sidebar
st.sidebar.title("🔐 User Authentication")

# Sign Up Flow
with st.sidebar.expander("📝 Sign Up", expanded=False):
    username_signup = st.text_input("Username", key="signup_user")
    name_signup = st.text_input("Full Name", key="signup_name")
    email_signup = st.text_input("Email", key="signup_email")
    password_signup = st.text_input("Password", type="password", key="signup_pass")
    confirm_password_signup = st.text_input("Confirm Password", type="password", key="signup_confirm")

    if st.button("Register", key="signup_btn"):
        if not all([username_signup, name_signup, email_signup, password_signup]):
            st.error("All fields are required")
        elif password_signup != confirm_password_signup:
            st.error("Passwords do not match")
        else:
            try:
                register_user(username_signup, name_signup, email_signup, password_signup)
                st.success("🎉 Account created! Please login below")
            except ValueError as e:
                st.error(str(e))

# Login Flow
with st.sidebar.expander("👤 Login", expanded=True):
    st.subheader("Login")
    username_login = st.text_input("Username", key="login_user")
    password_login = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login", key="login_btn"):
        users_config = load_users()
        user_data = users_config["credentials"]["usernames"].get(username_login)

        if user_data and verify_password(password_login, user_data["password"]):
            st.session_state["user_role"] = user_data["role"]
            st.session_state["username"] = username_login
            st.success(f"✅ Logged in as {username_login} ({user_data['role']})")
        else:
            st.error("❌ Invalid username or password")

if "user_role" in st.session_state and st.session_state["user_role"]:
    # Main page
    st.title("🏦 AI Credit Underwriting Engine")
    st.caption(f"Logged in as: **{st.session_state['username']} ({st.session_state['user_role']})**")

    # Applicant input form
    with st.form(key="credit_application_form"):
        st.subheader("📋 Credit Application")
        
        name = st.text_input(label="Applicant Name", placeholder="Enter name here...", key="name")
        age = st.number_input(label="Applicant Age", placeholder="Enter age here...", key="age", min_value=18, max_value=100)
        location = st.text_input(label="Applicant Location", placeholder="Enter location here...", key="location")
        employment_status = st.selectbox(label="Employment Status", options=["employed", "self-employed", "unemployed", "retired"], key="employment_status")
        employment_years = st.number_input(label="Employment Years", placeholder="Enter years here...", key="employment_years", min_value=0)
        
        st.subheader("💰 Financial Information")
        
        annual_income = st.number_input(label="Annual Income", placeholder="Enter income here...", key="annual_income", min_value=0.0)
        total_debt = st.number_input(label="Total Debt", placeholder="Enter debt here...", key="total_debt", min_value=0.0)
        credit_score = st.number_input(label="Credit Score", placeholder="Enter score here...", key="credit_score", min_value=300, max_value=850)
        credit_history_length = st.number_input(label="Credit History Length", placeholder="Enter length here...", key="credit_history_length", min_value=0)
        
        submitted = st.form_submit_button(label="Submit")
        
    # Run workflow once form is submitted
    if submitted:
        with st.spinner("Running credit underwriting engine..."):
            applicant = ApplicantState(
                name=name,
                age=age,
                location=location,
                annual_income=annual_income,
                total_debt=total_debt,
                credit_score=credit_score,
                credit_history_length=credit_history_length,
                employment_status=employment_status,
                employment_years=employment_years
            )
            
            credit_state = CreditState(
                applicant=applicant,
                messages=[
                    HumanMessage(
                        content="Evaluate this credit application and produce a decision and explanation based on the applicant's profile. Also, generate an optimal offer only if applicant is approved."
                    )
                ]
            )
            
            result = asyncio.run(workflow.ainvoke(credit_state.model_dump()))
                        
            st.success("✅ Credit Evaluation Completed")
            st.divider()
            
            # Display results
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Credit Decision")
                st.metric(
                    label="Decision",
                    value=result.get("decision", "N/A")
                )

                st.metric(
                    label="Creditworthiness Score",
                    value=result.get("creditworthiness_score", "N/A")
                )
                
            with col2:
                st.subheader("⚠️ Risk Signals")
                st.write("**Fraud Risk:**", result.get("fraud_risk_score", "N/A"))
                st.write("**Income Stability:**", result.get("income_stability_score", "N/A"))
                st.write("**Macroeconomic Risk:**", result.get("market_conditions_score", "N/A"))

            st.divider()
            
            st.subheader("🧠 Decision Explanation")
            st.write(result.get("explanation", "No explanation provided."))
            
            st.divider()
            
            st.subheader("💳 Credit Offer")
            offer = result.get("credit_offer", None)
            
            if offer:
                st.json(offer)
            else:
                st.info("No credit offer generated since the applicant is either not approved or still requires human review.")
    
else:
    st.info("Please log in to access the credit application.")
    st.stop() 
    
# if __name__ == "__main__":
#     applicant = ApplicantState(
#         name="Alice Johnson",
#         age=32,
#         location="Canada",
#         annual_income=85000,
#         total_debt=15000,
#         credit_score=720,
#         credit_history_length=8,
#         employment_status="employed",
#         employment_years=5
#     )

#     credit_state = CreditState(
#         applicant=applicant,
#         messages=[
#             HumanMessage(
#                 content="Evaluate this credit application and produce a decision, explanation, and suitable offer."
#             )
#         ]
#     )

#     result = asyncio.run(workflow.ainvoke(
#         credit_state.model_dump()
#     ))
    
#     # Filter out messages from the final print for brevity
#     print_result = {k: v for k, v in result.items() if k != "messages"}
#     print(json.dumps(print_result, indent=4, default=str))