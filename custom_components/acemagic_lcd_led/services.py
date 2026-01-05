"""Services for UART Time Sender."""

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import logging, os
from typing import Any

from .const import (
    DOMAIN, 
    IMAGE_WIDTH, 
    IMAGE_HEIGHT,
    TextAlignment,
    Orientation
)
from .text_config import TextElement, text_renderer
from .coordinator import UARTTimeSenderCoordinator
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

# services
SERVICE_FILL_IMAGE = "fill_image"
SERVICE_SET_PIXEL = "set_pixel"
SERVICE_TEST_PATTERN = "test_pattern"
SERVICE_CLEAR_IMAGE = "clear_image"
SERVICE_LOAD_BACKGROUND = "load_background_image"

# text services
SERVICE_ADD_TEXT = "add_text"
SERVICE_UPDATE_TEXT = "update_text"
SERVICE_REMOVE_TEXT = "remove_text"
SERVICE_CLEAR_ALL_TEXT = "clear_all_text"

STATIC_TEXT_PREFIX = "static:"
STATIC_TEXT_MARKERS = ["static", "none", "text:"]

# Service schemas
FILL_IMAGE_SCHEMA = vol.Schema({
    vol.Optional("background_color", default=[255, 0, 0]): vol.All(
        list, vol.Length(min=3, max=3),
        [vol.All(vol.Coerce(int), vol.Range(min=0, max=255))]
    ),
})

SET_PIXEL_SCHEMA = vol.Schema({
    vol.Required("x"): vol.All(vol.Coerce(int), vol.Range(min=0, max=IMAGE_WIDTH-1)),
    vol.Required("y"): vol.All(vol.Coerce(int), vol.Range(min=0, max=IMAGE_HEIGHT-1)),
    vol.Optional("pixel_color", default=[255, 0, 0]): vol.All(
        list, vol.Length(min=3, max=3),
        [vol.All(vol.Coerce(int), vol.Range(min=0, max=255))]
    ),
})

LOAD_BACKGROUND_SCHEMA = vol.Schema({
    vol.Optional("file_path_landscape", default="/config/custom_components/uart_time_sender/AceMagic_LANDSCAPE.png"): cv.string,
    vol.Optional("file_path_portrait", default="/config/custom_components/uart_time_sender/AceMagic_PORTRAIT.png"): cv.string,
    vol.Optional("keep_text", default=True): cv.boolean,
    vol.Optional("resize_mode", default="cover"): vol.In(["cover", "contain", "stretch", "center"]),
    vol.Optional("background_color", default=[0, 0, 0]): vol.All(
        list, vol.Length(min=3, max=3),
        [vol.All(vol.Coerce(int), vol.Range(min=0, max=255))]
    ),
})

TEST_PATTERN_SCHEMA = vol.Schema({})
CLEAR_IMAGE_SCHEMA = vol.Schema({})

ADD_TEXT_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.string,  # Меняем с entity_id на string
    vol.Optional("value", default=""): cv.string,  # Добавляем поле для статичного значения
    vol.Required("x"): vol.All(vol.Coerce(int), vol.Range(min=0, max=IMAGE_WIDTH-1)),
    vol.Required("y"): vol.All(vol.Coerce(int), vol.Range(min=0, max=IMAGE_HEIGHT-1)),
    vol.Optional("font_size", default=16): vol.All(vol.Coerce(int), vol.Range(min=8, max=72)),
    vol.Optional("color", default=[255, 255, 255]): vol.All(
        list, vol.Length(min=3, max=3),
        [vol.All(vol.Coerce(int), vol.Range(min=0, max=255))]
    ),
    vol.Optional("alignment", default="0"): vol.In(["0", "1", "2"]),
    vol.Optional("prefix", default=""): cv.string,
    vol.Optional("suffix", default=""): cv.string,
    vol.Optional("format", default="{value}"): cv.string,
    vol.Optional("font_path", default=""): cv.string,
})

UPDATE_TEXT_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.string,  # Меняем с entity_id на string
    vol.Optional("x"): vol.All(vol.Coerce(int), vol.Range(min=0, max=IMAGE_WIDTH-1)),
    vol.Optional("y"): vol.All(vol.Coerce(int), vol.Range(min=0, max=IMAGE_HEIGHT-1)),
    vol.Optional("font_size"): vol.All(vol.Coerce(int), vol.Range(min=8, max=72)),
    vol.Optional("color"): vol.All(
        list, vol.Length(min=3, max=3),
        [vol.All(vol.Coerce(int), vol.Range(min=0, max=255))]
    ),
    vol.Optional("alignment"): vol.In(["0", "1", "2"]),
    vol.Optional("prefix"): cv.string,
    vol.Optional("suffix"): cv.string,
    vol.Optional("format"): cv.string,
    vol.Optional("font_path"): cv.string,
})

REMOVE_TEXT_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
})

CLEAR_ALL_TEXT_SCHEMA = vol.Schema({})

async def async_setup_services(hass: HomeAssistant):
    """Set up services for UART Time Sender."""
    
    async def async_handle_fill_image(call: ServiceCall):
        """Handle fill_image service call."""
        _LOGGER.info("Fill image service called with RGB %s", call.data["background_color"])
        for entry_id, data in hass.data[DOMAIN].items():
            if isinstance(data, UARTTimeSenderCoordinator):
                coordinator = data
                coordinator.fill_image(
                    call.data["background_color"][0],
                    call.data["background_color"][1],
                    call.data["background_color"][2]
                )
    
    async def async_handle_set_pixel(call: ServiceCall):
        """Handle set_pixel service call."""
        _LOGGER.info(
            "Set pixel service called at (%d, %d) RGB %s",
            call.data["x"], call.data["y"], call.data["pixel_color"]
        )
        
        # Получаем все координаторы
        for entry_id, data in hass.data[DOMAIN].items():
            if isinstance(data, UARTTimeSenderCoordinator):
                coordinator = data
                coordinator.set_pixel(
                    call.data["x"],
                    call.data["y"],
                    call.data["pixel_color"][0],
                    call.data["pixel_color"][1],
                    call.data["pixel_color"][2]
                )
    
    async def async_handle_test_pattern(call: ServiceCall):
        """Handle test_pattern service call."""
        _LOGGER.info("Test pattern service called")
        
        # Получаем все координаторы
        for entry_id, data in hass.data[DOMAIN].items():
            if isinstance(data, UARTTimeSenderCoordinator):
                coordinator = data
                coordinator.create_test_pattern()
    
    async def async_handle_clear_image(call: ServiceCall):
        """Handle clear_image service call."""
        _LOGGER.info("Clear image service called")
        
        # Получаем все координаторы
        for entry_id, data in hass.data[DOMAIN].items():
            if isinstance(data, UARTTimeSenderCoordinator):
                coordinator = data
                coordinator.fill_image(0, 0, 0)  # Black

    async def async_handle_load_background(call: ServiceCall):
        """Handle load_background_image service call."""
        _LOGGER.info("Load background image service called")
        
        file_path_landscape = call.data.get("file_path_landscape")
        file_path_portrait = call.data.get("file_path_portrait")
        
        if file_path_landscape or file_path_portrait:
            for entry_id, data in hass.data[DOMAIN].items():
                if isinstance(data, UARTTimeSenderCoordinator):
                    coordinator = data
                    
                    if file_path_landscape:
                        coordinator.set_background_from_path(Orientation.LANDSCAPE.value, file_path_landscape)
                        _LOGGER.info("Landscape background set for coordinator %s: %s", 
                                    entry_id, file_path_landscape)
                    
                    if file_path_portrait:
                        coordinator.set_background_from_path(Orientation.PORTRAIT.value, file_path_portrait)
                        _LOGGER.info("Portrait background set for coordinator %s: %s", 
                                    entry_id, file_path_portrait)
        else:
            _LOGGER.warning("No file paths provided in load_background_image service call")

    
    def resize_image_for_display(image: Image.Image, target_size: tuple, 
                                mode: str, bg_color: tuple) -> Image.Image:
        """Resize image for display according to specified mode."""
        from PIL import Image, ImageOps
        
        if mode == "cover":
            # Обрезаем чтобы заполнить весь экран
            return ImageOps.fit(image, target_size, method=Image.Resampling.LANCZOS)
        
        elif mode == "contain":
            # Вписываем в экран с сохранением пропорций
            image.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # Создаем новое изображение с фоновым цветом
            new_image = Image.new('RGB', target_size, bg_color)
            
            # Центрируем изображение
            x_offset = (target_size[0] - image.size[0]) // 2
            y_offset = (target_size[1] - image.size[1]) // 2
            new_image.paste(image, (x_offset, y_offset))
            return new_image
        
        elif mode == "stretch":
            # Растягиваем/сжимаем до размеров экрана
            return image.resize(target_size, Image.Resampling.LANCZOS)
        
        elif mode == "center":
            # Не изменяем размер, просто центрируем
            new_image = Image.new('RGB', target_size, bg_color)
            x_offset = (target_size[0] - image.size[0]) // 2
            y_offset = (target_size[1] - image.size[1]) // 2
            new_image.paste(image, (x_offset, y_offset))
            return new_image
        
        return image


    # New text services - тоже нужно исправить
    async def async_handle_add_text(call: ServiceCall):
        """Handle add_text service call for both entities and static text."""
        entity_id = call.data["entity_id"]
        static_value = call.data.get("value", "")
        
            # Декодируем HTML entities если есть
        if "&#x" in static_value or "&#" in static_value:
            import html
            static_value = html.unescape(static_value)
        
        _LOGGER.info("Add text service called: entity_id=%s, static_value=%s", 
                     entity_id, static_value)
        
        # Проверяем, это статичный текст или entity?
        is_static = False
        final_entity_id = entity_id
        final_static_value = ""
        
        if (entity_id.lower() in ["static", "none", "text"] or 
            entity_id.lower().startswith("static:") or
            entity_id.lower().startswith("text:")):
            
            is_static = True
            
            # Извлекаем текст если указан как "static:Hello World"
            if ":" in entity_id:
                # Формат "static:Some Text" или "text:Some Text"
                parts = entity_id.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    static_text = parts[1].strip()
                else:
                    static_text = static_value
            else:
                # Формат "static" или "none" + поле value
                static_text = static_value
            
            if not static_text:
                _LOGGER.error("Static text requires either 'static:Your Text' format or 'value' field")
                return
            
            final_static_value = static_text
            
            # Создаем уникальный ID для статичного текста
            import hashlib
            text_hash = hashlib.md5(static_text.encode()).hexdigest()[:8]
            final_entity_id = f"static_text_{text_hash}"
            
            _LOGGER.info("Creating static text element: '%s' with ID: %s", 
                         static_text, final_entity_id)
        
        # Проверяем, не существует ли уже элемент с таким ID
        if final_entity_id in text_renderer._text_elements:
            _LOGGER.error("Text element with ID %s already exists", final_entity_id)
            return
        
        # Конвертируем alignment из строки в число
        alignment_str = call.data.get("alignment", "0")
        alignment_int = int(alignment_str) if alignment_str.isdigit() else 0
        
        # Create text element
        element = TextElement(
            entity_id=final_entity_id,
            x=call.data["x"],
            y=call.data["y"],
            font_size=call.data.get("font_size", 16),
            color=tuple(call.data.get("color", [255, 255, 255])),
            alignment=TextAlignment(alignment_int),
            prefix=call.data.get("prefix", ""),
            suffix=call.data.get("suffix", ""),
            format=call.data.get("format", "{value}"),
            font_path=call.data.get("font_path", ""),
            is_static=is_static,  # <-- Устанавливаем флаг
            static_value=final_static_value  # <-- Сохраняем значение
        )
        
        # Добавляем в рендерер
        success = text_renderer.add_text_element(element)
        
        if success:
            # Устанавливаем значение
            if is_static:
                # Для статичного текста
                text_renderer.update_sensor_value(final_entity_id, final_static_value)
                _LOGGER.info("Static text added: '%s' at (%d, %d)", 
                            final_static_value, element.x, element.y)
            else:
                # Для entity - получаем текущее состояние
                state = hass.states.get(entity_id)
                if state:
                    text_renderer.update_sensor_value(final_entity_id, state.state)
                    _LOGGER.info("Entity text added: %s at (%d, %d)", 
                                entity_id, element.x, element.y)
                else:
                    text_renderer.update_sensor_value(final_entity_id, "N/A")
                    _LOGGER.warning("Entity %s not found, using 'N/A'", entity_id)
            
            # Обновляем изображение на всех координаторах
            for entry_id, data in hass.data[DOMAIN].items():
                if isinstance(data, UARTTimeSenderCoordinator):
                    coordinator = data
                    coordinator._image_needs_update = True
                    coordinator._update_display_image()
            
            _LOGGER.info("Text element added successfully")
        else:
            _LOGGER.error("Failed to add text element")
    
    async def async_handle_update_text(call: ServiceCall):
        """Handle update_text service call."""
        entity_id = call.data["entity_id"]
        
        _LOGGER.info("Update text service called for entity: %s", entity_id)
        
        # Prepare update data
        update_data = {}
        for key in ["x", "y", "font_size", "color", "alignment", 
                   "prefix", "suffix", "format", "font_path", "value"]:
            if key in call.data:
                if key == "color" and isinstance(call.data[key], list):
                    update_data[key] = tuple(call.data[key])
                elif key == "alignment":
                    # Конвертируем alignment из строки в число
                    alignment_str = call.data[key]
                    alignment_int = int(alignment_str) if isinstance(alignment_str, str) and alignment_str.isdigit() else alignment_str
                    update_data[key] = TextAlignment(alignment_int)
                else:
                    update_data[key] = call.data[key]
        
        # Special handling for static text value update
        if "value" in update_data and entity_id in text_renderer._text_elements:
            element = text_renderer._text_elements[entity_id]
            if element.is_static:
                # Обновляем static_value в элементе
                update_data["static_value"] = update_data.pop("value")
                _LOGGER.info("Updating static text value for %s: %s", 
                            entity_id, update_data["static_value"])
        
        # Update element
        success = text_renderer.update_text_element(entity_id, **update_data)
        
        if success:
            # Обновляем значение в sensor_values если нужно
            if "static_value" in update_data:
                text_renderer.update_sensor_value(entity_id, update_data["static_value"])
            
            # Update image on all coordinators
            for entry_id, data in hass.data[DOMAIN].items():
                if isinstance(data, UARTTimeSenderCoordinator):
                    coordinator = data
                    coordinator._image_needs_update = True
                    coordinator._update_display_image()
            
            _LOGGER.info("Text element updated successfully for entity: %s", entity_id)
        else:
            _LOGGER.error("Failed to update text element for entity: %s", entity_id)
    
    async def async_handle_remove_text(call: ServiceCall):
        """Handle remove_text service call."""
        entity_id = call.data["entity_id"]
        
        _LOGGER.info("Remove text service called for entity: %s", entity_id)
        
        # Remove element
        success = text_renderer.remove_text_element(entity_id)
        
        if success:
            # Update image on all coordinators
            for entry_id, data in hass.data[DOMAIN].items():
                if isinstance(data, UARTTimeSenderCoordinator):
                    coordinator = data
                    coordinator._image_needs_update = True
                    coordinator._update_display_image()
            
            _LOGGER.info("Text element removed successfully for entity: %s", entity_id)
        else:
            _LOGGER.warning("Text element not found for entity: %s", entity_id)
    
    async def async_handle_clear_all_text(call: ServiceCall):
        """Handle clear_all_text service call."""
        _LOGGER.info("Clear all text service called")
        
        # Clear all elements
        text_renderer.clear_all_text_elements()
        
        # Update image on all coordinators
        for entry_id, data in hass.data[DOMAIN].items():
            if isinstance(data, UARTTimeSenderCoordinator):
                coordinator = data
                coordinator._image_needs_update = True
                coordinator._update_display_image()
        
        _LOGGER.info("All text elements cleared")
    
    # Register all services
    hass.services.async_register(
        DOMAIN, SERVICE_FILL_IMAGE, async_handle_fill_image,
        schema=FILL_IMAGE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SET_PIXEL, async_handle_set_pixel,
        schema=SET_PIXEL_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_TEST_PATTERN, async_handle_test_pattern,
        schema=TEST_PATTERN_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_IMAGE, async_handle_clear_image,
        schema=CLEAR_IMAGE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_LOAD_BACKGROUND, async_handle_load_background,
        schema=LOAD_BACKGROUND_SCHEMA
    )
    
    # Register text services
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_TEXT, async_handle_add_text,
        schema=ADD_TEXT_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_TEXT, async_handle_update_text,
        schema=UPDATE_TEXT_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_TEXT, async_handle_remove_text,
        schema=REMOVE_TEXT_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_ALL_TEXT, async_handle_clear_all_text,
        schema=CLEAR_ALL_TEXT_SCHEMA
    )
    
    return True