# Database Setup for Datalings

## Overview

The Datalings application uses a MySQL database to store player information and game data. All table names are prefixed with `datalings_` to avoid conflicts with other applications using the same database.

## Database Configuration

The database connection is configured in `.streamlit/secrets.toml`:

```toml
[connections.mysql]
dialect = "mysql"
host = "your_host"
port = 3306
database = "your_database"
username = "your_username"
password = "your_password"
```

## Tables

### datalings_players

Stores information about players in the system.

```sql
CREATE TABLE datalings_players (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `name`: Unique player name (required)
- `is_active`: Boolean flag to indicate if player is active (default: 1)
- `created_at`: Timestamp when player was created
- `updated_at`: Timestamp when player was last modified

### datalings_game_settings

Stores configurable game settings that can be used across different games.

```sql
CREATE TABLE datalings_game_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    note TEXT,
    type ENUM('number', 'boolean', 'list', 'time') NOT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `name`: Unique setting name (required)
- `note`: Optional description or note about the setting
- `type`: The data type of the setting (number, boolean, list, or time)
- `is_active`: Boolean flag to indicate if setting is active (default: 1)
- `created_at`: Timestamp when setting was created
- `updated_at`: Timestamp when setting was last modified

### datalings_game_setting_list_items

Stores individual items for game settings of type 'list'.

```sql
CREATE TABLE datalings_game_setting_list_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_id INT NOT NULL,
    value VARCHAR(255) NOT NULL,
    order_index INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (setting_id) REFERENCES datalings_game_settings(id) ON DELETE CASCADE,
    UNIQUE KEY unique_setting_value (setting_id, value)
);
```

**Columns:**
- `id`: Auto-incrementing primary key
- `setting_id`: Foreign key reference to the game setting
- `value`: The list item value
- `order_index`: Order position of the item in the list
- `created_at`: Timestamp when item was created

## Database Functions

The `functions/database.py` module provides the following functions:

**Player Functions:**
- `init_players_table()`: Creates the players table if it doesn't exist
- `get_all_players()`: Returns all players (active and inactive)
- `get_active_players()`: Returns only active players
- `add_player_to_database(name)`: Adds a new player to the database
- `update_player_status_in_database(player_id, is_active)`: Updates a player's active status
- `update_player_name_in_database(player_id, new_name)`: Updates a player's name
- `player_exists(name)`: Checks if a player with given name exists

**Game Settings Functions:**
- `init_game_settings_table()`: Creates the game settings tables if they don't exist
- `get_all_game_settings()`: Returns all game settings (active and inactive)
- `get_active_game_settings()`: Returns only active game settings
- `get_game_setting_list_items(setting_id)`: Returns all list items for a specific setting
- `add_game_setting_to_database(name, note, setting_type)`: Adds a new game setting (list types created as inactive)
- `add_list_item_to_setting(setting_id, value, order_index)`: Adds an item to a list-type setting
- `update_list_item_in_setting(item_id, new_value)`: Updates/renames an item in a list-type setting
- `update_game_setting_in_database(setting_id, new_name, new_type)`: Updates a setting's name and type
- `update_game_setting_status_in_database(setting_id, is_active)`: Updates a setting's active status
- `game_setting_exists_except_id(name, setting_id)`: Checks if a game setting name exists (excluding specific ID)

**Game Results Functions:**
- `init_game_results_tables()`: Creates the game results tables if they don't exist
- `add_game_to_database(game_date, player_scores, setting_values, notes)`: Records a new game with scores and settings
- `get_all_games()`: Returns all games with summary information
- `get_game_details(game_id)`: Returns detailed information about a specific game
- `update_game_in_database(game_id, game_date, player_scores, setting_values, notes)`: Updates an existing game
- `delete_game_from_database(game_id)`: Deletes a game and all related data
- `format_date_german(date_obj)`: Formats dates to German format (dd.mm.yyyy)
- `parse_german_date(date_str)`: Parses German format dates to date objects

## Usage

The database is automatically initialized when the application starts. The Settings page provides management for both players and game settings:

### Player Management
1. **Add Player Tab**: Add new players to the system
2. **Manage Players Tab**: View, edit names, and activate/deactivate existing players

### Game Settings Management
1. **Overview Tab**: View all settings with summary statistics
2. **Manage Tab**: Edit settings, manage list items, and activate/deactivate settings
3. **Create New Tab**: Create new game settings with different data types:
   - **Number**: Numeric values
   - **Boolean**: True/false values
   - **List**: Predefined list of options (created as inactive, items added via edit functionality)
   - **Time**: Duration tracking for games (validated for time format)

## Features

### Player Management
- **Unique Names**: Player names must be unique across the system
- **Name Editing**: Player names can be updated while maintaining unique constraints
- **Soft Delete**: Players can be deactivated instead of deleted to preserve historical data
- **Status Toggle**: Easy switching between active and inactive states

### Game Settings Management
- **Multiple Data Types**: Support for number, boolean, list, and time settings
- **Active/Inactive Status**: Settings can be activated/deactivated like players
- **Smart Activation**: List settings cannot be activated until they have at least one item
- **Soft Delete**: Settings can be deactivated instead of deleted to preserve historical data
- **Item Persistence**: List items can be renamed but never deleted to maintain data integrity
- **List Management**: For list-type settings, easily add/rename individual items via edit interface
- **Unique Names**: Setting names must be unique across the system (validated during editing)
- **Optional Notes**: Add descriptions to clarify setting purposes
- **Ordered Lists**: List items maintain their order through the order_index field
- **User-Friendly Messages**: Clear guidance when list settings need items added

### Game Results Management
- **Game Recording**: Record games with player scores and setting values
- **Type-Specific Inputs**: Different input types based on setting types:
  - **Number**: Number input with validation
  - **Boolean**: Toggle switches
  - **Time**: Number input for minutes (1-1440 range)
  - **List**: Selectbox with configured list items
- **Date Formatting**: All dates displayed in German format (dd.mm.yyyy)
- **Game History**: View all recorded games with summary statistics
- **Game Editing**: Edit all aspects of recorded games including scores and settings
- **Data Validation**: Ensures at least one non-zero score per game

## Migration Notes

### Adding Time Type to Existing Databases

If you're upgrading from a previous version that didn't have the 'time' setting type, the application will automatically attempt to migrate your database. If automatic migration fails, you can manually run:

```sql
ALTER TABLE datalings_game_settings 
MODIFY COLUMN type ENUM('number', 'boolean', 'list', 'time') NOT NULL;
```

The migration adds 'time' as a new option to the existing ENUM without affecting existing data.

### Game Results Tables

The system automatically creates three additional tables for game results:

```sql
-- Main games table
CREATE TABLE datalings_games (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Player scores for each game
CREATE TABLE datalings_game_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    player_id INT NOT NULL,
    score INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES datalings_games(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES datalings_players(id) ON DELETE CASCADE,
    UNIQUE KEY unique_game_player (game_id, player_id)
);

-- Game setting values for each game
CREATE TABLE datalings_game_setting_values (
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
);
```

**Key Features:**
- **Type-Specific Storage**: Different columns for each setting type for efficient querying
- **Referential Integrity**: Foreign keys ensure data consistency
- **Cascading Deletes**: Removing a game automatically removes all related scores and settings
- **Unique Constraints**: Prevents duplicate player scores or setting values per game

## Security Notes

- Database credentials are stored in `secrets.toml` (not version controlled)
- All database operations use parameterized queries with named parameters to prevent SQL injection
- Player names and setting names are validated and sanitized before database operations
- Duplicate name checking prevents data conflicts during editing