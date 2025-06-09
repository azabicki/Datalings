import streamlit as st
import pandas as pd
import functions.utils as ut
import functions.auth as auth
import functions.database as db

st.set_page_config(page_title="Settings", layout=ut.app_layout)

# auth
auth.login()

# init
ut.default_style()
ut.create_sidebar()

# Initialize database
db.init_players_table()
db.init_game_settings_table()

# Player Administration Section
with st.container(border=True):
    st.header("Players")

    # Create tabs for better organization
    tab1, tab2, tab3 = st.tabs(["Overview", "Manage", "Create New"])

    # Get all players
    players_df = db.get_all_players()

    # overview of players
    with tab1:
        if not players_df.empty:
            players_df_active = players_df[players_df["is_active"] == 1]
            players_df_inactive = players_df[players_df["is_active"] == 0]

            # Summary statistics first
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Players", len(players_df), border=True)
            with col2:
                st.metric("Active Players", len(players_df_active), border=True)
            with col3:
                st.metric("Inactive Players", len(players_df_inactive), border=True)

            # display ACTIVE players
            if len(players_df_active) > 0:
                for row_start in range(0, len(players_df_active), 2):
                    player_cols = st.columns([1, 2, 3], vertical_alignment="center")
                    with player_cols[0]:
                        st.write("**active**:" if row_start == 0 else "")
                    for col_idx in range(2):
                        player_idx = row_start + col_idx
                        if player_idx < len(players_df_active):
                            with player_cols[col_idx + 1]:
                                player = players_df_active.iloc[player_idx]
                                st.markdown(f"#### ✅ {player['name']}")

            # display INACTIVE players
            if len(players_df_inactive) > 0:
                for row_start in range(0, len(players_df_inactive), 2):
                    player_cols = st.columns([1, 2, 3], vertical_alignment="center")
                    with player_cols[0]:
                        st.write("**inactive**:" if row_start == 0 else "")
                    for col_idx in range(2):
                        player_idx = row_start + col_idx
                        if player_idx < len(players_df_inactive):
                            with player_cols[col_idx + 1]:
                                player = players_df_inactive.iloc[player_idx]
                                st.markdown(f"#### ❌ ~~{player['name']}~~")

        else:
            st.info(
                "No players found. Add some players using the 'Create New' tab above."
            )

    # edit players
    with tab2:
        st.write("_Manage players already in the system:_")

        if not players_df.empty:
            # Display players in a more user-friendly way
            for _, player in players_df.iterrows():
                col1, col2, col3 = st.columns([3, 2, 2], vertical_alignment="center")

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
                    if st.button(
                        "Edit",
                        key=f"edit_{player_id}",
                        type="secondary",
                        icon=":material/edit:",
                        use_container_width=True,
                    ):
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
                    button_icon = (
                        ":material/add_circle:"
                        if new_status
                        else ":material/remove_circle:"
                    )

                    if st.button(
                        button_text,
                        key=f"toggle_{player_id}",
                        type=button_type,
                        icon=button_icon,
                        use_container_width=True,
                    ):
                        if db.update_player_status_in_database(player_id, new_status):
                            action = "activated" if new_status else "deactivated"
                            st.rerun()

                # Show edit form if in edit mode
                if st.session_state.get(f"editing_{player_id}", False):
                    with st.form(f"edit_form_{player_id}", border=False):
                        new_name = st.text_input(
                            "New name:",
                            value=player_name,
                            key=f"edit_name_{player_id}",
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
                "No players found. Add some players using the 'Create New' tab above."
            )

    # add new players
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
                "Add Player", use_container_width=True, type="primary"
            )

            if submit_button:
                if new_player_name.strip():
                    if db.add_player_to_database(new_player_name.strip()):
                        # Increment form counter to reset the form
                        st.session_state.form_counter += 1
                        st.rerun()
                else:
                    st.error("Please enter a valid player name.")

ut.h_spacer(1)
# Game-Settings section
with st.container(border=True):
    st.header("Game Settings")

    # Create tabs for better organization
    tab1, tab2, tab3 = st.tabs(["Overview", "Manage", "Create New"])

    # Get all game settings
    settings_df = db.get_all_game_settings()

    # overview of game settings
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
            for _, setting in settings_df.iterrows():
                setting_id = int(setting["id"])
                setting_name = str(setting["name"])
                setting_note = (
                    str(setting["note"]) if setting["note"] is not None else ""
                )
                setting_type = str(setting["type"])
                is_active = (
                    bool(setting["is_active"])
                    if pd.notna(setting["is_active"]) is not False
                    else True
                )

                status_emoji = "✅" if is_active else "❌"
                type_emoji = {
                    "number": "🔢",
                    "boolean": "☑️",
                    "list": "📋",
                    "time": "⏱️",
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
                        st.write(
                            f"**Items**: _Please edit {setting_name} and add some items_"
                        )

        else:
            st.info(
                "No game settings found. Add some settings using the 'Create New' tab above."
            )

    # edit game settings
    with tab2:
        st.write("_Manage game setting already in the system:_")

        if len(settings_df) > 0:
            # Display settings
            for index, (_, setting) in enumerate(settings_df.iterrows()):
                setting_id = int(setting["id"])
                setting_name = str(setting["name"])
                setting_note = (
                    str(setting["note"]) if setting["note"] is not None else ""
                )

                setting_type = str(setting["type"])
                is_active = (
                    bool(setting["is_active"])
                    if pd.notna(setting["is_active"]) is not False
                    else True
                )

                col1, col2, col3, col4 = st.columns(
                    [5, 2, 1, 1], vertical_alignment="center"
                )
                with col1:
                    status_emoji = "✅" if is_active else "❌"
                    type_emoji = {
                        "number": "🔢",
                        "boolean": "☑️",
                        "list": "📋",
                        "time": "⏱️",
                    }
                    emoji = type_emoji.get(setting_type, "⚙️")

                    # Use strikethrough for inactive settings
                    if is_active:
                        st.markdown(f"##### {status_emoji} {emoji} {setting_name}")
                    else:
                        st.markdown(f"##### {status_emoji} {emoji} ~~{setting_name}~~")

                with col2:
                    # Initialize counter for this setting if not exists
                    counter_key = f"counter_{setting_id}"
                    if counter_key not in st.session_state:
                        st.session_state[counter_key] = 0

                    # Use counter in key to force reset after each action
                    segment_key = (
                        f"edit_setting_up_{setting_id}_{st.session_state[counter_key]}"
                    )

                    # Determine available options based on position
                    is_first = index == 0
                    is_last = index == len(settings_df) - 1

                    updown = {}
                    if not is_last:  # Can move down
                        updown[0] = ":material/arrow_downward:"
                    if not is_first:  # Can move up
                        updown[1] = ":material/arrow_upward:"

                    position_action = None
                    if updown:  # Only show segmented control if there are options
                        position_action = st.segmented_control(
                            "_",
                            options=updown.keys(),
                            format_func=lambda option: updown[option],
                            key=segment_key,
                            selection_mode="single",
                            label_visibility="collapsed",
                            default=None,
                        )

                    # Handle position changes
                    if position_action is not None:
                        if position_action == 1:  # Move up
                            if db.move_setting_up(setting_id):
                                st.session_state[counter_key] += 1
                                st.rerun()
                        elif position_action == 0:  # Move down
                            if db.move_setting_down(setting_id):
                                st.session_state[counter_key] += 1
                                st.rerun()

                with col3:
                    if st.button(
                        "",
                        key=f"edit_setting_{setting_id}",
                        type="secondary",
                        icon=":material/edit:",
                        use_container_width=True,
                    ):
                        # Toggle edit mode
                        current_editing = st.session_state.get(
                            f"editing_setting_{setting_id}", False
                        )
                        st.session_state[f"editing_setting_{setting_id}"] = (
                            not current_editing
                        )

                with col4:
                    # Toggle active/inactive
                    new_status = not is_active
                    button_type = "primary" if is_active else "secondary"
                    button_icon = (
                        ":material/add_circle:"
                        if new_status
                        else ":material/remove_circle:"
                    )

                    # Check if it's a list type with no items
                    button_disabled = False
                    if setting_type == "list" and not is_active:
                        list_items_df = db.get_game_setting_list_items(setting_id)
                        if len(list_items_df) == 0:
                            button_disabled = True

                    if st.button(
                        "",
                        key=f"toggle_setting_{setting_id}",
                        type=button_type,
                        icon=button_icon,
                        use_container_width=True,
                        disabled=button_disabled,
                        help=(
                            "Add list items before activating"
                            if button_disabled
                            else None
                        ),
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
                                "New Name:",
                                value=setting_name,
                                key=f"edit_setting_name_{setting_id}",
                            )

                        with col_type:
                            new_type = st.selectbox(
                                "New Type:",
                                options=["number", "boolean", "list", "time"],
                                index=[
                                    "number",
                                    "boolean",
                                    "list",
                                    "time",
                                ].index(setting_type),
                                format_func=lambda x: {
                                    "number": "🔢 Number",
                                    "boolean": "☑️ Boolean",
                                    "list": "📋 List",
                                    "time": "⏱️ Time",
                                }[x],
                                key=f"edit_setting_type_{setting_id}",
                            )

                        new_note = st.text_area(
                            "New Note (optional)",
                            value=setting_note,
                            height=80,
                            key=f"edit_setting_note_{setting_id}",
                        )

                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            save_button = st.form_submit_button(
                                "Save", use_container_width=True, icon=":material/save:"
                            )
                        with col_cancel:
                            cancel_button = st.form_submit_button(
                                "Cancel",
                                use_container_width=True,
                                icon=":material/cancel:",
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
                                    setting_id, new_name.strip(), new_type, new_note
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

                    # List item management outside the form (for list-type settings)
                    if setting_type == "list":
                        st.markdown("##### _Manage List Items_")

                        # Get current list items
                        list_items_df = db.get_game_setting_list_items(setting_id)

                        # Show current items for editing
                        if len(list_items_df) > 0:
                            for idx, (_, item_row) in enumerate(
                                list_items_df.iterrows(), 1
                            ):
                                col_item, col_edit = st.columns([3, 1])
                                item_id = int(item_row["id"])
                                item_value = str(item_row["value"])

                                with col_item:
                                    # Use text input for editing
                                    edit_key = f"edit_item_{setting_id}_{item_id}"
                                    if edit_key not in st.session_state:
                                        st.session_state[edit_key] = item_value

                                    new_value = st.text_input(
                                        f"Item {idx}:",
                                        value=st.session_state[edit_key],
                                        key=f"input_{edit_key}",
                                        label_visibility="collapsed",
                                    )

                                with col_edit:
                                    if st.button(
                                        "Rename",
                                        key=f"rename_item_{setting_id}_{item_id}",
                                        type="secondary",
                                        icon=":material/edit_note:",
                                        use_container_width=True,
                                        help="Update item name",
                                    ):
                                        if (
                                            new_value
                                            and new_value.strip()
                                            and new_value.strip() != item_value
                                        ):
                                            if db.update_list_item_in_setting(
                                                item_id, new_value.strip()
                                            ):
                                                st.session_state[edit_key] = (
                                                    new_value.strip()
                                                )
                                                st.rerun()
                                            elif not new_value or not new_value.strip():
                                                st.error(
                                                    "Please enter a valid item name."
                                                )
                                        else:
                                            st.info("No changes made.")
                        else:
                            st.info(
                                f"💡 Activate  _**{setting_name}**_ once you've added all desired list items."
                            )

                        # Add new item
                        col_input, col_add = st.columns(
                            [3, 1], vertical_alignment="bottom"
                        )

                        with col_input:
                            # Use counter for input field reset
                            input_counter_key = f"input_counter_{setting_id}"
                            if input_counter_key not in st.session_state:
                                st.session_state[input_counter_key] = 0

                            new_item = st.text_input(
                                "Add new item:",
                                placeholder="Enter new list item...",
                                key=f"input_new_item_{setting_id}_{st.session_state[input_counter_key]}",
                            )

                        with col_add:
                            if st.button(
                                "Add",
                                key=f"add_item_{setting_id}",
                                icon=":material/add:",
                                use_container_width=True,
                            ):
                                if new_item and new_item.strip():
                                    # Get the next order index
                                    next_order = len(list_items_df)
                                    if db.add_list_item_to_setting(
                                        setting_id, new_item.strip(), next_order
                                    ):
                                        # Clear input field by incrementing counter (creates new widget)
                                        st.session_state[input_counter_key] += 1
                                        st.rerun()
                                else:
                                    st.error("Please enter a valid item.")
                    st.divider()

        else:
            st.info(
                "No game settings found. Add some settings using the 'Create New' tab above."
            )

    # add game settings
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
                    options=["number", "boolean", "list", "time"],
                    format_func=lambda x: {
                        "number": "🔢 Number",
                        "boolean": "☑️ Boolean",
                        "list": "📋 List",
                        "time": "⏱️ Time",
                    }[x],
                )

            setting_note = st.text_area(
                "Note (optional)",
                placeholder="Optional description of this setting...",
                height=80,
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
                        # Reset form
                        st.session_state.settings_form_counter += 1
                        st.rerun()
                else:
                    st.error("Please enter a valid setting name.")

            # info about list-type settings
            st.write(
                "> :small[**NOTE:** _List-type settings_ are created as **inactive** by default. After creation, go to the Manage tab to add list items, then activate the setting.]"
            )
