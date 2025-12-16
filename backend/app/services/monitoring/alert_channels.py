"""
Alert Channels Registry
Defines available notification channels with their configuration schemas
Similar to plugin_registry.py
"""

ALERT_CHANNELS = {
    "smtp": {
        "name": "SMTP (Email)",
        "description": "Send alerts via email using SMTP server",
        "icon": "Mail",
        "category": "email",
        "config_schema": {
            "smtp_host": {"type": "string", "label": "SMTP Host", "placeholder": "smtp.gmail.com"},
            "smtp_port": {"type": "number", "label": "SMTP Port", "placeholder": "587"},
            "smtp_username": {"type": "string", "label": "Username", "placeholder": "user@example.com"},
            "smtp_password": {"type": "password", "label": "Password", "placeholder": "••••••••"},
            "from_email": {"type": "string", "label": "From Email", "placeholder": "alerts@homelab.local"},
            "to_emails": {"type": "string", "label": "To Emails (comma-separated)", "placeholder": "admin@example.com"},
            "use_tls": {"type": "boolean", "label": "Use TLS", "default": True}
        }
    },
    "telegram": {
        "name": "Telegram",
        "description": "Send alerts to Telegram chat or channel",
        "icon": "MessageCircle",
        "category": "messaging",
        "config_schema": {
            "bot_token": {"type": "password", "label": "Bot Token", "placeholder": "123456:ABC-DEF..."},
            "chat_id": {"type": "string", "label": "Chat ID", "placeholder": "-1001234567890"}
        },
        "setup_instructions": "1. Create a bot with @BotFather\n2. Get your bot token\n3. Add bot to your chat\n4. Get chat ID from https://api.telegram.org/bot<TOKEN>/getUpdates"
    },
    "ntfy": {
        "name": "ntfy",
        "description": "Send push notifications via ntfy.sh or self-hosted ntfy",
        "icon": "Bell",
        "category": "push",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "placeholder": "https://ntfy.sh", "default": "https://ntfy.sh"},
            "topic": {"type": "string", "label": "Topic", "placeholder": "homelab-alerts"},
            "username": {"type": "string", "label": "Username (optional)", "placeholder": ""},
            "password": {"type": "password", "label": "Password (optional)", "placeholder": ""}
        },
        "setup_instructions": "1. Choose a unique topic name\n2. Subscribe to the topic in ntfy mobile app or web\n3. Optionally protect topic with auth on your ntfy server"
    },
    "discord": {
        "name": "Discord",
        "description": "Send alerts to Discord channel via webhook",
        "icon": "MessageSquare",
        "category": "messaging",
        "config_schema": {
            "webhook_url": {"type": "password", "label": "Webhook URL", "placeholder": "https://discord.com/api/webhooks/..."}
        },
        "setup_instructions": "1. Go to Server Settings → Integrations → Webhooks\n2. Create new webhook\n3. Copy webhook URL"
    },
    "slack": {
        "name": "Slack",
        "description": "Send alerts to Slack channel via webhook",
        "icon": "Hash",
        "category": "messaging",
        "config_schema": {
            "webhook_url": {"type": "password", "label": "Webhook URL", "placeholder": "https://hooks.slack.com/services/..."}
        },
        "setup_instructions": "1. Go to https://api.slack.com/apps\n2. Create new app and enable Incoming Webhooks\n3. Add webhook to workspace and channel\n4. Copy webhook URL"
    },
    "pushover": {
        "name": "Pushover",
        "description": "Send push notifications via Pushover",
        "icon": "Smartphone",
        "category": "push",
        "config_schema": {
            "user_key": {"type": "password", "label": "User Key", "placeholder": "u..."},
            "api_token": {"type": "password", "label": "API Token", "placeholder": "a..."}
        },
        "setup_instructions": "1. Sign up at pushover.net\n2. Create an application to get API token\n3. Get your user key from dashboard"
    },
    "gotify": {
        "name": "Gotify",
        "description": "Self-hosted push notification server",
        "icon": "Server",
        "category": "push",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "placeholder": "https://gotify.example.com"},
            "app_token": {"type": "password", "label": "Application Token", "placeholder": "A..."}
        },
        "setup_instructions": "1. Install Gotify server\n2. Create application in Gotify\n3. Copy application token"
    },
    "webhook": {
        "name": "Generic Webhook",
        "description": "Send alerts to any custom webhook endpoint",
        "icon": "Link",
        "category": "custom",
        "config_schema": {
            "url": {"type": "string", "label": "Webhook URL", "placeholder": "https://example.com/webhook"},
            "method": {"type": "select", "label": "HTTP Method", "options": ["POST", "GET"], "default": "POST"},
            "headers": {"type": "textarea", "label": "Custom Headers (JSON)", "placeholder": "{\"Authorization\": \"Bearer token\"}"}
        }
    }
}

def get_channel_info(channel_type: str):
    """Get channel information by type"""
    return ALERT_CHANNELS.get(channel_type)

def get_all_channels():
    """Get all available channels"""
    return ALERT_CHANNELS
