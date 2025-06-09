import streamlit as st
import pandas as pd
from datetime import date
import functions.utils as ut
import functions.auth as auth
import functions.database as db

st.set_page_config(page_title="Game Results", layout="wide")

# auth
auth.login()

# init
ut.default_style()
ut.create_sidebar()

# Initialize database
db.init_players_table()
db.init_game_settings_table()
db.init_game_results_tables()

# create tabs for different sections
st.header("Game Results")
tab1, tab2 = st.tabs(["Game History", "Record New Game"])

# game history
with tab1:
    st.markdown("#### Game History")

    # Get all games
    games_df = db.get_all_games()

    if not games_df.empty:
        # Display summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Games", len(games_df), border=True)
        with col2:
            # Calculate average players per game
            avg_players = games_df["player_count"].mean()
            st.metric("Avg Players/Game", f"{avg_players:.1f}", border=True)
        with col3:
            # Show date range
            if len(games_df) > 0:
                latest_date = games_df["game_date"].max()
                formatted_date = db.format_date_german(latest_date)
                st.metric("Latest Game", formatted_date, border=True)

        # Display each game
        for _, game in games_df.iterrows():
            game_id = int(game["id"])
            game_date_str = db.format_date_german(game["game_date"])
            player_count = int(game["player_count"])
            notes = str(game["notes"]) if game["notes"] is not None else ""

            # Get detailed game information
            game_details = db.get_game_details(game_id)

            if not game_details:
                continue

            # Main game display
            with st.container(border=True):
                # title
                col1, col2, col3 = st.columns([3, 1, 1], vertical_alignment="center")
                with col1:
                    st.markdown(f"### 🎯 Game on {game_date_str}")

                # edit button
                with col2:
                    if st.button(
                        "Edit",
                        key=f"edit_game_{game_id}",
                        type="secondary",
                        icon=":material/edit:",
                        use_container_width=True,
                    ):
                        # Toggle edit mode
                        current_editing = st.session_state.get(
                            f"editing_game_{game_id}", False
                        )
                        st.session_state[f"editing_game_{game_id}"] = (
                            not current_editing
                        )
                        st.rerun()

                # delete button
                with col3:
                    if st.button(
                        "Delete",
                        key=f"delete_game_{game_id}",
                        type="secondary",
                        icon=":material/delete:",
                        use_container_width=True,
                    ):
                        # add here _deleting_ functionality
                        st.rerun()

                # player scores
                col1, col2 = st.columns(2)
                with col1:
                    if game_details.get("scores"):
                        st.write("**Player Scores:**")
                        scores_data = game_details["scores"]

                        # Sort by score (descending)
                        scores_data.sort(key=lambda x: x["score"], reverse=True)

                        score_text = []
                        for i, score_info in enumerate(scores_data):
                            position = i + 1
                            if position == 1:
                                medal = "🥇"
                            elif position == 2:
                                medal = " 🥈"
                            elif position == 3:
                                medal = "  🥉"
                            else:
                                medal = f"    {position}."
                            score_text.append(
                                f"{medal} {score_info['player_name']} : {score_info['score']} pts"
                            )

                        st.text("\n".join(score_text))

                # game settings
                with col2:
                    if game_details.get("settings"):
                        st.write("**Game Settings:**")
                        settings_text = []
                        for setting_info in game_details["settings"]:
                            value = setting_info["value"]
                            if setting_info["setting_type"] == "boolean":
                                value = "Yes" if value.lower() == "true" else "No"
                            elif setting_info["setting_type"] == "number":
                                value = int(float(value))
                            elif setting_info["setting_type"] == "time":
                                minutes = int(float(value))
                                if minutes > 60:
                                    hours = minutes // 60
                                    remaining_minutes = minutes % 60
                                    value = f"{hours}h {remaining_minutes:02d}m"
                                elif minutes == 60:
                                    value = "1h"
                                else:
                                    value = f"{minutes}m"

                            settings_text.append(
                                f"**{setting_info['setting_name']}**: {value}"
                            )

                        st.write(" <br> ".join(settings_text), unsafe_allow_html=True)

                # Display notes if any
                if notes and notes != "None":
                    st.write(f"**Notes:** {notes}")

                # Edit form
                if st.session_state.get(f"editing_game_{game_id}", False):
                    st.divider()
                    st.write("**Edit Game:**")

                    with st.form(f"edit_game_form_{game_id}", border=False):
                        # Date and Notes layout
                        col1, col2 = st.columns([1, 3])

                        with col1:
                            # Date input
                            current_date = (
                                db.parse_german_date(game_date_str) or date.today()
                            )
                            edit_game_date = st.date_input(
                                "Game Date",
                                value=current_date,
                                format="DD.MM.YYYY",
                                key=f"edit_date_{game_id}",
                            )

                        with col2:
                            # Notes input
                            edit_notes = st.text_area(
                                "Notes",
                                value=notes,
                                key=f"edit_notes_{game_id}",
                                height=80,
                            )

                        # Player scores
                        st.write("**Player Scores:**")
                        edit_player_scores = {}
                        if game_details.get("scores"):
                            # Create rows with 2 players each
                            scores_list = game_details["scores"]
                            for row_start in range(0, len(scores_list), 2):
                                score_cols = st.columns(2)
                                for col_idx in range(2):
                                    score_idx = row_start + col_idx
                                    if score_idx < len(scores_list):
                                        with score_cols[col_idx]:
                                            score_info = scores_list[score_idx]
                                            player_id = score_info["player_id"]
                                            player_name = score_info["player_name"]
                                            current_score = score_info["score"]

                                            new_score = st.number_input(
                                                f"🎮 {player_name}",
                                                min_value=-1000,
                                                max_value=10000,
                                                value=current_score,
                                                step=1,
                                                key=f"edit_score_{game_id}_{player_id}",
                                            )
                                            edit_player_scores[player_id] = new_score

                        # Game settings
                        edit_setting_values = {}
                        if game_details.get("settings"):
                            st.write("**Game Settings:**")
                            # Create rows with 2 settings each
                            settings_list = game_details["settings"]
                            for row_start in range(0, len(settings_list), 2):
                                settings_cols = st.columns(2)
                                for col_idx in range(2):
                                    setting_idx = row_start + col_idx
                                    if setting_idx < len(settings_list):
                                        with settings_cols[col_idx]:
                                            setting_info = settings_list[setting_idx]
                                            setting_id = setting_info["setting_id"]
                                            setting_name = setting_info["setting_name"]
                                            setting_type = setting_info["setting_type"]
                                            current_value = setting_info["value"]

                                            if setting_type == "number":
                                                try:
                                                    current_num = int(current_value)
                                                except:
                                                    current_num = 0
                                                new_value = st.number_input(
                                                    setting_name,
                                                    min_value=0,
                                                    value=current_num,
                                                    step=1,
                                                    key=f"edit_setting_{game_id}_{setting_id}",
                                                )
                                                if new_value > 0:
                                                    edit_setting_values[setting_id] = (
                                                        str(new_value)
                                                    )

                                            elif setting_type == "boolean":
                                                current_bool = (
                                                    current_value.lower() == "true"
                                                )
                                                new_value = st.toggle(
                                                    setting_name,
                                                    value=current_bool,
                                                    key=f"edit_setting_{game_id}_{setting_id}",
                                                )
                                                # Always save boolean values
                                                edit_setting_values[setting_id] = str(
                                                    new_value
                                                )

                                            elif setting_type == "time":
                                                try:
                                                    # Extract minutes from "X minutes" format
                                                    current_minutes = int(
                                                        current_value.split()[0]
                                                    )
                                                except:
                                                    current_minutes = 60
                                                new_value = st.number_input(
                                                    f"{setting_name} (minutes)",
                                                    min_value=1,
                                                    max_value=1440,
                                                    value=current_minutes,
                                                    step=1,
                                                    key=f"edit_setting_{game_id}_{setting_id}",
                                                )
                                                if new_value >= 1:
                                                    edit_setting_values[setting_id] = (
                                                        str(new_value)
                                                    )

                                            elif setting_type == "list":
                                                # Get list items for this setting
                                                list_items_df = (
                                                    db.get_game_setting_list_items(
                                                        setting_id
                                                    )
                                                )
                                                if len(list_items_df) > 0:
                                                    options = [""] + list_items_df[
                                                        "value"
                                                    ].tolist()
                                                    try:
                                                        current_index = options.index(
                                                            current_value
                                                        )
                                                    except:
                                                        current_index = 0
                                                    new_value = st.selectbox(
                                                        setting_name,
                                                        options=options,
                                                        index=current_index,
                                                        key=f"edit_setting_{game_id}_{setting_id}",
                                                    )
                                                    if (
                                                        new_value
                                                        and new_value.strip()
                                                        and new_value != ""
                                                    ):
                                                        edit_setting_values[
                                                            setting_id
                                                        ] = new_value

                        # Form buttons
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            save_game = st.form_submit_button(
                                "Save Changes",
                                use_container_width=True,
                                icon=":material/save:",
                            )
                        with col_cancel:
                            cancel_edit = st.form_submit_button(
                                "Cancel",
                                use_container_width=True,
                                icon=":material/cancel:",
                            )

                        if save_game:
                            if db.update_game_in_database(
                                game_id,
                                edit_game_date,
                                edit_player_scores,
                                edit_setting_values,
                                edit_notes or "",
                            ):
                                st.success("Game updated successfully!")
                                st.session_state[f"editing_game_{game_id}"] = False
                                st.rerun()

                        elif cancel_edit:
                            st.session_state[f"editing_game_{game_id}"] = False
                            st.rerun()

    else:
        st.info(
            "No games recorded yet. Use the 'Record New Game' tab to add your first game!"
        )

# new game
with tab2:
    st.markdown("#### Record New Game")

    # Get active players and game settings
    active_players = db.get_active_players()
    active_settings = db.get_active_game_settings()

    if len(active_players) == 0:
        st.warning(
            "No active players found. Please add and activate players in the Settings page."
        )
        st.stop()

    # Initialize form counter if not exists
    if "game_form_counter" not in st.session_state:
        st.session_state.game_form_counter = 0

    with st.form(f"new_game_form_{st.session_state.game_form_counter}", border=True):
        col1, col2 = st.columns([1, 3])

        with col1:
            # Date input - default to today, format as dd.mm.yyyy
            game_date = st.date_input(
                "Game Date",
                value=date.today(),
                format="DD.MM.YYYY",
                help="Date when the game was played (dd.mm.yyyy format)",
            )

        with col2:
            # Notes input
            notes = st.text_area(
                "Notes (optional)",
                placeholder="Optional notes about the game...",
                height=80,
            )

        st.divider()

        # Player scores section
        st.subheader("Player Scores")
        st.caption("Enter scores for each player")

        player_scores = {}
        # Create rows with 2 players each
        for row_start in range(0, len(active_players), 2):
            score_cols = st.columns(2)
            for col_idx in range(2):
                player_idx = row_start + col_idx
                if player_idx < len(active_players):
                    with score_cols[col_idx]:
                        player = active_players.iloc[player_idx]
                        player_id = int(player["id"])
                        player_name = str(player["name"])

                        score = st.number_input(
                            f"🎮 {player_name}",
                            min_value=-20,
                            max_value=200,
                            value=0,
                            step=1,
                            key=f"score_{player_id}_{st.session_state.game_form_counter}",
                        )
                        player_scores[player_id] = score

        # Game settings section
        if len(active_settings) > 0:
            st.divider()
            st.subheader("Game Settings")
            st.caption("Configure the game settings that were used")

            setting_values = {}
            # Create rows with 2 settings each
            for row_start in range(0, len(active_settings), 2):
                settings_cols = st.columns(2, vertical_alignment="bottom")
                for col_idx in range(2):
                    setting_idx = row_start + col_idx
                    if setting_idx < len(active_settings):
                        with settings_cols[col_idx]:
                            setting = active_settings.iloc[setting_idx]
                            setting_id = int(setting["id"])
                            setting_name = str(setting["name"])
                            setting_type = str(setting["type"])

                            if setting_type == "number":
                                value = st.number_input(
                                    setting_name,
                                    value=1,
                                    step=1,
                                    key=f"setting_{setting_id}_{st.session_state.game_form_counter}",
                                )
                                if value > 0:
                                    setting_values[setting_id] = str(int(value))

                            elif setting_type == "boolean":
                                # value = st.toggle(
                                #     setting_name,
                                #     key=f"setting_{setting_id}_{st.session_state.game_form_counter}",
                                # )
                                value = st.checkbox(
                                    setting_name,
                                    key=f"setting_{setting_id}_{st.session_state.game_form_counter}",
                                )
                                # Always save boolean values
                                setting_values[setting_id] = str(value)

                            elif setting_type == "time":
                                value = st.number_input(
                                    f"{setting_name} (minutes)",
                                    min_value=1,
                                    max_value=1440,  # 24 hours max
                                    value=60,
                                    step=1,
                                    key=f"setting_{setting_id}_{st.session_state.game_form_counter}",
                                )
                                if value >= 1:
                                    setting_values[setting_id] = str(int(value))

                            elif setting_type == "list":
                                # Get list items for this setting
                                list_items_df = db.get_game_setting_list_items(
                                    setting_id
                                )
                                if len(list_items_df) > 0:
                                    options = list_items_df["value"].tolist()
                                    value = st.selectbox(
                                        setting_name,
                                        options=options,
                                        key=f"setting_{setting_id}_{st.session_state.game_form_counter}",
                                    )
                                    if value and value.strip() and value != "":
                                        setting_values[setting_id] = value
                                else:
                                    st.info(f"No items configured for {setting_name}")
        else:
            setting_values = {}

        st.divider()

        # Submit button
        submit_game = st.form_submit_button(
            "Save Game",
            use_container_width=True,
            type="primary",
            icon=":material/save:",
        )

        if submit_game:
            # Validate that at least one player has a score
            non_zero_scores = [score for score in player_scores.values() if score != 0]
            if len(non_zero_scores) == 0:
                st.warning("At least one player should have a non-zero score.")
            else:
                if db.add_game_to_database(
                    game_date, player_scores, setting_values, notes
                ):
                    st.success("Game recorded successfully!")
                    st.session_state.game_form_counter += 1
                    st.rerun()
