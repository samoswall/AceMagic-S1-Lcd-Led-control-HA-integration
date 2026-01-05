"""Select entities for UART Time Sender."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
import logging

from .const import DOMAIN, THEME_OPTIONS, ORIENTATION_OPTIONS
from .coordinator import UARTTimeSenderCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UART Time Sender select entities."""
    coordinator: UARTTimeSenderCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        UARTTimeSenderThemeSelect(coordinator, entry),
        UARTTimeSenderOrientationSelect(coordinator, entry),
    ]
    
    async_add_entities(entities)


class UARTTimeSenderThemeSelect(SelectEntity):
    """Representation of UART Time Sender theme selection."""

    _attr_has_entity_name = True
    _attr_options = list(THEME_OPTIONS.values())
    _attr_icon = "mdi:palette"

    def __init__(
        self,
        coordinator: UARTTimeSenderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the select."""
        self.coordinator = coordinator
        self._entry = entry
#        self._attr_name = "Theme"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_theme"
        self.translation_key = "theme"
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
    def current_option(self) -> str | None:
        """Return current selected option."""
        theme_value = self.coordinator.theme
        return THEME_OPTIONS.get(theme_value)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Find the key for this option
        for key, value in THEME_OPTIONS.items():
            if value == option:
                self.coordinator.theme = key
                return
        
        _LOGGER.warning("Invalid theme option selected: %s", option)

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return {
            "hex_value": f"0x{self.coordinator.theme:02x}",
            "decimal_value": self.coordinator.theme,
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


class UARTTimeSenderOrientationSelect(SelectEntity):
    """Representation of UART Time Sender orientation selection."""

    _attr_has_entity_name = True
    _attr_options = list(ORIENTATION_OPTIONS.values())
    _attr_icon = "mdi:screen-rotation"

    def __init__(
        self,
        coordinator: UARTTimeSenderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the select."""
        self.coordinator = coordinator
        self._entry = entry
#        self._attr_name = "Orientation"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_orientation"
        self.translation_key = "orientation"
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
    def current_option(self) -> str | None:
        """Return current selected option."""
        orientation_value = self.coordinator.orientation
        return ORIENTATION_OPTIONS.get(orientation_value)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Теперь: 0x02=Landscape, 0x01=Portrait
        if option == ORIENTATION_OPTIONS[0x02]:  # "Landscape (170x320)"
            self.coordinator.orientation = 0x02
        elif option == ORIENTATION_OPTIONS[0x01]:  # "Portrait (320x170)"
            self.coordinator.orientation = 0x01
        else:
            _LOGGER.warning("Invalid orientation option selected: %s", option)

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return {
            "hex_value": f"0x{self.coordinator.orientation:02x}",
            "decimal_value": self.coordinator.orientation,
            "portrait_value": 0x00,
            "landscape_value": 0x01,
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