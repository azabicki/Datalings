import streamlit as st
import functions.utils as ut
import functions.auth as auth
import functions.database_dashboard as db_dashboard
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
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


@st.fragment
def render_cumulative_chart(cumulative_data, player_colors):
    """Render cumulative score progression chart as a fragment."""
    if not cumulative_data:
        st.info("No game data available for cumulative chart.")
        return
        
    cumulative_df = pd.DataFrame(cumulative_data)
    fig_cumulative = create_cumulative_chart(cumulative_df, player_colors)
    st.plotly_chart(fig_cumulative, use_container_width=True)


@st.fragment
def render_wins_chart(wins_data, player_colors):
    """Render wins chart as a fragment."""
    if not wins_data:
        st.info("No win data available.")
        return
        
    wins_df = pd.DataFrame(wins_data)
    chart_wins = create_wins_chart(wins_df, player_colors)
    st.altair_chart(chart_wins, use_container_width=True)


@st.fragment
def render_ranking_chart(ranking_data, player_colors):
    """Render ranking points chart as a fragment."""
    if not ranking_data:
        st.info("No ranking data available.")
        return
        
    ranking_df = pd.DataFrame(ranking_data)
    fig_ranking = create_ranking_chart_plotly(ranking_df, player_colors)
    st.plotly_chart(fig_ranking, use_container_width=True)


@st.fragment
def render_performance_radar(radar_data, player_colors, radar_style):
    """Render performance radar chart as a fragment."""
    if not radar_data:
        st.info("No performance data available.")
        return
        
    if radar_style == "Interactive (Plotly)":
        fig_radar = create_performance_radar_plotly(radar_data, player_colors)
        st.plotly_chart(fig_radar, use_container_width=True)
    elif radar_style == "Simple (Streamlit)":
        create_performance_radar_streamlit(radar_data, player_colors)
    else:
        chart_radar = create_performance_radar_altair(radar_data, player_colors)
        st.altair_chart(chart_radar, use_container_width=True)


@st.fragment
def render_heatmap(h2h_matrix):
    """Render head-to-head heatmap as a fragment."""
    if h2h_matrix.empty:
        st.info("No head-to-head data available.")
        return
        
    fig_h2h = create_heatmap_plotly(h2h_matrix)
    st.plotly_chart(fig_h2h, use_container_width=True)


@st.fragment
def render_detailed_stats_table(player_stats):
    """Render detailed statistics table as a fragment."""
    detailed_df = db_dashboard.get_detailed_stats_table_data(player_stats)
    st.dataframe(detailed_df, use_container_width=True, hide_index=True)


def create_cumulative_chart(cumulative_df, player_colors):
    """Create cumulative score progression chart with consistent colors."""
    fig = go.Figure()
    
    for player in cumulative_df["Player"].unique():
        player_data = cumulative_df[cumulative_df["Player"] == player]
        
        fig.add_trace(
            go.Scatter(
                x=player_data["Game"],
                y=player_data["Cumulative Score"],
                mode="lines+markers",
                name=player,
                line=dict(width=3, color=player_colors.get(player, "#666666")),
                marker=dict(size=8, color=player_colors.get(player, "#666666")),
                hovertemplate="<b>%{fullData.name}</b><br>" +
                             "Game: %{x}<br>" +
                             "Cumulative Score: %{y}<br>" +
                             "<extra></extra>",
            )
        )
    
    fig.update_layout(
        title="Cumulative Score Development Over Games",
        xaxis_title="Game Number",
        yaxis_title="Cumulative Score",
        hovermode="x unified",
        height=400,
        font=dict(color="black"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        modebar=dict(remove=["pan2d", "select2d", "lasso2d", "zoom2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"])
    )
    
    return fig


def create_wins_chart(wins_df, player_colors):
    """Create wins bar chart with consistent colors."""
    # Create color list matching the order of players in wins_df
    colors = [player_colors.get(player, "#666666") for player in wins_df["Player"]]
    
    chart = (
        alt.Chart(wins_df)
        .mark_bar(size=50)
        .encode(
            x=alt.X("Player:N", sort="-y", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Wins:Q", title="Number of Wins"),
            color=alt.Color(
                "Player:N",
                scale=alt.Scale(
                    domain=list(player_colors.keys()),
                    range=list(player_colors.values())
                ),
                legend=None
            ),
            tooltip=["Player:N", "Wins:Q"]
        )
        .properties(height=400, title="Victory Count by Player")
        .configure_axis(labelColor="black", titleColor="black")
        .configure_title(color="black")
    )
    
    return chart


def create_ranking_chart_plotly(ranking_df, player_colors):
    """Create ranking points chart with consistent colors."""
    colors = [player_colors.get(player, "#666666") for player in ranking_df["Player"]]
    
    fig = go.Figure()
    
    # Add total points bars
    fig.add_trace(
        go.Bar(
            name="Total Points",
            x=ranking_df["Player"],
            y=ranking_df["Total Points"],
            marker_color=colors,
            hovertemplate="<b>%{x}</b><br>Total Points: %{y}<extra></extra>",
        )
    )
    
    # Add average points line
    fig.add_trace(
        go.Scatter(
            name="Avg Points",
            x=ranking_df["Player"], 
            y=ranking_df["Avg Points"],
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="red", width=3),
            marker=dict(color="red", size=8),
            hovertemplate="<b>%{x}</b><br>Avg Points: %{y:.1f}<extra></extra>",
        )
    )
    
    fig.update_layout(
        title="Ranking Points System Results",
        xaxis_title="Player",
        yaxis=dict(title="Total Ranking Points", side="left"),
        yaxis2=dict(title="Average Points per Game", side="right", overlaying="y"),
        height=400,
        font=dict(color="black"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        modebar=dict(remove=["pan2d", "select2d", "lasso2d", "zoom2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"])
    )
    
    return fig


def create_performance_radar_plotly(radar_data, player_colors):
    """Create performance radar chart with consistent colors."""
    fig = go.Figure()
    
    categories = ["Total Score", "Win Rate", "Podium Rate", "Ranking Consistency", "Games Played"]
    
    for player_info in radar_data:
        player_name = player_info["Player"]
        values = [player_info[cat] for cat in categories]
        
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself",
                name=player_name,
                line_color=player_colors.get(player_name, "#666666"),
                fillcolor=player_colors.get(player_name, "#666666"),
                opacity=0.6,
            )
        )
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], color="black"),
            angularaxis=dict(color="black")
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        title="Multi-Dimensional Performance Comparison",
        height=500,
        font=dict(color="black"),
        modebar=dict(remove=["pan2d", "select2d", "lasso2d", "zoom2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"])
    )
    
    return fig


def create_performance_radar_streamlit(radar_data, player_colors):
    """Create simple performance radar using Streamlit components."""
    st.markdown("**Performance Metrics by Player:**")
    
    for player_info in radar_data:
        player_name = player_info["Player"]
        
        with st.container():
            st.markdown(f"**{player_name}**")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Score", f"{player_info['Total Score']:.1f}%")
                st.metric("Win Rate", f"{player_info['Win Rate']:.1f}%")
                st.metric("Games Played", f"{player_info['Games Played']:.1f}%")
            
            with col2:
                st.metric("Podium Rate", f"{player_info['Podium Rate']:.1f}%")
                st.metric("Consistency", f"{player_info['Ranking Consistency']:.1f}%")


def create_performance_radar_altair(radar_data, player_colors):
    """Create performance radar chart using Altair."""
    # Flatten data for Altair
    flattened_data = []
    for player_info in radar_data:
        player_name = player_info["Player"]
        for metric, value in player_info.items():
            if metric != "Player":
                flattened_data.append({
                    "Player": player_name,
                    "Metric": metric,
                    "Value": value
                })
    
    radar_df = pd.DataFrame(flattened_data)
    
    chart = (
        alt.Chart(radar_df)
        .mark_bar()
        .encode(
            x=alt.X("Value:Q", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("Metric:N"),
            color=alt.Color(
                "Player:N",
                scale=alt.Scale(
                    domain=list(player_colors.keys()),
                    range=list(player_colors.values())
                )
            ),
            row=alt.Row("Player:N"),
            tooltip=["Player:N", "Metric:N", "Value:Q"]
        )
        .properties(height=100, title="Performance Metrics by Player")
        .resolve_scale(x="independent")
        .configure_axis(labelColor="black", titleColor="black")
        .configure_title(color="black")
    )
    
    return chart


def create_heatmap_plotly(h2h_matrix):
    """Create head-to-head performance heatmap."""
    max_abs_value = max(abs(h2h_matrix.values.min()), abs(h2h_matrix.values.max()))
    
    fig = go.Figure(
        data=go.Heatmap(
            z=h2h_matrix.values,
            x=h2h_matrix.columns,
            y=h2h_matrix.index,
            colorscale="RdYlGn",
            zmid=0,
            hoverongaps=False,
            hovertemplate="<b>%{y} vs %{x}</b><br>Differential: %{z}<extra></extra>",
        )
    )
    
    fig.update_layout(
        title="Head-to-Head Win-Loss Differential (Interactive)",
        height=400,
        font=dict(color="black"),
        modebar=dict(remove=["pan2d", "select2d", "lasso2d", "zoom2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"])
    )
    
    fig.update_coloraxes(showscale=False)
    fig.update_traces(hoverlabel=dict(bgcolor="lightgrey", font_color="black"))
    
    return fig


# Main app #####################################################################
st.subheader("_Well well well.... who should we throw under the bus..???_")

# Get optimized dashboard data
with st.spinner("Loading dashboard data..."):
    dashboard_data = db_dashboard.get_dashboard_data_optimized()
    active_players, player_colors = db_dashboard.get_active_players_with_colors()

if dashboard_data is None:
    st.info(
        "🎮 No games recorded yet! Start playing to see your amazing stats and charts."
    )
    st.markdown("Add some games in the **Game Results** page to see:")
    st.markdown("- 📈 Cumulative score progression")
    st.markdown("- 🏅 Win statistics and rankings")
    st.markdown("- 🎯 Performance analytics")
    st.markdown("- 📊 Beautiful interactive charts")
else:
    player_stats = dashboard_data["player_stats"]
    scores_df = dashboard_data["scores_df"]
    total_games = dashboard_data["total_games"]
    age_stats = dashboard_data["age_stats"]
    chart_data = dashboard_data["chart_data"]

    # 1. CUMULATIVE POINTS DEVELOPMENT CHART ###################################
    st.subheader("📈 Cumulative Score Progression")
    st.markdown("*Track how each player's total score develops over time*")

    render_cumulative_chart(chart_data["cumulative_data"], player_colors)

    st.markdown("---")

    # 2. WIN COUNT CHART #######################################################
    st.subheader("🏅 Victory Statistics")
    st.markdown(
        "*Who's bringing home the most wins? (Ties count as wins for all tied players)*"
    )

    render_wins_chart(chart_data["wins_data"], player_colors)

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

    render_ranking_chart(chart_data["ranking_data"], player_colors)

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

    render_performance_radar(chart_data["radar_data"], player_colors, radar_style)

    # Detailed statistics table
    st.markdown("**📋 Detailed Player Statistics**")

    render_detailed_stats_table(player_stats)

    # 5: Head-to-Head Performance Matrix #######################################
    st.markdown("---")
    st.subheader("⚔️ Head-to-Head Performance")
    st.markdown("*Win-loss differential between players (row vs column)*")

    render_heatmap(chart_data["h2h_matrix"])

    st.markdown(
        """*Matrix shows win-loss differential:*
- positive (green) = more wins
- zero (white) = even
- negative (red) = more losses"""
    )

# Display color legend for players
if player_colors:
    st.markdown("---")
    st.markdown("**🎨 Player Color Legend**")
    cols = st.columns(len(player_colors))
    for i, (player, color) in enumerate(player_colors.items()):
        with cols[i]:
            st.markdown(
                f'<div style="background-color: {color}; padding: 10px; border-radius: 5px; text-align: center; color: black; font-weight: bold;">{player}</div>',
                unsafe_allow_html=True
            )

st.markdown("---")
st.markdown("*Keep playing to see your stats evolve! 🚀*")