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


def init_game_settings_table():
    """Initialize the game settings tables for datalings application."""
    conn = st.connection("mysql", type="sql")

    # Create game settings table
    create_game_settings_table_sql = """
    CREATE TABLE IF NOT EXISTS datalings_game_settings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        note TEXT,
        type ENUM('number', 'boolean', 'list') NOT NULL,
        is_active TINYINT(1) DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """

    # Create game setting list items table
    create_list_items_table_sql = """
    CREATE TABLE IF NOT EXISTS datalings_game_setting_list_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        setting_id INT NOT NULL,
        value VARCHAR(255) NOT NULL,
        order_index INT NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (setting_id) REFERENCES datalings_game_settings(id) ON DELETE CASCADE,
        UNIQUE KEY unique_setting_value (setting_id, value)
    )
    """

    try:
        with conn.session as session:
            session.execute(text(create_game_settings_table_sql))
            session.execute(text(create_list_items_table_sql))
            session.commit()
        logger.info("Game settings tables created successfully")
    except Exception as e:
        logger.error(f"Error creating game settings tables: {e}")
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
            "SELECT COUNT(*) as count FROM datalings_players WHERE name = :name",
            params={"name": name},
            ttl=60,
        )
        return result["count"].iloc[0] > 0
    except Exception as e:
        logger.error(f"Error checking if player exists: {e}")
        return False


def get_all_game_settings() -> pd.DataFrame:
    """Get all game settings from the database."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query("SELECT * FROM datalings_game_settings ORDER BY name", ttl=0)
        return df
    except Exception as e:
        logger.error(f"Error fetching game settings: {e}")
        st.error(f"Error fetching game settings: {e}")
        return pd.DataFrame()


def get_active_game_settings() -> pd.DataFrame:
    """Get only active game settings from the database."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query(
            "SELECT * FROM datalings_game_settings WHERE is_active = 1 ORDER BY name",
            ttl=0,
        )
        return df
    except Exception as e:
        logger.error(f"Error fetching active game settings: {e}")
        st.error(f"Error fetching active game settings: {e}")
        return pd.DataFrame()


def get_game_setting_list_items(setting_id: int) -> pd.DataFrame:
    """Get all list items for a specific game setting."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query(
            "SELECT * FROM datalings_game_setting_list_items WHERE setting_id = :setting_id ORDER BY order_index, value",
            params={"setting_id": setting_id},
            ttl=0,
        )
        return df
    except Exception as e:
        logger.error(f"Error fetching list items for setting {setting_id}: {e}")
        # Don't show error to user, just return empty DataFrame
        return pd.DataFrame()


def add_game_setting_to_database(
    name: str, note: str = "", setting_type: str = "text"
) -> int:
    """Add a new game setting to the database. Returns the setting ID if successful, 0 if failed."""
    conn = st.connection("mysql", type="sql")
    try:
        # Set list-type settings as inactive by default
        is_active = 0 if setting_type == "list" else 1

        with conn.session as session:
            session.execute(
                text(
                    "INSERT INTO datalings_game_settings (name, note, type, is_active) VALUES (:name, :note, :type, :is_active)"
                ),
                {
                    "name": name,
                    "note": note,
                    "type": setting_type,
                    "is_active": is_active,
                },
            )
            session.commit()
            # Get the last inserted ID using a separate query
            setting_id_result = session.execute(text("SELECT LAST_INSERT_ID()"))
            setting_id = setting_id_result.scalar()
        logger.info(f"Game setting '{name}' added successfully with ID {setting_id}")
        return int(setting_id) if setting_id else 0
    except Exception as e:
        logger.error(f"Error adding game setting '{name}': {e}")
        error_msg = str(e)
        if "Duplicate entry" in error_msg or "UNIQUE constraint" in error_msg:
            st.error(f"Game setting '{name}' already exists!")
        else:
            st.error(f"Error adding game setting: {error_msg}")
        return 0


def add_list_item_to_setting(setting_id: int, value: str, order_index: int = 0) -> bool:
    """Add a list item to a game setting."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            session.execute(
                text(
                    "INSERT INTO datalings_game_setting_list_items (setting_id, value, order_index) VALUES (:setting_id, :value, :order_index)"
                ),
                {"setting_id": setting_id, "value": value, "order_index": order_index},
            )
            session.commit()
        logger.info(f"List item '{value}' added to setting ID {setting_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding list item '{value}' to setting {setting_id}: {e}")
        error_msg = str(e)
        if "Duplicate entry" in error_msg or "UNIQUE constraint" in error_msg:
            st.error(f"List item '{value}' already exists for this setting!")
        else:
            st.error(f"Error adding list item: {error_msg}")
        return False


def delete_list_item_from_setting(item_id: int) -> bool:
    """Delete a list item from a game setting."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            session.execute(
                text("DELETE FROM datalings_game_setting_list_items WHERE id = :id"),
                {"id": item_id},
            )
            session.commit()
        logger.info(f"List item ID {item_id} deleted successfully")
        return True
    except Exception as e:
        logger.error(f"Error deleting list item ID {item_id}: {e}")
        st.error(f"Error deleting list item: {e}")
        return False


def update_game_setting_status_in_database(setting_id: int, is_active: bool) -> bool:
    """Update a game setting's active status."""
    conn = st.connection("mysql", type="sql")
    try:
        # Convert boolean to int for MySQL compatibility
        active_value = 1 if is_active else 0
        with conn.session as session:
            session.execute(
                text(
                    "UPDATE datalings_game_settings SET is_active = :active WHERE id = :id"
                ),
                {"active": active_value, "id": setting_id},
            )
            session.commit()
        status = "activated" if is_active else "deactivated"
        logger.info(f"Game setting ID {setting_id} {status} successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating game setting status: {e}")
        st.error(f"Error updating game setting status: {e}")
        return False


def update_game_setting_in_database(
    setting_id: int, new_name: str, new_type: str, new_note: str
) -> bool:
    """Update a game setting's name and type."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            session.execute(
                text(
                    "UPDATE datalings_game_settings SET name = :name, type = :type, note = :note WHERE id = :id"
                ),
                {
                    "name": new_name,
                    "type": new_type,
                    "note": new_note,
                    "id": setting_id,
                },
            )
            session.commit()
        logger.info(
            f"Game setting ID {setting_id} updated to '{new_name}' ({new_type}) successfully"
        )
        return True
    except Exception as e:
        logger.error(f"Error updating game setting: {e}")
        error_msg = str(e)
        if "Duplicate entry" in error_msg or "UNIQUE constraint" in error_msg:
            st.error(f"Game setting name '{new_name}' already exists!")
        else:
            st.error(f"Error updating game setting: {error_msg}")
        return False


def game_setting_exists_except_id(name: str, setting_id: int) -> bool:
    """Check if a game setting with the given name exists, excluding a specific ID."""
    conn = st.connection("mysql", type="sql")
    try:
        result = conn.query(
            "SELECT COUNT(*) as count FROM datalings_game_settings WHERE name = :name AND id != :setting_id",
            params={"name": name, "setting_id": setting_id},
            ttl=60,
        )
        return result["count"].iloc[0] > 0
    except Exception as e:
        logger.error(f"Error checking if game setting exists: {e}")
        return False
