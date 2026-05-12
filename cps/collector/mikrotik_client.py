"""
MikroTik RouterOS REST API client.

Uses the /rest endpoint available in RouterOS 7.1+.
Create a dedicated read-only API user in RouterOS:
  /user group add name=api-readonly policy=read,api,!local,!telnet,!ssh,!ftp,!reboot,!write,!policy,!test,!winbox,!password,!web,!sniff,!sensitive,!romon
  /user add name=api-user group=api-readonly password=api-password
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


@dataclass
class DhcpLease:
    mac_address: str
    ip_address: str
    hostname: str
    status: str          # "bound" | "waiting"
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_active(self) -> bool:
        return self.status == "bound"


class MikrotikClient:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 443,
        verify_ssl: bool = False,
        timeout: int = 10,
    ) -> None:
        self._base_url = f"https://{host}:{port}/rest"
        self._session = requests.Session()
        self._session.auth = (username, password)
        self._session.verify = verify_ssl
        self._timeout = timeout

    def _get(self, path: str, **params) -> list[dict]:
        url = f"{self._base_url}{path}"
        try:
            resp = self._session.get(url, params=params, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.SSLError as exc:
            logger.error("SSL error connecting to MikroTik: %s", exc)
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("Cannot reach MikroTik at %s: %s", url, exc)
            raise
        except requests.exceptions.HTTPError as exc:
            logger.error("HTTP %s from MikroTik: %s", exc.response.status_code, exc)
            raise

    def get_dhcp_leases(self) -> list[DhcpLease]:
        """Return all DHCP leases from all servers."""
        raw = self._get("/ip/dhcp-server/lease")
        leases: list[DhcpLease] = []
        for entry in raw:
            leases.append(
                DhcpLease(
                    mac_address=entry.get("mac-address", ""),
                    ip_address=entry.get("address", ""),
                    hostname=entry.get("host-name", entry.get("mac-address", "")),
                    status=entry.get("status", "waiting"),
                )
            )
        return leases

    def get_active_leases(self) -> list[DhcpLease]:
        """Return only leases with status == 'bound'."""
        return [l for l in self.get_dhcp_leases() if l.is_active]


class PresenceCollector:
    """Polls MikroTik periodically and persists presence data to SQLite."""

    def __init__(self, client: MikrotikClient, db, poll_interval: int = 30) -> None:
        self._client = client
        self._db = db
        self._poll_interval = poll_interval

    def run_forever(self) -> None:
        logger.info("Starting presence collector (interval=%ds)", self._poll_interval)
        while True:
            try:
                self._collect_once()
            except Exception as exc:
                logger.warning("Collection error (will retry): %s", exc)
            time.sleep(self._poll_interval)

    def _collect_once(self) -> None:
        leases = self._client.get_active_leases()
        count = len(leases)
        ts = datetime.now(timezone.utc)
        self._db.record_snapshot(ts, count, leases)
        logger.debug("Snapshot recorded: %d active clients at %s", count, ts.isoformat())