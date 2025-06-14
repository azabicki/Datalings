import streamlit as st
import functions.utils as ut
import functions.auth as auth

st.set_page_config(page_title="Hall of Fame", layout=ut.app_layout)

# auth
auth.login()

# init
ut.default_style()
ut.create_sidebar()

# init app
st.header("Hall of Fame")
