"""Number entities for UART Time Sender."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
import logging

from .const import (
    DOMAIN, 
    MIN_INTENSITY, 
    MAX_INTENSITY, 
    MIN_SPEED, 
    MAX_SPEED
)
from .coordinator import UARTTimeSenderCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UART Time Sender numbers."""
    coordinator: UARTTimeSenderCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        UARTTimeSenderIntensityNumber(coordinator, entry),
        UARTTimeSenderSpeedNumber(coordinator, entry),
    ]
    
    async_add_entities(entities)


class UARTTimeSenderIntensityNumber(NumberEntity):
    """Representation of UART Time Sender intensity control."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = MIN_INTENSITY
    _attr_native_max_value = MAX_INTENSITY
    _attr_native_step = 1
    _attr_icon = "mdi:brightness-6"

    def __init__(
        self,
        coordinator: UARTTimeSenderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number."""
        self.coordinator = coordinator
        self._entry = entry
#        self._attr_name = "Intensity"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_intensity"
        self.translation_key = "intensity"
        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            manufacturer=coordinator.manufacturer,
            model=coordinator.model,
            name=coordinator.device_name,
            configuration_url=f"homeassistant://config/integrations/integration/{DOMAIN}",
        )
        
        # Add to coordinator listeners
        coordinator.add_update_listener(self._handle_coordinator_update)

    @callback
    def _handle_coordinator_update(self):
        """Handle coordinator updates."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return current intensity."""
        return float(self.coordinator.intensity)

    async def async_set_native_value(self, value: float) -> None:
        """Set new intensity value."""
        int_value = int(value)
        if MIN_INTENSITY <= int_value <= MAX_INTENSITY:
            self.coordinator.intensity = int_value

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return {
            "min": MIN_INTENSITY,
            "max": MAX_INTENSITY,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies us."""
        return False

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
        # Also remove from coordinator's update listeners
        self.async_on_remove(
            lambda: self.coordinator.remove_update_listener(self._handle_coordinator_update)
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        self.coordinator.remove_update_listener(self._handle_coordinator_update)
        await super().async_will_remove_from_hass()


class UARTTimeSenderSpeedNumber(NumberEntity):
    """Representation of UART Time Sender speed control."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = MIN_SPEED
    _attr_native_max_value = MAX_SPEED
    _attr_native_step = 1
    _attr_icon = "mdi:speedometer"

    def __init__(
        self,
        coordinator: UARTTimeSenderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number."""
        self.coordinator = coordinator
        self._entry = entry
#        self._attr_name = "Speed"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_speed"
        self.translation_key = "speed"
        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            manufacturer=coordinator.manufacturer,
            model=coordinator.model,
            name=coordinator.device_name,
            configuration_url=f"homeassistant://config/integrations/integration/{DOMAIN}",
        )
        
        # Add to coordinator listeners
        coordinator.add_update_listener(self._handle_coordinator_update)

    @callback
    def _handle_coordinator_update(self):
        """Handle coordinator updates."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return current speed."""
        return float(self.coordinator.speed)

    async def async_set_native_value(self, value: float) -> None:
        """Set new speed value."""
        int_value = int(value)
        if MIN_SPEED <= int_value <= MAX_SPEED:
            self.coordinator.speed = int_value

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return {
            "min": MIN_SPEED,
            "max": MAX_SPEED,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies us."""
        return False

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
        # Also remove from coordinator's update listeners
        self.async_on_remove(
            lambda: self.coordinator.remove_update_listener(self._handle_coordinator_update)
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        self.coordinator.remove_update_listener(self._handle_coordinator_update)
        await super().async_will_remove_from_hass()