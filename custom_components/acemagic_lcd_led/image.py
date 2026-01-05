"""Image entity for UART Time Sender."""

from __future__ import annotations

import io
import logging
from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util
from .const import get_display_size
from .const import (
    DOMAIN, 
    IMAGE_WIDTH, 
    IMAGE_HEIGHT,
    IMAGE_SIZE,
    Orientation
)
from .coordinator import UARTTimeSenderCoordinator, pil_image_to_rgb565

_LOGGER = logging.getLogger(__name__)


class UARTTimeSenderImage(ImageEntity):
    """Representation of UART Time Sender image display."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_content_type = "image/png"

    def __init__(
        self,
        coordinator: UARTTimeSenderCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the image entity."""
        super().__init__(coordinator.hass)
        
        self.coordinator = coordinator
        self._entry = entry
#        self._attr_name = "Display Image"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_image"
        self.translation_key = "display_image"
        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            manufacturer=coordinator.manufacturer,
            model=coordinator.model,
            name=coordinator.device_name,
            configuration_url=f"homeassistant://config/integrations/integration/{DOMAIN}",
        )
        
        # Track state
        self._last_image_hash = None
        self._current_orientation = coordinator.orientation
        self._current_width = 0
        self._current_height = 0
        
        # Create initial image from coordinator data
        self._update_image_from_coordinator()
        
        # Add to coordinator listeners
        coordinator.add_update_listener(self._handle_coordinator_update)
        
        _LOGGER.info("Image entity initialized")

    def _rgb565_to_pil_image(self, rgb565_data: bytes):
        """Convert RGB565 bytes to PIL Image."""
        try:
            from PIL import Image
            
            width, height = get_display_size(self.coordinator.orientation)
            orientation = self.coordinator.orientation
            
            expected_size = width * height * 2
            if len(rgb565_data) != expected_size:
                _LOGGER.warning("Invalid RGB565 data length: %d, expected: %d", 
                              len(rgb565_data), expected_size)
                return None
            
            # ВАЖНО: Обратное преобразование с учетом путаницы ориентаций
            if orientation == 0x01:  # Наш PORTRAIT (физически LANDSCAPE)
                # Данные пришли построчно
                rgb888_array = bytearray()
                
                for i in range(0, len(rgb565_data), 2):
                    if i + 1 < len(rgb565_data):
                        low = rgb565_data[i + 1]
                        high = rgb565_data[i]
                        color = (high << 8) | low
                        
                        r5 = (color >> 11) & 0x1F
                        g6 = (color >> 5) & 0x3F
                        b5 = color & 0x1F
                        
                        r = (r5 * 255) // 31
                        g = (g6 * 255) // 63
                        b = (b5 * 255) // 31
                        
                        rgb888_array.extend([r, g, b])
                
                img = Image.frombytes('RGB', (width, height), bytes(rgb888_array))
                
            else:  # orientation == 0x01 - Наш LANDSCAPE (физически PORTRAIT)
                # Данные пришли по столбцам справа налево
                temp_img = Image.new('RGB', (width, height), color=(0, 0, 0))
                pixels = temp_img.load()
                
                data_idx = 0
                for x in range(width - 1, -1, -1):
                    for y in range(height):
                        if data_idx + 1 < len(rgb565_data):
                            low = rgb565_data[data_idx + 1]
                            high = rgb565_data[data_idx]
                            color = (high << 8) | low
                            
                            r5 = (color >> 11) & 0x1F
                            g6 = (color >> 5) & 0x3F
                            b5 = color & 0x1F
                            
                            r = (r5 * 255) // 31
                            g = (g6 * 255) // 63
                            b = (b5 * 255) // 31
                            
                            pixels[x, y] = (r, g, b)
                            data_idx += 2
                
                # Поворачиваем для отображения в HA
                img = temp_img #.rotate(90, expand=True)
            
            return img
        except Exception as err:
            _LOGGER.error("Failed to convert RGB565 to image: %s", err)
            return None

    def _update_image_from_coordinator(self):
        """Update image from coordinator data."""
        try:
            import hashlib
            
            # Get current image data from coordinator
            image_data = self.coordinator.image_data
            
            if image_data is None or len(image_data) == 0:
                _LOGGER.warning("No image data in coordinator")
                return
            
            # Get current display size
            width, height = get_display_size(self.coordinator.orientation)
            
            # Create hash of current state
            hash_input = image_data + bytes([self.coordinator.orientation])
            new_hash = hashlib.md5(hash_input).hexdigest()
            
            # Check if image changed
            if (new_hash != self._last_image_hash or 
                self._current_orientation != self.coordinator.orientation or
                self._current_width != width or
                self._current_height != height):
                
                _LOGGER.debug("Image data or orientation changed, updating display")
                
                # Convert to PIL image
                pil_image = self._rgb565_to_pil_image(image_data)
                
                if pil_image is not None:
                    # Сохраняем текущие размеры
                    self._current_width, self._current_height = pil_image.size
                    
                    # Convert to PNG bytes
                    with io.BytesIO() as output:
                        pil_image.save(output, format="PNG", optimize=True)
                        self._attr_image_bytes = output.getvalue()
                    
                    self._attr_image_last_updated = dt_util.now()
                    self._last_image_hash = new_hash
                    self._current_orientation = self.coordinator.orientation
                    
                    _LOGGER.info("Image updated: %d bytes, size: %dx%d, orientation: %d", 
                                len(self._attr_image_bytes), 
                                self._current_width, self._current_height,
                                self.coordinator.orientation)
                else:
                    _LOGGER.warning("Failed to create image from RGB565 data")
            
        except Exception as err:
            _LOGGER.error("Failed to update image from coordinator: %s", err)

    @callback
    def _handle_coordinator_update(self):
        """Handle coordinator updates."""
        self._update_image_from_coordinator()
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        return self._attr_image_bytes

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        
        # Initial update
        self._update_image_from_coordinator()
        
        # Listen for coordinator updates
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        
        _LOGGER.info("Image entity added to hass: %s", self.entity_id)

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        data = self.coordinator.data or {}
        image_settings = data.get("image_settings", {})
        
        # Получаем реальные размеры дисплея
        real_width, real_height = get_display_size(self.coordinator.orientation)
        
        # Используем правильные названия ориентаций
        orientation_name = "Portrait" if self.coordinator.orientation == Orientation.PORTRAIT.value else "Landscape"
        
        attrs = {
            "display_width": real_width,
            "display_height": real_height,
            "image_width": self._current_width,
            "image_height": self._current_height,
            "orientation": self.coordinator.orientation,
            "orientation_name": orientation_name,
            "format": "RGB565",
            "update_pending": image_settings.get("update_pending", False),
            "content_type": self._attr_content_type,
        }
        
        if self.coordinator._last_send_time:
            attrs["last_send"] = self.coordinator._last_send_time.isoformat()
            
        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UART Time Sender image."""
    coordinator: UARTTimeSenderCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entity = UARTTimeSenderImage(coordinator, entry)
    async_add_entities([entity])
    
    _LOGGER.debug("Image entity setup for entry: %s", entry.entry_id)