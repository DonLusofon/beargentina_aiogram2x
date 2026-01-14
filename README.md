## Telegram bot (aiogram 2.x)

Запуск:
1) Установите зависимости: `pip install -r requirements.txt`
2) Экспортируйте токен: `export BOT_TOKEN="YOUR_TOKEN"` (или передайте через ботхост)
3) По желанию задайте `BOT_USERNAME`, `ADMIN_CHAT_IDS`, `SITE_BASE_URL`, `EXTRA_CATALOG_PATH`, `SUPPORT_CONTACT`
4) Запустите: `python bot.py`

Каталог услуг хранится в файле `extra_catalog.json` (по умолчанию в репозитории, путь в `EXTRA_CATALOG_PATH`) и в `config.EXTRA_CATALOG`:
- `/new` добавляет услуги в память и сохраняет в `extra_catalog.json`; `/delete` удаляет и помечает `deleted`.
- После рестартов данные берутся из `extra_catalog.json`. Можно редактировать этот файл напрямую в репозитории (без команд бота).
- При желании можно вынести `EXTRA_CATALOG_PATH` на постоянный диск (env), но по умолчанию файл лежит рядом с кодом.
