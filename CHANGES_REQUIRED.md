# Изменения, необходимые для работы парсера

Перед запуском парсера на реальных сайтах необходимо выяснить и подставить актуальные селекторы и параметры. Ниже приведён чек-лист.

---

## 1. Fedresurs.ru — селекторы

Селекторы в `src/parsers/fedresurs.py`:
- Поле поиска ИНН: `input[formcontrolname='searchString']`
- Кнопка поиска: `.el-button`
- «Вся информация» — по тексту
- № дела: `a.underlined.info-header`
- Дата: `entity-card-bankruptcy-publication-wrapper` → `a.underlined`

---

## 2. Kad.arbitr.ru — селекторы

Селекторы в `src/parsers/kad_arbitr.py`:
- Поле поиска: `#sug-cases input`
- Таблица результатов: `#b-cases tbody tr`
- Вкладка «Электронное дело» — по тексту
- Документы: `ul.b-case-chrono-ed.js-case-chrono-ed`

---

## 3. Структура xlsx

| Параметр      | Переменная        | Описание                               |
| ------------- | ----------------- | -------------------------------------- |
| Имя листа     | `XLSX_SHEET_NAME` | Лист в xlsx (по умолчанию `Sheet1`)    |
| Колонка с ИНН | `XLSX_INN_COLUMN` | Заголовок колонки (по умолчанию `ИНН`) |

---

## 4. Обход блокировок (Camoufox)

```bash
pip install camoufox[geoip]
camoufox fetch  # скачать браузер
```

| Переменная | Описание |
| ---------- | -------- |
| `PROXY_URL` | Прокси (поддерживается с geoip) |
| `HEADLESS=false` | Видимый браузер |
| `DELAY_MIN` / `DELAY_MAX` | Пауза между запросами (сек) |

---

## 5. Тестовые данные

- **ИНН:** `231138771115` (из ТЗ)
- **№ дела:** `А32-28873/2024` (из ТЗ)

```bash
python scripts/test_camoufox.py 231138771115 --headed
```
