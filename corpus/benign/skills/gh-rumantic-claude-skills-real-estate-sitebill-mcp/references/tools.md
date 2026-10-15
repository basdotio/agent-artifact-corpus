# Справочник инструментов MCP-сервера Sitebill

Всего 16 инструментов. «Запись» означает, что инструмент виден только токену с правом `mcp:write` от сотрудника.
Поля с `*` обязательные.

## Поиск и подборки

### get_search_options
Справочники платформы: типы сделок и недвижимости, города (самые крупные по числу объектов), кастомные поля.
Параметры: `locale` (ru, en, sr, tg).

### resolve_location
Название города или района в id. Параметры: `query`* (часть названия), `city_id` (искать районы только этого города).

### search_properties
Поиск объектов. Основные параметры:
`deal_type` (`sale`, `rent_long`, `rent_daily`), `type`, `city_id`, `district_id`, `region_id`,
`price_min`, `price_max`, `rooms` (массив: `0` студия, `4` это «4 и более»), `area_min`, `area_max`,
`lot_area_min`, `lot_area_max`, `floor`, `exclude_top_floor`, `build_year_min`, `build_year_max`, `renovation`,
`is_new_building`, `has_parking`, `has_elevator`, `customFields` (до 5: `key`, `operator` из EQ/NEQ/GT/GTE/LT/LTE/CONTAINS/IN,
`value`), `check_in` и `check_out` (для посуточной аренды), `sort`, `scope` (`published` по умолчанию или `mine`),
`page`, `per_page` (1–20, по умолчанию 10), `locale`.

### get_property
Карточка объекта. Параметры: `id`*, `locale`.

### create_selection (запись)
Публичная ссылка-подборка для клиента. Принимает те же фильтры, что `search_properties`, плюс `title`
(короткое название для адреса ссылки, необязательно).

## Контакты (персональный токен сотрудника)

### list_contacts
Параметры: `search` (имя, телефон в любом формате, email), `stage_id`, `source`, `has_deals`,
`last_activity_before` (YYYY-MM-DD: с кем давно не общались), `page`, `per_page`.

### get_contact
Карточка клиента: каналы связи, сделки, заметки. Параметры: `id`* (ID контакта).

### create_contact (запись)
Параметры: `name`, `channels` (массив `{type, value}`), `notes` (до 5000 символов). Дубль по каналу связи не создаётся.

### add_contact_note (запись)
Параметры: `contact_id`*, `body`* (до 5000 символов).

## Сделки (персональный токен сотрудника)

### list_deals
Параметры: `search` (имя, телефон или email контакта), `status` (`open`, `won`, `lost`), `stage_id`, `contact_id`,
`property_id`, `operation`, `page`, `per_page`. В ответе воронки и их стадии (нужны для `create_deal` и `move_deal`).

### get_deal
Карточка сделки: требования клиента, предложенные объекты, история стадий. Параметры: `id`* (ID сделки).

### create_deal (запись)
Параметры: `contact_id`*, `direction` (`demand` клиент ищет, по умолчанию; `supply` клиент сдаёт или продаёт),
`operation`, `amount`, `currency`, `expected_close_date`, `notes`, `stage_id` (по умолчанию первая),
`property_ids` (до 20 предложенных объектов).

### move_deal (запись)
Параметры: `deal_id`*, `stage_id`* (из той же воронки), `lost_reason` (только для стадии со статусом lost).
Закрытие в успех или отказ только по прямому указанию пользователя.

### add_deal_comment (запись)
Параметры: `deal_id`*, `body`* (до 5000 символов).

## Объекты в базе (запись)

### create_property
Создаёт **черновик**. Обязательные: `title`, `type`, `deal_type`, `price`, `area_total`, `city_id`.
Дополнительно: `description`, `currency`, `district_id`, `building_number`, `rooms`, `bedrooms`, `bathrooms`, `floor`,
`floors_total`, `area_living`, `area_kitchen`, `lot_area`, `ceiling_height`, `build_year`, `renovation`, `has_elevator`,
`has_parking`, `has_air_conditioner`, `has_internet`, `has_security`, `is_new_building`, `lat`, `lng`,
`custom_fields` (`{ключ: значение}` из `get_search_options`), `locale`, `publish` (сработает только при наличии права).

### update_property
Меняет только переданные поля, остальное не трогает. Параметры: `id`*, поля из `create_property`, `status`
(например `active`, `inactive`, `archived`), `publish` (`true` опубликовать, `false` снять с сайта).

## Чего нет

Удаления объектов, контактов и сделок, загрузки фото объектов и смены владельца объекта. Экспортные флаги
(Авито, ЦИАН, Яндекс) агент не задаёт.

Список и параметры меняются только в сторону расширения: инструменты добавляются, существующие не переименовываются.
Актуальный список агент получает при подключении через `tools/list`.
