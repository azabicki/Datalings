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

## Database Functions

The `functions/database.py` module provides the following functions:

- `init_players_table()`: Creates the players table if it doesn't exist
- `get_all_players()`: Returns all players (active and inactive)
- `get_active_players()`: Returns only active players
- `add_player_to_database(name)`: Adds a new player to the database
- `update_player_status_in_database(player_id, is_active)`: Updates a player's active status
- `update_player_name_in_database(player_id, new_name)`: Updates a player's name
- `player_exists(name)`: Checks if a player with given name exists

## Usage

The database is automatically initialized when the application starts. Players can be managed through the Settings page, which provides:

1. **Add Player Tab**: Add new players to the system
2. **Manage Players Tab**: View, edit names, and activate/deactivate existing players

## Player Management Features

- **Unique Names**: Player names must be unique across the system
- **Name Editing**: Player names can be updated while maintaining unique constraints
- **Soft Delete**: Players can be deactivated instead of deleted to preserve historical data
- **Status Toggle**: Easy switching between active and inactive states

## Security Notes

- Database credentials are stored in `secrets.toml` (not version controlled)
- All database operations use parameterized queries to prevent SQL injection
- Player names are validated and sanitized before database operations