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
    """Авто-отправка сообщений для депозита раз в 3 дня"""
    strings = {
        "name": "sBFG11",
        "enabled": "✅ Авто-отправка включена! Буду отправлять сообщения раз в 3 дня.",
        "disabled": "🛑 Авто-отправка выключена.",
        "already_enabled": "⚠️ Уже включено.",
        "not_enabled": "⚠️ Авто-отправка не была включена.",
    }

    def __init__(self):
        self._task = None
        self._chat_id = None
        self._enabled = False

    async def client_ready(self, client, db):
        # Проверяем, был ли модуль включен до перезагрузки
        state = self.db.get("sbfg11", "state", {"enabled": False, "chat_id": None, "last_run": 0})
        if state["enabled"] and state["chat_id"]:
            self._enabled = True
            self._chat_id = state["chat_id"]
            if not self._task or self._task.done():
                self._task = asyncio.create_task(self._loop())

    def _get_state(self):
        return self.db.get("sbfg11", "state", {"enabled": False, "chat_id": None, "last_run": 0})

    def _set_state(self, state):
        self.db.set("sbfg11", "state", state)

    async def _send_pair(self, chat_id):
        try:
            # Отправляем напрямую через клиент, без utils
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
            return True
        except Exception as e:
            logger.exception(f"sBFG11 send error: {e}")
            return False

    async def _loop(self):
        while self._enabled:
            state = self._get_state()
            if not state["enabled"]:
                break
            chat_id = state["chat_id"]
            last_run = state["last_run"]
            now = int(time.time())
            interval = 3 * 86400 # 3 дня
            elapsed = now - last_run

            if last_run == 0 or elapsed >= interval:
                await self._send_pair(chat_id)
                state["last_run"] = now
                self._set_state(state)
                await asyncio.sleep(interval)
            else:
                wait = interval - elapsed
                await asyncio.sleep(wait)

    @loader.command
    async def sdep(self, message: Message):
        """.sdep — включить авто-отправку"""
        state = self._get_state()
        if state["enabled"]:
            # Используем message.edit вместо utils.answer
            await message.edit(self.strings("already_enabled"))
            return
        state = {"enabled": True, "chat_id": message.chat_id, "last_run": 0}
        self._set_state(state)
        self._enabled = True
        self._chat_id = message.chat_id
        self._task = asyncio.create_task(self._loop())
        # Используем message.edit вместо utils.answer
        await message.edit(self.strings("enabled"))

    @loader.command
    async def ddep(self, message: Message):
        """.ddep — выключить"""
        state = self._get_state()
        if not state["enabled"]:
            await message.edit(self.strings("not_enabled"))
            return
        self._enabled = False
        if self._task:
            self._task.cancel()
            self._task = None
        state["enabled"] = False
        self._set_state(state)
        await message.edit(self.strings("disabled"))
