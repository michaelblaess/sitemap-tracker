"""Erkennung eines vorgeschalteten Proxy-/Auth-Gateways oder SSO-Logins.

Ein Proxy- oder Authentifizierungs-Gateway (z. B. Zscaler) bzw. ein SSO-Login
(z. B. Microsoft) faengt Anfragen ab und leitet sie per Redirect auf
einen eigenen Host um (z. B. gateway.zscloud.net, login.microsoftonline.com).
Der Crawler folgt externen Redirects auf fremde Domains bewusst nicht und
extrahiert dort keine Links - der Crawl bleibt dann bei den Seed-URLs haengen
und wirkt "unvollstaendig".

Die Erkennung laeuft als EINMALIGE Vorab-Pruefung der Start-URL: Landet sie nach
Redirects auf einer FREMDEN Registrable-Domain (eTLD+1), ist ein Gateway
vorgeschaltet. Wichtig ist die Registrable-Domain (nicht der exakte Host):
- gateway.zscloud.net -> zscloud.net  != kunde.example  -> Gateway erkannt.
- www.kunde.example        -> kunde.example    == kunde.example  -> KEIN Gateway (das sind
  legitime Sitefinity-Alias-/301-Weiterleitungen innerhalb derselben Domain).
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


@dataclass
class ProxyDetection:
    """Ergebnis der Proxy-/Gateway-Erkennung."""

    host: str  # fremder Host, auf den die Start-URL landet (z. B. gateway.zscloud.net)
    final_url: str  # vollstaendige End-URL nach allen Redirects


def _registrable(host: str) -> str:
    """Liefert die Registrable-Domain (vereinfacht: die letzten zwei Labels).

    Beispiele: www.blog.kunde.example -> kunde.example, gateway.zscloud.net ->
    zscloud.net. Hinweis: Dies ist eine Heuristik ohne Public-Suffix-Liste -
    mehrteilige TLDs (z. B. co.uk) werden nicht exakt behandelt, was fuer die
    hier relevanten Firmen-/Gateway-Domains aber genuegt.

    Args:
        host:
            Der Hostname.

    Returns:
        Die vereinfachte Registrable-Domain (lowercase).
    """
    host = host.lower().strip(".")
    # IP-Adressen unveraendert lassen.
    if not host or host.replace(".", "").isdigit():
        return host
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


async def probe_proxy(
    start_url: str,
    *,
    cookies: list[dict[str, str]] | None = None,
    user_agent: str = "",
    timeout: int = 30,
) -> ProxyDetection | None:
    """Prueft vorab, ob die Start-URL von einem Proxy/Gateway abgefangen wird.

    Fuehrt einen einzelnen GET (mit Redirect-Verfolgung) auf die Start-URL aus
    und vergleicht die Registrable-Domain der End-URL mit der der Start-URL.

    Args:
        start_url:
            Die zu pruefende Start-URL.
        cookies:
            Optionale Cookies (gleiche wie fuer den Crawl).
        user_agent:
            Optionaler User-Agent (leer = httpx-Default).
        timeout:
            Timeout in Sekunden.

    Returns:
        Ein ``ProxyDetection`` wenn die Start-URL auf eine fremde
        Registrable-Domain umgeleitet wird, sonst ``None`` (auch bei
        Netzwerkfehlern - die meldet dann der eigentliche Crawl).
    """
    start_host = (urlparse(start_url).hostname or "").lower()
    if not start_host:
        return None
    start_reg = _registrable(start_host)

    jar = httpx.Cookies()
    for c in cookies or []:
        jar.set(c["name"], c["value"])

    headers = {"User-Agent": user_agent} if user_agent else {}

    try:
        async with httpx.AsyncClient(
            timeout=float(timeout),
            follow_redirects=True,
            verify=False,
            cookies=jar,
            headers=headers,
        ) as client:
            response = await client.get(start_url)
    except Exception:
        # Netzwerkfehler -> kein Proxy-Urteil; der eigentliche Crawl meldet ihn.
        return None

    # Ohne Redirect kein Gateway.
    if not response.history:
        return None

    final_host = (urlparse(str(response.url)).hostname or "").lower()
    if final_host and _registrable(final_host) != start_reg:
        return ProxyDetection(host=final_host, final_url=str(response.url))
    return None
