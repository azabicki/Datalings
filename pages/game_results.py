import streamlit as st
from datetime import date
import functions.utils as ut
import functions.auth as auth
import functions.database as db

st.set_page_config(page_title="Game Results", layout=ut.app_layout)

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
        # Fetch all game details in a single loop and calculate metrics
        all_game_details = {}
        duration_games = 0
        total_duration = 0
        age_games = 0
        total_age = 0
        total_points = 0
        total_player_points = 0
        total_player_count = 0
        location_counts = {}
        
        for _, game in games_df.iterrows():
            game_id = int(game["id"])
            game_details = db.get_game_details(game_id)
            all_game_details[game_id] = game_details
            
            if game_details:
                # Process scores
                if game_details.get("scores"):
                    game_total = sum(
                        score_info["score"] for score_info in game_details["scores"]
                    )
                    total_points += game_total
                    
                    for score_info in game_details["scores"]:
                        total_player_points += score_info["score"]
                        total_player_count += 1
                
                # Process settings
                if game_details.get("settings"):
                    for setting_info in game_details["settings"]:
                        setting_name_lower = setting_info["setting_name"].lower()
                        
                        # Duration calculation
                        if "duration" in setting_name_lower:
                            duration_games += 1
                            try:
                                minutes = int(float(setting_info["value"]))
                                total_duration += minutes
                            except:
                                pass
                        
                        # Age calculation
                        elif "age" in setting_name_lower:
                            age_games += 1
                            try:
                                age_value = int(float(setting_info["value"]))
                                total_age += age_value
                            except:
                                pass
                        
                        # Location calculation
                        elif "location" in setting_name_lower:
                            location = setting_info["value"]
                            if location and location.strip():
                                location_counts[location] = (
                                    location_counts.get(location, 0) + 1
                                )

        # Display summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Games", len(games_df), border=True)

        with col2:
            # Display average duration
            if duration_games > 0:
                Avg_duration = total_duration / duration_games
                if Avg_duration > 60:
                    hours = int(Avg_duration // 60)
                    remaining_minutes = int(Avg_duration % 60)
                    duration_text = f"{hours}h {remaining_minutes:02d}m"
                else:
                    duration_text = f"{Avg_duration:.0f}m"
                value_games = f"Avg Duration ({duration_games} games)"
                value = f"{duration_text}"
            else:
                value_games = "Avg Duration"
                value = None
            st.metric(value_games, value, border=True)

        with col3:
            # Display average age
            if age_games > 0:
                value = f"{total_age / age_games:.1f}"
            else:
                value = None
            st.metric("Avg Ages Played", value, border=True)

        with col1:
            # Display average points per game
            Avg_points_per_game = (
                total_points / len(games_df) if len(games_df) > 0 else 0
            )
            st.metric("Avg Points/Game", f"{Avg_points_per_game:.1f}", border=True)

        with col2:
            # Display average points per player per game
            Avg_points_per_player_per_game = (
                total_player_points / total_player_count
                if total_player_count > 0
                else 0
            )
            st.metric(
                "Avg Points/Player/Game",
                f"{Avg_points_per_player_per_game:.1f}",
                border=True,
            )

        with col3:
            # Display superhost
            if location_counts:
                superhost = max(location_counts.keys(), key=lambda x: location_counts[x])
                max_count = location_counts[superhost]

                # Check if there are ties
                tied_locations = [
                    loc for loc, count in location_counts.items() if count == max_count
                ]

                if len(tied_locations) > 1:
                    value = f"{superhost} (+{len(tied_locations)-1} tied)"
                else:
                    value = f"{superhost}"
            else:
                value = None
            st.metric("Superhost", value, border=True)

        # Display each game using pre-fetched details
        for game_index, (_, game) in enumerate(games_df.iterrows()):
            game_id = int(game["id"])
            game_number = len(games_df) - int(game_index)
            player_count = int(game["player_count"])
            notes = str(game["notes"]) if game["notes"] is not None else ""

            # Use pre-fetched game details
            game_details = all_game_details.get(game_id)

            if not game_details:
                continue

            # Create game title with new format
            game_title = ut.format_game_title(game_number, game["game_date"])

            # Main game display
            with st.container(border=True):
                # title
                col1, col2, col3 = st.columns([5, 1, 1], vertical_alignment="bottom")
                with col1:
                    st.markdown(f"### {game_title}")

                # edit button
                with col2:
                    if st.button(
                        "",
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
                        "",
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
                        current_rank = 1
                        prev_score = None

                        for i, score_info in enumerate(scores_data):
                            current_score = score_info["score"]

                            # If score changed, update rank to current position + 1
                            if prev_score is not None and current_score != prev_score:
                                current_rank = i + 1

                            # Assign medal based on rank
                            if current_rank == 1:
                                medal = "🥇"
                            elif current_rank == 2:
                                medal = " 🥈"
                            elif current_rank == 3:
                                medal = "  🥉"
                            else:
                                medal = f"    {current_rank}."

                            score_text.append(
                                f"{medal} {score_info['player_name']} : {score_info['score']} pts"
                            )

                            prev_score = current_score

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
                            current_date = game["game_date"]

                            # Ensure current_date is a date object
                            if not isinstance(current_date, date):
                                current_date = date.today()

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
                                type="primary",
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
                                value = st.toggle(
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
            # Prevent double submission
            submission_key = f"submitting_game_{st.session_state.game_form_counter}"
            if submission_key in st.session_state:
                st.warning("Game submission in progress...")
                st.stop()

            # Set submission flag
            st.session_state[submission_key] = True

            # Validate that at least one player has a score
            non_zero_scores = [score for score in player_scores.values() if score != 0]
            if len(non_zero_scores) == 0:
                del st.session_state[submission_key]
                st.warning("At least one player should have a non-zero score.")
            else:
                if db.add_game_to_database(
                    game_date, player_scores, setting_values, notes
                ):
                    # Clean up submission flag
                    del st.session_state[submission_key]
                    # Increment form counter to reset form
                    st.session_state.game_form_counter += 1
                    st.rerun()
                else:
                    # Clean up submission flag on failure
                    del st.session_state[submission_key]
