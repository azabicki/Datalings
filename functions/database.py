import streamlit as st
import pandas as pd
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def init_tables():
    """Initialize the players table for datalings application."""
    conn = st.connection("mysql", type="sql")

    # Create players table
    create_players_table_sql = """
    CREATE TABLE IF NOT EXISTS datalings_players (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        is_active TINYINT(1) DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_players_active (is_active)
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

    # """Initialize the game settings tables for datalings application."""
    conn = st.connection("mysql", type="sql")

    # Create game settings table
    create_game_settings_table_sql = """
    CREATE TABLE IF NOT EXISTS datalings_game_settings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        note TEXT,
        type ENUM('number', 'boolean', 'list', 'time') NOT NULL,
        position INT NOT NULL DEFAULT 0,
        is_active TINYINT(1) DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_game_settings_active (is_active),
        INDEX idx_game_settings_position (position)
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
        UNIQUE KEY unique_setting_value (setting_id, value),
        INDEX idx_setting_order (setting_id, order_index)
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

    # """Initialize the game results tables for datalings application."""
    conn = st.connection("mysql", type="sql")

    # Create games table
    create_games_table_sql = """
    CREATE TABLE IF NOT EXISTS datalings_games (
        id INT AUTO_INCREMENT PRIMARY KEY,
        game_date DATE NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """

    # Create game scores table
    create_scores_table_sql = """
    CREATE TABLE IF NOT EXISTS datalings_game_scores (
        id INT AUTO_INCREMENT PRIMARY KEY,
        game_id INT NOT NULL,
        player_id INT NOT NULL,
        score INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (game_id) REFERENCES datalings_games(id) ON DELETE CASCADE,
        FOREIGN KEY (player_id) REFERENCES datalings_players(id) ON DELETE CASCADE,
        UNIQUE KEY unique_game_player (game_id, player_id)
    )
    """

    # Create game settings values table
    create_game_settings_values_table_sql = """
    CREATE TABLE IF NOT EXISTS datalings_game_setting_values (
        id INT AUTO_INCREMENT PRIMARY KEY,
        game_id INT NOT NULL,
        setting_id INT NOT NULL,
        value_text TEXT,
        value_number INT,
        value_boolean TINYINT(1),
        value_time_minutes INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (game_id) REFERENCES datalings_games(id) ON DELETE CASCADE,
        FOREIGN KEY (setting_id) REFERENCES datalings_game_settings(id) ON DELETE CASCADE,
        UNIQUE KEY unique_game_setting (game_id, setting_id)
    )
    """

    try:
        with conn.session as session:
            session.execute(text(create_games_table_sql))
            session.execute(text(create_scores_table_sql))
            session.execute(text(create_game_settings_values_table_sql))
            session.commit()
        logger.info("Game results tables created successfully")
    except Exception as e:
        logger.error(f"Error creating game results tables: {e}")
        raise e


def nuke_database():
    """Delete all data from the database."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            session.execute(text("DELETE FROM datalings_game_setting_values"))
            session.execute(text("DELETE FROM datalings_game_scores"))
            session.execute(text("DELETE FROM datalings_games"))
            session.execute(text("DELETE FROM datalings_game_settings"))
            session.execute(text("DELETE FROM datalings_game_setting_list_items"))
            session.execute(text("DELETE FROM datalings_players"))
            session.commit()
        logger.info("Database nuked successfully")
    except Exception as e:
        logger.error(f"Error nuking database: {e}")
        raise e


def get_all_players() -> pd.DataFrame:
    """Get all players from the database."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query(
            "SELECT id, name, is_active FROM datalings_players ORDER BY name",
            ttl=0,
        )
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
            "SELECT id, name, is_active FROM datalings_players WHERE is_active = 1 ORDER BY name",
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



def get_all_game_settings() -> pd.DataFrame:
    """Get all game settings from the database ordered by position."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query(
            "SELECT id, name, note, type, position, is_active "
            "FROM datalings_game_settings ORDER BY position",
            ttl=0,
        )
        return df
    except Exception as e:
        logger.error(f"Error fetching game settings: {e}")
        st.error(f"Error fetching game settings: {e}")
        return pd.DataFrame()


def get_active_game_settings() -> pd.DataFrame:
    """Get only active game settings from the database ordered by position."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query(
            "SELECT id, name, note, type, position, is_active "
            "FROM datalings_game_settings WHERE is_active = 1 ORDER BY position",
            ttl=0,
        )
        return df
    except Exception as e:
        logger.error(f"Error fetching active game settings: {e}")
        st.error(f"Error fetching active game settings: {e}")
        return pd.DataFrame()


def get_game_setting_list_items(setting_id: int) -> pd.DataFrame:
    """Get list items for a specific game setting."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query(
            "SELECT id, setting_id, value, order_index "
            "FROM datalings_game_setting_list_items WHERE setting_id = :setting_id ORDER BY order_index, value",
            params={"setting_id": setting_id},
            ttl=0,
        )
        return df
    except Exception as e:
        logger.error(f"Error fetching list items for setting {setting_id}: {e}")
        # Don't show error to user, just return empty DataFrame
        return pd.DataFrame()


def get_next_game_setting_position() -> int:
    """Get the next available position for a new game setting."""
    conn = st.connection("mysql", type="sql")
    try:
        result = conn.query(
            "SELECT COALESCE(MAX(position), 0) + 1 as next_position FROM datalings_game_settings",
            ttl=0,
        )
        return int(result.iloc[0]["next_position"])
    except Exception as e:
        logger.error(f"Error getting next position: {e}")
        return 1


def add_game_setting_to_database(
    name: str, note: str = "", setting_type: str = "text"
) -> bool:
    """Add a new game setting to the database. Returns the setting ID if successful, 0 if failed."""
    conn = st.connection("mysql", type="sql")
    try:
        # Set list-type settings as inactive by default
        is_active = 0 if setting_type == "list" else 1

        # Get next position
        position = get_next_game_setting_position()

        with conn.session as session:
            session.execute(
                text(
                    "INSERT INTO datalings_game_settings (name, note, type, position, is_active) VALUES (:name, :note, :type, :position, :is_active)"
                ),
                {
                    "name": name,
                    "note": note,
                    "type": setting_type,
                    "position": position,
                    "is_active": is_active,
                },
            )
            session.commit()
            # Get the last inserted ID using a separate query
            setting_id_result = session.execute(text("SELECT LAST_INSERT_ID()"))
            setting_id = setting_id_result.scalar()
        logger.info(f"Game setting '{name}' added successfully with ID {setting_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding game setting '{name}': {e}")
        error_msg = str(e)
        if "Duplicate entry" in error_msg or "UNIQUE constraint" in error_msg:
            st.error(f"Game setting '{name}' already exists!")
        else:
            st.error(f"Error adding game setting: {error_msg}")
        return False


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


def update_list_item_in_setting(item_id: int, new_value: str) -> bool:
    """Update a list item's value in a game setting."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            session.execute(
                text(
                    "UPDATE datalings_game_setting_list_items SET value = :value WHERE id = :id"
                ),
                {"value": new_value, "id": item_id},
            )
            session.commit()
        logger.info(f"List item ID {item_id} updated to '{new_value}' successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating list item ID {item_id}: {e}")
        error_msg = str(e)
        if "Duplicate entry" in error_msg or "UNIQUE constraint" in error_msg:
            st.error(f"List item '{new_value}' already exists for this setting!")
        else:
            st.error(f"Error updating list item: {error_msg}")
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
    """Check if a game setting name already exists (excluding a specific ID)."""
    conn = st.connection("mysql", type="sql")
    try:
        result = conn.query(
            "SELECT COUNT(*) as count FROM datalings_game_settings WHERE name = :name AND id != :id",
            params={"name": name, "id": setting_id},
            ttl=0,
        )
        return int(result.iloc[0]["count"]) > 0
    except Exception as e:
        logger.error(f"Error checking if game setting exists: {e}")
        return False



def move_setting_up(setting_id: int) -> bool:
    """Move a setting up in position (decrease position number)."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            # Get current position
            current_result = session.execute(
                text("SELECT position FROM datalings_game_settings WHERE id = :id"),
                {"id": setting_id},
            )
            current_position = current_result.scalar()

            if current_position is None or current_position <= 1:
                return False  # Already at top or setting not found

            # Find the setting with the position we want to swap with
            swap_result = session.execute(
                text(
                    "SELECT id FROM datalings_game_settings WHERE position = :position LIMIT 1"
                ),
                {"position": current_position - 1},
            )
            swap_setting_id = swap_result.scalar()

            if swap_setting_id:
                # Swap positions
                session.execute(
                    text(
                        "UPDATE datalings_game_settings SET position = :position WHERE id = :id"
                    ),
                    {"position": current_position, "id": swap_setting_id},
                )
                session.execute(
                    text(
                        "UPDATE datalings_game_settings SET position = :position WHERE id = :id"
                    ),
                    {"position": current_position - 1, "id": setting_id},
                )

            session.commit()
        return True
    except Exception as e:
        logger.error(f"Error moving setting up: {e}")
        st.error(f"Error moving setting up: {e}")
        return False


def move_setting_down(setting_id: int) -> bool:
    """Move a setting down in position (increase position number)."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            # Get current position and max position
            current_result = session.execute(
                text("SELECT position FROM datalings_game_settings WHERE id = :id"),
                {"id": setting_id},
            )
            current_position = current_result.scalar()

            max_result = session.execute(
                text("SELECT MAX(position) FROM datalings_game_settings")
            )
            max_position = max_result.scalar()

            if current_position is None or current_position >= max_position:
                return False  # Already at bottom or setting not found

            # Find the setting with the position we want to swap with
            swap_result = session.execute(
                text(
                    "SELECT id FROM datalings_game_settings WHERE position = :position LIMIT 1"
                ),
                {"position": current_position + 1},
            )
            swap_setting_id = swap_result.scalar()

            if swap_setting_id:
                # Swap positions
                session.execute(
                    text(
                        "UPDATE datalings_game_settings SET position = :position WHERE id = :id"
                    ),
                    {"position": current_position, "id": swap_setting_id},
                )
                session.execute(
                    text(
                        "UPDATE datalings_game_settings SET position = :position WHERE id = :id"
                    ),
                    {"position": current_position + 1, "id": setting_id},
                )

            session.commit()
        return True
    except Exception as e:
        logger.error(f"Error moving setting down: {e}")
        st.error(f"Error moving setting down: {e}")
        return False


def add_game_to_database(
    game_date, player_scores: dict, setting_values: dict, notes: str = ""
) -> bool:
    """Add a new game with scores and settings to the database."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            # Insert game and get ID in same transaction
            session.execute(
                text(
                    "INSERT INTO datalings_games (game_date, notes) VALUES (:game_date, :notes)"
                ),
                {"game_date": game_date, "notes": notes},
            )

            # Get the game ID immediately after insertion
            game_id_result = session.execute(text("SELECT LAST_INSERT_ID()"))
            game_id = game_id_result.scalar()
            logger.info(f"Game inserted with ID: {game_id}")

            if not game_id or game_id == 0:
                logger.error("Failed to get valid game ID after insertion")
                st.error("Failed to create game record")
                session.rollback()
                return False

            # Verify the game was actually inserted
            verify_result = session.execute(
                text("SELECT id FROM datalings_games WHERE id = :game_id"),
                {"game_id": game_id},
            ).fetchone()

            if not verify_result:
                logger.error(f"Game ID {game_id} not found in database after insertion")
                st.error("Failed to verify game creation")
                session.rollback()
                return False

            # Debug: Log player scores before insertion
            logger.info(
                f"Attempting to insert scores for game {game_id}: {player_scores}"
            )

            # Check for duplicates in player_scores dictionary
            player_ids = list(player_scores.keys())
            unique_player_ids = set(player_ids)
            if len(player_ids) != len(unique_player_ids):
                logger.error(
                    f"Duplicate player IDs found in player_scores: {player_ids}"
                )
                st.error(
                    "Duplicate players detected in scores. Please refresh and try again."
                )
                session.rollback()
                return False

            # Insert player scores
            for player_id, score in player_scores.items():
                logger.info(f"Inserting score for player {player_id}: {score}")
                session.execute(
                    text(
                        "INSERT INTO datalings_game_scores (game_id, player_id, score) VALUES (:game_id, :player_id, :score)"
                    ),
                    {"game_id": game_id, "player_id": player_id, "score": score},
                )

            # Insert setting values
            for setting_id, value in setting_values.items():
                # Get setting type to determine which column to use
                setting_info = session.execute(
                    text(
                        "SELECT type FROM datalings_game_settings WHERE id = :setting_id"
                    ),
                    {"setting_id": setting_id},
                ).fetchone()

                if not setting_info:
                    logger.warning(f"Setting ID {setting_id} not found, skipping")
                    continue

                setting_type = setting_info[0]

                if setting_type == "number":
                    session.execute(
                        text(
                            "INSERT INTO datalings_game_setting_values (game_id, setting_id, value_number) VALUES (:game_id, :setting_id, :value)"
                        ),
                        {
                            "game_id": game_id,
                            "setting_id": setting_id,
                            "value": int(value),
                        },
                    )
                elif setting_type == "boolean":
                    bool_value = 1 if str(value).lower() == "true" else 0
                    session.execute(
                        text(
                            "INSERT INTO datalings_game_setting_values (game_id, setting_id, value_boolean) VALUES (:game_id, :setting_id, :value)"
                        ),
                        {
                            "game_id": game_id,
                            "setting_id": setting_id,
                            "value": bool_value,
                        },
                    )
                elif setting_type == "time":
                    session.execute(
                        text(
                            "INSERT INTO datalings_game_setting_values (game_id, setting_id, value_time_minutes) VALUES (:game_id, :setting_id, :value)"
                        ),
                        {
                            "game_id": game_id,
                            "setting_id": setting_id,
                            "value": int(value),
                        },
                    )
                elif setting_type == "list":
                    session.execute(
                        text(
                            "INSERT INTO datalings_game_setting_values (game_id, setting_id, value_text) VALUES (:game_id, :setting_id, :value)"
                        ),
                        {
                            "game_id": game_id,
                            "setting_id": setting_id,
                            "value": str(value),
                        },
                    )

            # Commit all changes at once
            session.commit()

        logger.info(f"Game added successfully with ID {game_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding game: {e}")
        st.error(f"Error saving game: {e}")
        return False


def get_all_games() -> pd.DataFrame:
    """Get all games from the database."""
    conn = st.connection("mysql", type="sql")
    try:
        df = conn.query(
            """
            SELECT g.id, g.game_date, g.notes, g.created_at,
                   COUNT(DISTINCT s.player_id) as player_count
            FROM datalings_games g
            LEFT JOIN datalings_game_scores s ON g.id = s.game_id
            GROUP BY g.id, g.game_date, g.notes, g.created_at
            ORDER BY g.game_date DESC, g.created_at DESC
        """,
            ttl=0,
        )
        return df
    except Exception as e:
        logger.error(f"Error fetching games: {e}")
        st.error(f"Error fetching games: {e}")
        return pd.DataFrame()



def update_game_in_database(
    game_id: int, game_date, player_scores: dict, setting_values: dict, notes: str = ""
) -> bool:
    """Update an existing game with new scores and settings."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            # Update game basic info
            session.execute(
                text(
                    "UPDATE datalings_games SET game_date = :game_date, notes = :notes WHERE id = :game_id"
                ),
                {"game_date": game_date, "notes": notes, "game_id": game_id},
            )

            # Update player scores
            for player_id, score in player_scores.items():
                session.execute(
                    text(
                        """
                        UPDATE datalings_game_scores
                        SET score = :score
                        WHERE game_id = :game_id AND player_id = :player_id
                    """
                    ),
                    {"score": score, "game_id": game_id, "player_id": player_id},
                )

            # Update setting values
            for setting_id, value in setting_values.items():
                # Get setting type
                setting_info = session.execute(
                    text(
                        "SELECT type FROM datalings_game_settings WHERE id = :setting_id"
                    ),
                    {"setting_id": setting_id},
                ).fetchone()

                if setting_info:
                    setting_type = setting_info[0]

                    if setting_type == "list":
                        session.execute(
                            text(
                                """
                                UPDATE datalings_game_setting_values
                                SET value_text = :value, value_number = NULL, value_boolean = NULL, value_time_minutes = NULL
                                WHERE game_id = :game_id AND setting_id = :setting_id
                            """
                            ),
                            {
                                "value": value,
                                "game_id": game_id,
                                "setting_id": setting_id,
                            },
                        )
                    elif setting_type == "number":
                        session.execute(
                            text(
                                """
                                UPDATE datalings_game_setting_values
                                SET value_number = :value, value_text = NULL, value_boolean = NULL, value_time_minutes = NULL
                                WHERE game_id = :game_id AND setting_id = :setting_id
                            """
                            ),
                            {
                                "value": int(value),
                                "game_id": game_id,
                                "setting_id": setting_id,
                            },
                        )
                    elif setting_type == "boolean":
                        bool_value = 1 if str(value).lower() == "true" else 0
                        session.execute(
                            text(
                                """
                                UPDATE datalings_game_setting_values
                                SET value_boolean = :value, value_text = NULL, value_number = NULL, value_time_minutes = NULL
                                WHERE game_id = :game_id AND setting_id = :setting_id
                            """
                            ),
                            {
                                "value": bool_value,
                                "game_id": game_id,
                                "setting_id": setting_id,
                            },
                        )
                    elif setting_type == "time":
                        session.execute(
                            text(
                                """
                                UPDATE datalings_game_setting_values
                                SET value_time_minutes = :value, value_text = NULL, value_number = NULL, value_boolean = NULL
                                WHERE game_id = :game_id AND setting_id = :setting_id
                            """
                            ),
                            {
                                "value": int(value),
                                "game_id": game_id,
                                "setting_id": setting_id,
                            },
                        )

            session.commit()

        logger.info(f"Game {game_id} updated successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating game {game_id}: {e}")
        st.error(f"Error updating game: {e}")
        return False


def delete_game_from_database(game_id: int) -> bool:
    """Delete a game and all related data from the database."""
    conn = st.connection("mysql", type="sql")
    try:
        with conn.session as session:
            # First, delete game setting values (explicit cleanup)
            session.execute(
                text(
                    "DELETE FROM datalings_game_setting_values WHERE game_id = :game_id"
                ),
                {"game_id": game_id},
            )

            # Then, delete game scores (explicit cleanup)
            session.execute(
                text("DELETE FROM datalings_game_scores WHERE game_id = :game_id"),
                {"game_id": game_id},
            )

            # Finally, delete the game itself
            session.execute(
                text("DELETE FROM datalings_games WHERE id = :game_id"),
                {"game_id": game_id},
            )

            session.commit()

        logger.info(f"Game {game_id} deleted successfully")
        return True
    except Exception as e:
        logger.error(f"Error deleting game {game_id}: {e}")
        st.error(f"Error deleting game: {e}")
        return False


def get_games_count() -> int:
    """Return total number of games in the database."""
    conn = st.connection("mysql", type="sql")
    try:
        result = conn.query(
            "SELECT COUNT(*) as count FROM datalings_games",
            ttl=0,
        )
        return int(result.iloc[0]["count"])
    except Exception as e:
        logger.error(f"Error counting games: {e}")
        st.error(f"Error counting games: {e}")
        return 0


def get_games_summary(limit: int, offset: int) -> pd.DataFrame:
    """Get paginated game summaries."""
    conn = st.connection("mysql", type="sql")
    try:
        summary_query = """
        SELECT
            g.id, g.game_date, g.notes, g.created_at,
            COUNT(DISTINCT s.player_id) as player_count,
            MAX(s.score) as highest_score,
            MIN(s.score) as lowest_score
        FROM datalings_games g
        LEFT JOIN datalings_game_scores s ON g.id = s.game_id
        GROUP BY g.id, g.game_date, g.notes, g.created_at
        ORDER BY g.game_date DESC, g.id DESC
        LIMIT :limit OFFSET :offset
        """
        df = conn.query(
            summary_query,
            params={"limit": limit, "offset": offset},
            ttl=0,
        )
        return df
    except Exception as e:
        logger.error(f"Error fetching games summary: {e}")
        st.error(f"Error fetching games summary: {e}")
        return pd.DataFrame()


def get_single_game_details(game_id: int) -> dict:
    """Return detailed scores and settings for a single game."""
    conn = st.connection("mysql", type="sql")
    try:
        game_query = """
        SELECT
            s.player_id, p.name as player_name, s.score,
            sv.setting_id, gs.name as setting_name, gs.type as setting_type,
            gs.position,
            CASE
                WHEN gs.type = 'list' THEN sv.value_text
                WHEN gs.type = 'number' THEN CAST(sv.value_number AS CHAR)
                WHEN gs.type = 'boolean' THEN CASE WHEN sv.value_boolean = 1 THEN 'True' ELSE 'False' END
                WHEN gs.type = 'time' THEN CAST(sv.value_time_minutes AS CHAR)
                ELSE ''
            END as setting_value
        FROM datalings_games g
        LEFT JOIN datalings_game_scores s ON g.id = s.game_id
        LEFT JOIN datalings_players p ON s.player_id = p.id
        LEFT JOIN datalings_game_setting_values sv ON g.id = sv.game_id
        LEFT JOIN datalings_game_settings gs ON sv.setting_id = gs.id
        WHERE g.id = :game_id
        ORDER BY s.score DESC, gs.position
        """
        df = conn.query(game_query, params={"game_id": game_id}, ttl=0)
        if df.empty:
            return {"scores": [], "settings": []}

        scores = []
        settings = []
        seen_players = set()
        seen_settings = set()

        for _, row in df.iterrows():
            if pd.notna(row["player_id"]) and row["player_id"] not in seen_players:
                scores.append(
                    {
                        "player_id": row["player_id"],
                        "player_name": row["player_name"],
                        "score": row["score"],
                    }
                )
                seen_players.add(row["player_id"])
            if pd.notna(row["setting_id"]) and row["setting_id"] not in seen_settings:
                settings.append(
                    {
                        "setting_id": row["setting_id"],
                        "setting_name": row["setting_name"],
                        "setting_type": row["setting_type"],
                        "value": row["setting_value"] or "",
                    }
                )
                seen_settings.add(row["setting_id"])

        return {"scores": scores, "settings": settings}
    except Exception as e:
        logger.error(f"Error fetching game {game_id} details: {e}")
        st.error(f"Error fetching game details: {e}")
        return {"scores": [], "settings": []}


def get_all_scores() -> pd.DataFrame:
    """Return all game scores with player names and game dates."""
    conn = st.connection("mysql", type="sql")
    try:
        query = """
            SELECT s.game_id,
                   g.game_date,
                   s.player_id,
                   p.name AS player_name,
                   s.score
            FROM datalings_game_scores s
            JOIN datalings_players p ON s.player_id = p.id
            JOIN datalings_games g ON s.game_id = g.id
            ORDER BY g.game_date, s.game_id
        """
        return conn.query(query, ttl=0)
    except Exception as e:
        logger.error(f"Error fetching all game scores: {e}")
        return pd.DataFrame()


def get_all_game_setting_values() -> pd.DataFrame:
    """Return all game setting values for all games."""
    conn = st.connection("mysql", type="sql")
    try:
        query = """
            SELECT sv.game_id, sv.setting_id, gs.name AS setting_name,
                   gs.type AS setting_type, sv.value_text, sv.value_number,
                   sv.value_boolean, sv.value_time_minutes
            FROM datalings_game_setting_values sv
            JOIN datalings_game_settings gs ON sv.setting_id = gs.id
            ORDER BY sv.game_id, gs.position
        """
        return conn.query(query, ttl=0)
    except Exception as e:
        logger.error(f"Error fetching all game setting values: {e}")
        return pd.DataFrame()
