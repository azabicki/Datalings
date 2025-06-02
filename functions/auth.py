import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader


# main login function
def login():
    # Load the config
    with open("./functions/user_credentials.yml") as file:
        config = yaml.load(file, Loader=SafeLoader)

    stauth.Hasher.hash_passwords(config["credentials"])
    with open("./functions/user_credentials.yml", "w") as file:
        yaml.dump(config, file, default_flow_style=False)

    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )

    try:
        authenticator.login("main")
    except Exception as e:
        st.error(e)

    # All the authentication info is stored in the session_state
    if st.session_state["authentication_status"]:
        st.session_state["auth"] = authenticator
    if st.session_state["authentication_status"] == False:
        st.error("Username/password is incorrect")
        # Stop the rendering if the user isn't connected
        st.stop()
    elif st.session_state["authentication_status"] == None:
        # Stop the rendering if the user isn't connected
        st.stop()
