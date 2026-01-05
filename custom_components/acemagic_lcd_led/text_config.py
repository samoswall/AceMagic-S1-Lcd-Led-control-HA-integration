"""Text configuration and rendering for UART Time Sender."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import IntEnum
from PIL import Image, ImageDraw, ImageFont
import io
import json

from .const import (
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
    DEFAULT_TEXT_COLOR,
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_PATH,
    INTEGRATION_DIR,
    IMAGE_SIZE,
    Orientation
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

class TextAlignment(IntEnum):
    LEFT = 0
    CENTER = 1
    RIGHT = 2

@dataclass
class DisplayConfig:
    """Configuration for display settings."""
    background_image_landscape: str = ""
    background_image_portrait: str = ""
    last_orientation: int = Orientation.LANDSCAPE.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "background_image_landscape": self.background_image_landscape,
            "background_image_portrait": self.background_image_portrait,
            "last_orientation": self.last_orientation
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DisplayConfig':
        """Create from dictionary."""
        return cls(
            background_image_landscape=data.get("background_image_landscape", ""),
            background_image_portrait=data.get("background_image_portrait", ""),
            last_orientation=data.get("last_orientation", Orientation.LANDSCAPE.value)
        )

@dataclass
class TextElement:
    """Configuration for a text element on the display."""
    entity_id: str
    x: int
    y: int
    font_size: int = DEFAULT_FONT_SIZE
    color: Tuple[int, int, int] = field(default_factory=lambda: DEFAULT_TEXT_COLOR)
    alignment: TextAlignment = TextAlignment.LEFT
    prefix: str = ""
    suffix: str = ""
    format: str = "{value}"
    font_path: str = ""
    is_static: bool = False  # <-- Добавляем флаг статичного текста
    static_value: str = ""   # <-- Добавляем поле для статичного значения
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure color is a tuple
        if isinstance(self.color, list):
            self.color = tuple(self.color)
        
        # Ensure alignment is TextAlignment enum
        if isinstance(self.alignment, int):
            self.alignment = TextAlignment(self.alignment)
        
        # Set default font path if not specified
        if not self.font_path:
            self.font_path = DEFAULT_FONT_PATH
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entity_id": self.entity_id,
            "x": self.x,
            "y": self.y,
            "font_size": self.font_size,
            "color": list(self.color),
            "alignment": int(self.alignment),
            "prefix": self.prefix,
            "suffix": self.suffix,
            "format": self.format,
            "font_path": self.font_path,
            "is_static": self.is_static,  # <-- Сохраняем флаг
            "static_value": self.static_value if self.is_static else ""  # <-- Сохраняем значение
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextElement':
        """Create from dictionary."""
        # Преобразуем alignment из int в TextAlignment
        if "alignment" in data:
            data["alignment"] = TextAlignment(data["alignment"])
        
        # Устанавливаем значения по умолчанию для новых полей
        if "is_static" not in data:
            data["is_static"] = False
        if "static_value" not in data:
            data["static_value"] = ""
        
        return cls(**data)
    
    def get_text(self, value: Any) -> str:
        """Format text with value."""
        try:
            # Если это статичный текст, используем static_value
            if self.is_static and self.static_value:
                # Форматируем статичное значение
                formatted_value = self.format.format(value=self.static_value)
                return f"{self.prefix}{formatted_value}{self.suffix}"
            
            # Иначе форматируем переданное значение
            formatted_value = self.format.format(value=value)
            return f"{self.prefix}{formatted_value}{self.suffix}"
        except Exception:
            if self.is_static and self.static_value:
                return f"{self.prefix}{self.static_value}{self.suffix}"
            return f"{self.prefix}{value}{self.suffix}"



class TextRenderer:
    """Renders text on the display image."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize text renderer."""
        self._text_elements: Dict[str, TextElement] = {}
        self._font_cache: Dict[Tuple[str, int], ImageFont.ImageFont] = {}
        self._sensor_values: Dict[str, Any] = {}
        self._display_config: DisplayConfig = DisplayConfig()
        self._config_path = config_path or os.path.join(INTEGRATION_DIR, "text_config.json")
        
        # Load saved configuration
        self._load_configuration()
        
        # После загрузки, инициализируем значения статичных текстов
        self._initialize_static_values()

    def _initialize_static_values(self):
        """Initialize static text values after loading configuration."""
        for element in self._text_elements.values():
            if element.is_static and element.static_value:
                # Устанавливаем значение для статичного текста
                self._sensor_values[element.entity_id] = element.static_value
                _LOGGER.debug("Initialized static text: %s = '%s'", 
                             element.entity_id, element.static_value)

    def set_background_image_path(self, orientation: int, path: str):
        """Set background image path for specific orientation."""
        if orientation == Orientation.LANDSCAPE.value:
            self._display_config.background_image_landscape = path
        else:  # PORTRAIT
            self._display_config.background_image_portrait = path
        self._save_configuration()
        _LOGGER.info("Background image for orientation %d set to: %s", orientation, path)
    
    def get_background_image_path(self, orientation: int) -> str:
        """Get background image path for specific orientation."""
        if orientation == Orientation.LANDSCAPE.value:
            return self._display_config.background_image_landscape
        else:  # PORTRAIT
            return self._display_config.background_image_portrait
    
    def clear_background_for_orientation(self, orientation: int):
        """Clear background image for specific orientation."""
        if orientation == Orientation.LANDSCAPE.value:
            self._display_config.background_image_landscape = ""
        else:  # PORTRAIT
            self._display_config.background_image_portrait = ""
        self._save_configuration()
        _LOGGER.info("Background image cleared for orientation %d", orientation)
    
    def clear_all_backgrounds(self):
        """Clear all background images."""
        self._display_config.background_image_landscape = ""
        self._display_config.background_image_portrait = ""
        self._save_configuration()
        _LOGGER.info("All background images cleared")
    
    def set_orientation(self, orientation: int):
        """Save last orientation."""
        self._display_config.last_orientation = orientation
        self._save_configuration()
    
    def get_orientation(self) -> int:
        """Get last orientation."""
        return self._display_config.last_orientation
        
    def add_text_element(self, element: TextElement) -> bool:
        """Add a text element to render."""
        if element.entity_id in self._text_elements:
            _LOGGER.warning("Text element for entity %s already exists", element.entity_id)
            return False
        
        self._text_elements[element.entity_id] = element
        _LOGGER.info("Added text element for entity: %s at (%d, %d)", 
                    element.entity_id, element.x, element.y)
        
        # Save configuration
        self._save_configuration()
        
        return True
        
    def update_text_element(self, entity_id: str, **kwargs) -> bool:
        """Update existing text element."""
        if entity_id not in self._text_elements:
            _LOGGER.error("Text element for entity %s not found", entity_id)
            return False
        
        element = self._text_elements[entity_id]
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(element, key):
                setattr(element, key, value)
        
        # Clear font cache for this element
        cache_key = (element.font_path, element.font_size)
        if cache_key in self._font_cache:
            del self._font_cache[cache_key]
        
        _LOGGER.info("Updated text element for entity: %s", entity_id)
        
        # Save configuration
        self._save_configuration()
        
        return True
        
    def clear_all_text_elements(self):
        """Remove all text elements."""
        self._text_elements.clear()
        self._font_cache.clear()
        self._sensor_values.clear()
        
        _LOGGER.info("Cleared all text elements")
        
        # Save configuration
        self._save_configuration()
    
    def update_sensor_value(self, entity_id: str, value: Any):
        """Update value for a sensor/entity."""
        self._sensor_values[entity_id] = value
        
    def get_font(self, font_path: str, font_size: int) -> ImageFont.ImageFont:
        """Get font for given path and size (with caching)."""
        cache_key = (font_path, font_size)
        
        if cache_key not in self._font_cache:
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    # Try to find font
                    possible_paths = [
                        font_path,
                        os.path.join("/usr/share/fonts/truetype/dejavu/", os.path.basename(font_path)),
                        os.path.join("/usr/share/fonts/truetype/liberation/", os.path.basename(font_path)),
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    ]
                    
                    font = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            font = ImageFont.truetype(path, font_size)
                            break
                    
                    if font is None:
                        # Fallback to default
                        font = ImageFont.load_default()
                        # Try to scale default font
                        if hasattr(font, 'getsize'):
                            # Default font in PIL doesn't have point size
                            pass
            except Exception as err:
                _LOGGER.error("Failed to load font %s: %s", font_path, err)
                font = ImageFont.load_default()
            
            self._font_cache[cache_key] = font
            
        return self._font_cache[cache_key]
    
    def render_text_on_image(
        self, 
        base_image: Image.Image, 
        orientation: int
    ) -> Image.Image:
        """Render text on the base image."""
        if not self._text_elements:
            return base_image.copy()
        
        _LOGGER.info("=== START render_text_on_image ===")
        _LOGGER.info("Orientation: %d, Base image size: %s", 
                    orientation, base_image.size)
        
        # Create a copy to draw on
        image = base_image.copy()
        draw = ImageDraw.Draw(image)
        
        width, height = image.size
        
        for element in self._text_elements.values():
            entity_id = element.entity_id
            if entity_id in self._sensor_values:
                value = self._sensor_values[entity_id]
                text = element.get_text(value)
                
                _LOGGER.info("Processing element: %s, value: %s, text: '%s'", 
                            entity_id, value, text)
                
                if text:
                    try:
                        # Get font
                        font = self.get_font(element.font_path, element.font_size)
                        
                        x = element.x
                        y = element.y
                        
                        _LOGGER.info("Drawing text at (%d, %d): '%s' (original: %d, %d)", 
                                   x, y, text, element.x, element.y)
                        
                        if text[:4] == "mdi:":
                            import mdi_pil as mdi
                            mdi.draw_mdi_icon(image, text,
                                icon_coords=[x,y],
                                icon_size=element.font_size,
                                icon_color=element.color
                            )

                         # Вставка png
        #                if text[0] == "/":
        #                    icon = Image.open(text)
                            # Изменяем размер иконки при необходимости
        #                    icon = icon.resize((element.font_size, element.font_size), Image.Resampling.LANCZOS)
                            # Меняем цвет
        #                    colored_icon = self.change_icon_color(icon, (element.color))
                            # Вставляем иконку на изображение (с поддержкой прозрачности)
        #                    image.paste(icon, (x, y), icon)
                        else:
                            draw.text((x, y), text, fill=element.color, font=font)
                        
                        # Рисуем красную точку в месте координат для отладки
        #                draw.ellipse([(x-2, y-2), (x+2, y+2)], fill=(255, 0, 0))
                        
                    except Exception as err:
                        _LOGGER.error("Failed to draw text '%s': %s", text, err)
                        import traceback
                        _LOGGER.error("Traceback: %s", traceback.format_exc())
            else:
                _LOGGER.warning("No sensor value for entity: %s", entity_id)
        
        _LOGGER.info("=== END render_text_on_image ===")
        return image
    
    def change_icon_color(self, icon, color) -> Image.Image:
        """Меняет цвет иконки, сохраняя прозрачность"""
        r, g, b = color
        data = icon.getdata()
        
        new_data = []
        for item in data:
            # Изменяем RGB, сохраняя альфа-канал
            if item[3] > 0:  # Если пиксель не прозрачный
                new_data.append((r, g, b, item[3]))
            else:
                new_data.append(item)
        
        icon.putdata(new_data)
        return icon
    
    
    def get_text_elements(self) -> List[TextElement]:
        """Get list of all text elements."""
        return list(self._text_elements.values())
    
    def get_required_entities(self) -> List[str]:
        """Get list of entity IDs required for text rendering."""
        return list(self._text_elements.keys())
    
    def _save_configuration(self):
        """Save text configuration to file."""
        try:
            config_data = {
                "text_elements": [elem.to_dict() for elem in self._text_elements.values()],
                "display_config": self._display_config.to_dict()
            }
            
            with open(self._config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            _LOGGER.debug("Saved text configuration to %s", self._config_path)
        except Exception as err:
            _LOGGER.error("Failed to save text configuration: %s", err)
    
    def _load_configuration(self):
        """Load text configuration from file."""
        try:
            _LOGGER.info("Loading text configuration from: %s", self._config_path)
            
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r') as f:
                    config_data = json.load(f)
                
                _LOGGER.info("Loaded config data")
                
                # Load text elements
                text_elements = config_data.get("text_elements", [])
                _LOGGER.info("Found %d text elements in config", len(text_elements))
                
                for idx, elem_data in enumerate(text_elements):
                    try:
                        element = TextElement.from_dict(elem_data)
                        self._text_elements[element.entity_id] = element
                        _LOGGER.info("[%d] Loaded text element: %s at (%d, %d)", 
                                   idx, element.entity_id, element.x, element.y)
                    except Exception as err:
                        _LOGGER.error("Failed to load text element %d: %s", idx, err)
                
                # Load display config
                display_config_data = config_data.get("display_config", {})
                self._display_config = DisplayConfig.from_dict(display_config_data)
                _LOGGER.info("Loaded display config: landscape=%s, portrait=%s, orientation=%d",
                           self._display_config.background_image_landscape,
                           self._display_config.background_image_portrait,
                           self._display_config.last_orientation)
                
                _LOGGER.info("Successfully loaded %d text elements", 
                           len(self._text_elements))
            else:
                _LOGGER.warning("Text config file not found: %s", self._config_path)
        except Exception as err:
            _LOGGER.error("Failed to load text configuration: %s", err)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())

# Global instance
text_renderer = TextRenderer()