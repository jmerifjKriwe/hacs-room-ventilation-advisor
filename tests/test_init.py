"""Test the Room Ventilation Advisor integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.room_ventilation_advisor import (
    async_migrate_entry,
    async_setup_entry,
    async_unload_entry,
)


@pytest.mark.asyncio
async def test_async_setup_entry() -> None:
    """Test setting up the integration."""
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.data = {"name": "Test Advisor"}

    # Mock the forward_entry_setups method
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    # Mock device registry
    with patch("custom_components.room_ventilation_advisor.dr") as mock_dr:
        mock_device_registry = MagicMock()
        mock_dr.async_get.return_value = mock_device_registry

        result = await async_setup_entry(hass, config_entry)

        assert result is True
        hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            config_entry, ["sensor"],
        )
        mock_device_registry.async_get_or_create.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry() -> None:
    """Test unloading the integration."""
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"

    # Mock the unload_platforms method
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    # Mock device registry
    with patch("custom_components.room_ventilation_advisor.dr") as mock_dr:
        mock_device_registry = MagicMock()
        mock_device = MagicMock()
        mock_device.id = "test_device_id"

        mock_device_registry.async_get_device.return_value = mock_device
        mock_dr.async_get.return_value = mock_device_registry

        result = await async_unload_entry(hass, config_entry)

        assert result is True
        hass.config_entries.async_unload_platforms.assert_called_once_with(
            config_entry, ["sensor"],
        )
        mock_device_registry.async_remove_device.assert_called_once_with(
            "test_device_id",
        )


@pytest.mark.asyncio
async def test_async_migrate_entry() -> None:
    """Test migrating config entries."""
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.version = 1

    result = await async_migrate_entry(hass, config_entry)

    assert result is True


@pytest.mark.asyncio
async def test_async_migrate_entry_unknown_version() -> None:
    """Test migrating config entries with unknown version."""
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.version = 999

    result = await async_migrate_entry(hass, config_entry)

    assert result is False
