#!/bin/bash
set -e

# 1. Generate/Update settings.cfg from environment variables
# This ensures tools/set_up_db.py and the app use the correct Docker connection details
cat <<EOF > /tmp/update_config.py
import configparser
import os

config = configparser.RawConfigParser()
# Try to read existing or example to preserve other settings
if os.path.exists('settings.cfg'):
    config.read('settings.cfg')
elif os.path.exists('settings.cfg.example'):
    config.read('settings.cfg.example')

if not config.has_section('sessions'): config.add_section('sessions')
if not config.has_section('flask'): config.add_section('flask')

env_map = {
    'SESSIONS_HOST': ('sessions', 'host'),
    'SESSIONS_PORT': ('sessions', 'port'),
    'SESSIONS_DBNAME': ('sessions', 'dbname'),
    'SESSIONS_USER': ('sessions', 'user'),
    'SESSIONS_PASSWORD': ('sessions', 'password'),
    'SESSIONS_SECRET_KEY_PUBLIC': ('sessions', 'secret_key_public'),
    'SESSIONS_SECRET_KEY_PRIVATE': ('sessions', 'secret_key_private'),
    'SESSIONS_EXPIRATION_TIME': ('sessions', 'expiration_time'),
    'FLASK_UPLOAD_FOLDER': ('flask', 'upload_folder')
}

for env_key, (section, option) in env_map.items():
    if env_key in os.environ:
        config.set(section, option, os.environ[env_key])

with open('settings.cfg', 'w') as f:
    config.write(f)
EOF
python3 /tmp/update_config.py

# 2. Wait for Database and Initialize if needed
cat <<EOF > /tmp/check_db.py
import time, psycopg2, os, sys

conn_params = {
    'host': os.environ.get('SESSIONS_HOST', 'db'),
    'port': os.environ.get('SESSIONS_PORT', '5432'),
    'dbname': os.environ.get('SESSIONS_DBNAME', 'sessions'),
    'user': os.environ.get('SESSIONS_USER', 'enmodal'),
    'password': os.environ.get('SESSIONS_PASSWORD', 'password')
}

print('Waiting for database connection...')
while True:
    try:
        conn = psycopg2.connect(**conn_params)
        conn.close()
        print('Database connected.')
        break
    except psycopg2.OperationalError:
        time.sleep(1)

try:
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sessions');")
    exists = cur.fetchone()[0]
    conn.close()
    if not exists:
        sys.exit(1) # Exit 1 indicates setup is needed
except Exception as e:
    print(e)
EOF

if ! python3 /tmp/check_db.py; then
    echo "Database not initialized. Running setup..."
    python3 tools/set_up_db.py
fi

# 3. Start the server
exec "$@"