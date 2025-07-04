import streamlit as st
from datetime import date
import functions.utils as ut
import functions.auth as auth
import functions.database as db
import pandas as pd
from typing import Dict
import time

st.set_page_config(page_title="Game Results", layout=ut.app_layout)

# auth
auth.login()

# init
ut.default_style()
ut.create_sidebar()


# Advanced caching with multiple layers
@st.cache_data(ttl=600, max_entries=3)
def get_games_summary(page: int, page_size: int):
    """Return cached game summaries for the requested page."""
    df = db.get_games_summary(limit=page_size, offset=(page - 1) * page_size)
    return df.to_dict("records") if not df.empty else []


@st.cache_data(ttl=600)
def get_total_game_count() -> int:
    """Cached total game count for pagination."""
    return db.get_games_count()


@st.cache_data(ttl=300, max_entries=50)
def get_single_game_details(game_id: int):
    """Get detailed information for a single game."""
    return db.get_single_game_details(game_id)


@st.cache_resource  # Cache database connection objects
def get_cached_players_and_settings():
    """Cache frequently accessed reference data."""
    try:
        active_players = db.get_active_players()
        active_settings = db.get_active_game_settings()
        return active_players, active_settings
    except Exception as e:
        st.error(f"Error fetching players/settings: {e}")
        return pd.DataFrame(), pd.DataFrame()


def refresh_reference_caches_if_needed():
    """Clear cached players/settings if other pages requested it."""
    if st.session_state.get("refresh_record_form"):
        get_cached_players_and_settings.clear()  # type: ignore
        st.session_state.refresh_record_form = False


# Advanced session state management
def init_session_state():
    """Initialize session state with performance optimizations."""
    if "game_page_size" not in st.session_state:
        st.session_state.game_page_size = 10
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1

    if "game_form_counter" not in st.session_state:
        st.session_state.game_form_counter = 0
    if "last_cache_clear" not in st.session_state:
        st.session_state.last_cache_clear = time.time()
    if "refresh_record_form" not in st.session_state:
        st.session_state.refresh_record_form = False
    if "refresh_statistics" not in st.session_state:
        st.session_state.refresh_statistics = False
    if "action_message" not in st.session_state:
        st.session_state.action_message = ""
    if "results_tab" not in st.session_state:
        st.session_state.results_tab = "Game History"


def clear_performance_caches():
    """Smart cache clearing - only clear what's needed."""
    try:
        # Clear game-specific caches
        get_games_summary.clear()  # type: ignore
        get_single_game_details.clear()  # type: ignore
        get_total_game_count.clear()  # type: ignore

        # Clear resource cache if needed
        if (
            time.time() - st.session_state.get("last_cache_clear", 0) > 1800
        ):  # 30 minutes
            get_cached_players_and_settings.clear()  # type: ignore
            st.session_state.last_cache_clear = time.time()

    except Exception as e:
        st.error(f"Error clearing caches: {e}")


@st.dialog("Delete Game")
def delete_game_dialog(game_data: Dict, game_number: int):
    """Optimized delete dialog with minimal data loading."""
    game_id = game_data["id"]
    game_title = ut.format_game_title(game_number, game_data["game_date"])

    st.write(
        f"Are you sure you want to delete<p>**{game_title}**?", unsafe_allow_html=True
    )
    st.warning(":material/warning: **This action cannot be undone** :material/warning:")

    # Show lightweight game summary
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Date:** {game_data['game_date']}")
        st.write(f"**Players:** {game_data['player_count']}")

    with col2:
        if game_data.get("highest_score"):
            st.write(f"**Highest Score:** {game_data['highest_score']} pts")
        if game_data.get("lowest_score"):
            st.write(f"**Lowest Score:** {game_data['lowest_score']} pts")

    st.divider()

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
                clear_performance_caches()
                st.session_state.refresh_statistics = True
                st.session_state.action_message = (
                    f"Game #{game_number} deleted successfully!"
                )
                st.session_state.results_tab = "Game History"
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


@st.dialog("Edit Game")
def edit_game_dialog(game_data: Dict, game_number: int):
    """Lazy-loaded edit dialog - only fetch detailed data when opened."""
    game_id = game_data["id"]
    game_title = ut.format_game_title(game_number, game_data["game_date"])

    st.write(f"**Editing:** {game_title}")

    # Lazy load detailed game data
    with st.spinner("Loading game details..."):
        game_details = get_single_game_details(game_id)

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

    # Player scores with efficient rendering
    st.subheader("Player Scores")
    edit_player_scores = {}
    scores_list = game_details.get("scores", [])

    if scores_list:
        # Use columns for better layout
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

    # Game settings with efficient rendering
    edit_setting_values = {}
    settings_list = game_details.get("settings", [])

    if settings_list:
        st.divider()
        st.subheader("Game Settings")

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
                clear_performance_caches()
                st.session_state.refresh_statistics = True
                st.session_state.action_message = (
                    f"Game #{game_number} updated successfully!"
                )
                st.session_state.results_tab = "Game History"
                st.rerun()
            else:
                st.error("Failed to update game. Please try again.")

    with col_cancel:
        if st.button(
            "Cancel",
            type="secondary",
            icon=":material/cancel:",
            use_container_width=True,
            key=f"cancel_edit_{game_id}",
        ):
            st.rerun()


@st.fragment
def display_single_game(game_data: Dict, game_number: int):
    """Ultra-optimized single game display with all details shown."""
    game_id = game_data["id"]
    game_title = ut.format_game_title(game_number, game_data["game_date"])

    with st.container(border=True):
        # Header with action buttons
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

        # Load game details
        game_details = get_single_game_details(game_id)

        # Game content
        col1, col2 = st.columns(2)

        with col1:
            if game_details.get("scores"):
                st.write("**Player Scores:**")
                scores_data = game_details["scores"]

                # Efficient score rendering
                score_text = []
                for i, score_info in enumerate(scores_data):
                    rank = i + 1
                    if rank == 1:
                        medal = "🥇"
                    elif rank == 2:
                        medal = " 🥈"
                    elif rank == 3:
                        medal = "  🥉"
                    else:
                        medal = f"    {rank}."

                    score_text.append(
                        f"{medal} {score_info['player_name']} : {score_info['score']} pts"
                    )

                st.text("\n".join(score_text))

        with col2:
            if game_details.get("settings"):
                st.write("**Game Settings:**")
                settings_text = []

                for setting_info in game_details["settings"]:
                    value = setting_info["value"]
                    setting_type = setting_info["setting_type"]

                    # Efficient value formatting
                    if setting_type == "boolean":
                        value = "Yes" if value.lower() == "true" else "No"
                    elif setting_type == "number":
                        try:
                            value = int(float(value))
                        except:
                            pass
                    elif setting_type == "time":
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

        # Notes
        notes = game_data.get("notes", "")
        if notes and notes != "None":
            st.write(f"**Notes:** {notes}")


@st.fragment
def display_new_game_form():
    """Optimized new game form with cached reference data."""
    st.markdown("#### Record New Game")

    refresh_reference_caches_if_needed()

    # Use cached players and settings
    active_players, active_settings = get_cached_players_and_settings()

    if len(active_players) == 0:
        st.warning(
            "No active players found. Please add and activate players in the Settings page."
        )
        return

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

        # Efficient player score input
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

        # Efficient settings input
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
                                    key=f"setting_{setting_id}_{st.session_state.game_form_counter}"
                                )
                                if value > 0:
                                    setting_values[setting_id] = str(int(value))

                            elif setting_type == "boolean":
                                value = st.toggle(
                                    setting_name,
                                    key=f"setting_{setting_id}_{st.session_state.game_form_counter}"
                                )
                                setting_values[setting_id] = str(value)

                            elif setting_type == "time":
                                value = st.number_input(
                                    f"{setting_name} (minutes)",
                                    min_value=1,
                                    max_value=1440,
                                    value=60,
                                    step=1,
                                    key=f"setting_{setting_id}_{st.session_state.game_form_counter}"
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
                                        key=f"setting_{setting_id}_{st.session_state.game_form_counter}"
                                    )
                                    if value and value.strip():
                                        setting_values[setting_id] = value
                                else:
                                    st.info(f"No items configured for {setting_name}")

        st.divider()

        # Submit button
        submit_game = st.form_submit_button(
            "Save Game",
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
                    clear_performance_caches()
                    st.session_state.refresh_statistics = True
                    new_count = db.get_games_count()
                    st.session_state.action_message = (
                        f"Game #{new_count} recorded successfully!"
                    )
                    st.session_state.results_tab = "Game History"
                    st.rerun()
                else:
                    del st.session_state[submission_key]
                    st.error("Failed to save game. Please try again.")


# Initialize session state
init_session_state()

# Main app layout
st.header("Game Results")
tab1, tab2 = st.tabs(
    [s.center(16, "\u2001") for s in ["Game History", "Record New Game"]]
)

# Game history tab with advanced optimizations
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("#### Game History")
    # Success message just below the header
    if st.session_state.get("action_message"):
        st.success(st.session_state.action_message)
        st.session_state.action_message = ""

    # Performance controls
    with col2:
        st.session_state.game_page_size = st.selectbox(
            "Games per page",
            options=[5, 10, 20, 50],
            format_func=lambda x: f"{x} games per page",
            index=1,  # Default to 10
            label_visibility="collapsed",
            key="page_size_selector",
        )

    total_games = get_total_game_count()
    games_per_page = st.session_state.game_page_size

    max_pages = max((total_games + games_per_page - 1) // games_per_page, 1)
    if max_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.session_state.current_page = st.selectbox(
                "Page",
                options=list(range(1, max_pages + 1)),
                index=min(st.session_state.current_page - 1, max_pages - 1),
                format_func=lambda x: f"Page {x} ({min((x-1)*games_per_page + 1, total_games)}-{min(x*games_per_page, total_games)} of {total_games})",
                key="page_selector",
            )
    else:
        st.session_state.current_page = 1

    games_data = get_games_summary(st.session_state.current_page, games_per_page)

    if games_data:
        games_to_display = games_data

        # Display games with optimized rendering
        for idx, game_data in enumerate(games_to_display):
            game_number = total_games - (
                (st.session_state.current_page - 1) * games_per_page + idx
            )
            display_single_game(game_data, game_number)

    else:
        st.info(
            "No games recorded yet. Use the 'Record New Game' tab to add your first game!"
        )

# New game tab
with tab2:
    display_new_game_form()
