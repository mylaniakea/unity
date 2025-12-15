"""
Migration script to add new alert features:
- Alert sound settings
- Maintenance mode
- Alert snoozing
- Threshold rule muting
- Notification templates
- Push subscriptions
- Notification logging
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from datetime import datetime

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/homelab.db")
print(f"Connecting to database: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)

def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def table_exists(table_name):
    """Check if a table exists"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def run_migration():
    print("\n=== Starting Migration ===\n")

    with engine.connect() as conn:
        # 1. Add columns to Settings table
        print("1. Updating Settings table...")
        if not column_exists('settings', 'alert_sound_enabled'):
            conn.execute(text("ALTER TABLE settings ADD COLUMN alert_sound_enabled BOOLEAN DEFAULT FALSE"))
            print("   ✓ Added alert_sound_enabled column")
        else:
            print("   - alert_sound_enabled already exists")

        if not column_exists('settings', 'maintenance_mode_until'):
            conn.execute(text("ALTER TABLE settings ADD COLUMN maintenance_mode_until TIMESTAMP WITH TIME ZONE"))
            print("   ✓ Added maintenance_mode_until column")
        else:
            print("   - maintenance_mode_until already exists")

        # 2. Add columns to ThresholdRule table
        print("\n2. Updating ThresholdRule table...")
        if not column_exists('threshold_rules', 'muted_until'):
            conn.execute(text("ALTER TABLE threshold_rules ADD COLUMN muted_until TIMESTAMP WITH TIME ZONE"))
            print("   ✓ Added muted_until column")
        else:
            print("   - muted_until already exists")

        # 3. Add columns to Alert table
        print("\n3. Updating Alert table...")
        if not column_exists('alerts', 'snoozed_until'):
            conn.execute(text("ALTER TABLE alerts ADD COLUMN snoozed_until TIMESTAMP WITH TIME ZONE"))
            print("   ✓ Added snoozed_until column")
        else:
            print("   - snoozed_until already exists")

        # 4. Add columns to AlertChannel table
        print("\n4. Updating AlertChannel table...")
        if not column_exists('alert_channels', 'template'):
            conn.execute(text("ALTER TABLE alert_channels ADD COLUMN template TEXT"))
            print("   ✓ Added template column")
        else:
            print("   - template already exists")

        # 5. Create PushSubscription table
        print("\n5. Creating PushSubscription table...")
        if not table_exists('push_subscriptions'):
            conn.execute(text("""
                CREATE TABLE push_subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    endpoint VARCHAR UNIQUE NOT NULL,
                    p256dh VARCHAR NOT NULL,
                    auth VARCHAR NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX ix_push_subscriptions_id ON push_subscriptions(id)"))
            conn.execute(text("CREATE INDEX ix_push_subscriptions_endpoint ON push_subscriptions(endpoint)"))
            print("   ✓ Created push_subscriptions table with indexes")
        else:
            print("   - push_subscriptions already exists")

        # 6. Create NotificationLog table
        print("\n6. Creating NotificationLog table...")
        if not table_exists('notification_logs'):
            conn.execute(text("""
                CREATE TABLE notification_logs (
                    id SERIAL PRIMARY KEY,
                    alert_id INTEGER,
                    channel_id INTEGER,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN NOT NULL,
                    message TEXT,
                    FOREIGN KEY (alert_id) REFERENCES alerts(id),
                    FOREIGN KEY (channel_id) REFERENCES alert_channels(id)
                )
            """))
            conn.execute(text("CREATE INDEX ix_notification_logs_id ON notification_logs(id)"))
            conn.execute(text("CREATE INDEX ix_notification_logs_alert_id ON notification_logs(alert_id)"))
            conn.execute(text("CREATE INDEX ix_notification_logs_channel_id ON notification_logs(channel_id)"))
            print("   ✓ Created notification_logs table with indexes")
        else:
            print("   - notification_logs already exists")

        conn.commit()

    print("\n=== Migration Complete! ===\n")
    print("All new columns and tables have been added successfully.")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
