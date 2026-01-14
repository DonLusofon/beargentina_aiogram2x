import argparse
import json
import logging
import os
import re
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

import config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


CatalogItem = Dict[str, Optional[str]]
catalog: Dict[str, CatalogItem] = {}
pending_new: Dict[int, Dict[str, Optional[str]]] = {}
pending_delete: Dict[int, Dict[str, Optional[str]]] = {}
extra_catalog: Dict[str, CatalogItem] = {}


def slugify(text: str) -> str:
    cleaned = re.sub(r"\s+", "-", text.strip().lower())
    cleaned = re.sub(r"[^a-z0-9\-_]+", "", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-_")
    return cleaned or ""


def normalize_username(raw: str) -> Optional[str]:
    if not raw:
        return None
    txt = raw.strip()
    # remove protocol and domain if given like https://t.me/username
    if txt.startswith("http"):
        try:
            parsed = urlparse(txt)
            if parsed.path:
                txt = parsed.path.lstrip("/")
        except Exception:  # noqa: BLE001
            txt = txt
    txt = txt.replace("@", "").strip()
    txt = txt.split()[0]
    if not txt or not re.match(r"^[A-Za-z0-9_]{3,}$", txt):
        return None
    return f"@{txt}"


def extract_slug(value: str) -> str:
    if not value:
        return ""
    txt = value.strip()
    parsed = None
    if "://" in txt or txt.startswith("t.me/") or txt.startswith("telegram.me/"):
        try:
            parsed = urlparse(txt)
        except Exception:  # noqa: BLE001
            parsed = None
    if parsed:
        qs = parse_qs(parsed.query)
        if qs.get("start"):
            return (qs["start"][0] or "").strip()
        last = parsed.path.rsplit("/", maxsplit=1)[-1].strip()
        if last.startswith("start="):
            return last.replace("start=", "", 1).strip()
        if last:
            return last
    if "start=" in txt:
        return txt.split("start=", 1)[-1].strip()
    return txt


def load_extra_catalog() -> Dict[str, CatalogItem]:
    path = getattr(config, "EXTRA_CATALOG_PATH", "")
    data: Dict[str, CatalogItem] = {}
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load EXTRA_CATALOG_PATH")
            data = {}
    if getattr(config, "EXTRA_CATALOG", None):
        data.update(config.EXTRA_CATALOG)
    return data


def save_extra_catalog(data: Dict[str, CatalogItem]) -> None:
    path = getattr(config, "EXTRA_CATALOG_PATH", "")
    if not path:
        return
    try:
        dir_path = os.path.dirname(path)
        os.makedirs(dir_path or ".", exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to save EXTRA_CATALOG_PATH")


async def _process_delete_input(user_id: int, text: str, message: types.Message) -> None:
    slug = extract_slug(text)

    if not slug:
        await message.answer("Не нашёл такую услугу. Введите slug ещё раз.")
        return

    item = catalog.get(slug)
    if not item:
        await message.answer("Услуга уже отсутствует.")
        pending_delete.pop(user_id, None)
        return

    deleted_name = item.get("product_name") or slug
    # удалить из каталога и extra_catalog
    catalog.pop(slug, None)
    if slug in extra_catalog:
        extra_catalog.pop(slug, None)
    extra_catalog[slug] = {"deleted": True}
    save_extra_catalog(extra_catalog)

    await message.answer(f'Услуга "{deleted_name}" была удалена.')
    pending_delete.pop(user_id, None)


def fetch_catalog() -> Dict[str, CatalogItem]:
    global extra_catalog
    extra_catalog = load_extra_catalog()
    data: Dict[str, CatalogItem] = {}
    added = 0
    for slug, item in extra_catalog.items():
        if item.get("deleted"):
            continue
        data[slug] = item
        added += 1
    logger.info("Loaded %d items from local catalog", added)
    return data


async def notify_seller(bot: Bot, item: CatalogItem, user: types.Message) -> bool:
    seller_chat_id = item.get("seller_chat_id")
    seller_username = item.get("seller_username")

    if not seller_chat_id and not seller_username:
        logger.warning("No seller contact for product %s", item.get("product_name"))
        return False

    if user and user.from_user:
        user_mention = f"@{user.from_user.username}" if user.from_user.username else user.from_user.mention_html()
    else:
        user_mention = "клиент"

    text = (
        f"🚀 Вам поступила заявка на услугу: \"{item.get('product_name', 'услуга')}\".\n"
        f"Заказчик: {user_mention}\n\n"
        "Свяжитесь, пожалуйста, с Заказчиком, в рабочее время."
    )

    try:
        target = seller_chat_id if seller_chat_id is not None else seller_username
        await bot.send_message(chat_id=target, text=text, parse_mode="HTML")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send notification to seller %s: %s", seller_chat_id or seller_username, exc)
        return False


async def notify_admins(bot: Bot, item: CatalogItem, user: types.Message) -> None:
    if not config.ADMIN_CHAT_IDS:
        return

    if user and user.from_user:
        user_mention = f"@{user.from_user.username}" if user.from_user.username else user.from_user.mention_html()
    else:
        user_mention = "клиент"

    seller_contact = item.get("seller_username") or ""

    text = (
        f"🚀 Заявка на услугу \"{item.get('product_name', 'услуга')}\".\n"
        f"Продавец: {item.get('seller_name', 'не указан')}"
        f"{f' {seller_contact}' if seller_contact else ''}\n"
        f"Заказчик: {user_mention}"
    )

    for admin_id in config.ADMIN_CHAT_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to notify admin %s: %s", admin_id, exc)


async def start_new_command(message: types.Message) -> None:
    if not message.from_user or message.from_user.id not in config.ADMIN_CHAT_IDS:
        await message.answer("Команда доступна только главным администраторам.")
        return
    pending_new[message.from_user.id] = {"step": "product"}
    await message.answer("Введите название услуги (колонка A).")


async def handle_new_flow(message: types.Message) -> None:
    user = message.from_user
    if not user or user.id not in pending_new:
        return

    state = pending_new[user.id]
    step = state.get("step")
    text = (message.text or "").strip()

    if step == "product":
        if not text:
            await message.answer("Название услуги не может быть пустым. Введите ещё раз.")
            return
        state["product_name"] = text
        state["step"] = "seller_name"
        await message.answer("Введите имя продавца (колонка D).")
        return

    if step == "seller_name":
        if not text:
            await message.answer("Имя продавца не может быть пустым. Введите ещё раз.")
            return
        state["seller_name"] = text
        state["step"] = "contact"
        await message.answer(
            "Введите числовой chat_id продавца. Узнать его можно в профиле (peer ID) "
            "или через бота @chatIDrobot."
        )
        return

    if step == "contact":
        contact_raw = text
        seller_chat_id = None
        seller_username = None
        if contact_raw.isdigit():
            seller_chat_id = int(contact_raw)
        if not seller_chat_id:
            await message.answer(
                "Нужен числовой chat_id. Откройте профиль (peer ID) или используйте @chatIDrobot и пришлите число."
            )
            return

        product_name = state.get("product_name") or "Услуга"
        seller_name = state.get("seller_name") or "Продавец"

        base_slug = slugify(product_name)
        slug = base_slug or slugify(seller_name) or "service"
        # гарантия уникальности
        if slug in catalog:
            idx = 2
            while f"{slug}-{idx}" in catalog:
                idx += 1
            slug = f"{slug}-{idx}"

        new_item = {
            "product_name": product_name,
            "seller_name": seller_name,
            "seller_chat_id": seller_chat_id,
            "seller_username": seller_username,
            "seller_contact_raw": contact_raw,
        }

        catalog[slug] = new_item
        extra_catalog[slug] = new_item
        save_extra_catalog(extra_catalog)

        pending_new.pop(user.id, None)

        if not config.BOT_USERNAME:
            link = f"(BOT_USERNAME не задан) slug: {slug}"
        else:
            link = f"https://t.me/{config.BOT_USERNAME}?start={slug}"

        await message.answer(
            "Создана новая услуга:\n"
            f"Название: {product_name}\n"
            f"Продавец: {seller_name}\n"
            f"Контакт: {seller_username or seller_chat_id}\n"
            f"Deep-link: {link}"
        )


async def start_delete_command(message: types.Message) -> None:
    if not message.from_user or message.from_user.id not in config.ADMIN_CHAT_IDS:
        await message.answer("Команда доступна только главным администраторам.")
        return
    if not catalog:
        await message.answer("Каталог пуст.")
        return

    user_id = message.from_user.id
    args = ""
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2:
            args = parts[1]
    # новая операция удаления
    pending_delete[user_id] = {}

    if args:
        await _process_delete_input(user_id, args, message)
    else:
        await message.answer("Введите slug услуги (то, что после start= в ссылке) или полную ссылку.")


async def handle_delete_flow(message: types.Message) -> None:
    user = message.from_user
    if not user or user.id not in pending_delete:
        return
    text = (message.text or "").strip()
    await _process_delete_input(user.id, text, message)


def build_customer_reply(item: CatalogItem) -> str:
    product_name = item.get("product_name") or "услуге"
    seller_username = item.get("seller_username") or ""
    support_contact = getattr(config, "SUPPORT_CONTACT", "@ksushasky")

    contact = seller_username or "представитель"
    return (
        f"Мы получили вашу заявку на услугу \"{product_name}\".\n\n"
        f"Партнер свяжется с Вами с аккаунта {contact} или Вы можете связаться с ним самостоятельно, написав в личные сообщения: {contact}\n\n"
        f"Если возникнут вопросы или сложности – пишите в нашу поддержку {support_contact}"
    )


async def handle_start(message: types.Message) -> None:
    payload = (message.get_args() or "").strip()

    if not payload:
        await message.answer(
            "Привет! Выберите услугу на сайте и нажмите кнопку «Заказать».\n"
            f"{config.SITE_BASE_URL}"
        )
        return

    item = catalog.get(payload)
    if not item:
        # на случай рассинхронизации памяти при рестарте/нескольких инстансах
        # перечитаем каталог ещё раз и попробуем найти снова
        catalog.update(fetch_catalog())
        item = catalog.get(payload)

    if not item:
        await message.answer(
            "Не смог найти товар по этой ссылке. "
            "Пожалуйста, вернитесь на сайт и нажмите кнопку «Заказать» ещё раз."
        )
        logger.warning("Unknown payload: %s", payload)
        return

    notified = await notify_seller(message.bot, item, message)
    await notify_admins(message.bot, item, message)
    await message.answer(build_customer_reply(item))


def main(print_links: bool = False) -> None:
    global catalog
    catalog = fetch_catalog()

    if print_links:
        if not config.BOT_USERNAME:
            raise RuntimeError("BOT_USERNAME is not set, cannot print links")
        for slug, item in catalog.items():
            link = f"https://t.me/{config.BOT_USERNAME}?start={slug}"
            print(f"{item.get('product_name', slug)} -> {link}")
        return

    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(bot)

    # handlers
    dp.register_message_handler(handle_start, commands=["start"])
    dp.register_message_handler(start_new_command, commands=["new"])
    dp.register_message_handler(start_delete_command, commands=["delete"])
    dp.register_message_handler(handle_new_flow, lambda m: m.from_user and m.from_user.id in pending_new)
    dp.register_message_handler(handle_delete_flow, lambda m: m.from_user and m.from_user.id in pending_delete)

    logger.info("Bot started")
    executor.start_polling(dp, skip_updates=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Beargentino marketplace bot")
    parser.add_argument("--print-links", action="store_true", help="Print start links for all products and exit")
    args = parser.parse_args()

    main(print_links=args.print_links)

