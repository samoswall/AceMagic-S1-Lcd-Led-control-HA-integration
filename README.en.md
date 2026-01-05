# AceMagic-S1-Lcd-Led-control-HA-integration
<p>
 <img height="80px" src="https://github.com/samoswall/AceMagic-S1-Lcd-Led-control-HA-integration/blob/main/image/icon.png">
 <img src="https://github.com/samoswall/AceMagic-S1-Lcd-Led-control-HA-integration/blob/main/image/acemagiclogo.png">
</p>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
![](https://img.shields.io/github/watchers/samoswall/AceMagic-S1-Lcd-Led-control-HA-integration.svg)
![](https://img.shields.io/github/stars/samoswall/AceMagic-S1-Lcd-Led-control-HA-integration.svg)
[![Donate](https://img.shields.io/badge/donate-Yandex-red.svg)](https://yoomoney.ru/fundraise/b8GYBARCVRE.230309)

[![EN](https://img.shields.io/badge/lang-RU-green.svg)](/README.md)      <-- Переключить язык описания - Кликни 

## Integration for Home Assistant allows displaying information on the front display and controlling the LED backlight of the AceMagic S1 mini PC.

## Configuration

During installation, you will be prompted to select a port for backlight control (it may vary on different PCs). Choose the one labeled as `/dev/ttyUSB0`.

All display information control is implemented through services, allowing dynamic changes to the screen content.

### Services

| Service Name | Description | Notes |
| --- | --- | --- |
| `acemagic_lcd_led.add_text` | Add static text or sensor value to the display | If the sensor ID is specified as `static`, static text will be added (you can specify `mdi:icon_name`)<br>Pay attention to the Python formatting string for the value (use `{value}`, you can also use `{value:.1f}`) |
| `acemagic_lcd_led.update_text` | Update properties of a text element | The update will occur if at least 1 parameter of the element changes. Specify an existing element! The list of elements is in the attributes of `sensor.minipc_acemagic_text_sensors` |
| `acemagic_lcd_led.remove_text` | Remove a text element from the display | Specify an existing element! The list of elements is in the attributes of `sensor.minipc_acemagic_text_sensors` |
| `acemagic_lcd_led.clear_all_text` | Remove all text elements from the display | The background will not be removed. Use the `load_background_image` service for the background |
| `acemagic_lcd_led.load_background_image` | Sets background parameters for different screen orientations | Specify the image path (see examples in the service) |
| `acemagic_lcd_led.fill_image` | Fill the entire display with a single color | Valid until updated, not saved |
| `acemagic_lcd_led.set_pixel` | Set the color of a specific pixel | Valid until updated, clears the background, not saved |
| `acemagic_lcd_led.test_pattern` | Display a test gradient pattern on the screen | Valid until updated, not saved |
| `acemagic_lcd_led.clear_image` | Clear the display (set to black) | Valid until updated, not saved |

ℹ️ **Information**:
* The file with current settings `text_config.json` is located in the integration folder.
* The `fonts` folder already contains 3 fonts:
  * `ArialRegular.ttf`
  * `RobotoCondensed-BoldItalic.ttf`
  * `DSEG7Classic-BoldItalic.ttf` (seven-segment display font)

ℹ️ **Planned improvements**:
* ⬛ Implement redrawing of a specific screen area for updates (currently, the entire screen is updated on change)
* ✔️ Implement time synchronization in the display (time is displayed when the mini PC is off)
* ⬛ Add widgets (chart, bar, etc.)

## Thanks

Thanks to the authors:
* [tjaworski](https://github.com/tjaworski/AceMagic-S1-LED-TFT-Linux) for detailed protocol description
* [Slalamander](https://github.com/Slalamander/mdi_pil) for the library for rendering MDI icons.
