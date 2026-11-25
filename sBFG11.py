# meta developer: @sBFG11
# scope: hikka_only

from .. import loader, utils
from herokutl.tl.functions.messages import SendMessageRequest
from herokutl.tl.types import Message
import asyncio
import time
import logging
import random  # Добавили для генерации ID

logger = logging.getLogger(__name__)

@loader.tds
class sBFG11(loader.Module):
    """Авто-отправка сообщений для депозита раз в 3 дня"""
    strings = {
        "name": "sBFG11",
        "enabled": "✅ <b>Авто-отправка включена!</b>\nБуду отправлять «депозит снять всё» и «депозит положить всё» раз в 3 дня в этот чат.",
        "disabled": "🛑 <b>Авто-отправка выключена.</b>",
        "already_enabled": "⚠️ Уже включено.",
        "not_enabled": "⚠️ Авто-отправка не была включена.",
    }

    def __init__(self):
        self._task = None
        self._chat_id = None
        self._enabled = False

    async def client_ready(self, client, db):
        self.db = db
        state = self._get_state()
        if state.get("enabled") and state.get("chat_id"):
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
            # Используем стандартный random.randint для ID
            await self._client(SendMessageRequest(
                peer=chat_id,
                message="депозит снять всё",
                random_id=random.randint(1, 2**63 - 1)
            ))
            await asyncio.sleep(1)
            await self._client(SendMessageRequest(
                peer=chat_id,
                message="депозит положить всё",
                random_id=random.randint(1, 2**63 - 1)
            ))
            return True
        except Exception as e:
            logger.exception(f"sBFG11 send error: {e}")
            return False

    async def _loop(self):
        while self._enabled:
            state = self._get_state()
            if not state.get("enabled"):
                break
            chat_id = state["chat_id"]
            last_run = state.get("last_run", 0)
            now = int(time.time())
            interval = 3 * 86400  # 3 дня
            elapsed = now - last_run

            if last_run == 0 or elapsed >= interval:
                await self._send_pair(chat_id)
                state["last_run"] = now
                self._set_state(state)
                await asyncio.sleep(interval)
            else:
                wait = interval - elapsed
                await asyncio.sleep(wait)

    @loader.command(args=True)
    async def sdep(self, message: Message):
        """.sdep — депозит снять/положить (включить)"""
        state = self._get_state()
        if state.get("enabled"):
            await utils.answer(message, self.strings("already_enabled"))
            return
        state = {"enabled": True, "chat_id": message.chat_id, "last_run": 0}
        self._set_state(state)
        self._enabled = True
        self._chat_id = message.chat_id
        self._task = asyncio.create_task(self._loop())
        await utils.answer(message, self.strings("enabled"))

    @loader.command(args=True)
    async def ddep(self, message: Message):
        """.ddep — выключить"""
        state = self._get_state()
        if not state.get("enabled"):
            await utils.answer(message, self.strings("not_enabled"))
            return
        self._enabled = False
        if self._task:
            self._task.cancel()
            self._task = None
        state["enabled"] = False
        self._set_state(state)
        await utils.answer(message, self.strings("disabled"))
