import streamlit as st
import pandas as pd
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
db.init_game_settings_table()

# init app
# st.header("Settings")

# Player Administration Section
with st.container(border=True):
    st.header("Players")

    # Create tabs for better organization
    tab1, tab2, tab3 = st.tabs(["Overview", "Manage", "Create New"])

    # Get all players
    players_df = db.get_all_players()

    with tab1:
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

        else:
            st.info(
                "No players found. Add some players using the 'Add Player' tab above."
            )

    with tab2:
        st.write("_Manage players already in the system:_")

        if not players_df.empty:
            # Display players in a more user-friendly way
            for index, player in players_df.iterrows():
                col1, col2, col3 = st.columns([3, 2, 2])

                player_id = int(player["id"])
                player_name = str(player["name"])
                is_active = bool(player["is_active"])

                with col1:
                    status_emoji = "✅" if is_active else "❌"
                    # Use markdown with larger font size for player name and strikethrough for inactive
                    if is_active:
                        st.markdown(f"##### {status_emoji} {player_name}")
                    else:
                        st.markdown(f"##### {status_emoji} ~~{player_name}~~")

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

                    if st.button(
                        button_text, key=f"toggle_{player_id}", type=button_type
                    ):
                        if db.update_player_status_in_database(player_id, new_status):
                            action = "activated" if new_status else "deactivated"
                            st.rerun()

                # Show edit form if in edit mode
                if st.session_state.get(f"editing_{player_id}", False):
                    with st.form(f"edit_form_{player_id}", border=False):
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
                        st.divider()

        else:
            st.info(
                "No players found. Add some players using the 'Add Player' tab above."
            )

    with tab3:
        st.write("_Add a new player to the system:_")

        # Initialize form counter if not exists
        if "form_counter" not in st.session_state:
            st.session_state.form_counter = 0

        with st.form(f"add_player_form_{st.session_state.form_counter}", border=False):
            new_player_name = st.text_input(
                "Player Name", placeholder="Enter player name..."
            )
            submit_button = st.form_submit_button(
                "Add Player", use_container_width=True
            )

            if submit_button:
                if new_player_name.strip():
                    if db.add_player_to_database(new_player_name.strip()):
                        st.success(f"Player '{new_player_name}' added successfully!")
                        # Increment form counter to reset the form
                        st.session_state.form_counter += 1
                        st.rerun()
                else:
                    st.error("Please enter a valid player name.")

# Game-Settings section
ut.h_spacer(1)
with st.container(border=True):
    st.header("Game Settings")

    # Create tabs for better organization
    tab1, tab2, tab3 = st.tabs(["Overview", "Manage", "Create New"])

    # Get all game settings
    settings_df = db.get_all_game_settings()
    with tab1:
        if len(settings_df) > 0:
            # Summary statistics first
            total_settings = len(settings_df)
            active_settings = len(settings_df[settings_df["is_active"] == 1])

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Settings", total_settings, border=True)
            with col2:
                st.metric("Active Settings", active_settings, border=True)

            # Display settings
            for index, setting in settings_df.iterrows():
                setting_id = int(setting["id"])
                setting_name = str(setting["name"])
                setting_note = str(setting["note"]) if pd.notna(setting["note"]) else ""
                setting_type = str(setting["type"])
                is_active = (
                    bool(setting["is_active"])
                    if pd.notna(setting["is_active"]) is not False
                    else True
                )

                status_emoji = "✅" if is_active else "❌"
                type_emoji = {
                    "text": "📝",
                    "number": "🔢",
                    "boolean": "☑️",
                    "list": "📋",
                }
                emoji = type_emoji.get(setting_type, "⚙️")

                # Use strikethrough for inactive settings
                if is_active:
                    st.markdown(f"#### {status_emoji} {emoji} {setting_name}")
                else:
                    st.markdown(f"#### {status_emoji} {emoji} ~~{setting_name}~~")

                # If a note is set
                if setting_note and setting_note != "None":
                    st.markdown(
                        f" -- *{setting_note}*",
                        unsafe_allow_html=True,
                    )

                # If it's a list type, show the list items
                if setting_type == "list":
                    list_items_df = db.get_game_setting_list_items(setting_id)
                    if len(list_items_df) > 0:
                        items = list_items_df["value"].tolist()
                        st.markdown(f"**Items:** {', '.join(items)}")
                    else:
                        st.markdown("**Items:** *No items added yet*")

        else:
            st.info(
                "No game settings found. Add some settings using the 'Add' tab above."
            )

    with tab2:
        st.write("_Manage game setting already in the system:_")

        if len(settings_df) > 0:
            # Display settings
            for index, setting in settings_df.iterrows():
                col1, col2, col3 = st.columns([2, 1, 1])

                setting_id = int(setting["id"])
                setting_name = str(setting["name"])
                setting_note = str(setting["note"]) if pd.notna(setting["note"]) else ""
                setting_type = str(setting["type"])
                is_active = (
                    bool(setting["is_active"])
                    if pd.notna(setting["is_active"])
                    else True
                )

                with col1:
                    status_emoji = "✅" if is_active else "❌"
                    type_emoji = {
                        "number": "🔢",
                        "boolean": "☑️",
                        "list": "📋",
                    }
                    emoji = type_emoji.get(setting_type, "⚙️")

                    # Use strikethrough for inactive settings
                    if is_active:
                        st.markdown(f"##### {status_emoji} {emoji} {setting_name}")
                    else:
                        st.markdown(f"##### {status_emoji} {emoji} ~~{setting_name}~~")

                    # If it's a list type, show the list items
                    if setting_type == "list":
                        list_items_df = db.get_game_setting_list_items(setting_id)
                        if len(list_items_df) > 0:
                            items = list_items_df["value"].tolist()
                            st.markdown(f"**Items:** {', '.join(items)}")
                        else:
                            st.markdown("**Items:** *No items added yet*")

                with col2:
                    if st.button(
                        "✏️ Edit", key=f"edit_setting_{setting_id}", type="secondary"
                    ):
                        # Toggle edit mode
                        current_editing = st.session_state.get(
                            f"editing_setting_{setting_id}", False
                        )
                        st.session_state[f"editing_setting_{setting_id}"] = (
                            not current_editing
                        )

                with col3:
                    # Toggle active/inactive
                    new_status = not is_active
                    button_text = "Deactivate" if is_active else "Activate"
                    button_type = "primary" if is_active else "secondary"

                    if st.button(
                        button_text,
                        key=f"toggle_setting_{setting_id}",
                        type=button_type,
                    ):
                        if db.update_game_setting_status_in_database(
                            setting_id, new_status
                        ):
                            st.rerun()

                # Show edit form if in edit mode
                if st.session_state.get(f"editing_setting_{setting_id}", False):
                    with st.form(f"edit_setting_form_{setting_id}", border=False):
                        col_name, col_type = st.columns(2)

                        with col_name:
                            new_name = st.text_input(
                                "New name:",
                                value=setting_name,
                                key=f"edit_setting_name_{setting_id}",
                            )

                        with col_type:
                            new_type = st.selectbox(
                                "Type:",
                                options=["text", "number", "boolean", "list"],
                                index=["text", "number", "boolean", "list"].index(
                                    setting_type
                                ),
                                format_func=lambda x: {
                                    "text": "📝 Text",
                                    "number": "🔢 Number",
                                    "boolean": "☑️ Boolean",
                                    "list": "📋 List",
                                }[x],
                                key=f"edit_setting_type_{setting_id}",
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
                            # Check if name already exists (excluding current setting)
                            if db.game_setting_exists_except_id(
                                new_name.strip(), setting_id
                            ):
                                st.error(
                                    f"Game setting name '{new_name.strip()}' already exists!"
                                )
                            else:
                                if db.update_game_setting_in_database(
                                    setting_id, new_name.strip(), new_type
                                ):
                                    st.session_state[
                                        f"editing_setting_{setting_id}"
                                    ] = False
                                    st.rerun()
                        elif save_button and not new_name.strip():
                            st.error("Please enter a valid setting name.")
                        elif cancel_button:
                            st.session_state[f"editing_setting_{setting_id}"] = False
                            st.rerun()
                        st.divider()

        else:
            st.info(
                "No game settings found. Add some settings using the 'Add' tab above."
            )

    with tab3:
        st.write("_Add a new game setting to the system:_")

        # Initialize form counter if not exists
        if "settings_form_counter" not in st.session_state:
            st.session_state.settings_form_counter = 0

        with st.form(
            f"add_setting_form_{st.session_state.settings_form_counter}", border=False
        ):
            col1, col2 = st.columns(2)

            with col1:
                new_setting_name = st.text_input(
                    "Setting Name *",
                    placeholder="e.g., Location, Game Mode, Difficulty...",
                )

            with col2:
                setting_type = st.selectbox(
                    "Type *",
                    options=["number", "boolean", "list"],
                    format_func=lambda x: {
                        "number": "🔢 Number",
                        "boolean": "☑️ Boolean",
                        "list": "📋 List",
                    }[x],
                )

            setting_note = st.text_area(
                "Note (optional)",
                placeholder="Optional description of this setting...",
                height=80,
            )

            # Note for list type
            if setting_type == "list":
                st.info(
                    "💡 List items can be added after creating the setting using the manage functionality."
                )

            # Submit button for the entire form
            submit_button = st.form_submit_button(
                "Create Game Setting", use_container_width=True, type="primary"
            )

            if submit_button:
                if new_setting_name.strip():
                    # Add the setting to database
                    setting_id = db.add_game_setting_to_database(
                        new_setting_name.strip(),
                        setting_note.strip() if setting_note else "",
                        setting_type,
                    )

                    if setting_id > 0:
                        st.success(
                            f"Game setting '{new_setting_name}' added successfully!"
                        )

                        # Reset form
                        st.session_state.settings_form_counter += 1
                        st.rerun()
                else:
                    st.error("Please enter a valid setting name.")
