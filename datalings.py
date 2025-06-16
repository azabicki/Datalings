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

# consistent player colors (slightly darker tones on green background)
PLAYER_COLORS = [
    "#cc8a8a",
    "#c9a275",
    "#978ecc",
    "#56c2ce",
    "#809ccc",
    "#a1cc98",
]


def assign_player_colors(players):
    """Map each player to a consistent color."""
    sorted_players = sorted(players)
    color_map = {}
    for idx, player in enumerate(sorted_players):
        color_map[player] = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
    return color_map


def darken_color(hex_color: str, factor: float = 0.85) -> str:
    """Return a darker shade of the given hex color."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = int(r * factor)
    g = int(g * factor)
    b = int(b * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


@st.cache_data(ttl=300)
def get_game_scores_with_rankings() -> pd.DataFrame:
    """Return all game scores with calculated ranks."""
    scores_df = db.get_all_scores()
    if scores_df.empty:
        return pd.DataFrame()

    # Rank scores within each game (ties share the same rank)
    scores_df["rank"] = (
        scores_df.groupby("game_id")["score"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    return scores_df


def calculate_ranking_points(rank: int) -> int:
    """Return points based on finishing rank."""
    if rank == 1:
        return 7
    elif rank == 2:
        return 4
    elif rank == 3:
        return 2
    else:
        return 1


@st.cache_data(ttl=300)
def calculate_comprehensive_stats():
    """Aggregate statistics for all players."""
    scores_df = get_game_scores_with_rankings()
    if scores_df.empty:
        return None

    total_games = scores_df["game_id"].nunique()

    player_stats = {}
    for player_name, player_data in scores_df.groupby("player_name"):
        games_played = len(player_data)
        total_score = int(player_data["score"].sum())
        avg_score = player_data["score"].mean()

        wins = (player_data["rank"] == 1).sum()
        podium_finishes = (player_data["rank"] <= 3).sum()

        total_ranking_points = player_data["rank"].map(calculate_ranking_points).sum()

        best_score = player_data["score"].max()
        worst_score = player_data["score"].min()
        best_rank = player_data["rank"].min()
        worst_rank = player_data["rank"].max()
        avg_rank = player_data["rank"].mean()
        score_std = player_data["score"].std() if games_played > 1 else 0

        player_stats[player_name] = {
            "games_played": games_played,
            "total_score": total_score,
            "avg_score": avg_score,
            "wins": wins,
            "podium_finishes": podium_finishes,
            "win_rate": wins / games_played * 100,
            "podium_rate": podium_finishes / games_played * 100,
            "total_ranking_points": int(total_ranking_points),
            "avg_ranking_points": total_ranking_points / games_played,
            "best_score": best_score,
            "worst_score": worst_score,
            "best_rank": best_rank,
            "worst_rank": worst_rank,
            "avg_rank": avg_rank,
            "score_consistency": score_std,
            "games_data": player_data,
        }

    settings_df = db.get_all_game_setting_values()
    total_age = 0
    age_games = 0
    if not settings_df.empty:
        age_settings = settings_df[
            settings_df["setting_name"].str.contains("age", case=False)
        ]
        if not age_settings.empty:
            age_games = age_settings["game_id"].nunique()
            age_values = age_settings["value_number"].fillna(age_settings["value_text"])
            total_age = (
                pd.to_numeric(age_values, errors="coerce").fillna(0).astype(int).sum()
            )

    return player_stats, scores_df, total_games, total_age, age_games


# 1 Chart creation functions ##########################################
def create_cumulative_chart(cumulative_df: pd.DataFrame, color_map: dict) -> go.Figure:
    """Create cumulative score chart with Plotly."""
    fig = px.line(
        cumulative_df,
        x="Game",
        y="Cumulative Score",
        color="Player",
        color_discrete_map=color_map,
        markers=False,
        hover_data=["Game Date"],
    )

    fig.update_layout(
        height=400,
        title="",
        xaxis_title="",
        yaxis_title="Cumulative Score",
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, title=None),
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
        hoverlabel=dict(bgcolor="lightyellow", font_size=14, font_color="black"),
    )

    fig.update_xaxes(tickprefix="Game ")
    return fig


def create_total_points_bar_chart(
    total_points_df: pd.DataFrame, color_map: dict
) -> go.Figure:
    """Create total points bar chart."""
    fig = px.bar(
        total_points_df,
        x="Player",
        y="Total Score",
        color="Player",
        color_discrete_map=color_map,
        text="Total Score",
    )

    fig.update_layout(
        height=400,
        xaxis_title="",
        yaxis_title="Total Points",
        font=dict(color="black"),
        xaxis=dict(categoryorder="total descending"),
        showlegend=False,
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
        textposition="inside",
        insidetextanchor="end",
        textfont=dict(size=14),
        hoverlabel=dict(bgcolor="lightyellow", font_size=14, font_color="black"),
    )

    return fig


# 2 Chart creation functions ##########################################
def create_wins_chart(wins_df: pd.DataFrame, color_map: dict) -> alt.Chart:
    """Create wins chart with Altair."""
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
                "Player:N",
                scale=alt.Scale(
                    domain=list(color_map.keys()), range=list(color_map.values())
                ),
                legend=None,
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


def create_wins_chart_plotly(wins_df: pd.DataFrame, color_map: dict) -> go.Figure:
    """Create wins chart with Plotly following the Altair style."""
    fig = px.bar(
        wins_df,
        x="Player",
        y="Wins",
        color="Player",
        color_discrete_map=color_map,
        text="Wins",
    )

    fig.update_layout(
        height=400,
        title="Total Wins by Player",
        xaxis_title="Player",
        yaxis_title="Total Wins",
        xaxis=dict(categoryorder="total descending"),
        showlegend=False,
        font=dict(color="black"),
    )

    fig.update_traces(
        textposition="inside",
        insidetextanchor="end",
        textfont=dict(size=12),
        hoverlabel=dict(bgcolor="lightyellow", font_size=14, font_color="black"),
    )

    return fig


def create_win_rate_podium_chart(rate_df: pd.DataFrame, color_map: dict) -> go.Figure:
    """Create win rate & podium rate grouped bar chart."""
    fig = go.Figure()

    for _, row in rate_df.iterrows():
        color = color_map.get(row["Player"], None)
        darker = darken_color(color)
        fig.add_trace(
            go.Bar(
                x=[row["Player"]],
                y=[row["Win Rate"]],
                showlegend=False,
                marker_color=color,
                offsetgroup="win",
                hovertemplate=f"{row['Player']} Win Rate: {row['Win Rate']:.1f}%<extra></extra>",
                hoverlabel=dict(
                    bgcolor="lightyellow", font_size=14, font_color="black"
                ),
            )
        )
        fig.add_trace(
            go.Bar(
                x=[row["Player"]],
                y=[row["Podium Rate"]],
                showlegend=False,
                marker_color=darker,
                offsetgroup="podium",
                hovertemplate=f"{row['Player']} Podium Rate: {row['Podium Rate']:.1f}%<extra></extra>",
                hoverlabel=dict(
                    bgcolor="lightyellow", font_size=14, font_color="black"
                ),
            )
        )

    # Legend items with grey colors
    fig.add_trace(
        go.Bar(
            x=[None],
            y=[None],
            name="Win Rate",
            marker_color="lightgray",
            showlegend=True,
        )
    )
    fig.add_trace(
        go.Bar(
            x=[None],
            y=[None],
            name="Podium Rate",
            marker_color="gray",
            showlegend=True,
        )
    )

    fig.update_layout(
        barmode="group",
        height=450,
        xaxis_title="Player",
        yaxis_title="Rate (%)",
        yaxis=dict(dtick=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
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


# 3 Chart creation functions ##########################################
def create_ranking_chart_plotly(ranking_df: pd.DataFrame, color_map: dict) -> go.Figure:
    """Create ranking points chart with Plotly."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Total Ranking Points", "Average Points per Game"),
        specs=[[{"secondary_y": False}, {"secondary_y": False}]],
    )

    # Total points bar chart
    colors = [color_map[p] for p in ranking_df["Player"]]
    fig.add_trace(
        go.Bar(
            x=ranking_df["Player"],
            y=ranking_df["Total Points"],
            name="Total Points",
            marker_color=colors,
            text=ranking_df["Total Points"],
            textposition="outside",
            textfont=dict(color="black"),
            hoverlabel=dict(bgcolor="lightyellow", font_size=14, font_color="black"),
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
            marker_color=colors,
            text=[f"{x:.1f}" for x in ranking_df["Avg Points"]],
            textposition="outside",
            textfont=dict(color="black"),
            hoverlabel=dict(bgcolor="lightyellow", font_size=14, font_color="black"),
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

    fig.update_yaxes(row=1, col=1)

    return fig


# 4 Chart creation functions ##########################################
def create_performance_radar_plotly(metrics_for_radar, color_map: dict) -> go.Figure:
    """Create performance radar chart with Plotly."""
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
                line=dict(width=5, color=color_map.get(player_data["Player"])),
                opacity=0.7,
                hoverlabel=dict(
                    bgcolor="lightyellow", font_size=14, font_color="black"
                ),
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


def create_performance_radar_streamlit(metrics_for_radar, color_map: dict) -> None:
    """Create performance metrics with Streamlit native."""
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
    chart_colors = [color_map[p] for p in area_chart_data.columns]

    st.area_chart(area_chart_data, height=400, color=chart_colors, stack="normalize")

    # Add a summary table below for exact values
    st.markdown("**📋 Exact Values**")
    radar_display = radar_df[["Player"] + categories]
    st.dataframe(
        radar_display.style.background_gradient(subset=categories, cmap="RdYlGn"),
        use_container_width=True,
    )


def create_performance_radar_altair(metrics_for_radar, color_map: dict) -> alt.Chart:
    """Create performance radar chart with Altair (parallel coordinates)."""
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
                scale=alt.Scale(
                    domain=list(color_map.keys()), range=list(color_map.values())
                ),
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
        width=700,
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
    fig.update_traces(
        hoverlabel=dict(bgcolor="lightyellow", font_size=14, font_color="black")
    )

    return fig


# Main app #####################################################################
st.markdown("#### _well well well.... who should be thrown under the bus..???_")
ut.h_spacer(2)
# Calculate comprehensive statistics
if st.session_state.get("refresh_statistics"):
    calculate_comprehensive_stats.clear()  # type: ignore
    get_game_scores_with_rankings.clear()  # type: ignore
    st.session_state.refresh_statistics = False

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
    color_map = assign_player_colors(player_stats.keys())

    # 1. CUMULATIVE POINTS DEVELOPMENT CHART ###################################
    st.subheader("📈 Current Standing")
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

        chart_options = ["Total Score", "Time Series"]
        chart_type = st.segmented_control(
            "Chart type",
            chart_options,
            key="cum_chart",
            default="Total Score",
            label_visibility="collapsed",
        )

        if chart_type == "Total Score":
            total_points_data = [
                {"Player": name, "Total Score": stats["total_score"]}
                for name, stats in player_stats.items()
            ]
            total_points_df = pd.DataFrame(total_points_data).sort_values(
                "Total Score", ascending=False
            )
            fig_points = create_total_points_bar_chart(total_points_df, color_map)
            st.plotly_chart(fig_points, use_container_width=True)
        else:
            fig_cumulative = create_cumulative_chart(cumulative_df, color_map)
            st.plotly_chart(fig_cumulative, use_container_width=True)

    # 2. WIN COUNT CHART #######################################################
    st.subheader("🏅 Victory Statistics")
    st.markdown(
        "*Who's bringing home the most wins? (Ties count as wins for all tied players)*"
    )

    # Create wins data
    wins_data = [(name, stats["wins"]) for name, stats in player_stats.items()]
    wins_data.sort(key=lambda x: x[1], reverse=True)
    wins_df = pd.DataFrame(wins_data, columns=["Player", "Wins"])

    chart_wins = create_wins_chart_plotly(wins_df, color_map)
    st.plotly_chart(chart_wins, use_container_width=True)

    # Win rate vs podium rate chart
    rate_data = [
        {
            "Player": name,
            "Win Rate": stats["win_rate"],
            "Podium Rate": stats["podium_rate"],
        }
        for name, stats in player_stats.items()
    ]
    rate_df = pd.DataFrame(rate_data)
    rate_df = rate_df.set_index("Player").loc[wins_df["Player"]].reset_index()
    fig_rates = create_win_rate_podium_chart(rate_df, color_map)
    st.plotly_chart(fig_rates, use_container_width=True)

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
        "*Based on finishing position: 1st=7pts, 2nd=4pts, 3rd=2pts, 4th+=1pt "
        + "(tied players get same rank and points)*"
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

    fig_ranking = create_ranking_chart_plotly(ranking_df, color_map)
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

    max_total_score = max(s["total_score"] for s in player_stats.values())
    min_avg_rank = min(s["avg_rank"] for s in player_stats.values())
    max_avg_rank = max(s["avg_rank"] for s in player_stats.values())

    for name, stats in player_stats.items():
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
        fig_radar = create_performance_radar_plotly(metrics_for_radar, color_map)
        st.plotly_chart(fig_radar, use_container_width=True)
    elif radar_style == "Simple (Streamlit)":
        create_performance_radar_streamlit(metrics_for_radar, color_map)
    else:
        chart_radar = create_performance_radar_altair(metrics_for_radar, color_map)
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

    players_sorted = sorted(
        player_stats.keys(), key=lambda p: player_stats[p]["total_score"], reverse=True
    )
    h2h_matrix = h2h_matrix.loc[players_sorted, players_sorted]
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
