import streamlit as st
import pandas as pd
import logging
from typing import Dict, Tuple, List, Optional
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


@st.cache_data(ttl=300, show_spinner=False)
def get_dashboard_data_optimized() -> Optional[Dict]:
    """
    Single optimized query to get all dashboard data at once.
    Returns comprehensive data structure for dashboard rendering.
    """
    conn = st.connection("mysql", type="sql")
    
    try:
        # Main comprehensive query - get all game data with scores and rankings in one go
        main_query = """
        WITH game_rankings AS (
            SELECT 
                g.id as game_id,
                g.game_date,
                g.notes,
                s.player_id,
                p.name as player_name,
                s.score,
                RANK() OVER (PARTITION BY g.id ORDER BY s.score DESC) as game_rank,
                COUNT(*) OVER (PARTITION BY g.id) as players_in_game
            FROM datalings_games g
            LEFT JOIN datalings_game_scores s ON g.id = s.game_id
            LEFT JOIN datalings_players p ON s.player_id = p.id
            WHERE s.score IS NOT NULL AND p.is_active = 1
        )
        SELECT 
            game_id,
            game_date,
            notes,
            player_id,
            player_name,
            score,
            game_rank,
            players_in_game,
            CASE 
                WHEN game_rank = 1 THEN 7
                WHEN game_rank = 2 THEN 4
                WHEN game_rank = 3 THEN 2
                ELSE 1
            END as ranking_points
        FROM game_rankings
        ORDER BY game_date DESC, score DESC
        """
        
        scores_df = conn.query(main_query, ttl=300)
        
        if scores_df.empty:
            return None
            
        # Get game settings data in a single query
        settings_query = """
        SELECT 
            sv.game_id,
            gs.name as setting_name,
            gs.type as setting_type,
            CASE 
                WHEN gs.type = 'number' THEN CAST(sv.value_number as CHAR)
                WHEN gs.type = 'boolean' THEN CASE WHEN sv.value_boolean = 1 THEN 'True' ELSE 'False' END
                WHEN gs.type = 'time' THEN CAST(sv.value_time_minutes as CHAR)
                ELSE sv.value_text
            END as setting_value
        FROM datalings_game_setting_values sv
        JOIN datalings_game_settings gs ON sv.setting_id = gs.id
        WHERE sv.game_id IN (SELECT DISTINCT game_id FROM (
            SELECT g.id as game_id
            FROM datalings_games g
            LEFT JOIN datalings_game_scores s ON g.id = s.game_id
            LEFT JOIN datalings_players p ON s.player_id = p.id
            WHERE s.score IS NOT NULL AND p.is_active = 1
        ) tmp)
        ORDER BY sv.game_id, gs.position
        """
        
        settings_df = conn.query(settings_query, ttl=300)
        
        # Calculate comprehensive statistics
        dashboard_data = _calculate_comprehensive_stats_optimized(scores_df, settings_df)
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error in get_dashboard_data_optimized: {e}")
        return None


def _calculate_comprehensive_stats_optimized(scores_df: pd.DataFrame, settings_df: pd.DataFrame) -> Dict:
    """
    Calculate all dashboard statistics in an optimized way.
    """
    # Basic aggregations
    total_games = scores_df["game_id"].nunique()
    
    # Player statistics calculation
    player_stats = {}
    
    # Group by player for efficient calculation
    player_groups = scores_df.groupby("player_name")
    
    for player_name, player_data in player_groups:
        games_played = len(player_data)
        total_score = player_data["score"].sum()
        avg_score = player_data["score"].mean()
        
        # Win and podium statistics
        wins = len(player_data[player_data["game_rank"] == 1])
        podium_finishes = len(player_data[player_data["game_rank"] <= 3])
        
        # Ranking points
        total_ranking_points = player_data["ranking_points"].sum()
        
        # Performance metrics
        best_score = player_data["score"].max()
        worst_score = player_data["score"].min()
        best_rank = player_data["game_rank"].min()
        worst_rank = player_data["game_rank"].max()
        avg_rank = player_data["game_rank"].mean()
        
        # Consistency (standard deviation)
        score_std = player_data["score"].std() if games_played > 1 else 0
        
        player_stats[player_name] = {
            "games_played": games_played,
            "total_score": int(total_score),
            "avg_score": avg_score,
            "wins": wins,
            "podium_finishes": podium_finishes,
            "win_rate": (wins / games_played * 100) if games_played > 0 else 0,
            "podium_rate": (podium_finishes / games_played * 100) if games_played > 0 else 0,
            "total_ranking_points": int(total_ranking_points),
            "avg_ranking_points": total_ranking_points / games_played if games_played > 0 else 0,
            "best_score": int(best_score),
            "worst_score": int(worst_score),
            "best_rank": int(best_rank),
            "worst_rank": int(worst_rank),
            "avg_rank": avg_rank,
            "score_consistency": score_std,
            "games_data": player_data.sort_values("game_date")
        }
    
    # Process settings for age statistics
    age_stats = _calculate_age_statistics(settings_df)
    
    # Prepare data for charts
    chart_data = _prepare_chart_data(scores_df, player_stats)
    
    return {
        "player_stats": player_stats,
        "scores_df": scores_df,
        "total_games": total_games,
        "age_stats": age_stats,
        "chart_data": chart_data
    }


def _calculate_age_statistics(settings_df: pd.DataFrame) -> Dict:
    """Calculate age-related statistics from settings."""
    total_age = 0
    age_games = 0
    
    if not settings_df.empty:
        # Look for age-related settings
        age_settings = settings_df[
            settings_df["setting_name"].str.lower().str.contains("age", na=False)
        ]
        
        for _, setting in age_settings.iterrows():
            try:
                age_value = float(setting["setting_value"])
                total_age += age_value
                age_games += 1
            except (ValueError, TypeError):
                continue
    
    return {
        "total_age": total_age,
        "age_games": age_games,
        "avg_age": total_age / age_games if age_games > 0 else 0
    }


def _prepare_chart_data(scores_df: pd.DataFrame, player_stats: Dict) -> Dict:
    """Prepare optimized data structures for chart rendering."""
    
    # Cumulative data preparation
    cumulative_data = []
    for player_name, stats in player_stats.items():
        player_games = stats["games_data"].sort_values("game_date")
        cumulative_score = 0
        
        for i, (_, game) in enumerate(player_games.iterrows(), 1):
            cumulative_score += game["score"]
            cumulative_data.append({
                "Player": player_name,
                "Game": i,
                "Cumulative Score": cumulative_score,  
                "Game Date": game["game_date"]
            })
    
    # Wins data preparation
    wins_data = [
        {"Player": name, "Wins": stats["wins"]} 
        for name, stats in player_stats.items()
    ]
    wins_data.sort(key=lambda x: x["Wins"], reverse=True)
    
    # Ranking data preparation
    ranking_data = [
        {
            "Player": name, 
            "Total Points": stats["total_ranking_points"],
            "Avg Points": stats["avg_ranking_points"]
        }
        for name, stats in player_stats.items()
    ]
    ranking_data.sort(key=lambda x: x["Total Points"], reverse=True)
    
    # Performance radar data preparation
    max_total_score = max(s["total_score"] for s in player_stats.values()) if player_stats else 1
    max_win_rate = max(s["win_rate"] for s in player_stats.values()) if player_stats else 1
    max_podium_rate = max(s["podium_rate"] for s in player_stats.values()) if player_stats else 1
    min_avg_rank = min(s["avg_rank"] for s in player_stats.values()) if player_stats else 1
    max_avg_rank = max(s["avg_rank"] for s in player_stats.values()) if player_stats else 1
    total_games = max(s["games_played"] for s in player_stats.values()) if player_stats else 1
    
    radar_data = []
    for name, stats in player_stats.items():
        radar_data.append({
            "Player": name,
            "Total Score": (stats["total_score"] / max_total_score) * 100 if max_total_score > 0 else 0,
            "Win Rate": stats["win_rate"],
            "Podium Rate": stats["podium_rate"],
            "Ranking Consistency": 100 - ((stats["avg_rank"] - min_avg_rank) / (max_avg_rank - min_avg_rank)) * 100 if max_avg_rank > min_avg_rank else 100,
            "Games Played": (stats["games_played"] / total_games) * 100 if total_games > 0 else 0
        })
    
    # Head-to-head matrix preparation
    h2h_matrix = _calculate_head_to_head_matrix(scores_df, list(player_stats.keys()))
    
    return {
        "cumulative_data": cumulative_data,
        "wins_data": wins_data,
        "ranking_data": ranking_data,
        "radar_data": radar_data,
        "h2h_matrix": h2h_matrix
    }


def _calculate_head_to_head_matrix(scores_df: pd.DataFrame, players: List[str]) -> pd.DataFrame:
    """Calculate head-to-head win-loss differential matrix efficiently."""
    
    h2h_matrix = pd.DataFrame(0, index=players, columns=players)
    
    # Group by game for efficient processing
    game_groups = scores_df.groupby("game_id")
    
    for game_id, game_scores in game_groups:
        if len(game_scores) > 1:
            # Get all players and their ranks for this game
            game_players = game_scores[["player_name", "game_rank"]].values
            
            # Compare each pair of players
            for i, (player1, rank1) in enumerate(game_players):
                for j, (player2, rank2) in enumerate(game_players):
                    if (i != j and player1 in h2h_matrix.index and player2 in h2h_matrix.columns):
                        if rank1 < rank2:  # Player1 beat Player2 (lower rank = better)
                            h2h_matrix.loc[player1, player2] += 1
                        elif rank1 > rank2:  # Player1 lost to Player2
                            h2h_matrix.loc[player1, player2] -= 1
                        # If ranks are equal (tie), no change to differential
    
    return h2h_matrix


@st.cache_data(ttl=300, show_spinner=False)  
def get_active_players_with_colors() -> Tuple[List[str], Dict[str, str]]:
    """
    Get active players and assign consistent pastel colors (avoiding green tones).
    Returns tuple of (player_names, color_mapping)
    """
    conn = st.connection("mysql", type="sql")
    
    try:
        query = """
        SELECT name 
        FROM datalings_players 
        WHERE is_active = 1 
        ORDER BY name
        """
        
        players_df = conn.query(query, ttl=300)
        
        if players_df.empty:
            return [], {}
        
        player_names = players_df["name"].tolist()
        
        # Define 4+ pastel colors (avoiding green tones)
        pastel_colors = [
            "#FFB3BA",  # Light pink
            "#FFDFBA",  # Light peach  
            "#FFFFBA",  # Light yellow
            "#BAE1FF",  # Light blue
            "#DCC5FF",  # Light purple
            "#FFD1DC",  # Light rose
            "#F0E6FF",  # Light lavender
            "#FFE5CC"   # Light apricot
        ]
        
        # Create consistent color mapping
        color_mapping = {}
        for i, player in enumerate(player_names):
            color_mapping[player] = pastel_colors[i % len(pastel_colors)]
        
        return player_names, color_mapping
        
    except Exception as e:
        logger.error(f"Error in get_active_players_with_colors: {e}")
        return [], {}


@st.cache_data(ttl=600, show_spinner=False)
def get_detailed_stats_table_data(player_stats: Dict) -> pd.DataFrame:
    """
    Create detailed statistics table data optimized for display.
    """
    detailed_stats = []
    
    for name, stats in player_stats.items():
        detailed_stats.append({
            "Player": name,
            "Games": stats["games_played"],
            "Total Score": stats["total_score"],
            "Avg Score": f"{stats['avg_score']:.1f}",
            "Wins": stats["wins"],
            "Win Rate": f"{stats['win_rate']:.1f}%",
            "Podium": stats["podium_finishes"],
            "Ranking Points": stats["total_ranking_points"],
            "Avg Rank": f"{stats['avg_rank']:.1f}",
            "Best Score": stats["best_score"],
            "Consistency": f"{stats['score_consistency']:.1f}"
        })
    
    detailed_df = pd.DataFrame(detailed_stats)
    return detailed_df.sort_values("Ranking Points", ascending=False)


def clear_dashboard_cache():
    """Clear all dashboard-related caches."""
    get_dashboard_data_optimized.clear()
    get_active_players_with_colors.clear()
    get_detailed_stats_table_data.clear()