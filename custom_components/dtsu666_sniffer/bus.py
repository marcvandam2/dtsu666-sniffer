"""Leest de DTSU666: passief (ruwe RTU-frames) of actief (Modbus TCP)."""
from __future__ import annotations

import asyncio
import logging
import struct
import time
from typing import Callable

from .const import CURRENT_BLOCK, MODE_SNIFF, POLL_BLOCKS, REGS, VOLTAGE_BLOCK

_LOGGER = logging.getLogger(__name__)


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def _crc_ok(frame: bytes) -> bool:
    return len(frame) > 3 and crc16(frame[:-2]) == struct.unpack("<H", frame[-2:])[0]


def decode(start: int, payload: bytes) -> dict[str, float]:
    """Zet registerdata (vanaf `start`) om naar waarden volgens REGS."""
    out = {}
    for i in range(0, len(payload) - 3, 4):
        reg = start + i // 2
        if reg in REGS:
            key, _n, _u, factor, *_ = REGS[reg]
            out[key] = round(struct.unpack(">f", payload[i:i + 4])[0] * factor, 4)
    return out


def _mbap_len(buf: bytes) -> int:
    """Lengte van een Modbus TCP-frame vooraan in `buf`, 0 als het er geen is."""
    if len(buf) < 8 or buf[2:4] != b"\0\0":
        return 0
    ln = struct.unpack(">H", buf[4:6])[0]
    return 6 + ln if 3 <= ln <= 254 and buf[7] in (3, 4, 0x10, 0x83, 0x84, 0x90) else 0


def parse_rtu(buf: bytes, pending: dict[tuple[int, int], int], slave: int):
    """Haalt complete frames uit `buf`. Geeft (rest, [waarden-dicts]) terug.

    Transparant kanaal: ruwe RTU-frames met CRC. Kanaal op Modbus TCP: de Waveshare
    stuurt het busverkeer van de Deye door als Modbus TCP-frames (MBAP-kop, geen CRC).
    `pending` onthoudt per (adres, aantal registers) het startregister van de laatste
    vraag, zodat het antwoord (dat geen registeradres bevat) aan de juiste registers
    gekoppeld wordt; onze eigen stroomvraag (8 registers) verschilt in lengte van die
    van de Deye (6 en 12).
    """
    found = []
    while len(buf) >= 5:
        adr, fn = buf[0], buf[1]
        used = 0
        size = _mbap_len(buf)
        if size and not (fn in (3, 4) and len(buf) >= 8 and _crc_ok(buf[:8])):
            if len(buf) < size:
                break
            unit, mfn, pdu = buf[6], buf[7], buf[8:size]
            if mfn in (3, 4) and len(pdu) == 4:
                start, count = struct.unpack(">HH", pdu)
                pending[(unit, count)] = start
            elif mfn in (3, 4) and pdu and pdu[0] == len(pdu) - 1 and (unit, pdu[0] // 2) in pending:
                if unit == slave:
                    found.append(decode(pending[(unit, pdu[0] // 2)], pdu[1:]))
            buf = buf[size:]
            continue
        if fn in (3, 4):
            n = buf[2]
            if (adr, n // 2) in pending and len(buf) >= 5 + n and _crc_ok(buf[:5 + n]):
                if adr == slave:
                    found.append(decode(pending[(adr, n // 2)], buf[3:3 + n]))
                used = 5 + n
            elif len(buf) >= 8 and _crc_ok(buf[:8]):
                start, count = struct.unpack(">HH", buf[2:6])
                pending[(adr, count)] = start
                used = 8
            elif len(buf) < max(8, 5 + n):
                break  # frame nog niet compleet
        elif fn == 0x10 and len(buf) >= 8 and _crc_ok(buf[:8]):
            used = 8  # antwoord op schrijven, overslaan
        elif len(buf) < 8:
            break
        buf = buf[used:] if used else buf[1:]
    return buf, found


class Dtsu666Bus:
    def __init__(self, host, port, mode, slave, interval, on_data: Callable[[dict], None],
                 u_interval=0):
        self.host, self.port, self.mode = host, port, mode
        self.slave, self.interval, self.on_data = slave, interval, on_data
        self.u_interval = u_interval  # spanning vragen elke n s, 0 = nooit
        self._task: asyncio.Task | None = None
        self.last_seen = 0.0
        self.ask = False  # schakelaar 'Stroom zelf meevragen', standaard uit

    def start(self, hass):
        self._task = hass.async_create_background_task(self._run(), "dtsu666_sniffer")

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def _run(self):
        while True:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), 10)
                _LOGGER.info("Verbonden met %s:%s (%s)", self.host, self.port, self.mode)
                try:
                    if self.mode == MODE_SNIFF:
                        await self._sniff(reader, writer)
                    else:
                        await self._poll(reader, writer)
                finally:
                    writer.close()
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Verbinding %s:%s weg (%s), opnieuw over 10 s",
                                self.host, self.port, err)
            await asyncio.sleep(10)

    async def _sniff(self, reader, writer):
        """Meelezen tussen de Deye (master) en de meter.

        De Deye leest alleen Pa/Pb/Pc en de kWh-tellers. Met `ask` aan vragen we zelf
        U en I (elke `interval` s), anders alleen U (elke `u_interval` s), direct na een antwoord aan de Deye: dan is de bus
        even stil en botst onze vraag niet met de zijne (getoetst 2 nov 2026, elke 1 s:
        Deye mist 3 van 302 met onze vraag, 7 van 317 zonder).
        """
        buf = b""
        pending: dict[tuple[int, int], int] = {}
        mbap = None
        last_ask = last_u = 0.0
        while True:
            chunk = await asyncio.wait_for(reader.read(1024), 120)
            if not chunk:
                raise ConnectionError("gesloten door de gateway")
            if mbap is None:
                mbap = bool(_mbap_len(chunk))
            buf, found = parse_rtu(buf + chunk, pending, self.slave)
            for data in found:
                self._emit(data)
            if not found:
                continue
            now = time.monotonic()
            if self.ask and now - last_ask >= max(self.interval, 1):
                last_ask = last_u = now
                start, count = CURRENT_BLOCK
            elif self.u_interval and now - last_u >= self.u_interval:
                last_u = now
                start, count = VOLTAGE_BLOCK
            else:
                continue
            pdu = struct.pack(">BBHH", self.slave, 3, start, count)
            writer.write(struct.pack(">HHH", 9, 0, 6) + pdu if mbap
                         else pdu + struct.pack("<H", crc16(pdu)))
            await writer.drain()
            pending[(self.slave, count)] = start

    async def _poll(self, reader, writer):
        """Actief: zelf vragen via de Modbus TCP-gateway."""
        tid = 0
        while True:
            data = {}
            for start, count in POLL_BLOCKS:
                tid = (tid + 1) & 0xFFFF
                writer.write(struct.pack(">HHHBBHH", tid, 0, 6, self.slave, 3, start, count))
                await writer.drain()
                head = await asyncio.wait_for(reader.readexactly(8), 5)
                if head[7] & 0x80:
                    await reader.readexactly(1)
                    raise ConnectionError(f"modbus-fout op {start:#x}")
                n = (await asyncio.wait_for(reader.readexactly(1), 5))[0]
                data.update(decode(start, await asyncio.wait_for(reader.readexactly(n), 5)))
            self._emit(data)
            await asyncio.sleep(self.interval)

    def _emit(self, data):
        # de Deye leest alleen Pa/Pb/Pc; het totaal is hun som
        if "p_t" not in data and all(k in data for k in ("p_a", "p_b", "p_c")):
            data["p_t"] = round(data["p_a"] + data["p_b"] + data["p_c"], 1)
        if data:
            self.last_seen = time.time()
            self.on_data(data)
