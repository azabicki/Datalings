import streamlit as st
import functions.utils as ut
import functions.auth as auth
import functions.database as db

st.set_page_config(page_title="Standings", layout="wide")

# auth
auth.login()

# init
ut.default_style()
ut.create_sidebar()

# Initialize database
db.init_players_table()

# init app
st.markdown("_...work in progress..._")
# st.header("Who should be thrown under the bus?")


# # Get active players from database
# st.divider()
# players_df = db.get_active_players()

# if not players_df.empty:
#     st.subheader("Active Players")
#     for index, player in players_df.iterrows():
#         player_name = str(player["name"])
#         created_date = str(player["created_at"])[:10]  # Extract date part
#         st.write(f"🎮 **{player_name}** - *Player since {created_date}*")
# else:
#     st.info("No active players found. Add some players in the Settings page.")
