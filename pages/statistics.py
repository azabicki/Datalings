import streamlit as st
import functions.utils as ut
import functions.auth as auth
import functions.database as db
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from scipy.stats import gaussian_kde
from pandas import PeriodIndex, wide_to_long


st.set_page_config(page_title="Statistics", layout=ut.app_layout)

# auth
auth.login()

# init
ut.default_style()
ut.create_sidebar()


# Cache data loading for performance ###########################################
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_all_game_data():
    """Load and process all game data efficiently with optimized queries"""
    games_df = db.get_all_games()
    if games_df.empty:
        return pd.DataFrame(), pd.DataFrame(), {}

    all_game_data = []
    game_stats = []
    host_selections = []
    total_ages_played = 0

    for _, game_row in games_df.iterrows():
        game_id = int(game_row["id"])
        game_date = game_row["game_date"]
        game_details = db.get_game_details(game_id)

        # Game-level stats
        scores = game_details.get("scores", [])
        if scores:
            game_scores = [score["score"] for score in scores]
            game_duration = None
            num_ages = None
            host_selection = None

            # Extract settings more efficiently
            for setting in game_details.get("settings", []):
                setting_name = setting["setting_name"]
                setting_name_lower = setting_name.lower()

                if "duration" in setting_name_lower or "time" in setting_name_lower:
                    try:
                        game_duration = float(setting["value"])
                    except:
                        pass
                elif "# ages" in setting_name_lower or setting_name_lower == "ages":
                    try:
                        num_ages = int(float(setting["value"]))
                        total_ages_played += num_ages
                    except:
                        pass
                elif "host" in setting_name_lower:
                    host_selection = setting["value"]
                    host_selections.append(host_selection)

            game_total_score = sum(game_scores)

            game_stats.append(
                {
                    "game_id": game_id,
                    "game_date": game_date,
                    "player_count": len(scores),
                    "total_score": game_total_score,
                    "avg_score": np.mean(game_scores),
                    "min_score": min(game_scores),
                    "max_score": max(game_scores),
                    "score_range": max(game_scores) - min(game_scores),
                    "duration": game_duration,
                    "num_ages": num_ages,
                    "host_selection": host_selection,
                }
            )

            # Individual score data
            for score_data in scores:
                all_game_data.append(
                    {
                        "game_id": game_id,
                        "game_date": game_date,
                        "player_id": score_data["player_id"],
                        "player_name": score_data["player_name"],
                        "score": score_data["score"],
                        "duration": game_duration,
                        "num_ages": num_ages,
                        "host_selection": host_selection,
                    }
                )

    scores_df = pd.DataFrame(all_game_data)
    games_df = pd.DataFrame(game_stats)

    # Calculate summary stats
    stats = {}
    if not scores_df.empty and not games_df.empty:
        # Find superhost (most frequent host selection)
        superhost = "N/A"
        superhost_count = 0
        if host_selections:
            from collections import Counter

            host_counts = Counter(host_selections)
            if host_counts:
                superhost = host_counts.most_common(1)[0][0]
                superhost_count = host_counts.most_common(1)[0][1]
                # Check for ties
                max_count = host_counts.most_common(1)[0][1]
                tied_hosts = [
                    host for host, count in host_counts.items() if count == max_count
                ]
                if len(tied_hosts) > 1:
                    superhost = ", ".join(tied_hosts)

        # Calculate average score per game correctly (sum of scores per game, then mean)
        avg_score_per_game = games_df["total_score"].mean()

        stats = {
            "total_games": len(games_df),
            "total_points": scores_df["score"].sum(),
            "total_duration": (
                games_df["duration"].sum()
                if bool(games_df["duration"].notna().any())
                else 0
            ),
            "total_ages_played": total_ages_played,
            "avg_score_per_player_per_game": scores_df["score"].mean(),
            "avg_score_per_game": avg_score_per_game,
            "highest_score": scores_df["score"].max(),
            "highest_score_player": (
                scores_df.loc[scores_df["score"].idxmax(), "player_name"]
                if not scores_df.empty
                else None
            ),
            "lowest_score": scores_df["score"].min(),
            "lowest_score_player": (
                scores_df.loc[scores_df["score"].idxmin(), "player_name"]
                if not scores_df.empty
                else None
            ),
            "avg_score_range": games_df["score_range"].mean(),
            "shortest_game": (
                games_df["duration"].min()
                if bool(games_df["duration"].notna().any())
                else None
            ),
            "longest_game": (
                games_df["duration"].max()
                if bool(games_df["duration"].notna().any())
                else None
            ),
            "avg_duration": (
                games_df["duration"].mean()
                if bool(games_df["duration"].notna().any())
                else None
            ),
            "lowest_ages": (
                games_df["num_ages"].min()
                if bool(games_df["num_ages"].notna().any())
                else None
            ),
            "highest_ages": (
                games_df["num_ages"].max()
                if bool(games_df["num_ages"].notna().any())
                else None
            ),
            "avg_ages": (
                games_df["num_ages"].mean()
                if bool(games_df["num_ages"].notna().any())
                else None
            ),
            "superhost": superhost,
            "superhost_count": superhost_count,
        }

    return scores_df, games_df, stats


def format_duration(minutes):
    """Format duration in minutes to h:mm h format"""
    if pd.isna(minutes) or minutes is None:
        return "N/A"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}:{mins:02d}h"


def create_metric_tile(title, value, border=True):
    """Create a styled metric tile with border"""
    if isinstance(value, float):
        if value > 1000:
            value = f"{value:,.0f}"
        else:
            value = f"{value:.1f}"

    st.metric(title, value, border=border)


# Load data ####################################################################
scores_df, games_df, summary_stats = load_all_game_data()

if scores_df.empty:
    st.warning("No game data available.")
    st.stop()


# Overview section #############################################################
@st.fragment
def overview_section():
    st.subheader(":material/visibility: :material/remove: Overview")

    # Two metrics per row
    col1, col2, col3 = st.columns(3)
    with col1:
        create_metric_tile("Total Games", summary_stats.get("total_games"))
    with col2:
        create_metric_tile("Total Points", summary_stats.get("total_points"))
    with col3:
        create_metric_tile("Total Ages Played", summary_stats.get("total_ages_played"))

    # Superhost tile (full width)
    host = summary_stats.get("superhost", "N/A")
    host_count = summary_stats.get("superhost_count", 0)
    create_metric_tile(":material/home: Superhost", f"{host} ({host_count} times)")


overview_section()


# Time & Day section ###########################################################
@st.fragment
def time_day_section():
    st.subheader(":material/schedule: :material/remove: Time & Day")

    # Duration tiles - two per row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_time = summary_stats.get("total_duration", 0)
        create_metric_tile("Total Time", format_duration(total_time))
    with col2:
        avg_dur = summary_stats.get("avg_duration")
        create_metric_tile("Avg Duration", format_duration(avg_dur))
    with col3:
        shortest = summary_stats.get("shortest_game")
        create_metric_tile("Shortest Game", format_duration(shortest))
    with col4:
        longest = summary_stats.get("longest_game")
        create_metric_tile("Longest Game", format_duration(longest))

    # Day of week chart
    if not games_df.empty:
        games_df_copy = games_df.copy()
        games_df_copy["game_date"] = pd.to_datetime(games_df_copy["game_date"])
        games_df_copy["day_of_week"] = games_df_copy["game_date"].dt.day_name()

        day_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        day_counts = (
            games_df_copy["day_of_week"].value_counts().reindex(day_order, fill_value=0)
        )

        fig_dow = px.bar(
            x=day_counts.index,
            y=day_counts.values,
            labels={"x": "", "y": "# Games"},
            color_discrete_sequence=["#84fab0"],
        )

        fig_dow.update_layout(
            title="Games Played by Day of Week",
            height=300,
            title_font_size=16,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14,
            showlegend=False,
            xaxis_tickangle=-45,
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

        fig_dow.update_yaxes(dtick=1)

        hover_labels = [
            f"{day}: {count} {'game' if count == 1 else 'games'}"
            for day, count in zip(day_counts.index, day_counts.values)
        ]
        fig_dow.update_traces(
            hovertext=hover_labels,
            hovertemplate="%{hovertext}<extra></extra>",
            hoverlabel=dict(
                bgcolor="lightyellow",  # <- background color
                font_size=14,
                font_color="black",  # optional: text color
            ),
        )
        st.plotly_chart(fig_dow, use_container_width=True)

        # Monthly games chart - only show month names
        games_df_copy["year_month"] = games_df_copy["game_date"].dt.to_period("M")
        monthly_counts = games_df_copy["year_month"].value_counts().sort_index()

        # Format month labels to show only month name
        month_labels = [
            period.to_timestamp().strftime("%b %Y")
            for period in PeriodIndex(monthly_counts.index)
        ]

        fig_monthly = px.bar(
            x=month_labels,
            y=monthly_counts.values,
            labels={"x": "", "y": "# Games"},
            color_discrete_sequence=["#a8e6cf"],
        )

        fig_monthly.update_layout(
            title="Games Played by Month",
            height=300,
            title_font_size=16,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14,
            showlegend=False,
            xaxis_tickangle=-45,
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
        fig_monthly.update_yaxes(dtick=1)

        hover_labels = [
            f"{month.to_timestamp().strftime('%B %Y')}: {count} {'game' if count == 1 else 'games'}"
            for month, count in zip(
                PeriodIndex(monthly_counts.index), monthly_counts.values
            )
        ]
        fig_monthly.update_traces(
            hovertext=hover_labels,
            hovertemplate="%{hovertext}<extra></extra>",
            hoverlabel=dict(
                bgcolor="lightyellow",  # <- background color
                font_size=14,
                font_color="black",  # optional: text color
            ),
        )
        st.plotly_chart(fig_monthly, use_container_width=True)


ut.h_spacer(3)
time_day_section()


# Ages section #################################################################
@st.fragment
def ages_section():
    st.subheader(":material/stacks: :material/remove: Ages")

    # Ages tiles - two per row
    col1, col2, col3 = st.columns(3)
    with col1:
        lowest_ages = summary_stats.get("lowest_ages")
        create_metric_tile("Lowest #Ages", int(lowest_ages) if lowest_ages else "N/A")
    with col2:
        avg_ages = summary_stats.get("avg_ages")
        create_metric_tile("Average #Ages", f"{avg_ages:.1f}" if avg_ages else "N/A")
    with col3:
        highest_ages = summary_stats.get("highest_ages")
        create_metric_tile(
            "Highest #Ages", int(highest_ages) if highest_ages else "N/A"
        )

    # Age per game chart
    if not games_df.empty and bool(games_df["num_ages"].notna().any()):
        ages_data = games_df.dropna(subset=["num_ages"]).copy()
        ages_data = ages_data.sort_values("game_date")
        ages_data["game_label"] = [f"Game {i+1}" for i in range(len(ages_data))]

        fig_ages = px.line(
            ages_data,
            x="game_label",
            y="num_ages",
            labels={"game_label": "", "num_ages": "# Ages"},
            color_discrete_sequence=["#ff9999"],
        )
        fig_ages.update_traces(line=dict(width=3))  # Set line width to 3
        fig_ages.update_yaxes(dtick=1, range=[ages_data["num_ages"].min() - 0.5, 16.5])

        fig_ages.update_layout(
            title_text="Ages played per Game",
            height=300,
            title_font_size=16,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14,
            showlegend=False,
            xaxis_tickangle=-45,
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

        fig_ages.update_traces(
            hovertemplate="played %{y} Ages in %{x}<extra></extra>",
            hoverlabel=dict(
                bgcolor="lightyellow",  # <- background color
                font_size=14,
                font_color="black",  # optional: text color
            ),
        )

        st.plotly_chart(fig_ages, use_container_width=True)


ut.h_spacer(3)
ages_section()


# Score Statistics section #####################################################
@st.fragment
def score_statistics_section():
    st.subheader(":material/scoreboard: :material/remove: Scores")

    # Score tiles - two per row
    col1, col2, col3 = st.columns(3)
    with col1:
        avg_game_score = summary_stats.get("avg_score_per_game")
        create_metric_tile(
            "Avg Score / Game", f"{avg_game_score:.1f}" if avg_game_score else "N/A"
        )
    with col2:
        avg_score = summary_stats.get("avg_score_per_player_per_game")
        create_metric_tile(
            "Avg Score / Player", f"{avg_score:.1f}" if avg_score else "N/A"
        )
    with col3:
        avg_range = summary_stats.get("avg_score_range")
        create_metric_tile(
            "Avg Score Range", f"{avg_range:.1f}" if avg_range else "N/A"
        )

    col1, col2 = st.columns(2)
    with col1:
        highest = summary_stats.get("highest_score")
        highest_player = summary_stats.get("highest_score_player")
        create_metric_tile(
            "Highest Score", f"{int(highest)} - {highest_player}" if highest else "N/A"
        )
    with col2:
        lowest = summary_stats.get("lowest_score")
        lowest_player = summary_stats.get("lowest_score_player")
        create_metric_tile(
            "Lowest Score", f"{int(lowest)} - {lowest_player}" if lowest else "N/A"
        )

    # Score distribution chart with maximum 3 bins
    if not scores_df.empty:
        score_data = np.asarray(scores_df["score"].dropna())
        bin_width = 2

        # Compute bins and frequencies manually
        counts, bin_edges = np.histogram(
            score_data,
            bins=np.arange(min(score_data), max(score_data) + bin_width, bin_width),
        )
        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])

        # Histogram trace with bin width = 3
        hist_trace = go.Bar(
            x=bin_centers,
            y=counts,
            width=bin_width,
            marker_color="#ff9999",
            name="Histogram",
        )

        # KDE line overlay
        kde = gaussian_kde(score_data)
        x_range = np.linspace(min(score_data) - 5, max(score_data) + 5, 1000)
        kde_values = kde(x_range)

        # Scale KDE to match histogram (approximate scaling)
        kde_values_scaled = kde_values * len(score_data) * bin_width

        kde_trace = go.Scatter(
            x=x_range,
            y=kde_values_scaled,
            mode="lines",
            name="Density",
            line=dict(color="grey", width=2.5),
            hoverinfo="skip",
        )

        # Combine both
        fig_dist = go.Figure(data=[hist_trace, kde_trace])

        fig_dist.update_layout(
            title="Distribution of Scores",
            xaxis_title="Score",
            yaxis_title="Count",
            height=350,
            title_font_size=16,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14,
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

        fig_dist.update_yaxes(dtick=1)

        hover_texts = [
            f"{count} times between {int(left)} and {int(right)} points"
            for count, left, right in zip(counts, bin_edges[:-1], bin_edges[1:])
        ]
        fig_dist.update_traces(
            hovertext=hover_texts,
            hovertemplate="%{hovertext}<extra></extra>",
            hoverlabel=dict(
                bgcolor="lightyellow",  # <- background color
                font_size=14,
                font_color="black",  # optional: text color
            ),
        )

        st.plotly_chart(fig_dist, use_container_width=True)

    # Score range per game chart with wider lines and larger markers
    if not games_df.empty:
        games_sorted = games_df.sort_values("game_date").reset_index(drop=True)
        games_sorted["game_label"] = [f"Game {i+1}" for i in range(len(games_sorted))]

        fig_range = go.Figure()

        # Add range lines with increased width
        for i, row in games_sorted.iterrows():
            fig_range.add_trace(
                go.Scatter(
                    x=[row["game_label"], row["game_label"]],
                    y=[row["min_score"], row["max_score"]],
                    mode="lines",
                    line=dict(color="lightblue", width=16),  # Increased width
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

            # Add average score dot with larger size
            fig_range.add_trace(
                go.Scatter(
                    x=[row["game_label"]],
                    y=[row["avg_score"]],
                    mode="markers",
                    marker=dict(symbol=25, color="red", size=16),
                    # marker=dict(symbol="diamond-wide", color="red", size=16),
                    showlegend=False,
                    hovertemplate=f"Avg Score: {row['avg_score']:.1f}<extra></extra>",
                )
            )

        # Add individual player scores with larger markers
        for game_id in games_sorted["game_id"]:
            game_scores = scores_df[scores_df["game_id"] == game_id]
            game_label = games_sorted[games_sorted["game_id"] == game_id][
                "game_label"
            ].iloc[0]

            fig_range.add_trace(
                go.Scatter(
                    x=[game_label] * len(game_scores),
                    y=game_scores["score"],
                    mode="markers",
                    marker=dict(symbol=300, color="darkblue", size=8, opacity=0.8),
                    showlegend=False,
                    hovertemplate="<br>".join(
                        [
                            f"{row['player_name']}: {row['score']}"
                            for _, row in game_scores.iterrows()
                        ]
                    )
                    + "<extra></extra>",
                )
            )

        fig_range.update_layout(
            title="Score Range per Game",
            yaxis_title="Score",
            height=400,
            title_font_size=16,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14,
            xaxis_tickangle=-45,
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

        fig_range.update_traces(
            hoverlabel=dict(
                bgcolor="lightyellow",  # <- background color
                font_size=14,
                font_color="black",  # optional: text color
            )
        )

        st.plotly_chart(fig_range, use_container_width=True)

    # Score consistency by player with player names on figure
    if not games_df.empty:
        player_stats = (
            scores_df.groupby("player_name")
            .agg({"score": ["mean", "std", "count"]})
            .round(2)
        )

        player_stats.columns = ["avg_score", "score_std", "game_count"]
        player_stats = player_stats.reset_index()
        player_stats = player_stats[
            player_stats["game_count"] >= 2
        ]  # Only players with 2+ games

        if not player_stats.empty:
            fig_consistency = px.scatter(
                player_stats,
                x="avg_score",
                y="score_std",
                size="game_count",
                text="player_name",
                color="game_count",
                color_continuous_scale="Purpor",
            )

            fig_consistency.update_traces(textposition="top center")

            fig_consistency.update_layout(
                title="Score Consistency by Player",
                xaxis_title="Average Score",
                yaxis_title="Score Standard Deviation",
                height=450,
                title_font_size=16,
                xaxis_title_font_size=14,
                yaxis_title_font_size=14,
                coloraxis=dict(
                    cmin=player_stats["game_count"].min() - 1,
                    cmax=player_stats["game_count"].max() + 1,
                ),
                coloraxis_colorbar=dict(
                    title=dict(text="Games Played", side="right"), tickmode="linear"
                ),
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

            fig_consistency.update_traces(
                hovertemplate="<b>%{text}</b> played %{marker.size} games &<br>"
                + "scored on average:<br>"
                + "%{x:.1f} ± %{y:.1f} points<extra></extra>",
                hoverlabel=dict(
                    bgcolor="lightyellow",  # <- background color
                    font_size=14,
                    font_color="black",  # optional: text color
                ),
                marker=dict(line=dict(color="white", width=2)),
            )

            st.plotly_chart(fig_consistency, use_container_width=True)

    # Duration vs scores chart
    if not games_df.empty:
        duration_games = games_df.dropna(subset=["duration"])
        if not duration_games.empty:
            fig_duration_scores = px.scatter(
                duration_games,
                x="duration",
                y="avg_score",
                size="player_count",
                color="total_score",
                color_continuous_scale="sunset",
            )

            fig_duration_scores.update_layout(
                title="Duration vs Average Scores",
                xaxis_title="Duration (minutes)",
                yaxis_title="Average Score",
                height=400,
                title_font_size=16,
                xaxis_title_font_size=14,
                yaxis_title_font_size=14,
                coloraxis_colorbar=dict(title=dict(text="Total Score", side="right")),
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

            fig_duration_scores.update_traces(
                hoverlabel=dict(
                    bgcolor="lightyellow",  # <- background color
                    font_size=14,
                    font_color="black",  # optional: text color
                ),
                marker=dict(line=dict(color="white", width=2)),
            )

            st.plotly_chart(fig_duration_scores, use_container_width=True)

    # Number of Ages vs scores chart - using num_ages and coloring by max_score
    if not games_df.empty:
        ages_games = games_df.dropna(subset=["num_ages"])
        if not ages_games.empty:
            fig_ages_scores = px.scatter(
                ages_games,
                x="num_ages",
                y="avg_score",
                size="player_count",
                color="max_score",
                color_continuous_scale="sunset",
            )

            fig_ages_scores.update_layout(
                title="# Ages vs Average Scores",
                xaxis_title="Ages played",
                yaxis_title="Average Score",
                height=400,
                title_font_size=16,
                xaxis_title_font_size=14,
                yaxis_title_font_size=14,
                coloraxis_colorbar=dict(title=dict(text="Highest Score", side="right")),
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

            fig_ages_scores.update_traces(
                hoverlabel=dict(
                    bgcolor="lightyellow",  # <- background color
                    font_size=14,
                    font_color="black",  # optional: text color
                ),
                marker=dict(line=dict(color="white", width=2)),
            )

            st.plotly_chart(fig_ages_scores, use_container_width=True)


ut.h_spacer(3)
score_statistics_section()
