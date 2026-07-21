"""Rate-Limit fuer ausgehende Requests.

Warum das noetig ist: Die Parallelitaet (Semaphore) begrenzt nur, wie viele
Requests GLEICHZEITIG laufen - nicht, wie viele pro Minute rausgehen. Antwortet
der Server schnell, crawlt das Werkzeug entsprechend schnell weiter. Anders als
bei einem Sitemap-Scan steht die Zahl der Seiten hier vorher nicht fest: der
Crawler folgt Links bis zur eingestellten Tiefe und kann eine grosse Website
vollstaendig durchlaufen. Mit aktivem Rendering laeuft dabei jeder Aufruf an den
Zwischenspeichern des Servers vorbei und erzeugt ein Vielfaches der Last eines
normalen Besuchers.

Der Limiter verteilt die Requests gleichmaessig ueber die Zeit (kein Burst):
bei 60 Requests/Minute geht genau einer pro Sekunde raus. Gewartet wird
ausserhalb des Locks, damit sich mehrere Aufrufer ihre Slots vorab holen und
parallel warten koennen, statt sich gegenseitig zu serialisieren.
"""

from __future__ import annotations

import asyncio


class RateLimiter:
    """Verteilt Requests gleichmaessig ueber die Zeit.

    Ist die Rate 0 oder negativ, ist der Limiter abgeschaltet und `acquire()`
    kehrt sofort zurueck - so laesst sich das Objekt bedingungslos einhaengen,
    ohne an jeder Aufrufstelle auf None zu pruefen.
    """

    def __init__(self, per_minute: int) -> None:
        self._interval = 60.0 / per_minute if per_minute > 0 else 0.0
        self._lock = asyncio.Lock()
        self._next_slot = 0.0

    @property
    def enabled(self) -> bool:
        """Gibt zurueck, ob tatsaechlich gedrosselt wird."""
        return self._interval > 0.0

    async def acquire(self) -> None:
        """Wartet, bis der naechste Zeitschlitz frei ist."""
        if self._interval <= 0.0:
            return

        loop = asyncio.get_running_loop()
        async with self._lock:
            now = loop.time()
            # Liegt der letzte Slot in der Vergangenheit, startet die Kette neu
            # bei jetzt - sonst wuerde eine Pause spaeter zu einem Burst fuehren.
            slot = max(now, self._next_slot)
            self._next_slot = slot + self._interval

        delay = slot - now
        if delay > 0:
            await asyncio.sleep(delay)
