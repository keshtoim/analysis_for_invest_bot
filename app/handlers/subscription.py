from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from app.config import OWNER_CHAT_ID
from app.db.database import get_subscription, grant_subscription, revoke_subscription
from app.keyboards.subscription import subscription_keyboard
from app.models.analysis_type import ANALYSIS_TYPE_LABELS, AnalysisType
from app.services.stats_service import get_stats
from app.utils.html import escape_html

router = Router()

FREE_VERSION_TEXT = (
    "Сейчас бот полностью бесплатный — платные подписки ещё не подключены. "
    "Просто пользуйся анализом 🙂"
)


def _is_owner(user_id: int) -> bool:
    return bool(OWNER_CHAT_ID) and str(user_id) == str(OWNER_CHAT_ID)


@router.message(Command("subscription"))
async def cmd_subscription(message: Message) -> None:
    sub = await get_subscription(message.from_user.id)
    active = sub is not None and datetime.fromisoformat(sub["expires_at"]) > datetime.utcnow()

    if active:
        text = f"Подписка «{sub['plan']}» активна до {sub['expires_at'][:10]}."
    else:
        text = "Активной подписки нет."

    await message.answer(text, reply_markup=subscription_keyboard())


@router.callback_query(F.data == "subscription:purchase")
async def handle_purchase(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(FREE_VERSION_TEXT)


@router.message(Command("grant_subscription"))
async def cmd_grant_subscription(message: Message, command: CommandObject) -> None:
    if not _is_owner(message.from_user.id):
        return

    args = (command.args or "").split()
    if len(args) != 2:
        await message.answer("Формат: /grant_subscription <user_id> <дней>")
        return

    try:
        target_user_id, days = int(args[0]), int(args[1])
    except ValueError:
        await message.answer("user_id и дни должны быть числами.")
        return

    await grant_subscription(target_user_id, days=days, source="manual")
    await message.answer(f"Подписка выдана: user_id={target_user_id}, на {days} дн.")


@router.message(Command("revoke_subscription"))
async def cmd_revoke_subscription(message: Message, command: CommandObject) -> None:
    if not _is_owner(message.from_user.id):
        return

    args = (command.args or "").split()
    if len(args) != 1:
        await message.answer("Формат: /revoke_subscription <user_id>")
        return

    try:
        target_user_id = int(args[0])
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return

    await revoke_subscription(target_user_id)
    await message.answer(f"Подписка отозвана: user_id={target_user_id}")


def _format_stats(stats: dict) -> str:
    lines = [
        "<b>📊 Статистика бота</b>",
        "",
        "<b>Пользователи</b>",
        f"- Всего: {stats['total_users']}",
        f"- Новых за 24ч: {stats['new_users_24h']}",
        f"- Новых за 7д: {stats['new_users_7d']}",
        "",
        "<b>Запросы анализа</b>",
        f"- Всего: {stats['total_requests']}",
        f"- За 24ч: {stats['requests_24h']}",
        f"- За 7д: {stats['requests_7d']}",
        f"- Активных юзеров за 7д: {stats['active_users_7d']}",
    ]

    if stats["requests_by_type"]:
        lines.append("")
        lines.append("<b>По видам анализа</b>")
        for atype_value, count in stats["requests_by_type"]:
            try:
                label = ANALYSIS_TYPE_LABELS[AnalysisType(atype_value)]
            except ValueError:
                label = atype_value
            lines.append(f"- {label}: {count}")

    if stats["top_companies"]:
        lines.append("")
        lines.append(f"<b>Топ-{len(stats['top_companies'])} компаний</b>")
        for company, count in stats["top_companies"]:
            lines.append(f"- {escape_html(company)}: {count}")

    lines.append("")
    lines.append("<b>Прочее</b>")
    lines.append(f"- Компаний в кэше: {stats['cached_companies']}")
    lines.append(f"- Активных подписок: {stats['active_subscriptions']}")
    lines.append(f"- Бот жив (heartbeat): {'да' if stats['bot_alive'] else 'нет'}")

    return "\n".join(lines)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not _is_owner(message.from_user.id):
        return

    stats = await get_stats()
    await message.answer(_format_stats(stats))
