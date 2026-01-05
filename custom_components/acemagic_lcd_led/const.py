"""Constants for UART Time Sender integration."""

from enum import IntEnum
from homeassistant.const import Platform
import os

DOMAIN = "acemagic_lcd_led"
DEFAULT_NAME = "AceMagic LCD&LED Controller"
DEFAULT_BAUDRATE = 9600  # Фиксированная скорость для CH340
CONF_PORT = "port"
CONF_TEXT_SENSORS = "text_sensors"

VID_04D9 = "04d9"
PID_FD01 = "fd01"

# Platform constants
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.IMAGE,
    Platform.SENSOR,  # Добавляем для текстовых сенсоров
]

# Device info
MANUFACTURER = "AceMagic"
MODEL = "S1"
DEVICE_NAME = "MiniPC AceMagic"

# Signature bytes
SIGNATURE_CONTROL = 0xFA
SIGNATURE_IMAGE = [0x55, 0xA3, 0xF0, 0x01, 0x00, 0x00, 0x00, 0x10]

# Image constants
IMAGE_WIDTH = 320
IMAGE_HEIGHT = 170
IMAGE_SIZE = IMAGE_WIDTH * IMAGE_HEIGHT * 2  # 320 * 170 * 2 bytes (16-bit color)

# Orientation values
class Orientation(IntEnum):
    PORTRAIT = 0x02  # Книжная (ширина 170, высота 320) 
    LANDSCAPE = 0x01  # Альбомная (ширина 320, высота 170)

ORIENTATION_OPTIONS = {
    Orientation.PORTRAIT.value: "Portrait (170x320)",
    Orientation.LANDSCAPE.value: "Landscape (320x170)",
}

# Размеры экрана в зависимости от ориентации
def get_display_size(orientation: int) -> tuple[int, int]:
    """Get display dimensions based on orientation."""
    if orientation == Orientation.LANDSCAPE.value:
        return (320, 170)  # Ширина x Высота
    else:  # PORTRAIT
        return (170, 320)  # Ширина x Высота

# Theme values
class Themes(IntEnum):
    RAINBOW = 0x01
    BREATHING = 0x02
    COLOR_CYCLE = 0x03
    OFF = 0x04
    AUTOMATIC = 0x05

THEME_OPTIONS = {
    Themes.RAINBOW.value: "Rainbow",
    Themes.BREATHING.value: "Breathing",
    Themes.COLOR_CYCLE.value: "Color Cycle",
    Themes.OFF.value: "Off",
    Themes.AUTOMATIC.value: "Automatic",
}

# Text configuration
class TextAlignment(IntEnum):
    LEFT = 0
    CENTER = 1
    RIGHT = 2

# Default values
DEFAULT_THEME = Themes.RAINBOW.value
DEFAULT_INTENSITY = 3
DEFAULT_SPEED = 3
DEFAULT_ORIENTATION = Orientation.PORTRAIT.value
DEFAULT_TEXT_COLOR = (255, 255, 255)  # White
DEFAULT_BACKGROUND_COLOR = (0, 0, 0)   # Black
DEFAULT_FONT_SIZE = 16

# Limits
MIN_INTENSITY = 1
MAX_INTENSITY = 5
MIN_SPEED = 1
MAX_SPEED = 5

# Paths
INTEGRATION_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_FONT_PATH = os.path.join(INTEGRATION_DIR, "fonts", "ArialRegular.ttf")
START_LOGO_PATH = os.path.join(INTEGRATION_DIR, "startlogo.png")