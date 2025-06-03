import os
import streamlit as st


def default_style() -> None:
    """
    Defines defaults styling and layout settings.

    Args:
        None

    Returns:
        None
    """

    css = """
    <style>
        [data-testid="stSidebar"]{
            min-width: 280px;
            max-width: 280px;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def create_sidebar() -> None:
    """
    creates the left-side menu

    Args:
        None

    Returns:
        None
    """

    # title
    st.sidebar.markdown("# datalings", unsafe_allow_html=True)
    h_spacer(height=2, sb=True)

    # pages
    st.sidebar.page_link("datalings.py", label=":material/leaderboard: Standings")
    st.sidebar.page_link(
        os.path.join("pages", "hall_of_fame.py"),
        label=":material/dashboard: Hall of Fame",
    )
    st.sidebar.page_link(
        os.path.join("pages", "statistics.py"),
        label=":material/query_stats: Statistics",
    )
    st.sidebar.page_link(
        os.path.join("pages", "game_results.py"),
        label=":material/sports_score: Game Results",
    )
    st.sidebar.divider()
    st.sidebar.page_link(
        os.path.join("pages", "settings.py"), label=":material/settings: Settings"
    )

    # user is connected
    h_spacer(height=2, sb=True)
    if st.session_state["authentication_status"]:
        authenticator = st.session_state["auth"]
        authenticator.logout(
            button_name=f"logout {st.session_state.get("username")}",
            location="sidebar",
            use_container_width=True,
        )


def h_spacer(height: int = 0, sb: bool = False) -> None:
    """
    Adds empty lines.

    Args:
        height (int): Number of lines to add, defaults to 0
        sb (bool): If True, adds lines to sidebar. If False, adds to main area, defaults to False

    Returns:
        None
    """

    for _ in range(height):
        if sb:
            st.sidebar.write("\n")
        else:
            st.write("\n")
