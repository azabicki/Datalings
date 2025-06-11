import streamlit as st
import functions.utils as ut
import functions.auth as auth
import functions.database as db
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import calendar
from scipy import stats
import plotly.figure_factory as ff

st.set_page_config(page_title="Statistics", layout=ut.app_layout)

# auth
auth.login()

# init
ut.default_style()
ut.create_sidebar()

# Custom CSS for better styling
st.markdown(
    """
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        margin: 0.5rem 0;
        text-align: center;
    }
    .stat-card {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: #333;
        margin: 0.5rem 0;
        text-align: center;
    }
    .highlight-card {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: #333;
        margin: 0.5rem 0;
        text-align: center;
    }
    .record-card {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: #333;
        margin: 0.5rem 0;
        text-align: center;
    }
    .superhost-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 0.75rem;
        color: white;
        margin: 1rem 0;
        text-align: center;
        border: 3px solid #ffd700;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .player-record-card {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: #333;
        margin: 0.5rem 0;
        text-align: center;
    }
</style>
""",
    unsafe_allow_html=True,
)

def get_all_game_scores():
    """Get all game scores with game details"""
    games_df = db.get_all_games()
    if games_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    all_game_data = []
    game_stats = []

    for _, game_row in games_df.iterrows():
        game_id = int(game_row["id"])
        game_date = game_row["game_date"]
        game_details = db.get_game_details(game_id)

        # Game-level stats
        scores = game_details.get("scores", [])
        if scores:
            game_scores = [score["score"] for score in scores]
            game_duration = None
            game_ages = []

            # Extract duration and ages from settings
            for setting in game_details.get("settings", []):
                setting_name_lower = setting["setting_name"].lower()
                if "duration" in setting_name_lower or "time" in setting_name_lower:
                    try:
                        game_duration = float(setting["value"])
                    except:
                        pass
                elif "age" in setting_name_lower:
                    try:
                        age_val = float(setting["value"])
                        game_ages.append(age_val)
                    except:
                        pass

            avg_age = np.mean(game_ages) if game_ages else None
            total_ages = len(game_ages)

            game_stats.append({
                "game_id": game_id,
                "game_date": game_date,
                "player_count": len(scores),
                "total_score": sum(game_scores),
                "avg_score": np.mean(game_scores),
                "min_score": min(game_scores),
                "max_score": max(game_scores),
                "score_range": max(game_scores) - min(game_scores),
                "duration": game_duration,
                "avg_age": avg_age,
                "total_ages": total_ages
            })

            # Individual score data
            for score_data in scores:
                all_game_data.append({
                    "game_id": game_id,
                    "game_date": game_date,
                    "player_id": score_data["player_id"],
                    "player_name": score_data["player_name"],
                    "score": score_data["score"],
                    "duration": game_duration,
                    "avg_age": avg_age,
                    "total_ages": total_ages
                })

    return pd.DataFrame(all_game_data), pd.DataFrame(game_stats)

def find_record_holders(scores_df):
    """Find players with highest and lowest scores"""
    if scores_df.empty:
        return None, None, None, None
    
    max_score_idx = scores_df["score"].idxmax()
    min_score_idx = scores_df["score"].idxmin()
    
    highest_scorer = scores_df.loc[max_score_idx, "player_name"]
    highest_score = scores_df.loc[max_score_idx, "score"]
    
    lowest_scorer = scores_df.loc[min_score_idx, "player_name"]
    lowest_score = scores_df.loc[min_score_idx, "score"]
    
    return highest_scorer, highest_score, lowest_scorer, lowest_score

def find_superhost(scores_df):
    """Find the player who appears in the most games (Superhost)"""
    if scores_df.empty:
        return None, 0
    
    player_game_counts = scores_df.groupby("player_name")["game_id"].nunique().sort_values(ascending=False)
    if len(player_game_counts) > 0:
        superhost = player_game_counts.index[0]
        game_count = player_game_counts.iloc[0]
        return superhost, game_count
    
    return None, 0

def calculate_game_statistics(scores_df, games_df):
    """Calculate comprehensive game statistics"""
    if scores_df.empty or games_df.empty:
        return {}

    # Basic game statistics
    total_games = len(games_df)
    total_players_sessions = len(scores_df)
    unique_players = scores_df["player_name"].nunique()

    # Score statistics
    all_scores = scores_df["score"].values
    avg_score = np.mean(all_scores)
    median_score = np.median(all_scores)
    min_score = np.min(all_scores)
    max_score = np.max(all_scores)
    score_std = np.std(all_scores)

    # Game size statistics
    avg_players_per_game = games_df["player_count"].mean()
    min_players_per_game = games_df["player_count"].min()
    max_players_per_game = games_df["player_count"].max()

    # Duration statistics
    duration_data = games_df.dropna(subset=["duration"])
    timed_games_count = len(duration_data)
    if not duration_data.empty:
        avg_duration = duration_data["duration"].mean()
        min_duration = duration_data["duration"].min()
        max_duration = duration_data["duration"].max()
        total_duration = duration_data["duration"].sum()
    else:
        avg_duration = min_duration = max_duration = total_duration = None

    # Age statistics (ages played during games)
    age_data = games_df.dropna(subset=["avg_age"])
    if not age_data.empty:
        avg_age_played = age_data["avg_age"].mean()
        min_age_played = age_data["avg_age"].min()
        max_age_played = age_data["avg_age"].max()
        total_ages_played = games_df["total_ages"].sum()
    else:
        avg_age_played = min_age_played = max_age_played = total_ages_played = None

    # Temporal statistics
    games_df["game_date"] = pd.to_datetime(games_df["game_date"])
    if not games_df.empty:
        first_game = games_df["game_date"].min()
        last_game = games_df["game_date"].max()
        days_playing = (last_game - first_game).days + 1
        games_per_day = total_games / max(days_playing, 1)
    else:
        first_game = last_game = None
        days_playing = games_per_day = 0

    # Player participation stats
    player_participation = scores_df.groupby("player_name").agg({
        "game_id": "nunique",
        "score": ["mean", "std"]
    }).round(2)
    
    most_active_player = player_participation["game_id"]["nunique"].idxmax() if not player_participation.empty else None
    most_active_count = player_participation["game_id"]["nunique"].max() if not player_participation.empty else 0

    return {
        "total_games": total_games,
        "total_players_sessions": total_players_sessions,
        "unique_players": unique_players,
        "avg_score": avg_score,
        "median_score": median_score,
        "min_score": min_score,
        "max_score": max_score,
        "score_std": score_std,
        "score_range": max_score - min_score,
        "avg_players_per_game": avg_players_per_game,
        "min_players_per_game": min_players_per_game,
        "max_players_per_game": max_players_per_game,
        "avg_duration": avg_duration,
        "min_duration": min_duration,
        "max_duration": max_duration,
        "total_duration": total_duration,
        "timed_games_count": timed_games_count,
        "avg_age_played": avg_age_played,
        "min_age_played": min_age_played,
        "max_age_played": max_age_played,
        "total_ages_played": total_ages_played,
        "first_game": first_game,
        "last_game": last_game,
        "days_playing": days_playing,
        "games_per_day": games_per_day,
        "most_active_player": most_active_player,
        "most_active_count": most_active_count
    }

def create_score_distribution_chart_with_kde(scores_df):
    """Create score distribution histogram with KDE overlay"""
    if scores_df.empty:
        return None

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add histogram
    fig.add_trace(
        go.Histogram(
            x=scores_df["score"],
            nbinsx=20,
            name="Score Frequency",
            marker_color="rgba(102, 126, 234, 0.7)",
            yaxis="y"
        ),
        secondary_y=False,
    )
    
    # Add KDE
    try:
        kde = stats.gaussian_kde(scores_df["score"])
        x_range = np.linspace(scores_df["score"].min(), scores_df["score"].max(), 100)
        kde_values = kde(x_range)
        
        fig.add_trace(
            go.Scatter(
                x=x_range,
                y=kde_values,
                mode="lines",
                name="Density",
                line=dict(color="red", width=3),
                yaxis="y2"
            ),
            secondary_y=True,
        )
    except:
        pass  # Skip KDE if it fails
    
    # Update layout
    fig.update_layout(
        title="Score Distribution with Density Curve",
        height=400,
        title_font_size=16,
        showlegend=True
    )
    
    fig.update_xaxes(title_text="Score", title_font_size=14)
    fig.update_yaxes(title_text="Frequency", secondary_y=False, title_font_size=14)
    fig.update_yaxes(title_text="Density", secondary_y=True, title_font_size=14)
    
    return fig

def create_games_over_time_chart(games_df):
    """Create games played over time chart"""
    if games_df.empty:
        return None

    games_df["game_date"] = pd.to_datetime(games_df["game_date"])
    games_df = games_df.sort_values("game_date")

    # Group by month
    games_df["month"] = games_df["game_date"].dt.to_period("M")
    monthly_games = games_df.groupby("month").size().reset_index(name="games_count")
    monthly_games["month"] = monthly_games["month"].astype(str)

    fig = px.line(
        monthly_games,
        x="month",
        y="games_count",
        title="Games Played Over Time",
        labels={"month": "Month", "games_count": "Number of Games"},
        markers=True,
        color_discrete_sequence=["#764ba2"]
    )

    fig.update_layout(
        height=400,
        title_font_size=16,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14,
        xaxis_tickangle=45
    )
    
    return fig

def create_player_count_distribution(games_df):
    """Create player count distribution chart"""
    if games_df.empty:
        return None
    
    player_count_dist = games_df["player_count"].value_counts().sort_index()
    
    fig = px.bar(
        x=player_count_dist.index,
        y=player_count_dist.values,
        title="Distribution of Player Count per Game",
        labels={"x": "Number of Players", "y": "Number of Games"},
        color_discrete_sequence=["#f093fb"]
    )
    
    fig.update_layout(
        height=400,
        title_font_size=16,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14,
        showlegend=False
    )
    
    return fig

def create_duration_vs_scores_chart(games_df):
    """Create duration vs average score scatter plot"""
    duration_data = games_df.dropna(subset=["duration"])
    if duration_data.empty:
        return None
    
    fig = px.scatter(
        duration_data,
        x="duration",
        y="avg_score",
        size="player_count",
        title="Game Duration vs Average Score",
        labels={"duration": "Duration (minutes)", "avg_score": "Average Score", "player_count": "Players"},
        color="player_count",
        color_continuous_scale="viridis",
        hover_data=["game_date"]
    )
    
    fig.update_layout(
        height=400,
        title_font_size=16,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14
    )
    
    return fig

def create_ages_vs_scores_chart(games_df):
    """Create ages played vs average score scatter plot"""
    age_data = games_df.dropna(subset=["avg_age"])
    if age_data.empty:
        return None
    
    fig = px.scatter(
        age_data,
        x="avg_age",
        y="avg_score",
        size="player_count",
        title="Ages Played vs Average Score",
        labels={"avg_age": "Average Age Played", "avg_score": "Average Score", "player_count": "Players"},
        color="total_ages",
        color_continuous_scale="plasma",
        hover_data=["game_date", "total_ages"]
    )
    
    fig.update_layout(
        height=400,
        title_font_size=16,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14
    )
    
    return fig

def create_score_progression_chart(scores_df):
    """Create score progression over time"""
    if scores_df.empty:
        return None
    
    scores_df["game_date"] = pd.to_datetime(scores_df["game_date"])
    scores_df = scores_df.sort_values("game_date")
    
    # Calculate rolling average
    scores_df["rolling_avg"] = scores_df["score"].rolling(window=5, min_periods=1).mean()
    
    fig = px.scatter(
        scores_df,
        x="game_date",
        y="score",
        title="Score Progression Over Time",
        labels={"game_date": "Date", "score": "Score"},
        opacity=0.6,
        color_discrete_sequence=["#667eea"]
    )
    
    # Add rolling average line
    fig.add_trace(
        go.Scatter(
            x=scores_df["game_date"],
            y=scores_df["rolling_avg"],
            mode="lines",
            name="5-Game Moving Average",
            line=dict(color="red", width=3)
        )
    )
    
    fig.update_layout(
        height=400,
        title_font_size=16,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14
    )
    
    return fig

def create_day_of_week_chart(games_df):
    """Create day of week gaming pattern chart"""
    if games_df.empty:
        return None
    
    games_df["game_date"] = pd.to_datetime(games_df["game_date"])
    games_df["day_of_week"] = games_df["game_date"].dt.day_name()
    
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_counts = games_df["day_of_week"].value_counts().reindex(day_order, fill_value=0)
    
    fig = px.bar(
        x=day_counts.index,
        y=day_counts.values,
        title="Games Played by Day of Week",
        labels={"x": "Day of Week", "y": "Number of Games"},
        color_discrete_sequence=["#84fab0"]
    )
    
    fig.update_layout(
        height=400,
        title_font_size=16,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14,
        showlegend=False
    )
    
    return fig

def create_score_consistency_chart(scores_df):
    """Create score consistency chart by player"""
    if scores_df.empty:
        return None
    
    player_stats = scores_df.groupby("player_name").agg({
        "score": ["mean", "std", "count"]
    }).round(2)
    
    player_stats.columns = ["avg_score", "score_std", "game_count"]
    player_stats = player_stats[player_stats["game_count"] >= 3]  # Only players with 3+ games
    
    if player_stats.empty:
        return None
    
    fig = px.scatter(
        player_stats.reset_index(),
        x="avg_score",
        y="score_std",
        size="game_count",
        title="Score Consistency by Player (Lower std = More Consistent)",
        labels={"avg_score": "Average Score", "score_std": "Score Standard Deviation", "game_count": "Games Played"},
        text="player_name",
        color_discrete_sequence=["#f5576c"]
    )
    
    fig.update_traces(textposition="top center")
    
    fig.update_layout(
        height=500,
        title_font_size=16,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14
    )
    
    return fig

# Main app
st.header("🎮 Game Statistics")

# Load data
scores_df, games_df = get_all_game_scores()

if scores_df.empty:
    st.warning("No game data available yet. Play some games to see statistics!")
    st.stop()

# Calculate statistics
stats = calculate_game_statistics(scores_df, games_df)

# Find record holders and superhost
highest_scorer, highest_score, lowest_scorer, lowest_score = find_record_holders(scores_df)
superhost, superhost_games = find_superhost(scores_df)

# Overview section
st.subheader("📊 Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <h3 style="margin: 0; font-size: 2rem;">{stats['total_games']}</h3>
            <p style="margin: 0;">Total Games</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <h3 style="margin: 0; font-size: 2rem;">{stats['unique_players']}</h3>
            <p style="margin: 0;">Unique Players</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <h3 style="margin: 0; font-size: 2rem;">{stats['total_players_sessions']}</h3>
            <p style="margin: 0;">Player Sessions</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    if stats['days_playing'] > 0:
        st.markdown(
            f"""
            <div class="metric-card">
                <h3 style="margin: 0; font-size: 2rem;">{stats['games_per_day']:.1f}</h3>
                <p style="margin: 0;">Games per Day</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Superhost section
if superhost:
    st.subheader("👑 Superhost")
    st.markdown(
        f"""
        <div class="superhost-card">
            <h2 style="margin: 0; font-size: 2.5rem;">🏆 {superhost}</h2>
            <h3 style="margin: 0.5rem 0 0 0;">Superhost with {superhost_games} games!</h3>
            <p style="margin: 0.5rem 0 0 0;">Most active player in the community</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Score Statistics with record holders
st.subheader("🎯 Score Statistics")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"""
        <div class="stat-card">
            <h4 style="margin: 0;">Average Score</h4>
            <h3 style="margin: 0; font-size: 1.5rem;">{stats['avg_score']:.1f}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        f"""
        <div class="stat-card">
            <h4 style="margin: 0;">Median Score</h4>
            <h3 style="margin: 0; font-size: 1.5rem;">{stats['median_score']:.1f}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    if highest_scorer:
        st.markdown(
            f"""
            <div class="player-record-card">
                <h4 style="margin: 0;">🥇 Highest Score</h4>
                <h3 style="margin: 0; font-size: 1.5rem;">{highest_score}</h3>
                <p style="margin: 0; font-size: 0.9rem;"><strong>{highest_scorer}</strong></p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    if lowest_scorer:
        st.markdown(
            f"""
            <div class="player-record-card">
                <h4 style="margin: 0;">📉 Lowest Score</h4>
                <h3 style="margin: 0; font-size: 1.5rem;">{lowest_score}</h3>
                <p style="margin: 0; font-size: 0.9rem;"><strong>{lowest_scorer}</strong></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

with col3:
    st.markdown(
        f"""
        <div class="record-card">
            <h4 style="margin: 0;">Score Range</h4>
            <h3 style="margin: 0; font-size: 1.5rem;">{stats['score_range']}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        f"""
        <div class="record-card">
            <h4 style="margin: 0;">Score Std Dev</h4>
            <h3 style="margin: 0; font-size: 1.5rem;">{stats['score_std']:.1f}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Game Statistics
st.subheader("🎲 Game Statistics")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"""
        <div class="stat-card">
            <h4 style="margin: 0;">Avg Players per Game</h4>
            <h3 style="margin: 0; font-size: 1.5rem;">{stats['avg_players_per_game']:.1f}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class="stat-card">
            <h4 style="margin: 0;">Min Players</h4>
            <h3 style="margin: 0; font-size: 1.5rem;">{stats['min_players_per_game']}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="stat-card">
            <h4 style="margin: 0;">Max Players</h4>
            <h3 style="margin: 0; font-size: 1.5rem;">{stats['max_players_per_game']}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Duration Statistics (if available)
if stats['avg_duration'] is not None:
    st.subheader("⏱️ Duration Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""
            <div class="stat-card">
                <h4 style="margin: 0;">Avg Duration</h4>
                <h3 style="margin: 0; font-size: 1.5rem;">{stats['avg_duration']:.0f} min</h3>
                <p style="margin: 0; font-size: 0.8rem;">({stats['timed_games_count']} timed games)</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col2:
        st.markdown(
            f"""
            <div class="highlight-card">
                <h4 style="margin: 0;">Shortest Game</h4>
                <h3 style="margin: 0; font-size: 1.5rem;">{stats['min_duration']:.0f} min</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col3:
        st.markdown(
            f"""
            <div class="highlight-card">
                <h4 style="margin: 0;">Longest Game</h4>
                <h3 style="margin: 0; font-size: 1.5rem;">{stats['max_duration']:.0f} min</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col4:
        st.markdown(
            f"""
            <div class="record-card">
                <h4 style="margin: 0;">Total Time Played</h4>
                <h3 style="margin: 0; font-size: 1.5rem;">{stats['total_duration']:.0f} min</h3>
                <p style="margin: 0; font-size: 0.8rem;">({stats['total_duration']/60:.1f} hours)</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Ages Statistics (ages played during games)
if stats['avg_age_played'] is not None:
    st.subheader("🎯 Ages Played Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""
            <div class="stat-card">
                <h4 style="margin: 0;">Avg Age Played</h4>
                <h3 style="margin: 0; font-size: 1.5rem;">{stats['avg_age_played']:.1f}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col2:
        st.markdown(
            f"""
            <div class="stat-card">
                <h4 style="margin: 0;">Youngest Age</h4>
                <h3 style="margin: 0; font-size: 1.5rem;">{stats['min_age_played']:.0f}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col3:
        st.markdown(
            f"""
            <div class="stat-card">
                <h4 style="margin: 0;">Oldest Age</h4>
                <h3 style="margin: 0; font-size: 1.5rem;">{stats['max_age_played']:.0f}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col4:
        st.markdown(
            f"""
            <div class="record-card">
                <h4 style="margin: 0;">Total Ages Played</h4>
                <h3 style="margin: 0; font-size: 1.5rem;">{stats['total_ages_played']}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Temporal Statistics
if stats['first_game'] is not None:
    st.subheader("📅 Temporal Statistics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(
            f"""
            <div class="stat-card">
                <h4 style="margin: 0;">First Game</h4>
                <h3 style="margin: 0; font-size: 1.2rem;">{stats['first_game'].strftime('%Y-%m-%d')}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col2:
        st.markdown(
            f"""
            <div class="stat-card">
                <h4 style="margin: 0;">Latest Game</h4>
                <h3 style="margin: 0; font-size: 1.2rem;">{stats['last_game'].strftime('%Y-%m-%d')}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col3:
        st.markdown(
            f"""
            <div class="stat-card">
                <h4 style="margin: 0;">Days Playing</h4>
                <h3 style="margin: 0; font-size: 1.5rem;">{stats['days_playing']}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Charts section
st.subheader("📈 Charts & Visualizations")

# Score distribution with KDE
score_dist_chart = create_score_distribution_chart_with_kde(scores_df)
if score_dist_chart:
    st.plotly_chart(score_dist_chart, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    # Games over time
    games_time_chart = create_games_over_time_chart(games_df)
    if games_time_chart:
        st.plotly_chart(games_time_chart, use_container_width=True)

with col2:
    # Player count distribution
    player_count_chart = create_player_count_distribution(games_df)
    if player_count_chart:
        st.plotly_chart(player_count_chart, use_container_width=True)

# Score progression over time
score_progression_chart = create_score_progression_chart(scores_df)
if score_progression_chart:
    st.plotly_chart(score_progression_chart, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    # Duration vs scores (if duration data is available)
    if stats['avg_duration'] is not None:
        duration_scores_chart = create_duration_vs_scores_chart(games_df)
        if duration_scores_chart:
            st.plotly_chart(duration_scores_chart, use_container_width=True)

with col2:
    # Ages vs scores (if age data is available)
    if stats['avg_age_played'] is not None:
        ages_scores_chart = create_ages_vs_scores_chart(games_df)
        if ages_scores_chart:
            st.plotly_chart(ages_scores_chart, use_container_width=True)

# Day of week pattern
dow_chart = create_day_of_week_chart(games_df)
if dow_chart:
    st.plotly_chart(dow_chart, use_container_width=True)

# Score consistency chart
consistency_chart = create_score_consistency_chart(scores_df)
if consistency_chart:
    st.plotly_chart(consistency_chart, use_container_width=True)

# Fun facts section
st.subheader("🎉 Fun Facts & Insights")

fun_facts = []

if stats['total_games'] > 0:
    fun_facts.append(f"🎮 You've played a total of {stats['total_games']} games!")

if stats['total_duration'] is not None:
    hours = stats['total_duration'] / 60
    if hours > 24:
        days = hours / 24
        fun_facts.append(f"⏰ Total gaming time: {hours:.1f} hours ({days:.1f} days)!")
    else:
        fun_facts.append(f"⏰ Total gaming time: {hours:.1f} hours!")

if stats['score_range'] > 0:
    fun_facts.append(f"📊 Score spread: {stats['score_range']} points between highest and lowest!")

if stats['max_players_per_game'] > stats['min_players_per_game']:
    fun_facts.append(f"👥 Player range: {stats['min_players_per_game']} to {stats['max_players_per_game']} players per game!")

if stats['games_per_day'] >= 1:
    fun_facts.append(f"🔥 You're playing {stats['games_per_day']:.1f} games per day on average!")

if highest_scorer and lowest_scorer:
    if highest_scorer == lowest_scorer:
        fun_facts.append(f"🎯 {highest_scorer} holds both the highest AND lowest score records!")
    else:
        fun_facts.append(f"🏆 Record holders: {highest_scorer} (highest) and {lowest_scorer} (lowest)")

if superhost and stats['most_active_player']:
    if superhost == stats['most_active_player']:
        fun_facts.append(f"👑 {superhost} is both the Superhost and most active player!")

if stats['total_ages_played'] and stats['total_ages_played'] > stats['total_games']:
    avg_ages_per_game = stats['total_ages_played'] / stats['total_games']
    fun_facts.append(f"🎯 Average of {avg_ages_per_game:.1f} different ages played per game!")

# Gaming frequency insights
if stats['days_playing'] > 0:
    if stats['games_per_day'] > 2:
        fun_facts.append("🚀 High-frequency gamers - more than 2 games per day!")
    elif stats['games_per_day'] > 1:
        fun_facts.append("🎲 Regular gamers - more than 1 game per day!")
    elif stats['games_per_day'] > 0.5:
        fun_facts.append("📅 Consistent gamers - playing every other day!")

# Score distribution insights
if stats['score_std'] > 0:
    cv = stats['score_std'] / stats['avg_score'] * 100  # Coefficient of variation
    if cv > 50:
        fun_facts.append("📈 High score variability - games have very different scoring patterns!")
    elif cv < 20:
        fun_facts.append("📊 Consistent scoring - games tend to have similar score ranges!")

# Display fun facts
for fact in fun_facts:
    st.info(fact)

if not fun_facts:
    st.info("🎲 Play more games to unlock fun facts!")

# Additional insights section
if len(scores_df) > 10:  # Only show if we have enough data
    st.subheader("🔍 Additional Insights")
    
    # Recent trends
    recent_games = scores_df.tail(5)
    if len(recent_games) >= 3:
        recent_avg = recent_games['score'].mean()
        overall_avg = scores_df['score'].mean()
        
        if recent_avg > overall_avg * 1.1:
            st.success("📈 Scores are trending upward in recent games!")
        elif recent_avg < overall_avg * 0.9:
            st.warning("📉 Scores have been lower in recent games.")
        else:
            st.info("📊 Recent scores are consistent with overall average.")
    
    # Player diversity
    unique_players_ratio = stats['unique_players'] / stats['total_games']
    if unique_players_ratio > 0.8:
        st.info("👥 High player diversity - many different players across games!")
    elif unique_players_ratio < 0.3:
        st.info("👥 Core gaming group - same players tend to play together!")