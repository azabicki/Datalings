import streamlit as st
import streamlit_authenticator as stauth


def login():
    # Load credentials from st.secrets
    credentials = {
        "usernames": {
            username: {"name": name, "password": pwd, "roles": role}
            for username, name, pwd, role in zip(
                st.secrets.credentials.usernames,
                st.secrets.credentials.names,
                st.secrets.credentials.passwords,
                st.secrets.credentials.roles,
            )
        }
    }

    # Setup authenticator
    authenticator = stauth.Authenticate(
        credentials,
        cookie_name="my_app_login",  # persistent login
        cookie_key="auth",  # session key
        cookie_expiry_days=7,
    )

    # authenticate
    authenticator.login("main")

    # Handle case where login returns None
    if st.session_state["authentication_status"] == False:
        st.error("Username or password is incorrect")
        st.stop()
    elif st.session_state["authentication_status"] == None:
        st.stop()
    elif st.session_state["authentication_status"]:
        st.session_state["auth"] = authenticator
