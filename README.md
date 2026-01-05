# AceMagic-S1-Lcd-Led-control-HA-integration
<p>
 <img height="80px" src="https://github.com/samoswall/AceMagic-S1-Lcd-Led-control-HA-integration/blob/main/image/icon.png">
 <img src="https://github.com/samoswall/AceMagic-S1-Lcd-Led-control-HA-integration/blob/main/image/acemagiclogo.png">
</p>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
![](https://img.shields.io/github/watchers/samoswall/AceMagic-S1-Lcd-Led-control-HA-integration.svg)
![](https://img.shields.io/github/stars/samoswall/AceMagic-S1-Lcd-Led-control-HA-integration.svg)
[![Donate](https://img.shields.io/badge/donate-Yandex-red.svg)](https://yoomoney.ru/fundraise/b8GYBARCVRE.230309)

[![EN](https://img.shields.io/badge/lang-EN-green.svg)](/README.en.md)      <-- Changing the description language - Click me 

#### Интеграция для Home Assistant позволяет выводить информацию на передний дисплей и управлять светодиодной подсветкой мини-ПК AceMagic S1.

## Конфигурирование

При установке интеграции будет предложено выбрать порт для управления подсветкой (возможно на разных ПК он может отличаться). Выбирайте тот, который подписан как /dev/ttyUSB0.

Все управление информацией на дисплее реализовано через сервисы, что позволяет динамически менять информацию на экране.

### Сервисы

| Имя сервиса | Описание | Примечание
| ----  | ----------- | -----------
| acemagic_lcd_led.add_text | Добавить статический текст или значение сенсора на дисплей | Если ID сенсора указать как `static` то добавится статичный текст (можно указать `mdi:имя_иконки`)<br>Обратите внимание на строку форматирования Python для значения (используйте `{value}` можно использовать `{value:.1f}`)
| acemagic_lcd_led.update_text | Обновить свойства текстового элемента | Обновление произойдет если изменится минимум 1 параметр у элемента для обновления. Указывайте существующий элемент! Список элементов находится в аттрибутах `sensor.minipc_acemagic_text_sensors`
| acemagic_lcd_led.remove_text| Удалить текстовый элемент с дисплея | Указывайте существующий элемент! Список элементов находится в аттрибутах `sensor.minipc_acemagic_text_sensors`
| acemagic_lcd_led.clear_all_text| Удалить все текстовые элементы с дисплея | Фон не удалится. Для фона используйте сервис `load_background_image`
| acemagic_lcd_led.load_background_image| Устанавливает параметры фона для разных ориентаций экрана | Укажите путь к картинке (см. примеры в сервисе) 
| acemagic_lcd_led.fill_image | Залить весь дисплей одним цветом | Действует до обновления, не сохраняется
| acemagic_lcd_led.set_pixel | Установить цвет конкретного пикселя | Действует до обновления, очищает фон, не сохраняется
| acemagic_lcd_led.test_pattern | Показать тестовый градиентный узор на экране | Действует до обновления, не сохраняется
| acemagic_lcd_led.clear_image | Очистить дисплей (установить черный цвет) |  Действует до обновления, не сохраняется

ℹ️ **Справочно**: <br>
Файл с текущими настройками `text_config.json` находится в папке с интеграцией.<br>
В папку `fonts` уже загружены 3 шрифра: 
- ArialRegular.ttf
- RobotoCondensed-BoldItalic.ttf
- DSEG7Classic-BoldItalic.ttf (шрифт семисегментного индикатора)

ℹ️ **Планы для доработок**: <br>
⬛ Сделать перерисовку конкретной области экрана для обнавления (пока при изменении обновляется весь экран)<br>
✔️ Сделать синхронизацию времени в дисплее (время показывается при выключенном МиниПК)<br>
⬛ Добавить виджеты (график, бар и т.д.)<br>

## Благодарности

Спасибо авторам:
- [tjaworski](https://github.com/tjaworski/AceMagic-S1-LED-TFT-Linux) за подробное описание протокола
- [Slalamander](https://github.com/Slalamander/mdi_pil) за библиотеку для рендера иконок mdi.

