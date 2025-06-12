import streamlit as st
from datetime import date
import functions.utils as ut
import functions.auth as auth
import functions.database as db
import pandas as pd
from typing import Dict, List, Optional

st.set_page_config(page_title="Game Results", layout=ut.app_layout)

# auth
auth.login()

# init
ut.default_style()
ut.create_sidebar()


# Optimization: Create a more efficient database function
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_all_games_with_details():
    """Get all games with their details in a single optimized query."""
    conn = st.connection("mysql", type="sql")
    try:
        # Single query to get all game data
        games_query = """
        SELECT
            g.id, g.game_date, g.notes, g.created_at,
            COUNT(DISTINCT s.player_id) as player_count,
            GROUP_CONCAT(DISTINCT CONCAT(p.name, ':', s.score) ORDER BY s.score DESC SEPARATOR '|') as scores_concat,
            GROUP_CONCAT(DISTINCT CONCAT(gs.name, ':', gs.type, ':',
                CASE
                    WHEN gs.type = 'list' THEN sv.value_text
                    WHEN gs.type = 'number' THEN sv.value_number
                    WHEN gs.type = 'boolean' THEN sv.value_boolean
                    WHEN gs.type = 'time' THEN sv.value_time_minutes
                END) ORDER BY gs.position SEPARATOR '|') as settings_concat
        FROM datalings_games g
        LEFT JOIN datalings_game_scores s ON g.id = s.game_id
        LEFT JOIN datalings_players p ON s.player_id = p.id
        LEFT JOIN datalings_game_setting_values sv ON g.id = sv.game_id
        LEFT JOIN datalings_game_settings gs ON sv.setting_id = gs.id
        GROUP BY g.id, g.game_date, g.notes, g.created_at
        ORDER BY g.game_date DESC, g.id DESC
        """

        df = conn.query(games_query, ttl=300)

        # Process the concatenated data
        processed_games = []
        for _, row in df.iterrows():
            game_data = {
                "id": row["id"],
                "game_date": row["game_date"],
                "notes": row["notes"],
                "created_at": row["created_at"],
                "player_count": row["player_count"],
                "scores": [],
                "settings": [],
            }

            # Parse scores
            if row["scores_concat"]:
                for score_data in row["scores_concat"].split("|"):
                    if ":" in score_data:
                        name, score = score_data.split(":", 1)
                        game_data["scores"].append(
                            {"player_name": name, "score": int(score)}
                        )

            # Parse settings
            if row["settings_concat"]:
                for setting_data in row["settings_concat"].split("|"):
                    parts = setting_data.split(":", 2)
                    if len(parts) >= 3:
                        name, setting_type, value = parts
                        game_data["settings"].append(
                            {
                                "setting_name": name,
                                "setting_type": setting_type,
                                "value": value,
                            }
                        )

            processed_games.append(game_data)

        return processed_games
    except Exception as e:
        st.error(f"Error fetching games: {e}")
        return []


@st.fragment
def display_game_statistics(games_data: List[Dict]):
    """Fragment for displaying game statistics - only recalculates when games change."""
    if not games_data:
        return

    # Calculate statistics
    duration_games = 0
    total_duration = 0
    age_games = 0
    total_age = 0
    location_counts = {}

    for game in games_data:
        for setting in game.get("settings", []):
            setting_name_lower = setting["setting_name"].lower()

            if "duration" in setting_name_lower:
                duration_games += 1
                try:
                    minutes = int(float(setting["value"]))
                    total_duration += minutes
                except:
                    pass
            elif "age" in setting_name_lower:
                age_games += 1
                try:
                    age_value = int(float(setting["value"]))
                    total_age += age_value
                except:
                    pass
            elif "host" in setting_name_lower:
                location = setting["value"]
                if location and location.strip():
                    location_counts[location] = location_counts.get(location, 0) + 1

    # Display statistics
    col1, col2, col3 = st.columns([2, 2, 3])

    with col1:
        st.metric("Total Games", len(games_data), border=True)

    with col2:
        if duration_games > 0:
            avg_duration = total_duration / duration_games
            if avg_duration > 60:
                hours = int(avg_duration // 60)
                remaining_minutes = int(avg_duration % 60)
                duration_text = f"{hours}h {remaining_minutes:02d}m"
            else:
                duration_text = f"{avg_duration:.0f}m"
            value = duration_text
        else:
            value = None
        st.metric("Avg Duration", value, border=True)

    with col3:
        if location_counts:
            superhost = max(location_counts.keys(), key=lambda x: location_counts[x])
            max_count = location_counts[superhost]
            tied_locations = [
                loc for loc, count in location_counts.items() if count == max_count
            ]

            if len(tied_locations) > 1:
                value = f"{superhost} (+{len(tied_locations)-1} tied)"
            else:
                value = superhost
        else:
            value = None
        st.metric("Superhost", value, border=True)


@st.dialog("Delete Game", width="small")
def delete_game_dialog(game_data: Dict, game_number: int):
    """Dialog for deleting a game."""
    game_id = game_data["id"]
    game_title = ut.format_game_title(game_number, game_data["game_date"])

    st.write(
        f"Are you sure you want to delete<br>**{game_title}**?", unsafe_allow_html=True
    )
    st.warning(":material/bolt: **This action cannot be undone** :material/bolt:")

    # Show game summary
    st.write("**Game Summary:**")
    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Date:** {game_data['game_date']}")
        st.write(f"**Players:** {game_data['player_count']}")

    with col2:
        if game_data.get("scores"):
            winner = max(game_data["scores"], key=lambda x: x["score"])
            st.write(f"**Winner:** {winner['player_name']}")
            st.write(f"**Score:** {winner['score']} pts")

    st.divider()

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Yes, Delete Game",
            type="primary",
            icon=":material/delete:",
            use_container_width=True,
            key=f"confirm_delete_{game_id}",
        ):
            if db.delete_game_from_database(game_id):
                st.cache_data.clear()  # Clear cache after deletion
                st.success("Game deleted successfully!")
                st.rerun()
            else:
                st.error("Failed to delete game. Please try again.")

    with col2:
        if st.button(
            "Cancel",
            type="secondary",
            icon=":material/cancel:",
            use_container_width=True,
            key=f"cancel_delete_{game_id}",
        ):
            st.rerun()


@st.dialog("Edit Game", width="small")
def edit_game_dialog(game_data: Dict, game_number: int):
    """Dialog for editing a game."""
    game_id = game_data["id"]
    game_title = ut.format_game_title(game_number, game_data["game_date"])

    st.write(f"**Editing:** {game_title}")

    # Get fresh data for editing (not cached)
    game_details = db.get_game_details(game_id)

    # Date and Notes
    col1, col2 = st.columns([1, 2])

    with col1:
        current_date = game_data["game_date"]
        if not isinstance(current_date, date):
            current_date = date.today()
        edit_game_date = st.date_input(
            "Game Date",
            value=current_date,
            format="DD.MM.YYYY",
            key=f"dialog_edit_date_{game_id}",
        )

    with col2:
        notes = str(game_data.get("notes", "")) if game_data.get("notes") else ""
        edit_notes = st.text_area(
            "Notes", value=notes, key=f"dialog_edit_notes_{game_id}", height=70
        )

    st.divider()

    # Player scores
    st.subheader("Player Scores")
    edit_player_scores = {}
    if game_details.get("scores"):
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
                            key=f"dialog_edit_score_{game_id}_{player_id}",
                        )
                        edit_player_scores[player_id] = new_score

    # Game settings
    edit_setting_values = {}
    if game_details.get("settings"):
        st.divider()
        st.subheader("Game Settings")
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
                                current_num = int(float(current_value))
                            except:
                                current_num = 0
                            new_value = st.number_input(
                                setting_name,
                                min_value=0,
                                value=current_num,
                                step=1,
                                key=f"dialog_edit_setting_{game_id}_{setting_id}",
                            )
                            if new_value > 0:
                                edit_setting_values[setting_id] = str(new_value)

                        elif setting_type == "boolean":
                            current_bool = current_value.lower() == "true"
                            new_value = st.toggle(
                                setting_name,
                                value=current_bool,
                                key=f"dialog_edit_setting_{game_id}_{setting_id}",
                            )
                            edit_setting_values[setting_id] = str(new_value)

                        elif setting_type == "time":
                            try:
                                current_minutes = int(float(current_value))
                            except:
                                current_minutes = 60
                            new_value = st.number_input(
                                f"{setting_name} (minutes)",
                                min_value=1,
                                max_value=1440,
                                value=current_minutes,
                                step=1,
                                key=f"dialog_edit_setting_{game_id}_{setting_id}",
                            )
                            if new_value >= 1:
                                edit_setting_values[setting_id] = str(new_value)

                        elif setting_type == "list":
                            list_items_df = db.get_game_setting_list_items(setting_id)
                            if len(list_items_df) > 0:
                                options = [""] + list_items_df["value"].tolist()
                                try:
                                    current_index = options.index(current_value)
                                except:
                                    current_index = 0
                                new_value = st.selectbox(
                                    setting_name,
                                    options=options,
                                    index=current_index,
                                    key=f"dialog_edit_setting_{game_id}_{setting_id}",
                                )
                                if new_value and new_value.strip():
                                    edit_setting_values[setting_id] = new_value

    st.divider()

    # Action buttons
    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button(
            "Save Changes",
            type="primary",
            icon=":material/save:",
            use_container_width=True,
            key=f"save_edit_{game_id}",
        ):
            if db.update_game_in_database(
                game_id,
                edit_game_date,
                edit_player_scores,
                edit_setting_values,
                edit_notes or "",
            ):
                st.cache_data.clear()  # Clear cache after update
                st.success("Game updated successfully!")
                st.rerun()
            else:
                st.error("Failed to update game. Please try again.")

    with col_cancel:
        if st.button(
            "Cancel",
            type="secondary",
            use_container_width=True,
            key=f"cancel_edit_{game_id}",
        ):
            st.rerun()


@st.fragment
def display_single_game(game_data: Dict, game_number: int):
    """Fragment for displaying a single game with dialog buttons."""
    game_id = game_data["id"]

    # Create game title
    game_title = ut.format_game_title(game_number, game_data["game_date"])

    with st.container(border=True):
        # Title and buttons
        col1, col2, col3 = st.columns([5, 1, 1], vertical_alignment="bottom")
        with col1:
            st.markdown(f"### {game_title}")

        with col2:
            if st.button(
                "",
                key=f"edit_game_{game_id}",
                type="secondary",
                icon=":material/edit:",
                use_container_width=True,
                help="Edit this game",
            ):
                edit_game_dialog(game_data, game_number)

        with col3:
            if st.button(
                "",
                key=f"delete_game_{game_id}",
                type="secondary",
                icon=":material/delete:",
                use_container_width=True,
                help="Delete this game",
            ):
                delete_game_dialog(game_data, game_number)

        # Game content
        col1, col2 = st.columns(2)

        with col1:
            if game_data.get("scores"):
                st.write("**Player Scores:**")
                scores_data = game_data["scores"]
                scores_data.sort(key=lambda x: x["score"], reverse=True)

                score_text = []
                current_rank = 1
                prev_score = None

                for i, score_info in enumerate(scores_data):
                    current_score = score_info["score"]
                    if prev_score is not None and current_score != prev_score:
                        current_rank = i + 1

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

        with col2:
            if game_data.get("settings"):
                st.write("**Game Settings:**")
                settings_text = []
                for setting_info in game_data["settings"]:
                    value = setting_info["value"]
                    if setting_info["setting_type"] == "boolean":
                        value = "Yes" if value.lower() == "true" else "No"
                    elif setting_info["setting_type"] == "number":
                        try:
                            value = int(float(value))
                        except:
                            pass
                    elif setting_info["setting_type"] == "time":
                        try:
                            minutes = int(float(value))
                            if minutes > 60:
                                hours = minutes // 60
                                remaining_minutes = minutes % 60
                                value = f"{hours}h {remaining_minutes:02d}m"
                            elif minutes == 60:
                                value = "1h"
                            else:
                                value = f"{minutes}m"
                        except:
                            pass

                    settings_text.append(f"**{setting_info['setting_name']}**: {value}")

                st.write(" <br> ".join(settings_text), unsafe_allow_html=True)

        # Display notes
        notes = game_data.get("notes", "")
        if notes and notes != "None":
            st.write(f"**Notes:** {notes}")


@st.fragment
def display_new_game_form():
    """Fragment for new game form."""
    st.markdown("#### Record New Game")

    # Get active players and game settings (cached)
    active_players = db.get_active_players()
    active_settings = db.get_active_game_settings()

    if len(active_players) == 0:
        st.warning(
            "No active players found. Please add and activate players in the Settings page."
        )
        return

    # Initialize form counter if not exists
    if "game_form_counter" not in st.session_state:
        st.session_state.game_form_counter = 0

    with st.form(f"new_game_form_{st.session_state.game_form_counter}", border=True):
        col1, col2 = st.columns([1, 3])

        with col1:
            game_date = st.date_input(
                "Game Date", value=date.today(), format="DD.MM.YYYY"
            )

        with col2:
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
        setting_values = {}
        if len(active_settings) > 0:
            st.divider()
            st.subheader("Game Settings")
            st.caption("Configure the game settings that were used")

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
                                setting_values[setting_id] = str(value)

                            elif setting_type == "time":
                                value = st.number_input(
                                    f"{setting_name} (minutes)",
                                    min_value=1,
                                    max_value=1440,
                                    value=60,
                                    step=1,
                                    key=f"setting_{setting_id}_{st.session_state.game_form_counter}",
                                )
                                if value >= 1:
                                    setting_values[setting_id] = str(int(value))

                            elif setting_type == "list":
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
                                    if value and value.strip():
                                        setting_values[setting_id] = value
                                else:
                                    st.info(f"No items configured for {setting_name}")

        st.divider()

        # Submit button
        submit_game = st.form_submit_button(
            "💾 Save Game",
            use_container_width=True,
            type="primary",
            icon=":material/save:",
        )

        if submit_game:
            submission_key = f"submitting_game_{st.session_state.game_form_counter}"
            if submission_key in st.session_state:
                st.warning("Game submission in progress...")
                return

            st.session_state[submission_key] = True

            non_zero_scores = [score for score in player_scores.values() if score != 0]
            if len(non_zero_scores) == 0:
                del st.session_state[submission_key]
                st.warning("At least one player should have a non-zero score.")
            else:
                if db.add_game_to_database(
                    game_date, player_scores, setting_values, notes
                ):
                    del st.session_state[submission_key]
                    st.session_state.game_form_counter += 1
                    st.cache_data.clear()  # Clear cache after adding new game
                    st.success("Game saved successfully!")
                    st.rerun()
                else:
                    del st.session_state[submission_key]
                    st.error("Failed to save game. Please try again.")


# Main app layout
st.header("Game Results")
tab1, tab2 = st.tabs(
    [s.center(16, "\u2001") for s in ["Game History", "Record New Game"]]
)

# Game history tab
with tab1:
    st.markdown("#### Game History")

    # Get all games with details (cached)
    games_data = get_all_games_with_details()

    if games_data:
        # Display statistics in a fragment
        display_game_statistics(games_data)

        # Add pagination for large datasets
        games_per_page = 10
        total_games = len(games_data)

        if total_games > games_per_page:
            # Pagination controls
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                page = st.selectbox(
                    "Page",
                    options=list(range(1, (total_games // games_per_page) + 2)),
                    format_func=lambda x: f"Page {x} ({min((x-1)*games_per_page + 1, total_games)}-{min(x*games_per_page, total_games)} of {total_games})",
                )

            start_idx = (page - 1) * games_per_page
            end_idx = min(start_idx + games_per_page, total_games)
            games_to_display = games_data[start_idx:end_idx]
        else:
            games_to_display = games_data

        # Display games
        for idx, game_data in enumerate(games_to_display):
            game_number = total_games - (games_data.index(game_data))
            display_single_game(game_data, game_number)

    else:
        st.info(
            "No games recorded yet. Use the 'Record New Game' tab to add your first game!"
        )

# New game tab
with tab2:
    display_new_game_form()
