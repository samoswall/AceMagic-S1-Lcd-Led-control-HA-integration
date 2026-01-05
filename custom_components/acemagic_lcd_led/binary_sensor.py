"""Binary sensor for UART Time Sender."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
import logging

from .const import DOMAIN
from .coordinator import UARTTimeSenderCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UART Time Sender binary sensor."""
    coordinator: UARTTimeSenderCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([UARTTimeSenderConnectionSensor(coordinator, entry)])


class UARTTimeSenderConnectionSensor(BinarySensorEntity):
    """Representation of UART Time Sender connection status."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: UARTTimeSenderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self._entry = entry
#        self._attr_name = "Connection"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_connection"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:connection"
        self.translation_key = "connection"
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
    def is_on(self) -> bool:
        """Return true if both connections (serial and USB) are established."""
        data = self.coordinator.data or {}
        
        # Check both connections
        serial_connected = data.get("serial_connected", False)
        usb_connected = data.get("usb_connected", False)
        
        # Return True only if both connections are established
        # You can change this logic based on your needs:
        # - For partial connection (at least one connected): return serial_connected or usb_connected
        # - For full connection (both connected): return serial_connected and usb_connected
        
        # Using "at least one connected" logic
        return serial_connected or usb_connected

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        data = self.coordinator.data or {}
        
        # Clean port string
        port_display = self._entry.data["port"]
        port_clean = port_display.split(" ")[0] if isinstance(port_display, str) else port_display
        
        attributes = {
            "port": port_clean,
            "port_name": port_display,
            "baudrate": self._entry.data.get("baudrate", 9600),
            "status": data.get("status", "unknown"),
            "serial_connected": data.get("serial_connected", False),
            "usb_connected": data.get("usb_connected", False),
            "last_send": data.get("last_send"),
        }
        
        # Add control settings
        control_settings = data.get("control_settings", {})
        if control_settings:
            attributes.update({
                "theme": control_settings.get("theme"),
                "theme_name": control_settings.get("theme_name"),
                "intensity": control_settings.get("intensity"),
                "speed": control_settings.get("speed")
            })
        
        if "error" in data:
            attributes["error"] = data["error"]
            
        if data.get("last_send"):
            attributes["last_send"] = data["last_send"].isoformat()
            
        return attributes

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