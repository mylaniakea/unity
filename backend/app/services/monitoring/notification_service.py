"""
Notification Service
Handles sending alerts through various channels (SMTP, Telegram, ntfy, etc.)
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
import json
from typing import Dict, Any
import logging
from sqlalchemy.orm import Session # Import Session
from app.core.database import get_db # Import get_db
from app import models # Import models

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending notifications through configured channels"""

    @staticmethod
    async def send_notification(db: Session, channel: Dict[str, Any], alert_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Send notification through the specified channel and log the attempt.

        Args:
            db: The database session.
            channel: AlertChannel dict with type and config
            alert_data: Alert information to send

        Returns:
            tuple[bool, str]: True and success message if sent successfully, False and error message otherwise
        """
        channel_type = channel.get('channel_type')
        config = channel.get('config', {})
        channel_id = channel.get('id')
        alert_id = alert_data.get('alert_id')

        success = False
        message = ""

        # Create a notification log entry before attempting to send
        log_entry = models.NotificationLog(
            alert_id=alert_id,
            channel_id=channel_id,
            success=False, # Assume failure initially
            message="Attempting to send..."
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        try:
            if channel_type == 'smtp':
                success, message = await NotificationService._send_smtp(channel, config, alert_data) # Pass channel to _send_smtp
            elif channel_type == 'telegram':
                success, message = await NotificationService._send_telegram(channel, config, alert_data) # Pass channel
            elif channel_type == 'ntfy':
                success, message = await NotificationService._send_ntfy(channel, config, alert_data) # Pass channel
            elif channel_type == 'discord':
                success, message = await NotificationService._send_discord(channel, config, alert_data) # Pass channel
            elif channel_type == 'slack':
                success, message = await NotificationService._send_slack(channel, config, alert_data) # Pass channel
            elif channel_type == 'pushover':
                success, message = await NotificationService._send_pushover(channel, config, alert_data) # Pass channel
            elif channel_type == 'gotify':
                success, message = await NotificationService._send_gotify(channel, config, alert_data) # Pass channel
            elif channel_type == 'webhook':
                success, message = await NotificationService._send_webhook(channel, config, alert_data) # Pass channel
            else:
                logger.warning(f"Unknown channel type: {channel_type}")
                success = False
                message = f"Unknown channel type: {channel_type}"
        except Exception as e:
            logger.error(f"Failed to send notification via {channel_type}: {e}")
            success = False
            message = str(e)
        finally:
            # Update the log entry with the final status
            log_entry.success = success
            log_entry.message = message
            db.add(log_entry) # Re-add for update
            db.commit()
            db.refresh(log_entry)

            return success, message

    @staticmethod
    async def _send_smtp(channel: Dict[str, Any], config: Dict[str, Any], alert_data: Dict[str, Any]) -> tuple[bool, str]:
        """Send email via SMTP"""
        try:
            from_email = config.get('from_email')
            to_emails = config.get('to_emails')
            smtp_host = config.get('smtp_host')
            smtp_port = config.get('smtp_port')
            use_tls = config.get('use_tls', True)
            smtp_username = config.get('smtp_username')
            smtp_password = config.get('smtp_password')

            if not from_email: return False, "Sender email (from_email) is missing."
            if not to_emails: return False, "Recipient email(s) (to_emails) is missing."
            if not smtp_host: return False, "SMTP host is missing."
            if not smtp_port: return False, "SMTP port is missing."

            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_emails

            template = channel.get('template')
            if template:
                try:
                    rendered_message = template.format(**alert_data)
                    msg['Subject'] = f"Homelab Alert: {alert_data['severity'].upper()}"
                    body = rendered_message
                except KeyError as e:
                    return False, f"Template rendering failed: Missing variable {e}."
                except Exception as e:
                    return False, f"Template rendering failed: {e}"
            else:
                msg['Subject'] = f"[{alert_data['severity'].upper()}] Homelab Alert: {alert_data['message']}"
                body = f"""
Homelab Intelligence Alert

Severity: {alert_data['severity'].upper()}
Server: {alert_data.get('server_name', 'Unknown')}
Message: {alert_data['message']}
Metric Value: {alert_data['metric_value']}
Triggered At: {alert_data['triggered_at']}

---
Homelab Intelligence Hub
                """

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_host, int(smtp_port))
            if use_tls:
                server.starttls()

            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)

            server.send_message(msg)
            server.quit()

            logger.info(f"SMTP notification sent successfully")
            return True, "Notification sent successfully via SMTP."
        except smtplib.SMTPAuthenticationError:
            return False, "SMTP authentication failed. Check username and password."
        except smtplib.SMTPConnectError as e:
            return False, f"SMTP connection error: {e}"
        except smtplib.SMTPRecipientsRefused:
            return False, "Recipient email address refused."
        except smtplib.SMTPSenderRefused:
            return False, "Sender email address refused."
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False, str(e)

    @staticmethod
    async def _send_telegram(channel: Dict[str, Any], config: Dict[str, Any], alert_data: Dict[str, Any]) -> tuple[bool, str]:
        """Send message via Telegram Bot API"""
        try:
            bot_token = config.get('bot_token')
            chat_id = config.get('chat_id')

            if not bot_token: return False, "Telegram bot token (bot_token) is missing."
            if not chat_id: return False, "Telegram chat ID (chat_id) is missing."

            severity_emoji = {
                'critical': '🔴',
                'warning': '🟡',
                'info': '🔵'
            }.get(alert_data['severity'], '⚪')

            template = channel.get('template')
            if template:
                try:
                    message = template.format(**alert_data)
                except KeyError as e:
                    return False, f"Template rendering failed: Missing variable {e}."
                except Exception as e:
                    return False, f"Template rendering failed: {e}"
            else:
                message = f"""{severity_emoji} *Homelab Alert*

*Severity:* {alert_data['severity'].upper()}
*Server:* {alert_data.get('server_name', 'Unknown')}
*Message:* {alert_data['message']}
*Value:* {alert_data['metric_value']}

_Triggered at {alert_data['triggered_at']}_
                """

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json={
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                })

                if response.status_code == 200:
                    logger.info("Telegram notification sent successfully")
                    return True, "Notification sent successfully via Telegram."
                else:
                    error_detail = response.json().get("description", response.text) if response.content else response.text
                    logger.error(f"Telegram API error: {error_detail}")
                    return False, f"Telegram API error: {error_detail}"
        except httpx.HTTPStatusError as e:
            return False, f"Telegram HTTP error: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Telegram request error: {e}"
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False, str(e)

    @staticmethod
    async def _send_ntfy(channel: Dict[str, Any], config: Dict[str, Any], alert_data: Dict[str, Any]) -> tuple[bool, str]:
        """Send push notification via ntfy"""
        try:
            server_url = config.get('server_url', 'https://ntfy.sh')
            topic = config.get('topic')

            if not topic: return False, "ntfy topic is missing."

            url = f"{server_url.rstrip('/')}/{topic}"

            headers = {
                'Title': f"{alert_data['severity'].upper()}: {alert_data.get('server_name', 'Server')} Alert",
                'Priority': 'high' if alert_data['severity'] == 'critical' else 'default',
                'Tags': alert_data['severity']
            }

            # Add auth if configured
            auth = None
            if config.get('username') and config.get('password'):
                auth = (config['username'], config['password'])

            template = channel.get('template')
            if template:
                try:
                    message_body = template.format(**alert_data)
                except KeyError as e:
                    return False, f"Template rendering failed: Missing variable {e}."
                except Exception as e:
                    return False, f"Template rendering failed: {e}"
            else:
                message_body = f"{alert_data['message']}\nValue: {alert_data['metric_value']}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    content=message_body,
                    headers=headers,
                    auth=auth
                )

                if response.status_code == 200:
                    logger.info("ntfy notification sent successfully")
                    return True, "Notification sent successfully via ntfy."
                else:
                    logger.error(f"ntfy API error: {response.status_code} - {response.text}")
                    return False, f"ntfy API error: {response.status_code} - {response.text}"
        except httpx.HTTPStatusError as e:
            return False, f"ntfy HTTP error: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return False, f"ntfy request error: {e}"
        except Exception as e:
            logger.error(f"ntfy error: {e}")
            return False, str(e)

    @staticmethod
    async def _send_discord(channel: Dict[str, Any], config: Dict[str, Any], alert_data: Dict[str, Any]) -> tuple[bool, str]:
        """Send message via Discord webhook"""
        try:
            webhook_url = config.get('webhook_url')

            if not webhook_url: return False, "Discord webhook URL (webhook_url) is missing."

            color = {
                'critical': 0xFF0000,  # Red
                'warning': 0xFFFF00,   # Yellow
                'info': 0x0000FF       # Blue
            }.get(alert_data['severity'], 0x808080)

            template = channel.get('template')
            if template:
                try:
                    description = template.format(**alert_data)
                except KeyError as e:
                    return False, f"Template rendering failed: Missing variable {e}."
                except Exception as e:
                    return False, f"Template rendering failed: {e}"
            else:
                description = alert_data['message']

            payload = {
                'embeds': [{
                    'title': f"🚨 Homelab Alert",
                    'description': description,
                    'color': color,
                    'fields': [
                        {'name': 'Severity', 'value': alert_data['severity'].upper(), 'inline': True},
                        {'name': 'Server', 'value': alert_data.get('server_name', 'Unknown'), 'inline': True},
                        {'name': 'Metric Value', 'value': str(alert_data['metric_value']), 'inline': True}
                    ],
                    'timestamp': alert_data['triggered_at']
                }]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)

                if response.status_code in [200, 204]:
                    logger.info("Discord notification sent successfully")
                    return True, "Notification sent successfully via Discord."
                else:
                    error_detail = response.json().get("message", response.text) if response.content else response.text
                    logger.error(f"Discord webhook error: {response.status_code} - {error_detail}")
                    return False, f"Discord webhook error: {response.status_code} - {error_detail}"
        except httpx.HTTPStatusError as e:
            return False, f"Discord HTTP error: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Discord request error: {e}"
        except Exception as e:
            logger.error(f"Discord error: {e}")
            return False, str(e)

    @staticmethod
    async def _send_slack(channel: Dict[str, Any], config: Dict[str, Any], alert_data: Dict[str, Any]) -> tuple[bool, str]:
        """Send message via Slack webhook"""
        try:
            webhook_url = config.get('webhook_url')

            if not webhook_url: return False, "Slack webhook URL (webhook_url) is missing."

            color = {
                'critical': 'danger',
                'warning': 'warning',
                'info': 'good'
            }.get(alert_data['severity'], '#808080')

            template = channel.get('template')
            if template:
                try:
                    text = template.format(**alert_data)
                except KeyError as e:
                    return False, f"Template rendering failed: Missing variable {e}."
                except Exception as e:
                    return False, f"Template rendering failed: {e}"
            else:
                text = alert_data['message']

            payload = {
                'attachments': [{
                    'color': color,
                    'title': '🚨 Homelab Alert',
                    'text': text,
                    'fields': [
                        {'title': 'Severity', 'value': alert_data['severity'].upper(), 'short': True},
                        {'title': 'Server', 'value': alert_data.get('server_name', 'Unknown'), 'short': True},
                        {'title': 'Metric Value', 'value': str(alert_data['metric_value']), 'short': True}
                    ],
                    'ts': alert_data.get('timestamp', '')
                }]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)

                if response.status_code == 200:
                    logger.info("Slack notification sent successfully")
                    return True, "Notification sent successfully via Slack."
                else:
                    logger.error(f"Slack webhook error: {response.status_code} - {response.text}")
                    return False, f"Slack webhook error: {response.status_code} - {response.text}"
        except httpx.HTTPStatusError as e:
            return False, f"Slack HTTP error: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Slack request error: {e}"
        except Exception as e:
            logger.error(f"Slack error: {e}")
            return False, str(e)

    @staticmethod
    async def _send_pushover(channel: Dict[str, Any], config: Dict[str, Any], alert_data: Dict[str, Any]) -> tuple[bool, str]:
        """Send push notification via Pushover"""
        try:
            user_key = config.get('user_key')
            api_token = config.get('api_token')

            if not user_key: return False, "Pushover user key (user_key) is missing."
            if not api_token: return False, "Pushover API token (api_token) is missing."

            priority = 1 if alert_data['severity'] == 'critical' else 0

            template = channel.get('template')
            if template:
                try:
                    message_body = template.format(**alert_data)
                except KeyError as e:
                    return False, f"Template rendering failed: Missing variable {e}."
                except Exception as e:
                    return False, f"Template rendering failed: {e}"
            else:
                message_body = f"{alert_data['message']}\nValue: {alert_data['metric_value']}"

            payload = {
                'token': api_token,
                'user': user_key,
                'title': f"{alert_data['severity'].upper()}: {alert_data.get('server_name', 'Server')} Alert",
                'message': message_body,
                'priority': priority
            }

            async with httpx.AsyncClient() as client:
                response = await client.post('https://api.pushover.net/1/messages.json', data=payload)

                if response.status_code == 200:
                    logger.info("Pushover notification sent successfully")
                    return True, "Notification sent successfully via Pushover."
                else:
                    error_detail = response.json().get("errors", response.text) if response.content else response.text
                    logger.error(f"Pushover API error: {response.status_code} - {error_detail}")
                    return False, f"Pushover API error: {response.status_code} - {error_detail}"
        except httpx.HTTPStatusError as e:
            return False, f"Pushover HTTP error: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Pushover request error: {e}"
        except Exception as e:
            logger.error(f"Pushover error: {e}")
            return False, str(e)

    @staticmethod
    async def _send_gotify(channel: Dict[str, Any], config: Dict[str, Any], alert_data: Dict[str, Any]) -> tuple[bool, str]:
        """Send push notification via Gotify"""
        try:
            server_url = config.get('server_url')
            app_token = config.get('app_token')

            if not server_url: return False, "Gotify server URL (server_url) is missing."
            if not app_token: return False, "Gotify application token (app_token) is missing."

            priority = 8 if alert_data['severity'] == 'critical' else 5

            template = channel.get('template')
            if template:
                try:
                    message_body = template.format(**alert_data)
                except KeyError as e:
                    return False, f"Template rendering failed: Missing variable {e}."
                except Exception as e:
                    return False, f"Template rendering failed: {e}"
            else:
                message_body = f"{alert_data['message']}\nValue: {alert_data['metric_value']}"

            payload = {
                'title': f"{alert_data['severity'].upper()}: {alert_data.get('server_name', 'Server')} Alert",
                'message': message_body,
                'priority': priority
            }

            url = f"{server_url.rstrip('/')}/message?token={app_token}"

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)

                if response.status_code == 200:
                    logger.info("Gotify notification sent successfully")
                    return True, "Notification sent successfully via Gotify."
                else:
                    error_detail = response.json().get("error", response.text) if response.content else response.text
                    logger.error(f"Gotify API error: {response.status_code} - {error_detail}")
                    return False, f"Gotify API error: {response.status_code} - {error_detail}"
        except httpx.HTTPStatusError as e:
            return False, f"Gotify HTTP error: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Gotify request error: {e}"
        except Exception as e:
            logger.error(f"Gotify error: {e}")
            return False, str(e)

    @staticmethod
    async def _send_webhook(channel: Dict[str, Any], config: Dict[str, Any], alert_data: Dict[str, Any]) -> tuple[bool, str]:
        """Send notification via generic webhook"""
        try:
            url = config.get('url')
            method = config.get('method', 'POST').upper()

            if not url: return False, "Webhook URL is missing."

            headers = {}
            if config.get('headers'):
                try:
                    headers = json.loads(config['headers'])
                except:
                    logger.warning("Failed to parse webhook headers JSON")
                    return False, "Failed to parse webhook headers. Ensure it is valid JSON."
            
            template = channel.get('template')
            if template:
                try:
                    templated_alert_data = alert_data.copy()
                    templated_alert_data['message'] = template.format(**alert_data) # Only template the message field for webhooks by default
                except KeyError as e:
                    return False, f"Template rendering failed: Missing variable {e}."
                except Exception as e:
                    return False, f"Template rendering failed: {e}"
            else:
                templated_alert_data = alert_data

            async with httpx.AsyncClient() as client:
                if method == 'POST':
                    response = await client.post(url, json=templated_alert_data, headers=headers)
                else:
                    response = await client.get(url, params=templated_alert_data, headers=headers)

                if response.status_code in [200, 201, 202, 204]:
                    logger.info("Webhook notification sent successfully")
                    return True, "Notification sent successfully via Webhook."
                else:
                    logger.error(f"Webhook error: {response.status_code} - {response.text}")
                    return False, f"Webhook error: {response.status_code} - {response.text}"
        except httpx.HTTPStatusError as e:
            return False, f"Webhook HTTP error: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Webhook request error: {e}"
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return False, str(e)
