#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL
"""
import sqlite3
import psycopg2
import json

# SQLite connection
sqlite_conn = sqlite3.connect('backend/data/homelab.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

# PostgreSQL connection
pg_conn = psycopg2.connect(
    dbname='homelab_db',
    user='homelab_user',
    password='homelab_password',
    host='localhost',
    port='5432'
)
pg_cur = pg_conn.cursor()

print("Starting migration from SQLite to PostgreSQL...")

# Migrate server_profiles
print("\nMigrating server_profiles...")
sqlite_cur.execute("SELECT * FROM server_profiles")
profiles = sqlite_cur.fetchall()
for profile in profiles:
    pg_cur.execute("""
        INSERT INTO server_profiles
        (id, name, description, ip_address, ssh_port, ssh_username, ssh_key_path,
         use_local_agent, enabled_plugins, detected_plugins, hardware_info, os_info, packages, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            ip_address = EXCLUDED.ip_address,
            hardware_info = EXCLUDED.hardware_info,
            os_info = EXCLUDED.os_info
    """, (
        profile['id'],
        profile['name'],
        profile['description'],
        profile['ip_address'],
        profile['ssh_port'] if profile['ssh_port'] else 22,
        profile['ssh_username'],
        profile['ssh_key_path'],
        bool(profile['use_local_agent']) if profile['use_local_agent'] is not None else False,
        '[]',  # enabled_plugins (new column, default empty)
        '{}',  # detected_plugins (new column, default empty)
        profile['hardware_info'] if profile['hardware_info'] else '{}',
        profile['os_info'] if profile['os_info'] else '{}',
        profile['packages'] if profile['packages'] else '[]',
        profile['created_at'],
        profile['updated_at']
    ))
print(f"Migrated {len(profiles)} server profiles")

# Migrate settings
print("\nMigrating settings...")
sqlite_cur.execute("SELECT * FROM settings")
settings_rows = sqlite_cur.fetchall()
for setting in settings_rows:
    # Check if settings exist
    pg_cur.execute("SELECT id FROM settings WHERE id = %s", (setting['id'],))
    if pg_cur.fetchone():
        print("Settings already exist, skipping...")
    else:
        # Get cron values or use defaults (handle missing columns)
        try:
            cron_24hr = setting['cron_24hr_report'] or '0 2 * * *'
        except (KeyError, IndexError):
            cron_24hr = '0 2 * * *'
        try:
            cron_7day = setting['cron_7day_report'] or '0 3 * * 1'
        except (KeyError, IndexError):
            cron_7day = '0 3 * * 1'
        try:
            cron_monthly = setting['cron_monthly_report'] or '0 4 1 * *'
        except (KeyError, IndexError):
            cron_monthly = '0 4 1 * *'

        pg_cur.execute("""
            INSERT INTO settings (id, providers, active_model, primary_provider, fallback_provider,
                                system_prompt, cron_24hr_report, cron_7day_report, cron_monthly_report, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            setting['id'],
            setting['providers'] if setting['providers'] else '{}',
            setting['active_model'],
            setting['primary_provider'],
            setting['fallback_provider'],
            setting['system_prompt'],
            cron_24hr,
            cron_7day,
            cron_monthly,
            setting['updated_at']
        ))
print(f"Migrated {len(settings_rows)} settings")

# Migrate reports (if any)
print("\nMigrating reports...")
sqlite_cur.execute("SELECT * FROM reports")
reports = sqlite_cur.fetchall()
for report in reports:
    pg_cur.execute("""
        INSERT INTO reports (id, server_id, report_type, start_time, end_time, aggregated_data, generated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, (
        report['id'],
        report['server_id'],
        report['report_type'],
        report['start_time'],
        report['end_time'],
        report['aggregated_data'] if report['aggregated_data'] else '{}',
        report['generated_at']
    ))
print(f"Migrated {len(reports)} reports")

# Migrate knowledge (if any)
print("\nMigrating knowledge...")
sqlite_cur.execute("SELECT * FROM knowledge")
knowledge_items = sqlite_cur.fetchall()
for item in knowledge_items:
    pg_cur.execute("""
        INSERT INTO knowledge (id, title, content, category, tags, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, (
        item['id'],
        item['title'],
        item['content'],
        item['category'],
        item['tags'] if item['tags'] else '[]',
        item['created_at'],
        item['updated_at']
    ))
print(f"Migrated {len(knowledge_items)} knowledge items")

# Commit and close
pg_conn.commit()
print("\n✅ Migration completed successfully!")

# Update sequence counters
print("\nUpdating sequence counters...")
pg_cur.execute("SELECT setval('server_profiles_id_seq', (SELECT MAX(id) FROM server_profiles))")
pg_cur.execute("SELECT setval('reports_id_seq', COALESCE((SELECT MAX(id) FROM reports), 1))")
pg_cur.execute("SELECT setval('knowledge_id_seq', COALESCE((SELECT MAX(id) FROM knowledge), 1))")
pg_conn.commit()

pg_cur.close()
pg_conn.close()
sqlite_cur.close()
sqlite_conn.close()

print("\n✅ All done! Data migrated from SQLite to PostgreSQL")
