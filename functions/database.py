import streamlit as st
import pandas as pd
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def init_players_table():
    """Initialize the players table for datalings application."""
    conn = st.connection("mysql", type="sql")

    # Create players table
    create_players_table_sql = """
    CREATE TABLE IF NOT EXISTS datalings_players (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        is_active TINYINT(1) DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """

    try:
        with conn.session as session:
            session.execute(text(create_players_table_sql))
            session.commit()
        logger.info("Players table created successfully")
    except Exception as e:
        logger.error(f"Error creating players table: {e}")
        raise e


def get_all_players() -> pd.DataFrame:
    """Get all players from the database."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query("SELECT * FROM datalings_players ORDER BY name", ttl=0)
        return df
    except Exception as e:
        logger.error(f"Error fetching players: {e}")
        st.error(f"Error fetching players: {e}")
        return pd.DataFrame()


def get_active_players() -> pd.DataFrame:
    """Get only active players from the database."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query(
            "SELECT * FROM datalings_players WHERE is_active = 1 ORDER BY name",
            ttl=0,
        )
        return df
    except Exception as e:
        logger.error(f"Error fetching active players: {e}")
        st.error(f"Error fetching active players: {e}")
        return pd.DataFrame()


def add_player_to_database(name: str) -> bool:
    """Add a new player to the database."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            session.execute(
                text("INSERT INTO datalings_players (name) VALUES (:name)"),
                {"name": name},
            )
            session.commit()
        logger.info(f"Player '{name}' added successfully")
        return True
    except Exception as e:
        logger.error(f"Error adding player '{name}': {e}")
        error_msg = str(e)
        if "Duplicate entry" in error_msg or "UNIQUE constraint" in error_msg:
            st.error(f"Player '{name}' already exists!")
        else:
            st.error(f"Error adding player: {error_msg}")
        return False


def update_player_status_in_database(player_id: int, is_active: bool) -> bool:
    """Update a player's active status."""
    conn = st.connection("mysql", type="sql")
    try:
        # Convert boolean to int for MySQL compatibility
        active_value = 1 if is_active else 0
        with conn.session as session:
            session.execute(
                text("UPDATE datalings_players SET is_active = :active WHERE id = :id"),
                {"active": active_value, "id": player_id},
            )
            session.commit()
        status = "activated" if is_active else "deactivated"
        logger.info(f"Player ID {player_id} {status} successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating player status: {e}")
        st.error(f"Error updating player status: {e}")
        return False


def update_player_name_in_database(player_id: int, new_name: str) -> bool:
    """Update a player's name."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            session.execute(
                text("UPDATE datalings_players SET name = :name WHERE id = :id"),
                {"name": new_name, "id": player_id},
            )
            session.commit()
        logger.info(f"Player ID {player_id} name updated to '{new_name}' successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating player name: {e}")
        error_msg = str(e)
        if "Duplicate entry" in error_msg or "UNIQUE constraint" in error_msg:
            st.error(f"Player name '{new_name}' already exists!")
        else:
            st.error(f"Error updating player name: {error_msg}")
        return False


def player_exists(name: str) -> bool:
    """Check if a player with the given name exists."""
    conn = st.connection("mysql", type="sql")
    try:
        result = conn.query(
            "SELECT COUNT(*) as count FROM datalings_players WHERE name = %s",
            params=(name,),
            ttl=60,
        )
        return result["count"].iloc[0] > 0
    except Exception as e:
        logger.error(f"Error checking if player exists: {e}")
        return False
