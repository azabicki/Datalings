import streamlit as st
import pandas as pd
import logging
from typing import Dict, Tuple, List
from collections import Counter

logger = logging.getLogger(__name__)


def get_all_game_statistics_optimized() -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Optimized function to get all game statistics in minimal database queries.
    Returns: (scores_df, games_df, summary_stats)
    """
    conn = st.connection("mysql", type="sql")

    try:
        # Single comprehensive query to get all game data with scores and basic stats
        comprehensive_query = """
        SELECT
            g.id as game_id,
            g.game_date,
            g.notes,
            s.player_id,
            p.name as player_name,
            s.score,
            COUNT(s.player_id) OVER (PARTITION BY g.id) as player_count,
            SUM(s.score) OVER (PARTITION BY g.id) as game_total_score,
            AVG(s.score) OVER (PARTITION BY g.id) as game_avg_score,
            MIN(s.score) OVER (PARTITION BY g.id) as game_min_score,
            MAX(s.score) OVER (PARTITION BY g.id) as game_max_score,
            (MAX(s.score) OVER (PARTITION BY g.id) - MIN(s.score) OVER (PARTITION BY g.id)) as game_score_range
        FROM datalings_games g
        LEFT JOIN datalings_game_scores s ON g.id = s.game_id
        LEFT JOIN datalings_players p ON s.player_id = p.id
        WHERE s.score IS NOT NULL
        ORDER BY g.game_date DESC, s.score DESC
        """

        main_df = conn.query(comprehensive_query, ttl=300)

        if main_df.empty:
            return pd.DataFrame(), pd.DataFrame(), {}

        # Get all game settings in a single query
        settings_query = """
        SELECT
            sv.game_id,
            gs.name as setting_name,
            gs.type as setting_type,
            sv.value_text,
            sv.value_number,
            sv.value_boolean,
            sv.value_time_minutes
        FROM datalings_game_setting_values sv
        JOIN datalings_game_settings gs ON sv.setting_id = gs.id
        WHERE sv.game_id IN (SELECT DISTINCT id FROM datalings_games)
        ORDER BY sv.game_id, gs.position
        """

        settings_df = conn.query(settings_query, ttl=300)

        # Process settings data efficiently
        settings_processed = process_game_settings_bulk(settings_df)

        # Merge settings data with main data
        main_df = main_df.merge(settings_processed, on="game_id", how="left")

        # Create scores DataFrame
        scores_df: pd.DataFrame = main_df[
            [
                "game_id",
                "game_date",
                "player_id",
                "player_name",
                "score",
                "duration",
                "num_ages",
                "host_selection",
            ]
        ].copy()

        # Create games DataFrame (one row per game)
        games_df = main_df.groupby("game_id").first().reset_index()
        games_df = games_df[
            [
                "game_id",
                "game_date",
                "player_count",
                "game_total_score",
                "game_avg_score",
                "game_min_score",
                "game_max_score",
                "game_score_range",
                "duration",
                "num_ages",
                "host_selection",
            ]
        ].copy()

        # Rename columns for consistency
        games_df.rename(
            {
                "game_total_score": "total_score",
                "game_avg_score": "avg_score",
                "game_min_score": "min_score",
                "game_max_score": "max_score",
                "game_score_range": "score_range",
            },
            inplace=True,
        )

        # Calculate summary statistics efficiently
        summary_stats = calculate_summary_statistics_optimized(scores_df, games_df)

        return scores_df, games_df, summary_stats

    except Exception as e:
        logger.error(f"Error in optimized game statistics query: {e}")
        st.error(f"Error loading game statistics: {e}")
        return pd.DataFrame(), pd.DataFrame(), {}


def process_game_settings_bulk(settings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Process game settings in bulk to extract duration, ages, and host information.
    """
    if settings_df.empty:
        return pd.DataFrame()

    # Process each setting type
    processed_settings = []

    for game_id in settings_df["game_id"].unique():
        game_settings = settings_df[settings_df["game_id"] == game_id]

        duration = None
        num_ages = None
        host_selection = None

        for _, setting_row in game_settings.iterrows():
            setting_name_lower = setting_row["setting_name"].lower()
            setting_type = setting_row["setting_type"]

            # Get value based on type
            if setting_type == "time":
                value = setting_row["value_time_minutes"]
            elif setting_type == "number":
                value = setting_row["value_number"]
            elif setting_type == "list":
                value = setting_row["value_text"]
            elif setting_type == "boolean":
                value = setting_row["value_boolean"]
            else:
                value = setting_row["value_text"]

            # Extract specific settings
            if (
                "duration" in setting_name_lower or "time" in setting_name_lower
            ) and setting_type == "time":
                duration = float(value) if value is not None else None
            elif (
                "# ages" in setting_name_lower or setting_name_lower == "ages"
            ) and setting_type == "number":
                num_ages = int(float(value)) if value is not None else None
            elif "host" in setting_name_lower and setting_type == "list":
                host_selection = str(value) if value is not None else None

        processed_settings.append(
            {
                "game_id": game_id,
                "duration": duration,
                "num_ages": num_ages,
                "host_selection": host_selection,
            }
        )

    return pd.DataFrame(processed_settings)


def calculate_summary_statistics_optimized(
    scores_df: pd.DataFrame, games_df: pd.DataFrame
) -> Dict:
    """
    Calculate summary statistics using vectorized operations for better performance.
    """
    if scores_df.empty or games_df.empty:
        return {}

    # Basic statistics using vectorized operations
    total_games = len(games_df)
    total_points = int(scores_df["score"].sum())

    # Duration statistics
    duration_mask = games_df["duration"].notna()
    total_duration = (
        games_df.loc[duration_mask, "duration"].sum() if duration_mask.any() else 0
    )
    shortest_game = (
        games_df.loc[duration_mask, "duration"].min() if duration_mask.any() else None
    )
    longest_game = (
        games_df.loc[duration_mask, "duration"].max() if duration_mask.any() else None
    )
    avg_duration = (
        games_df.loc[duration_mask, "duration"].mean() if duration_mask.any() else None
    )

    # Ages statistics
    ages_mask = games_df["num_ages"].notna()
    total_ages_played = (
        int(games_df.loc[ages_mask, "num_ages"].sum()) if ages_mask.any() else 0
    )
    lowest_ages = games_df.loc[ages_mask, "num_ages"].min() if ages_mask.any() else None
    highest_ages = (
        games_df.loc[ages_mask, "num_ages"].max() if ages_mask.any() else None
    )
    avg_ages = games_df.loc[ages_mask, "num_ages"].mean() if ages_mask.any() else None

    # Score statistics
    avg_score_per_player_per_game = float(scores_df["score"].mean())
    avg_score_per_game = float(games_df["total_score"].mean())
    avg_score_range = float(games_df["score_range"].mean())

    # Min/Max scores with players
    max_score_idx = scores_df["score"].idxmax()
    min_score_idx = scores_df["score"].idxmin()

    highest_score = int(scores_df.loc[max_score_idx, "score"])
    highest_score_player = scores_df.loc[max_score_idx, "player_name"]
    lowest_score = int(scores_df.loc[min_score_idx, "score"])
    lowest_score_player = scores_df.loc[min_score_idx, "player_name"]

    # Superhost calculation
    host_selections = games_df["host_selection"].dropna().tolist()
    superhost = "N/A"
    superhost_count = 0

    if host_selections:
        host_counts = Counter(host_selections)
        if host_counts:
            max_count = max(host_counts.values())
            tied_hosts = [
                host for host, count in host_counts.items() if count == max_count
            ]
            superhost = ", ".join(tied_hosts) if len(tied_hosts) > 1 else tied_hosts[0]
            superhost_count = max_count

    return {
        "total_games": total_games,
        "total_points": total_points,
        "total_duration": total_duration,
        "total_ages_played": total_ages_played,
        "avg_score_per_player_per_game": avg_score_per_player_per_game,
        "avg_score_per_game": avg_score_per_game,
        "highest_score": highest_score,
        "highest_score_player": highest_score_player,
        "lowest_score": lowest_score,
        "lowest_score_player": lowest_score_player,
        "avg_score_range": avg_score_range,
        "shortest_game": shortest_game,
        "longest_game": longest_game,
        "avg_duration": avg_duration,
        "lowest_ages": int(lowest_ages) if lowest_ages is not None else None,
        "highest_ages": int(highest_ages) if highest_ages is not None else None,
        "avg_ages": avg_ages,
        "superhost": superhost,
        "superhost_count": superhost_count,
    }


def get_game_aggregations_for_charts() -> Dict[str, pd.DataFrame]:
    """
    Get pre-aggregated data for charts to improve rendering performance.
    """
    conn = st.connection("mysql", type="sql")

    try:
        # Day of week aggregation
        dow_query = """
        SELECT
            DAYNAME(game_date) as day_of_week,
            COUNT(*) as game_count
        FROM datalings_games
        GROUP BY DAYNAME(game_date), DAYOFWEEK(game_date)
        ORDER BY DAYOFWEEK(game_date)
        """

        # Monthly aggregation
        monthly_query = """
        SELECT
            DATE_FORMAT(game_date, '%Y-%m') as year_month,
            COUNT(*) as game_count
        FROM datalings_games
        GROUP BY DATE_FORMAT(game_date, '%Y-%m')
        ORDER BY year_month
        """

        # Score distribution bins
        score_distribution_query = """
        SELECT
            FLOOR(s.score/50)*50 as score_bin,
            COUNT(*) as frequency
        FROM datalings_game_scores s
        GROUP BY FLOOR(s.score/50)*50
        ORDER BY score_bin
        """

        # Player consistency data
        player_consistency_query = """
        SELECT
            p.name as player_name,
            COUNT(s.score) as game_count,
            AVG(s.score) as avg_score,
            STDDEV(s.score) as score_std
        FROM datalings_game_scores s
        JOIN datalings_players p ON s.player_id = p.id
        GROUP BY p.id, p.name
        HAVING COUNT(s.score) >= 2
        ORDER BY avg_score DESC
        """

        return {
            "day_of_week": conn.query(dow_query, ttl=600),
            "monthly": conn.query(monthly_query, ttl=600),
            "score_distribution": conn.query(score_distribution_query, ttl=600),
            "player_consistency": conn.query(player_consistency_query, ttl=600),
        }

    except Exception as e:
        logger.error(f"Error getting chart aggregations: {e}")
        return {}


def get_performance_metrics() -> Dict[str, float]:
    """
    Get database performance metrics for monitoring.
    """
    conn = st.connection("mysql", type="sql")

    try:
        # Get table sizes
        table_sizes_query = """
        SELECT
            TABLE_NAME,
            TABLE_ROWS,
            (DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024 as SIZE_MB
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME LIKE 'datalings_%'
        """

        table_info = conn.query(table_sizes_query, ttl=3600)

        metrics = {
            "total_games": 0,
            "total_scores": 0,
            "total_settings": 0,
            "db_size_mb": 0,
        }

        for _, row in table_info.iterrows():
            if row["TABLE_NAME"] == "datalings_games":
                metrics["total_games"] = int(row["TABLE_ROWS"] or 0)
            elif row["TABLE_NAME"] == "datalings_game_scores":
                metrics["total_scores"] = int(row["TABLE_ROWS"] or 0)
            elif row["TABLE_NAME"] == "datalings_game_setting_values":
                metrics["total_settings"] = int(row["TABLE_ROWS"] or 0)

            metrics["db_size_mb"] += float(row["SIZE_MB"] or 0)

        return metrics

    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {}


def create_materialized_statistics_view():
    """
    Create a materialized view for statistics if supported by the database.
    This would be called during database setup or maintenance.
    """
    conn = st.connection("mysql", type="sql")

    try:
        # Note: MySQL doesn't support materialized views, but we can create a regular view
        # or a summary table that gets updated periodically
        view_query = """
        CREATE OR REPLACE VIEW datalings_game_statistics AS
        SELECT
            g.id as game_id,
            g.game_date,
            COUNT(DISTINCT s.player_id) as player_count,
            SUM(s.score) as total_score,
            AVG(s.score) as avg_score,
            MIN(s.score) as min_score,
            MAX(s.score) as max_score,
            MAX(s.score) - MIN(s.score) as score_range,
            STDDEV(s.score) as score_std
        FROM datalings_games g
        LEFT JOIN datalings_game_scores s ON g.id = s.game_id
        WHERE s.score IS NOT NULL
        GROUP BY g.id, g.game_date
        ORDER BY g.game_date DESC
        """

        conn.query(view_query, ttl=0)
        logger.info("Successfully created/updated datalings_game_statistics view")
        return True

    except Exception as e:
        logger.error(f"Error creating statistics view: {e}")
        return False


# Utility functions for the optimized implementation


def batch_process_games(game_ids: List[int], batch_size: int = 50) -> Dict:
    """
    Process games in batches to avoid memory issues with large datasets.
    """
    conn = st.connection("mysql", type="sql")
    results = {"scores": [], "games": [], "settings": []}

    for i in range(0, len(game_ids), batch_size):
        batch = game_ids[i : i + batch_size]
        batch_str = ",".join(map(str, batch))

        try:
            # Process batch of games
            batch_query = f"""
            SELECT g.id, g.game_date, s.player_id, p.name as player_name, s.score
            FROM datalings_games g
            JOIN datalings_game_scores s ON g.id = s.game_id
            JOIN datalings_players p ON s.player_id = p.id
            WHERE g.id IN ({batch_str})
            ORDER BY g.game_date DESC, s.score DESC
            """

            batch_data = conn.query(batch_query, ttl=0)
            results["scores"].append(batch_data)

        except Exception as e:
            logger.error(f"Error processing game batch {batch}: {e}")
            continue

    return results


def get_incremental_updates(last_update_time: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Get only the games and scores that have been updated since the last refresh.
    Useful for implementing incremental cache updates.
    """
    conn = st.connection("mysql", type="sql")

    try:
        incremental_query = """
        SELECT
            g.id as game_id,
            g.game_date,
            g.created_at,
            s.player_id,
            p.name as player_name,
            s.score
        FROM datalings_games g
        LEFT JOIN datalings_game_scores s ON g.id = s.game_id
        LEFT JOIN datalings_players p ON s.player_id = p.id
        WHERE g.created_at > %s OR g.id IN (
            SELECT DISTINCT sv.game_id
            FROM datalings_game_setting_values sv
            WHERE sv.created_at > %s
        )
        ORDER BY g.game_date DESC
        """

        new_data = conn.query(
            incremental_query, params=[last_update_time, last_update_time], ttl=0
        )

        # Split into scores and games DataFrames
        if not new_data.empty:
            scores_df = new_data[new_data["score"].notna()].copy()
            games_df = (
                new_data.groupby(["game_id", "game_date", "created_at"])
                .size()
                .reset_index(name="player_count")
            )
            return scores_df, games_df
        else:
            return pd.DataFrame(), pd.DataFrame()

    except Exception as e:
        logger.error(f"Error getting incremental updates: {e}")
        return pd.DataFrame(), pd.DataFrame()
