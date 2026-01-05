"""Coordinator for UART Time Sender."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
import time
from typing import Any, Dict
import os

import serial_asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, 
    SIGNATURE_CONTROL,
    DEFAULT_THEME, 
    DEFAULT_INTENSITY, 
    DEFAULT_SPEED,
    DEFAULT_ORIENTATION,
    DEFAULT_BACKGROUND_COLOR,
    THEME_OPTIONS,
    ORIENTATION_OPTIONS,
    MANUFACTURER,
    MODEL,
    DEVICE_NAME,
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
    IMAGE_SIZE,
    Orientation,
    get_display_size
)
from .text_config import text_renderer
from .usb_manager import USBManager

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


def rgb888_to_rgb565(r: int, g: int, b: int) -> bytes:
    """Convert RGB888 to RGB565 bytes with endian swap."""
    # RGB565: RRRRR GGGGGG BBBBB
    r5 = (r >> 3) & 0x1F
    g6 = (g >> 2) & 0x3F
    b5 = (b >> 3) & 0x1F
    
    # Combine to 16-bit
    color = (r5 << 11) | (g6 << 5) | b5
    color_swapped = ((color & 0xFF) << 8) | ((color >> 8) & 0xFF)
    
    return color_swapped.to_bytes(2, 'big')


def pil_image_to_rgb565(pil_image, width=None, height=None, orientation=None):
    """Convert PIL Image to RGB565 bytes with orientation support."""
    from PIL import Image
    
    if width is None:
        width = pil_image.width
    if height is None:
        height = pil_image.height
    
    # Ensure correct size and mode
    if pil_image.size != (width, height):
        pil_image = pil_image.resize((width, height), Image.Resampling.LANCZOS)
    
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    
    pixels = pil_image.load()
    rgb565_data = bytearray()
    
    if orientation == Orientation.PORTRAIT.value:
        # Для портретной ориентации - столбцы справа налево
        for x in range(width - 1, -1, -1):
            for y in range(height):
                r, g, b = pixels[x, y]
                
                # RGB565 conversion
                r5 = (r >> 3) & 0x1F
                g6 = (g >> 2) & 0x3F
                b5 = (b >> 3) & 0x1F
                
                color = (r5 << 11) | (g6 << 5) | b5
                
                # Маленький эндиан
                rgb565_data.append((color >> 8) & 0xFF)
                rgb565_data.append(color & 0xFF)
                
    else:
        # Для альбомной ориентации - строки слева направо
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                
                # RGB565 conversion
                r5 = (r >> 3) & 0x1F
                g6 = (g >> 2) & 0x3F
                b5 = (b >> 3) & 0x1F
                
                color = (r5 << 11) | (g6 << 5) | b5
                
                # Маленький эндиан
                rgb565_data.append((color >> 8) & 0xFF)
                rgb565_data.append(color & 0xFF)
                
    
    return bytes(rgb565_data)


def create_default_image() -> bytes:
    """Create default black image in RGB565 format."""
    # Black color in RGB565: 0x0000
    black_pixel = b'\x00\x00'
    return black_pixel * (IMAGE_WIDTH * IMAGE_HEIGHT)


class UARTTimeSenderCoordinator(DataUpdateCoordinator):
    """Coordinator to manage UART data sending."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),
        )
        
        self._entry = entry
        self._serial_writer = None
        self._usb_manager = USBManager()
        self._port = entry.data["port"]
        self._connection_established = False
        self._last_send_time = None
        
        # Device settings
        self._theme = DEFAULT_THEME
        self._intensity = DEFAULT_INTENSITY
        self._speed = DEFAULT_SPEED
        
        # Set saved orientation from config
        saved_orientation = text_renderer.get_orientation()
        if saved_orientation in [Orientation.PORTRAIT.value, Orientation.LANDSCAPE.value]:
            self._orientation = saved_orientation
        else:
            self._orientation = DEFAULT_ORIENTATION
        
        # Image data
        self._image_data = create_default_image()
        self._image_update_pending = False
        self._image_needs_update = True
        
        # Sensor states
        self._sensor_states: Dict[str, Any] = {}
        
        # Device info
        self.device_id = f"{DOMAIN}_{entry.entry_id}"
        self.device_name = DEVICE_NAME
        self.manufacturer = MANUFACTURER
        self.model = MODEL
        
        # Listeners
        self._update_listeners = []
        
        # Flags
        self._initial_image_sent = False
        self._is_sending_image = False  # Флаг отправки изображения
        
        # Keepalive task
        self._keepalive_task = None
        
    @property
    def display_width(self) -> int:
        """Get display width based on orientation."""
        width, _ = get_display_size(self._orientation)
        return width
    
    @property
    def display_height(self) -> int:
        """Get display height based on orientation."""
        _, height = get_display_size(self._orientation)
        return height

    def add_update_listener(self, listener):
        """Add listener for settings updates."""
        self._update_listeners.append(listener)

    def remove_update_listener(self, listener):
        """Remove listener."""
        if listener in self._update_listeners:
            self._update_listeners.remove(listener)

    @callback
    def async_notify_listeners(self):
        """Notify all listeners about settings changes."""
        for listener in self._update_listeners:
            listener()

    @property
    def theme(self) -> int:
        """Get current theme."""
        return self._theme

    @theme.setter
    def theme(self, value: int):
        """Set theme and send update."""
        if self._theme != value:
            self._theme = value
            self.async_notify_listeners()
            asyncio.create_task(self._send_control_packet())

    @property
    def intensity(self) -> int:
        """Get current intensity."""
        return self._intensity

    @intensity.setter
    def intensity(self, value: int):
        """Set intensity and send update."""
        if self._intensity != value:
            self._intensity = value
            self.async_notify_listeners()
            asyncio.create_task(self._send_control_packet())

    @property
    def speed(self) -> int:
        """Get current speed."""
        return self._speed

    @speed.setter
    def speed(self, value: int):
        """Set speed and send update."""
        if self._speed != value:
            self._speed = value
            self.async_notify_listeners()
            asyncio.create_task(self._send_control_packet())

    @property
    def orientation(self) -> int:
        """Get current orientation."""
        return self._orientation

    @orientation.setter
    def orientation(self, value: int):
        """Set orientation and send update."""
        if self._orientation != value:
            self._orientation = value
            text_renderer.set_orientation(value)
            self.async_notify_listeners()
            asyncio.create_task(self._send_orientation_packet())
            self._image_needs_update = True
            self._update_display_image()

    @property
    def image_data(self) -> bytes:
        """Get current image data in RGB565 format."""
        return self._image_data

    @image_data.setter
    def image_data(self, value: bytes):
        """Set image data in RGB565 format and send update."""
        expected_size = self.display_width * self.display_height * 2
        
        if len(value) == expected_size and value != self._image_data:
            self._image_data = value
            self._image_update_pending = True
            self.async_notify_listeners()
            asyncio.create_task(self._send_image_packet())

    def set_pixel(self, x: int, y: int, r: int, g: int, b: int):
        """Set single pixel color with orientation support."""
        # ВАЖНО: Координаты x, y всегда задаются для landscape ориентации
        # Нужно преобразовать их в координаты текущей ориентации
        
        # Получаем текущие размеры
        width = self.display_width
        height = self.display_height
        
        # Определяем целевые координаты в зависимости от ориентации
        if self._orientation == Orientation.PORTRAIT.value:
            # Для портретной ориентации:
            # x_landscape -> (width - 1 - y_portrait)
            # y_landscape -> x_portrait
            target_x = y
            target_y = x
        else:
            # Для альбомной ориентации - координаты без изменений
            target_x = x
            target_y = y
        
        if 0 <= target_x < width and 0 <= target_y < height:
            # Создаем новое изображение и устанавливаем пиксель
            from PIL import Image, ImageDraw
            
            # Создаем изображение правильного размера
            img = Image.new('RGB', (width, height), color=(0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Устанавливаем пиксель
            draw.point((target_x, target_y), fill=(r, g, b))
            
            # Добавляем текст если есть
            if text_renderer._text_elements:
                img = text_renderer.render_text_on_image(img, self._orientation)
            
            # Форматируем для устройства
            rgb565_data = self._format_image_for_device(img, self._orientation)
            self.image_data = rgb565_data

    def fill_image(self, r: int, g: int, b: int):
        """Fill entire image with one color."""
        from PIL import Image
        
        # Get actual display size
        width = self.display_width
        height = self.display_height
        
        # Create solid color image
        img = Image.new('RGB', (width, height), color=(r, g, b))
        
        # Add text if configured
        if text_renderer._text_elements:
            img = text_renderer.render_text_on_image(
                img, 
                self._orientation
            )
        
        # Convert to RGB565 and update
        rgb565_data = pil_image_to_rgb565(img, width, height, self._orientation)
        self.image_data = rgb565_data

    def create_test_pattern(self):
        """Create test pattern image."""
        from PIL import Image, ImageDraw
        
        # Get actual display size
        width = self.display_width
        height = self.display_height
        
        # Create gradient image
        img = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(img)
        
        for y in range(height):
            for x in range(width):
                # Create gradient pattern
                r = (x * 255) // width
                g = (y * 255) // height
                b = 128
                draw.point((x, y), fill=(r, g, b))
        
        # Add text if configured
        if text_renderer._text_elements:
            img = text_renderer.render_text_on_image(
                img, 
                self._orientation
            )
        
        # Convert to RGB565 and update
        rgb565_data = pil_image_to_rgb565(img, width, height, self._orientation)
        self.image_data = rgb565_data
        
    def update_sensor_state(self, entity_id: str, state: Any):
        """Update sensor state for text rendering."""
        _LOGGER.debug("Updating sensor %s: %s", entity_id, state)
        text_renderer.update_sensor_value(entity_id, state)
        self._sensor_states[entity_id] = state
        self._image_needs_update = True
        self._update_display_image()

    def _update_display_image(self):
        """Update the display image with current text and settings."""
        try:
            from PIL import Image
            
            _LOGGER.debug("Updating display image with orientation: %d", self._orientation)
            
            width = self.display_width
            height = self.display_height
            
            # Получаем фоновое изображение для текущей ориентации
            bg_path = text_renderer.get_background_image_path(self._orientation)
            
            # Создаем базовое изображение
            if bg_path and os.path.exists(bg_path):
                bg_image = Image.open(bg_path)
                
                if bg_image.mode != 'RGB':
                    bg_image = bg_image.convert('RGB')
                
                if bg_image.size != (width, height):
                    bg_image = bg_image.resize((width, height), Image.Resampling.LANCZOS)
                
                base_img = bg_image.copy()
                _LOGGER.debug("Using background image for orientation %d: %s", 
                             self._orientation, bg_path)
            else:
                base_img = Image.new('RGB', (width, height), 
                                   color=DEFAULT_BACKGROUND_COLOR)
                _LOGGER.debug("No background image for orientation %d, using black", 
                             self._orientation)
            
            # Рендерим текст
            if text_renderer._text_elements:
                img = text_renderer.render_text_on_image(base_img, self._orientation)
            else:
                img = base_img
            
            # Convert to RGB565
            rgb565_data = pil_image_to_rgb565(img, width, height, self._orientation)
            
            # Update image data
            self._image_data = rgb565_data
            self._image_update_pending = True
            self._image_needs_update = False
            
            _LOGGER.debug("Display image updated: %d bytes, orientation: %d", 
                         len(self._image_data), self._orientation)
            
            # Schedule send to device
            if not self._is_sending_image:
                asyncio.create_task(self._send_image_packet())
            else:
                _LOGGER.debug("Image sending in progress, will send later")
                self._image_update_pending = True
            
        except Exception as err:
            _LOGGER.error("Failed to update display image: %s", err)
    
    def _format_image_for_device(self, pil_image: Image.Image, orientation: int) -> bytes:
        """Format PIL image for device with correct orientation."""
        from PIL import Image
        
        width = self.display_width
        height = self.display_height
        
        if pil_image.size != (width, height):
            pil_image = pil_image.resize((width, height), Image.Resampling.LANCZOS)
        
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        pixels = pil_image.load()
        
        # ВАЖНО: Меняем местами обработку ориентаций
        if orientation == 0x01:  # То, что мы называем PORTRAIT
            # На самом деле это LANDSCAPE для дисплея
            # Отправляем построчно как для landscape
            rgb565_data = bytearray()
            
            for y in range(height):
                for x in range(width):
                    r, g, b = pixels[x, y]
                    
                    r5 = (r >> 3) & 0x1F
                    g6 = (g >> 2) & 0x3F
                    b5 = (b >> 3) & 0x1F
                    
                    color = (r5 << 11) | (g6 << 5) | b5
                    
                    rgb565_data.append((color >> 8) & 0xFF)
                    rgb565_data.append(color & 0xFF)
            
        else:  # orientation == 0x01 - То, что мы называем LANDSCAPE
            # На самом деле это PORTRAIT для дисплея
            # Отправляем по столбцам справа налево как для portrait
            rgb565_data = bytearray()
            
            for x in range(width - 1, -1, -1):
                for y in range(height):
                    r, g, b = pixels[x, y]
                    
                    r5 = (r >> 3) & 0x1F
                    g6 = (g >> 2) & 0x3F
                    b5 = (b >> 3) & 0x1F
                    
                    color = (r5 << 11) | (g6 << 5) | b5
                    
                    rgb565_data.append((color >> 8) & 0xFF)
                    rgb565_data.append(color & 0xFF)
        
        return bytes(rgb565_data)

    async def _async_setup_serial_connection(self) -> bool:
        """Set up serial connection for LED control."""
        try:
            port = self._port.split(" ")[0]
            
            _, self._serial_writer = await serial_asyncio.open_serial_connection(
                url=port,
                baudrate=9600,
                timeout=1
            )
            
            _LOGGER.info("Serial connection established to %s", port)
            await self._send_control_packet()
            
            return True
            
        except Exception as err:
            _LOGGER.error("Failed to establish serial connection: %s", err)
            self._serial_writer = None
            return False
    
    async def _async_setup_usb_connection(self) -> bool:
        """Set up USB connection for display."""
        try:
            success = await self._usb_manager.connect()
            if success:
                # Start keepalive task
                if not self._keepalive_task:
                    self._keepalive_task = asyncio.create_task(self._keepalive_loop())
                
                _LOGGER.info("USB connection established")
                return True
            return False
                
        except Exception as err:
            _LOGGER.error("Failed to establish USB connection: %s", err)
            return False

    async def _send_orientation_packet(self) -> None:
        """Send orientation packet to USB device."""
        if not self._usb_manager.is_connected:
            await self._async_setup_usb_connection()
        
        if self._usb_manager.is_connected:
            await self._usb_manager.send_orientation_packet(self._orientation)
            _LOGGER.debug("Orientation packet sent: %s", self._orientation)

    async def _send_control_packet(self) -> None:
        """Send control packet to serial device."""
        if not self._serial_writer:
            await self._async_setup_serial_connection()
        
        if self._serial_writer:
            try:
                total = SIGNATURE_CONTROL + self._theme + self._intensity + self._speed
                checksum = total & 0xFF
                
                data = bytes([
                    SIGNATURE_CONTROL,
                    self._theme,
                    self._intensity,
                    self._speed,
                    checksum
                ])
                
                self._serial_writer.write(data)
                await self._serial_writer.drain()
                
                self._last_send_time = dt_util.now()
                _LOGGER.debug("Control packet sent")
                
            except Exception as err:
                _LOGGER.error("Failed to send control packet: %s", err)
                self._serial_writer = None

    async def _send_image_packet(self) -> None:
        """Send image packet to USB device."""
        if self._is_sending_image:
            _LOGGER.debug("Image sending already in progress, skipping")
            return
        
        self._is_sending_image = True
        try:
            await self._send_image_packet_internal()
        finally:
            self._is_sending_image = False
    
    async def _send_image_packet_internal(self) -> None:
        """Internal method to send image packet."""
        # Don't send if no update pending
        if not self._image_update_pending:
            _LOGGER.debug("No image update pending")
            return
        
        if not self._usb_manager.is_connected:
            success = await self._async_setup_usb_connection()
            if not success:
                return
        
        try:
            _LOGGER.info("Sending image packet: %d bytes", len(self._image_data))
            success = await self._usb_manager.send_image_packet(self._image_data)
            
            if success:
                self._last_send_time = dt_util.now()
                self._image_update_pending = False
                _LOGGER.info("Image packet sent successfully")
            else:
                _LOGGER.error("Failed to send image packet")
                
        except Exception as err:
            _LOGGER.error("Failed to send image packet: %s", err)

    async def _keepalive_loop(self):
        """Send keepalive packets every 1 seconds."""
        _LOGGER.info("Starting keepalive loop")
        
        while True:
            try:
                await asyncio.sleep(1)
                
                if self._usb_manager.is_connected:
                    await self._usb_manager.send_keepalive_packet()
                    _LOGGER.debug("Keepalive packet sent")
                
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Error in keepalive loop: %s", err)
                await asyncio.sleep(5)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update connection status."""
        # Check if image needs update
        if self._image_needs_update:
            self._update_display_image()
        
        try:
            serial_connected = self._serial_writer is not None
            usb_connected = self._usb_manager.is_connected
            
            status = "connected" if (serial_connected and usb_connected) else "partial"
            
            return {
                "status": status,
                "last_send": self._last_send_time,
                "serial_connected": serial_connected,
                "usb_connected": usb_connected,
                "control_settings": {
                    "theme": self._theme,
                    "theme_name": THEME_OPTIONS.get(self._theme, "Unknown"),
                    "intensity": self._intensity,
                    "speed": self._speed
                }
            }
            
        except Exception as err:
            _LOGGER.error("Connection check failed: %s", err)
            return {
                "status": "error", 
                "last_send": self._last_send_time, 
                "error": str(err)
            }

    async def async_config_entry_first_refresh(self):
        """First refresh after setup."""
        await self.async_refresh()
        
        # Initialize sensor states
        await self._initialize_sensor_states()
        
        # Initial image send
        self._image_update_pending = True
        asyncio.create_task(self._send_image_packet())
        
        _LOGGER.info("Startup complete")
    
    async def _initialize_sensor_states(self):
        """Initialize sensor states from Home Assistant."""
        try:
            required_entities = text_renderer.get_required_entities()
            
            for entity_id in required_entities:
                state = self.hass.states.get(entity_id)
                if state:
                    text_renderer.update_sensor_value(entity_id, state.state)
                    self._sensor_states[entity_id] = state.state
                else:
                    text_renderer.update_sensor_value(entity_id, "N/A")
                    self._sensor_states[entity_id] = "N/A"
            
            # Update display image
            self._image_needs_update = True
            self._update_display_image()
            
        except Exception as err:
            _LOGGER.error("Failed to initialize sensor states: %s", err)

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        # Cancel keepalive task
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
        
        # Close USB connection
        await self._usb_manager.disconnect()
        
        # Close serial connection
        if self._serial_writer:
            try:
                self._serial_writer.close()
                await self._serial_writer.wait_closed()
            except Exception:
                pass
        
        _LOGGER.info("Connections closed")