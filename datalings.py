import streamlit as st
import functions.utils as ut
import functions.auth as auth

st.set_page_config(page_title="Standings")  # , layout="wide")

# auth
auth.login()

# init
ut.default_style()
ut.create_sidebar()

# init app
st.header("Who should be thrown under the bus?")
st.button("testing the primary color", key="button_key", type="primary")


conn = st.connection("mysql", type="sql")
# # Perform query.
df = conn.query("SELECT * from mytable;", ttl=600)

# Print results.
for row in df.itertuples():
    st.write(f"{row.name} has a :{row.pet}:")
