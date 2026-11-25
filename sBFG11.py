# meta developer: @sBFG11
# scope: hikka_only

from .. import loader, utils
from herokutl.tl.functions.messages import SendMessageRequest
from herokutl.tl.types import Message
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

@loader.tds
class sBFG11(loader.Module):
    """Авто-отправка двух сообщений раз в 3 дня"""
    strings = {
        "name": "sBFG11",
        "enabled": "✅ <b>Авто-отправка включена!</b>\nБуду отправлять «депозит снять всё» и «депозит положить всё» раз в 3 дня в этот чат.",
        "disabled": "🛑 <b>Авто-отправка выключена.</b>",
        "already_enabled": "⚠️ Уже включено.",
        "not_enabled": "⚠️ Авто-отправка не была включена.",
        "started_now": "🚀 <b>Первый цикл отправлен сразу.</b> Следующий — через 3 дня.",
    }

    def __init__(self):
        self._task = None
        self._chat_id = None
        self._enabled = False

    async def _get_state(self):
        """Получить состояние из БД"""
        return await self.db.get("sbfg11", "state", {"enabled": False, "chat_id": None, "last_run": 0})

    async def _set_state(self, state):
        await self.db.set("sbfg11", "state", state)

    async def _send_pair(self, chat_id):
        """Отправить два сообщения подряд"""
        try:
            await self._client(SendMessageRequest(
                peer=chat_id,
                message="депозит снять всё",
                random_id=utils.get_random_id()
            ))
            await asyncio.sleep(1)
            await self._client(SendMessageRequest(
                peer=chat_id,
                message="депозит положить всё",
                random_id=utils.get_random_id()
            ))
            logger.info(f"sBFG11: sent pair to {chat_id}")
            return True
        except Exception as e:
            logger.exception(f"sBFG11 send error: {e}")
            return False

    async def _loop(self):
        """Бесконечный цикл с интервалом 3 дня"""
        while self._enabled:
            state = await self._get_state()
            if not state["enabled"]:
                break
            chat_id = state["chat_id"]
            last_run = state["last_run"]
            now = int(time.time())
            interval = 3 * 86400  # 3 дня в секундах
            elapsed = now - last_run

            if last_run == 0 or elapsed >= interval:
                await self._send_pair(chat_id)
                state["last_run"] = now
                await self._set_state(state)
                await asyncio.sleep(interval)
            else:
                # Ждём до следующего запуска
                wait = interval - elapsed
                await asyncio.sleep(wait)

    @loader.on_load
    async def _restore_on_load(self):
        """Восстановить цикл после перезагрузки модуля/бота"""
        state = await self._get_state()
        if state["enabled"] and state["chat_id"]:
            self._enabled = True
            self._chat_id = state["chat_id"]
            if not self._task or self._task.done():
                self._task = asyncio.create_task(self._loop())

    @loader.command
    async def sdepcmd(self, message: Message):
        """.sdep — включить авто-отправку двух сообщений раз в 3 дня"""
        state = await self._get_state()
        if state["enabled"]:
            await utils.answer(message, self.strings("already_enabled"))
            return
        state = {"enabled": True, "chat_id": message.chat_id, "last_run": 0}
        await self._set_state(state)
        self._enabled = True
        self._chat_id = message.chat_id
        self._task = asyncio.create_task(self._loop())
        await utils.answer(message, self.strings("enabled"))

    @loader.command
    async def ddepcmd(self, message: Message):
        """.ddep — выключить авто-отправку"""
        state = await self._get_state()
        if not state["enabled"]:
            await utils.answer(message, self.strings("not_enabled"))
            return
        self._enabled = False
        if self._task:
            self._task.cancel()
            self._task = None
        state["enabled"] = False
        await self._set_state(state)
        await utils.answer(message, self.strings("disabled"))
