import streamlit as st
import functions.utils as ut
import functions.auth as auth
import functions.database as db
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import altair as alt

st.set_page_config(page_title="Datalings Dashboard", layout=ut.app_layout)

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
    }
    .winner-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        margin: 0.5rem 0;
        text-align: center;
    }
    .stMetric > label {
        font-size: 1.2rem !important;
        font-weight: bold !important;
    }
    .chart-style-selector {
        background-color: #f0f2f6;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def get_game_scores_with_rankings():
    """Get all game scores with rankings calculated"""
    games_df = db.get_all_games()
    if games_df.empty:
        return pd.DataFrame()

    all_game_data = []

    for _, game_row in games_df.iterrows():
        game_id = int(game_row["id"])
        game_date = game_row["game_date"]
        game_details = db.get_game_details(game_id)

        if game_details["scores"]:
            # Sort by score descending to get rankings
            scores = sorted(
                game_details["scores"], key=lambda x: x["score"], reverse=True
            )

            # Calculate proper ranks with ties
            current_rank = 1
            prev_score = None

            for i, score_data in enumerate(scores):
                # If score is different from previous, update rank to current position + 1
                if prev_score is not None and score_data["score"] != prev_score:
                    current_rank = i + 1

                all_game_data.append(
                    {
                        "game_id": game_id,
                        "game_date": game_date,
                        "player_id": score_data["player_id"],
                        "player_name": score_data["player_name"],
                        "score": score_data["score"],
                        "rank": current_rank,
                    }
                )

                prev_score = score_data["score"]

    return pd.DataFrame(all_game_data)


def calculate_ranking_points(rank, total_players):
    """Calculate points based on ranking system: 1st=7, 2nd=4, 3rd=2, 4th+=1 (handles ties)"""
    if rank == 1:
        return 7
    elif rank == 2:
        return 4
    elif rank == 3:
        return 2
    else:
        return 1


def calculate_comprehensive_stats():
    """Calculate all scoring statistics"""
    scores_df = get_game_scores_with_rankings()
    if scores_df.empty:
        return None

    # Group by player for comprehensive stats
    player_stats = {}

    # Get total games played
    total_games = scores_df["game_id"].nunique()

    for player_name in scores_df["player_name"].unique():
        player_data = scores_df[scores_df["player_name"] == player_name]

        # Basic stats
        games_played = len(player_data)
        total_score = player_data["score"].sum()
        avg_score = player_data["score"].mean()

        # Win statistics (rank 1 = win, even with ties)
        wins = len(player_data[player_data["rank"] == 1])
        podium_finishes = len(player_data[player_data["rank"] <= 3])

        # Ranking points
        player_data["ranking_points"] = player_data.apply(
            lambda row: calculate_ranking_points(
                row["rank"], len(scores_df[scores_df["game_id"] == row["game_id"]])
            ),
            axis=1,
        )
        total_ranking_points = player_data["ranking_points"].sum()

        # Performance metrics
        best_score = player_data["score"].max()
        worst_score = player_data["score"].min()
        best_rank = player_data["rank"].min()
        worst_rank = player_data["rank"].max()
        avg_rank = player_data["rank"].mean()

        # Consistency (lower is better)
        score_std = player_data["score"].std() if games_played > 1 else 0

        player_stats[player_name] = {
            "games_played": games_played,
            "total_score": total_score,
            "avg_score": avg_score,
            "wins": wins,
            "podium_finishes": podium_finishes,
            "win_rate": wins / games_played * 100,
            "podium_rate": podium_finishes / games_played * 100,
            "total_ranking_points": total_ranking_points,
            "avg_ranking_points": total_ranking_points / games_played,
            "best_score": best_score,
            "worst_score": worst_score,
            "best_rank": best_rank,
            "worst_rank": worst_rank,
            "avg_rank": avg_rank,
            "score_consistency": score_std,
            "games_data": player_data,
        }

    # Get all games to calculate age statistics
    games_df = db.get_all_games()
    total_age = 0
    age_games = 0

    # Calculate age statistics from game settings
    for _, game in games_df.iterrows():
        game_id = int(game["id"])
        game_details = db.get_game_details(game_id)

        if game_details and game_details.get("settings"):
            for setting_info in game_details["settings"]:
                setting_name_lower = setting_info["setting_name"].lower()
                if "age" in setting_name_lower:
                    age_games += 1
                    age_value = int(float(setting_info["value"]))
                    total_age += age_value

    return player_stats, scores_df, total_games, total_age, age_games


# 1 Chart creation functions ##########################################
def create_cumulative_chart(cumulative_df):
    """Create cumulative score chart with Plotly"""
    fig = px.line(
        cumulative_df,
        x="Game",
        y="Cumulative Score",
        color="Player",
        title="Cumulative Score Development (Interactive)",
        markers=True,
        hover_data=["Game Date"],
    )

    fig.update_layout(
        height=500,
        xaxis_title="Game Number",
        yaxis_title="Cumulative Score",
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        font=dict(color="black"),
        xaxis=dict(dtick=1),
        modebar=dict(
            remove=[
                "pan2d",
                "select2d",
                "lasso2d",
                "zoom2d",
                "zoomIn2d",
                "zoomOut2d",
                "autoScale2d",
                "resetScale2d",
            ]
        ),
    )

    fig.update_traces(
        line=dict(width=5),
        marker=dict(size=10),
        hoverlabel=dict(bgcolor="lightgrey", font_color="black"),
    )
    return fig


# 2 Chart creation functions ##########################################
def create_wins_chart(wins_df):
    """Create wins chart with Altair"""
    chart = (
        alt.Chart(wins_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "Player:N",
                title="Player",
                sort="-y",
                axis=alt.Axis(labelColor="black", titleColor="black"),
            ),
            y=alt.Y(
                "Wins:Q",
                title="Total Wins",
                axis=alt.Axis(tickMinStep=1, labelColor="black", titleColor="black"),
            ),
            color=alt.Color(
                "Player:N", scale=alt.Scale(scheme="category10"), legend=None
            ),
            tooltip=["Player:N", "Wins:Q"],
        )
        .properties(
            width=500,
            height=400,
            title=alt.TitleParams(text="Total Wins by Player (Altair)", color="black"),
        )
    )

    # Add text labels
    text = (
        alt.Chart(wins_df)
        .mark_text(
            align="center",
            baseline="bottom",
            dy=-5,
            fontSize=12,
            fontWeight="bold",
            color="black",
        )
        .encode(
            x=alt.X("Player:N", sort="-y"), y=alt.Y("Wins:Q"), text=alt.Text("Wins:Q")
        )
    )

    return (
        (chart + text)
        .configure_axis(labelColor="black", titleColor="black")
        .configure_title(color="black")
    )


# 3 Chart creation functions ##########################################
def create_ranking_chart_plotly(ranking_df):
    """Create ranking points chart with Plotly"""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Total Ranking Points", "Average Points per Game"),
        specs=[[{"secondary_y": False}, {"secondary_y": False}]],
    )

    # Total points bar chart
    fig.add_trace(
        go.Bar(
            x=ranking_df["Player"],
            y=ranking_df["Total Points"],
            name="Total Points",
            marker_color=[
                "#FF6B6B",
                "#4ECDC4",
                "#45B7D1",
                "#96CEB4",
                "#FECA57",
                "#FF9FF3",
                "#54A0FF",
                "#5F27CD",
            ][: len(ranking_df)],
            text=ranking_df["Total Points"],
            textposition="outside",
            textfont=dict(color="black"),
            hoverlabel=dict(bgcolor="lightgrey", font_color="black"),
        ),
        row=1,
        col=1,
    )

    # Average points bar chart
    fig.add_trace(
        go.Bar(
            x=ranking_df["Player"],
            y=ranking_df["Avg Points"],
            name="Avg Points",
            marker_color=[
                "#FF6B6B",
                "#4ECDC4",
                "#45B7D1",
                "#96CEB4",
                "#FECA57",
                "#FF9FF3",
                "#54A0FF",
                "#5F27CD",
            ][: len(ranking_df)],
            text=[f"{x:.1f}" for x in ranking_df["Avg Points"]],
            textposition="outside",
            textfont=dict(color="black"),
            hoverlabel=dict(bgcolor="lightgrey", font_color="black"),
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        height=450,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        title_text="Ranking Points System (Interactive)",
        font=dict(color="black"),
        modebar=dict(
            remove=[
                "pan2d",
                "select2d",
                "lasso2d",
                "zoom2d",
                "zoomIn2d",
                "zoomOut2d",
                "autoScale2d",
                "resetScale2d",
            ]
        ),
    )

    fig.update_yaxes(dtick=1, row=1, col=1)

    return fig


# 4 Chart creation functions ##########################################
def create_performance_radar_plotly(metrics_for_radar):
    """Create performance radar chart with Plotly"""
    fig = go.Figure()

    categories = [
        "Total Score",
        "Win Rate",
        "Podium Rate",
        "Ranking Consistency",
        "Games Played",
    ]

    for player_data in metrics_for_radar:
        values = [player_data[cat] for cat in categories]
        values += [values[0]]  # Close the radar chart

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill="toself",
                name=player_data["Player"],
                line=dict(width=5),
                opacity=0.7,
                hoverlabel=dict(bgcolor="lightgrey", font_color="black"),
            )
        )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
            angularaxis=dict(color="black"),
        ),
        height=600,
        title="Multi-Dimensional Performance Radar (Interactive)",
        font=dict(color="black"),
        modebar=dict(
            remove=[
                "pan2d",
                "select2d",
                "lasso2d",
                "zoom2d",
                "zoomIn2d",
                "zoomOut2d",
                "autoScale2d",
                "resetScale2d",
            ]
        ),
    )

    return fig


def create_performance_radar_streamlit(metrics_for_radar):
    """Create performance metrics with Streamlit native"""
    st.subheader("Multi-Dimensional Performance (Area Chart)")

    # Create a DataFrame for easier visualization
    categories = [
        "Total Score",
        "Win Rate",
        "Podium Rate",
        "Ranking Consistency",
        "Games Played",
    ]

    radar_df = pd.DataFrame(metrics_for_radar)

    # Prepare data for area chart - transpose so players are columns and categories are index
    area_chart_data = radar_df.set_index("Player")[categories].T

    # Create area chart with transparency using RGBA colors
    # Generate RGBA colors with alpha=0.6 for transparency
    num_players = len(area_chart_data.columns)
    colors = [
        (255, 99, 132, 0.8),  # Red with alpha
        (54, 162, 235, 0.8),  # Blue with alpha
        (255, 205, 86, 0.8),  # Yellow with alpha
        (75, 192, 192, 0.8),  # Teal with alpha
        (153, 102, 255, 0.8),  # Purple with alpha
        (255, 159, 64, 0.8),  # Orange with alpha
        (199, 199, 199, 0.8),  # Grey with alpha
        (83, 102, 255, 0.8),  # Indigo with alpha
    ]

    # Use only as many colors as needed
    chart_colors = colors[:num_players]

    st.area_chart(area_chart_data, height=400, color=chart_colors, stack="normalize")

    # Add a summary table below for exact values
    st.markdown("**📋 Exact Values**")
    radar_display = radar_df[["Player"] + categories]
    st.dataframe(
        radar_display.style.background_gradient(subset=categories, cmap="RdYlGn"),
        use_container_width=True,
    )


def create_performance_radar_altair(metrics_for_radar):
    """Create performance radar chart with Altair (as parallel coordinates)"""
    # Convert to long format for Altair
    radar_df = pd.DataFrame(metrics_for_radar)
    categories = [
        "Total Score",
        "Win Rate",
        "Podium Rate",
        "Ranking Consistency",
        "Games Played",
    ]

    # Melt the DataFrame
    melted_df = radar_df.melt(
        id_vars=["Player"], value_vars=categories, var_name="Metric", value_name="Value"
    )

    # Create parallel coordinates chart
    chart = (
        alt.Chart(melted_df)
        .mark_line(strokeWidth=5, opacity=0.8)
        .encode(
            x=alt.X(
                "Metric:N",
                title="Performance Metrics",
                axis=alt.Axis(labelColor="black", titleColor="black"),
            ),
            y=alt.Y(
                "Value:Q",
                title="Score (0-100)",
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(labelColor="black", titleColor="black"),
            ),
            color=alt.Color(
                "Player:N",
                scale=alt.Scale(scheme="category10"),
                legend=alt.Legend(labelColor="black", titleColor="black"),
            ),
            tooltip=["Player:N", "Metric:N", "Value:Q"],
        )
        .properties(
            width=600,
            height=400,
            title=alt.TitleParams(
                text="Multi-Dimensional Performance (Parallel Coordinates)",
                color="black",
            ),
        )
        .configure_axis(labelColor="black", titleColor="black")
        .configure_title(color="black")
    )

    return chart


# 5 Chart creation functions ##########################################
def create_heatmap_plotly(h2h_matrix):
    """Create head-to-head heatmap with Plotly"""
    # Find the maximum absolute value for symmetric color scale
    max_abs_value = max(abs(h2h_matrix.values.min()), abs(h2h_matrix.values.max()))

    fig = px.imshow(
        h2h_matrix.values,
        labels=dict(x="Opponent", y="Player", color="Win Differential"),
        x=h2h_matrix.columns,
        y=h2h_matrix.index,
        color_continuous_scale="RdYlGn",
        range_color=[-max_abs_value, max_abs_value],
        title="Head-to-Head Win-Loss Differential (Interactive)",
    )

    fig.update_layout(
        height=400,
        font=dict(color="black"),
        modebar=dict(
            remove=[
                "pan2d",
                "select2d",
                "lasso2d",
                "zoom2d",
                "zoomIn2d",
                "zoomOut2d",
                "autoScale2d",
                "resetScale2d",
            ]
        ),
    )

    fig.update_coloraxes(showscale=False)
    fig.update_traces(hoverlabel=dict(bgcolor="lightgrey", font_color="black"))

    return fig


# Main app #####################################################################
st.markdown("#### _well well well.... who should be thrown under the bus..???_")
ut.h_spacer(2)
# Calculate comprehensive statistics
stats_result = calculate_comprehensive_stats()

if stats_result is None:
    st.info(
        "🎮 No games recorded yet! Start playing to see your amazing stats and charts."
    )
    st.markdown("Add some games in the **Game Results** page to see:")
    st.markdown("- 📈 Cumulative score progression")
    st.markdown("- 🏅 Win statistics and rankings")
    st.markdown("- 🎯 Performance analytics")
    st.markdown("- 📊 Beautiful interactive charts")
else:
    player_stats, scores_df, total_games, total_age, age_games = stats_result

    # 1. CUMULATIVE POINTS DEVELOPMENT CHART ###################################
    st.subheader("📈 Cumulative Score Progression")
    st.markdown("*Track how each player's total score develops over time*")

    # Prepare data for cumulative chart
    cumulative_data = []
    for player_name, stats in player_stats.items():
        player_games = stats["games_data"].sort_values("game_date")
        cumulative_score = 0

        for i, (_, game) in enumerate(player_games.iterrows(), 1):
            cumulative_score += game["score"]
            cumulative_data.append(
                {
                    "Player": player_name,
                    "Game": i,
                    "Cumulative Score": cumulative_score,
                    "Game Date": game["game_date"],
                }
            )

    if cumulative_data:
        cumulative_df = pd.DataFrame(cumulative_data)

        fig_cumulative = create_cumulative_chart(cumulative_df)
        st.plotly_chart(fig_cumulative, use_container_width=True)

    st.markdown("---")

    # 2. WIN COUNT CHART #######################################################
    st.subheader("🏅 Victory Statistics")
    st.markdown(
        "*Who's bringing home the most wins? (Ties count as wins for all tied players)*"
    )

    # Create wins data
    wins_data = [(name, stats["wins"]) for name, stats in player_stats.items()]
    wins_data.sort(key=lambda x: x[1], reverse=True)
    wins_df = pd.DataFrame(wins_data, columns=["Player", "Wins"])

    chart_wins = create_wins_chart(wins_df)
    st.altair_chart(chart_wins, use_container_width=True)

    # Additional win statistics
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🥇 Win Rates**")
        for name, stats in sorted(
            player_stats.items(), key=lambda x: x[1]["win_rate"], reverse=True
        ):
            st.write(
                f"**{name}**: {stats['win_rate']:.1f}% ({stats['wins']}/{stats['games_played']} games)"
            )

    with col2:
        st.markdown("**🏆 Podium Rates**")
        for name, stats in sorted(
            player_stats.items(), key=lambda x: x[1]["podium_rate"], reverse=True
        ):
            st.write(
                f"**{name}**: {stats['podium_rate']:.1f}% ({stats['podium_finishes']}/{stats['games_played']} games)"
            )

    st.markdown("---")

    # 3. RANKING POINTS SYSTEM #################################################
    st.subheader("🎯 Ranking Points System")
    st.markdown(
        "*Based on finishing position: 1st=7pts, 2nd=4pts, 3rd=2pts, 4th+=1pt (tied players get same rank and points)*"
    )

    # Create ranking points data
    ranking_data = [
        (name, stats["total_ranking_points"], stats["avg_ranking_points"])
        for name, stats in player_stats.items()
    ]
    ranking_data.sort(key=lambda x: x[1], reverse=True)
    ranking_df = pd.DataFrame(
        ranking_data, columns=["Player", "Total Points", "Avg Points"]
    )

    fig_ranking = create_ranking_chart_plotly(ranking_df)
    st.plotly_chart(fig_ranking, use_container_width=True)

    st.markdown("---")

    # 4. ADDITIONAL PERFORMANCE ANALYTICS ######################################
    st.subheader("📊 Advanced Performance Analytics")

    # Performance comparison radar chart
    st.markdown("**🎯 Multi-Dimensional Performance Comparison**")

    # Chart style selector
    radar_style = st.radio(
        "Select chart style:",
        ["Interactive (Plotly)", "Simple (Streamlit)", "Advanced (Altair)"],
        key="radar_style",
        horizontal=True,
    )

    # Normalize metrics for radar chart (0-100 scale)
    metrics_for_radar = []
    for name, stats in player_stats.items():
        # Normalize each metric to 0-100 scale
        max_total_score = max(s["total_score"] for s in player_stats.values())
        max_win_rate = max(s["win_rate"] for s in player_stats.values())
        max_podium_rate = max(s["podium_rate"] for s in player_stats.values())
        min_avg_rank = min(s["avg_rank"] for s in player_stats.values())
        max_avg_rank = max(s["avg_rank"] for s in player_stats.values())

        metrics_for_radar.append(
            {
                "Player": name,
                "Total Score": (stats["total_score"] / max_total_score) * 100,
                "Win Rate": stats["win_rate"],
                "Podium Rate": stats["podium_rate"],
                "Ranking Consistency": 100
                - ((stats["avg_rank"] - min_avg_rank) / (max_avg_rank - min_avg_rank))
                * 100,
                "Games Played": (stats["games_played"] / total_games) * 100,
            }
        )

    if radar_style == "Interactive (Plotly)":
        fig_radar = create_performance_radar_plotly(metrics_for_radar)
        st.plotly_chart(fig_radar, use_container_width=True)
    elif radar_style == "Simple (Streamlit)":
        create_performance_radar_streamlit(metrics_for_radar)
    else:
        chart_radar = create_performance_radar_altair(metrics_for_radar)
        st.altair_chart(chart_radar, use_container_width=True)

    # Detailed statistics table
    st.markdown("**📋 Detailed Player Statistics**")

    detailed_stats = []
    for name, stats in player_stats.items():
        detailed_stats.append(
            {
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
                "Consistency": f"{stats['score_consistency']:.1f}",
            }
        )

    detailed_df = pd.DataFrame(detailed_stats)
    detailed_df = detailed_df.sort_values("Ranking Points", ascending=False)

    st.dataframe(detailed_df, use_container_width=True, hide_index=True)

    # 5: Head-to-Head Performance Matrix #######################################
    st.markdown("---")
    st.subheader("⚔️ Head-to-Head Performance")
    st.markdown("*Win-loss differential between players (row vs column)*")

    # Create head-to-head win-loss differential matrix
    players = list(player_stats.keys())
    h2h_matrix = pd.DataFrame(0, index=players, columns=players)

    # Calculate win-loss differential for each player pair
    for game_id in scores_df["game_id"].unique():
        game_scores = (
            scores_df[scores_df["game_id"] == game_id].copy().sort_values("rank")
        )
        if len(game_scores) > 1:
            # Get all players and their ranks for this game
            game_players = game_scores[["player_name", "rank"]].values

            # Compare each pair of players
            for i, (player1, rank1) in enumerate(game_players):
                for j, (player2, rank2) in enumerate(game_players):
                    if (
                        i != j
                        and player1 in h2h_matrix.index
                        and player2 in h2h_matrix.columns
                    ):
                        if rank1 < rank2:  # Player1 beat Player2 (lower rank = better)
                            h2h_matrix.loc[player1, player2] += 1
                        elif rank1 > rank2:  # Player1 lost to Player2
                            h2h_matrix.loc[player1, player2] -= 1
                        # If ranks are equal (tie), no change to differential

    fig_h2h = create_heatmap_plotly(h2h_matrix)
    st.plotly_chart(fig_h2h, use_container_width=True)

    st.markdown(
        """*Matrix shows win-loss differential:*
- positive (green) = more wins
- zero (white) = even
- negative (red) = more losses"""
    )

st.markdown("---")
st.markdown("*Keep playing to see your stats evolve! 🚀*")
