"""The UART Time Sender integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .coordinator import UARTTimeSenderCoordinator
from .services import async_setup_services
from .text_config import text_renderer

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the UART Time Sender component."""
    hass.data.setdefault(DOMAIN, {})
    
    # Store configuration
    hass.data[DOMAIN]["config"] = config.get(DOMAIN, {})
    
    # Setup services
    await async_setup_services(hass)
    
    # Setup sensor tracking
    await async_setup_sensor_tracking(hass)
    
    return True


async def async_setup_sensor_tracking(hass: HomeAssistant):
    """Set up sensor state tracking for text display."""
    
    @callback
    def handle_state_change(event):
        """Handle state change for tracked entities."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        
        if new_state and entity_id in text_renderer.get_required_entities():
            _LOGGER.debug("Sensor %s changed: %s", entity_id, new_state.state)
            
            # Update on all coordinators
            for entry_id in hass.data[DOMAIN]:
                if isinstance(hass.data[DOMAIN][entry_id], UARTTimeSenderCoordinator):
                    coordinator = hass.data[DOMAIN][entry_id]
                    coordinator.update_sensor_state(entity_id, new_state.state)
    
    # Listen for state changes of tracked entities
    hass.bus.async_listen("state_changed", handle_state_change)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UART Time Sender from a config entry."""
    
    # Create coordinator
    coordinator = UARTTimeSenderCoordinator(hass, entry)
    
    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Start the coordinator
    await coordinator.async_config_entry_first_refresh()
    
    # Setup all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Force initial image update with text
    await coordinator._initialize_sensor_states()
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Stop coordinator
        if entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN].pop(entry.entry_id)
            await coordinator.async_shutdown()
    
    return unload_ok