#!/bin/bash

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE playlists;

EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "playlists" <<-EOSQL
    CREATE TABLE playlists (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        user_id INTEGER NOT NULL
    );
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "playlists" <<-EOSQL
    CREATE TABLE shared (
        playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (playlist_id, user_id)
    );
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "playlists" <<-EOSQL
    CREATE TABLE playlist_songs (
        playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
        artist TEXT NOT NULL,
        title TEXT NOT NULL,
        PRIMARY KEY (playlist_id, artist, title)
    );
EOSQL