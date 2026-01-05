"""Sensor tracking for UART Time Sender text display."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change

from .const import DOMAIN
from .coordinator import UARTTimeSenderCoordinator
from .text_config import TextElement, text_renderer

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor tracking for UART Time Sender."""
    coordinator: UARTTimeSenderCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Get text configuration from configuration.yaml
    config = hass.data[DOMAIN].get("config", {})
    text_sensors_config = config.get("text_sensors", [])
    
    entities = []
    remove_listeners = []
    
    for sensor_config in text_sensors_config:
        entity_id = sensor_config.get("entity_id")
        if entity_id:
            # Create text element
            text_element = TextElement(
                entity_id=entity_id,
                x=sensor_config.get("x", 0),
                y=sensor_config.get("y", 0),
                font_size=sensor_config.get("font_size", 16),
                color=tuple(sensor_config.get("color", (255, 255, 255))),
                alignment=sensor_config.get("alignment", 0),
                prefix=sensor_config.get("prefix", ""),
                suffix=sensor_config.get("suffix", ""),
                format=sensor_config.get("format", "{value}")
            )
            
            text_renderer.add_text_element(text_element)
            
            # Track state changes
            def create_state_change_handler(entity_id, coordinator):
                @callback
                def handle_state_change(entity_id, old_state, new_state):
                    if new_state:
                        coordinator.update_sensor_state(entity_id, new_state.state)
                
                return handle_state_change
            
            listener = async_track_state_change(
                hass, entity_id, 
                create_state_change_handler(entity_id, coordinator)
            )
            remove_listeners.append(listener)
    
    # Store remove listeners
    hass.data[DOMAIN]["remove_listeners"] = remove_listeners
    
    # Add sensor entities for monitoring
    async_add_entities([TextSensorTracker(coordinator, entry)])


class TextSensorTracker(SensorEntity):
    """Tracker for text sensor states."""
    
    _attr_has_entity_name = True
    
    def __init__(self, coordinator: UARTTimeSenderCoordinator, entry: ConfigEntry):
        """Initialize."""
        self.coordinator = coordinator
        self._entry = entry
#        self._attr_name = "Text Sensors"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_text_tracker"
        self.translation_key = "text_sensors"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            manufacturer=coordinator.manufacturer,
            model=coordinator.model,
            name=coordinator.device_name,
            configuration_url=f"homeassistant://config/integrations/integration/{DOMAIN}",
        )
    
    @property
    def state(self) -> str:
        """Return state."""
        return str(len(text_renderer._text_elements))
    
    @property
    def extra_state_attributes(self):
        """Return attributes."""
        return {
            "tracked_sensors": list(text_renderer._text_elements.keys()),
            "sensor_count": len(text_renderer._text_elements)
        }
    
    @property
    def available(self) -> bool:
        """Return if available."""
        return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload sensor tracking."""
    # Remove state change listeners
    remove_listeners = hass.data[DOMAIN].get("remove_listeners", [])
    for remove_listener in remove_listeners:
        remove_listener()
    
    return True