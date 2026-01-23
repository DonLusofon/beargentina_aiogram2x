import os

from dotenv import load_dotenv

load_dotenv()


def env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


BOT_TOKEN = env("BOT_TOKEN", "")  # берётся из окружения ботхоста
BOT_USERNAME = env("BOT_USERNAME", "volfson_test_bot").lstrip("@")

# Базовая страница каталога (для подсказок пользователю)
SITE_BASE_URL = env("SITE_BASE_URL", "https://comunaglobal.com")
# Путь к локальному файлу с дополнительными записями (по умолчанию в репозитории)
EXTRA_CATALOG_PATH = env("EXTRA_CATALOG_PATH", "extra_catalog.json")
# Контакт поддержки, который показываем заказчику
SUPPORT_CONTACT = env("SUPPORT_CONTACT", "@ksushasky")

# Главные админы, которым уходят все заявки
ADMIN_CHAT_IDS = tuple(
    int(x)
    for x in (env("ADMIN_CHAT_IDS", "367102417,108343575").split(","))
    if x.strip().isdigit()
)

# Резервные записи, если ссылки отсутствуют в таблице
EXTRA_CATALOG = {
    "test4333": {
        "product_name": "TEST Илья",
        "seller_name": "Илья Вольфсон",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    "test4422": {
        "product_name": "TEST Илья",
        "seller_name": "Илья Вольфсон",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    # Дополнительно добавленные deep-link слуги (нет в таблице)
    "foto9063": {
        "product_name": "foto9063",
        "seller_name": "Продавец",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    "foto1574": {
        "product_name": "foto1574",
        "seller_name": "Продавец",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    "foto7391": {
        "product_name": "foto7391",
        "seller_name": "Продавец",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    "car7419": {
        "product_name": "car7419",
        "seller_name": "Продавец",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    "car5930": {
        "product_name": "car5930",
        "seller_name": "Продавец",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    "car8167": {
        "product_name": "car8167",
        "seller_name": "Продавец",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    "massage0681": {
        "product_name": "massage0681",
        "seller_name": "Продавец",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    "yoga3851": {
        "product_name": "yoga3851",
        "seller_name": "Продавец",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    "exchange4321": {
        "product_name": "exchange4321",
        "seller_name": "Продавец",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    "flowers3448": {
        "product_name": "flowers3448",
        "seller_name": "Продавец",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
    "tours4861": {
        "product_name": "tours4861",
        "seller_name": "Продавец",
        "seller_chat_id": 367102417,
        "seller_username": None,
        "seller_contact_raw": "367102417",
    },
}

