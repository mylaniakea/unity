"""
Tests for notification system.
"""
import pytest
from app.services.notifications import NotificationService
from app.models.notifications import NotificationChannel


@pytest.fixture
def notification_service(test_db):
    """Create notification service with test database."""
    return NotificationService(test_db)


def test_get_supported_services():
    """Test getting list of supported services."""
    services = NotificationService.get_supported_services()
    
    assert len(services) > 0
    assert any(s["type"] == "email" for s in services)
    assert any(s["type"] == "slack" for s in services)
    assert any(s["type"] == "discord" for s in services)


def test_create_channel(notification_service):
    """Test creating a notification channel."""
    channel = notification_service.create_channel(
        name="Test Email",
        apprise_url="mailto://user:pass@example.com",
        service_type="email",
        description="Test email channel"
    )
    
    assert channel.id is not None
    assert channel.name == "Test Email"
    assert channel.service_type == "email"
    assert channel.is_active is True
    assert channel.success_count == 0
    assert channel.failure_count == 0


def test_get_channels(notification_service):
    """Test getting notification channels."""
    # Create test channels
    notification_service.create_channel(
        name="Test Channel 1",
        apprise_url="json://example.com/webhook",
        service_type="webhook"
    )
    
    notification_service.create_channel(
        name="Test Channel 2",
        apprise_url="slack://token/channel",
        service_type="slack",
        is_active=False
    )
    
    # Get active channels only
    active_channels = notification_service.get_channels(active_only=True)
    assert len(active_channels) == 1
    assert active_channels[0].name == "Test Channel 1"
    
    # Get all channels
    all_channels = notification_service.get_channels(active_only=False)
    assert len(all_channels) == 2


def test_update_channel(notification_service):
    """Test updating a notification channel."""
    channel = notification_service.create_channel(
        name="Original Name",
        apprise_url="json://example.com/webhook",
        service_type="webhook"
    )
    
    updated = notification_service.update_channel(
        str(channel.id),
        name="Updated Name",
        is_active=False
    )
    
    assert updated.name == "Updated Name"
    assert updated.is_active is False
    assert updated.service_type == "webhook"  # Unchanged


def test_delete_channel(notification_service):
    """Test deleting a notification channel."""
    channel = notification_service.create_channel(
        name="To Delete",
        apprise_url="json://example.com/webhook",
        service_type="webhook"
    )
    
    success = notification_service.delete_channel(str(channel.id))
    assert success is True
    
    # Verify it's gone
    deleted = notification_service.get_channel_by_id(str(channel.id))
    assert deleted is None


@pytest.mark.asyncio
async def test_send_notification_no_channels(notification_service):
    """Test sending notification when no channels configured."""
    result = await notification_service.send_notification(
        title="Test",
        body="Test message"
    )
    
    assert result["success"] is False
    assert "No active notification channels" in result["message"]


@pytest.mark.asyncio
async def test_send_notification_with_invalid_channel(notification_service):
    """Test sending notification with invalid channel (will fail but not crash)."""
    # Create channel with invalid URL (will fail to send)
    channel = notification_service.create_channel(
        name="Invalid Channel",
        apprise_url="invalid://url",
        service_type="custom"
    )
    
    result = await notification_service.send_notification(
        title="Test Notification",
        body="This should fail",
        channel_ids=[str(channel.id)]
    )
    
    # Should not crash, but mark as failed
    assert "results" in result
    assert len(result["results"]) == 1
    assert result["results"][0]["success"] is False
