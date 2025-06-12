import streamlit as st
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_all_games_with_details_optimized():
    """
    Optimized function to get all games with their details in a single query.
    This eliminates the N+1 query problem by fetching everything at once.
    """
    conn = st.connection("mysql", type="sql")
    try:
        # Single optimized query to get all game data
        query = """
        SELECT
            g.id as game_id,
            g.game_date,
            g.notes,
            g.created_at,
            -- Player scores
            s.player_id,
            p.name as player_name,
            s.score,
            -- Settings
            sv.setting_id,
            gs.name as setting_name,
            gs.type as setting_type,
            gs.position,
            CASE
                WHEN gs.type = 'list' THEN sv.value_text
                WHEN gs.type = 'number' THEN CAST(sv.value_number AS CHAR)
                WHEN gs.type = 'boolean' THEN CASE WHEN sv.value_boolean = 1 THEN 'True' ELSE 'False' END
                WHEN gs.type = 'time' THEN CAST(sv.value_time_minutes AS CHAR)
                ELSE ''
            END as setting_value
        FROM datalings_games g
        LEFT JOIN datalings_game_scores s ON g.id = s.game_id
        LEFT JOIN datalings_players p ON s.player_id = p.id
        LEFT JOIN datalings_game_setting_values sv ON g.id = sv.game_id
        LEFT JOIN datalings_game_settings gs ON sv.setting_id = gs.id
        ORDER BY g.game_date DESC, g.id DESC, s.score DESC, gs.position
        """

        df = conn.query(query, ttl=300)

        # Process the results into structured data
        games_dict = {}

        for _, row in df.iterrows():
            game_id = row["game_id"]

            # Initialize game if not exists
            if game_id not in games_dict:
                games_dict[game_id] = {
                    "id": game_id,
                    "game_date": row["game_date"],
                    "notes": row["notes"],
                    "created_at": row["created_at"],
                    "scores": [],
                    "settings": [],
                    "player_count": 0,
                    "_player_ids": set(),
                    "_setting_ids": set(),
                }

            game = games_dict[game_id]

            # Add player score if exists and not already added
            if row["player_id"] and row["player_id"] not in game["_player_ids"]:
                game["scores"].append(
                    {
                        "player_id": row["player_id"],
                        "player_name": row["player_name"],
                        "score": row["score"],
                    }
                )
                game["_player_ids"].add(row["player_id"])
                game["player_count"] += 1

            # Add setting if exists and not already added
            if row["setting_id"] and row["setting_id"] not in game["_setting_ids"]:
                game["settings"].append(
                    {
                        "setting_id": row["setting_id"],
                        "setting_name": row["setting_name"],
                        "setting_type": row["setting_type"],
                        "value": row["setting_value"] or "",
                    }
                )
                game["_setting_ids"].add(row["setting_id"])

        # Clean up helper fields and convert to list
        games_list = []
        for game in games_dict.values():
            # Remove helper fields
            del game["_player_ids"]
            del game["_setting_ids"]

            # Sort scores by score descending
            game["scores"].sort(key=lambda x: x["score"], reverse=True)

            games_list.append(game)

        return games_list

    except Exception as e:
        logger.error(f"Error fetching games with details: {e}")
        st.error(f"Error fetching games: {e}")
        return []


@st.cache_data(ttl=600)  # Cache for 10 minutes (less frequent changes)
def get_game_statistics_optimized():
    """
    Optimized function to calculate game statistics.
    Separate from game details for better caching.
    """
    conn = st.connection("mysql", type="sql")
    try:
        # Single query to get all statistics data
        stats_query = """
        SELECT
            COUNT(DISTINCT g.id) as total_games,
            -- Duration stats
            AVG(CASE
                WHEN gs.name LIKE '%duration%' AND sv.value_time_minutes IS NOT NULL
                THEN sv.value_time_minutes
                END) as avg_duration,
            COUNT(CASE
                WHEN gs.name LIKE '%duration%' AND sv.value_time_minutes IS NOT NULL
                THEN 1
                END) as duration_game_count,
            -- Age stats
            AVG(CASE
                WHEN gs.name LIKE '%age%' AND sv.value_number IS NOT NULL
                THEN sv.value_number
                END) as avg_age,
            COUNT(CASE
                WHEN gs.name LIKE '%age%' AND sv.value_number IS NOT NULL
                THEN 1
                END) as age_game_count,
            -- Location stats
            sv.value_text as location,
            COUNT(CASE
                WHEN gs.name LIKE '%location%' AND sv.value_text IS NOT NULL
                THEN 1
                END) as location_count
        FROM datalings_games g
        LEFT JOIN datalings_game_setting_values sv ON g.id = sv.game_id
        LEFT JOIN datalings_game_settings gs ON sv.setting_id = gs.id
        WHERE gs.name LIKE '%location%' OR gs.name LIKE '%duration%' OR gs.name LIKE '%age%' OR gs.id IS NULL
        GROUP BY sv.value_text
        """

        df = conn.query(stats_query, ttl=600)

        if df.empty:
            return {"total_games": 0, "avg_duration": None, "superhost": None}

        # Process results
        total_games = df["total_games"].iloc[0] if not df.empty else 0
        avg_duration = df["avg_duration"].iloc[0] if not df.empty else None

        # Find superhost (most frequent location)
        location_counts = {}
        for _, row in df.iterrows():
            if row["location"] and row["location_count"] > 0:
                location_counts[row["location"]] = row["location_count"]

        superhost = None
        if location_counts:
            max_count = max(location_counts.values())
            tied_locations = [
                loc for loc, count in location_counts.items() if count == max_count
            ]

            if len(tied_locations) > 1:
                superhost = f"{tied_locations[0]} (+{len(tied_locations)-1} tied)"
            else:
                superhost = tied_locations[0]

        return {
            "total_games": total_games,
            "avg_duration": avg_duration,
            "superhost": superhost,
        }

    except Exception as e:
        logger.error(f"Error fetching game statistics: {e}")
        return {"total_games": 0, "avg_duration": None, "superhost": None}


def clear_games_cache():
    """Helper function to clear game-related caches after updates."""
    try:
        # Clear specific cached functions
        get_all_games_with_details_optimized.clear()
        get_game_statistics_optimized.clear()

        # Also clear general cache
        st.cache_data.clear()

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")


@st.cache_data(ttl=1800)  # Cache for 30 minutes (rarely changes)
def get_active_players_cached():
    """Cached version of get_active_players for better performance."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query(
            "SELECT id, name FROM datalings_players WHERE is_active = 1 ORDER BY name",
            ttl=1800,
        )
        return df
    except Exception as e:
        logger.error(f"Error fetching active players: {e}")
        st.error(f"Error fetching active players: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=1800)  # Cache for 30 minutes (rarely changes)
def get_active_game_settings_cached():
    """Cached version of get_active_game_settings for better performance."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query(
            """SELECT id, name, type, position
               FROM datalings_game_settings
               WHERE is_active = 1
               ORDER BY position, name""",
            ttl=1800,
        )
        return df
    except Exception as e:
        logger.error(f"Error fetching active game settings: {e}")
        st.error(f"Error fetching active game settings: {e}")
        return pd.DataFrame()


def batch_get_game_setting_list_items(
    setting_ids: List[int],
) -> Dict[int, pd.DataFrame]:
    """
    Optimized function to get list items for multiple settings in one query.
    """
    if not setting_ids:
        return {}

    conn = st.connection("mysql", type="sql")
    try:
        # Create placeholders for the IN clause
        placeholders = ",".join(
            [":setting_id_" + str(i) for i in range(len(setting_ids))]
        )

        # Create parameters dict
        params = {
            f"setting_id_{i}": setting_id for i, setting_id in enumerate(setting_ids)
        }

        query = f"""
        SELECT setting_id, value, order_index
        FROM datalings_game_setting_list_items
        WHERE setting_id IN ({placeholders})
        ORDER BY setting_id, order_index, value
        """

        df = conn.query(query, params=params, ttl=1800)

        # Group by setting_id
        result = {}
        for setting_id in setting_ids:
            setting_df = df[df["setting_id"] == setting_id][
                ["value", "order_index"]
            ].copy()
            result[setting_id] = setting_df

        return result

    except Exception as e:
        logger.error(f"Error fetching list items for settings {setting_ids}: {e}")
        return {setting_id: pd.DataFrame() for setting_id in setting_ids}


def optimized_delete_game(game_id: int) -> bool:
    """
    Optimized delete function that also clears relevant caches.
    """
    try:
        # Import the original delete function
        from . import database as db

        result = db.delete_game_from_database(game_id)

        if result:
            # Clear caches after successful deletion
            clear_games_cache()

        return result

    except Exception as e:
        logger.error(f"Error deleting game {game_id}: {e}")
        return False


def optimized_add_game(
    game_date, player_scores: dict, setting_values: dict, notes: str = ""
) -> bool:
    """
    Optimized add game function that also clears relevant caches.
    """
    try:
        # Import the original add function
        from . import database as db

        result = db.add_game_to_database(
            game_date, player_scores, setting_values, notes
        )

        if result:
            # Clear caches after successful addition
            clear_games_cache()

        return result

    except Exception as e:
        logger.error(f"Error adding game: {e}")
        return False


def optimized_update_game(
    game_id: int, game_date, player_scores: dict, setting_values: dict, notes: str = ""
) -> bool:
    """
    Optimized update game function that also clears relevant caches.
    """
    try:
        # Import the original update function
        from . import database as db

        result = db.update_game_in_database(
            game_id, game_date, player_scores, setting_values, notes
        )

        if result:
            # Clear caches after successful update
            clear_games_cache()

        return result

    except Exception as e:
        logger.error(f"Error updating game {game_id}: {e}")
        return False
