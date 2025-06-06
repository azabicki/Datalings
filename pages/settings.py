import streamlit as st
import functions.utils as ut
import functions.auth as auth
import functions.database as db

st.set_page_config(page_title="Settings", layout="wide")

# auth
auth.login()

# init
ut.default_style()
ut.create_sidebar()

# Initialize database
db.init_players_table()

# init app
# st.header("Settings")

# Player Administration Section
st.subheader("Player Administration")

# Create tabs for better organization
tab1, tab2 = st.tabs(["Manage Players", "Add Player"])

with tab1:
    # Get all players
    players_df = db.get_all_players()

    if not players_df.empty:
        # Summary statistics first
        total_players = len(players_df)
        active_players = len(players_df[players_df["is_active"] == 1])
        inactive_players = total_players - active_players

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Players", total_players, border=True)
        with col2:
            st.metric("Active Players", active_players, border=True)
        with col3:
            st.metric("Inactive Players", inactive_players, border=True)

        # Display players in a more user-friendly way
        for index, player in players_df.iterrows():
            col1, col2, col3 = st.columns([2, 1, 1])

            player_id = int(player["id"])
            player_name = str(player["name"])
            is_active = bool(player["is_active"])

            with col1:
                status_emoji = "✅" if is_active else "❌"
                # Use markdown with larger font size for player name and strikethrough for inactive
                if is_active:
                    st.markdown(f"#### {status_emoji} {player_name}")
                else:
                    st.markdown(f"#### {status_emoji} ~~{player_name}~~")

            with col2:
                # Edit button - toggle edit mode
                if st.button("✏️ Edit", key=f"edit_{player_id}", type="secondary"):
                    # Toggle edit mode
                    current_editing = st.session_state.get(
                        f"editing_{player_id}", False
                    )
                    st.session_state[f"editing_{player_id}"] = not current_editing

            with col3:
                # Toggle active/inactive
                new_status = not is_active
                button_text = "Deactivate" if is_active else "Activate"
                button_type = "primary" if is_active else "secondary"

                if st.button(button_text, key=f"toggle_{player_id}", type=button_type):
                    if db.update_player_status_in_database(player_id, new_status):
                        action = "activated" if new_status else "deactivated"
                        st.rerun()

            # Show edit form if in edit mode
            if st.session_state.get(f"editing_{player_id}", False):
                with st.form(f"edit_form_{player_id}"):
                    new_name = st.text_input(
                        "New name:", value=player_name, key=f"edit_name_{player_id}"
                    )
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        save_button = st.form_submit_button(
                            "Save", use_container_width=True
                        )
                    with col_cancel:
                        cancel_button = st.form_submit_button(
                            "Cancel", use_container_width=True
                        )

                    if save_button and new_name.strip():
                        if db.update_player_name_in_database(
                            player_id, new_name.strip()
                        ):
                            st.session_state[f"editing_{player_id}"] = False
                            st.rerun()
                    elif cancel_button:
                        st.session_state[f"editing_{player_id}"] = False
                        st.rerun()

    else:
        st.info("No players found. Add some players using the 'Add Player' tab above.")

with tab2:
    st.write("Add a new player to the system:")

    # Initialize form counter if not exists
    if "form_counter" not in st.session_state:
        st.session_state.form_counter = 0

    with st.form(f"add_player_form_{st.session_state.form_counter}"):
        new_player_name = st.text_input(
            "Player Name", placeholder="Enter player name..."
        )
        submit_button = st.form_submit_button("Add Player", use_container_width=True)

        if submit_button:
            if new_player_name.strip():
                if db.add_player_to_database(new_player_name.strip()):
                    st.success(f"Player '{new_player_name}' added successfully!")
                    # Increment form counter to reset the form
                    st.session_state.form_counter += 1
                    st.rerun()
            else:
                st.error("Please enter a valid player name.")
