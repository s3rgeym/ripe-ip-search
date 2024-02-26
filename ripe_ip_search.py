import requests
import argparse

import sys
from typing import Sequence, Any, NamedTuple, Iterable
from dataclasses import dataclass
import logging
import itertools
import ipaddress
import json
import os

__version__ = "0.1.0"

_LOG = logging.getLogger(__name__)


class ANSI:
    CSI = "\x1b["
    RESET = f"{CSI}m"
    CLEAR_LINE = f"{CSI}2K\r"
    BLACK = f"{CSI}30m"
    RED = f"{CSI}31m"
    GREEN = f"{CSI}32m"
    YELLOW = f"{CSI}33m"
    BLUE = f"{CSI}34m"
    MAGENTA = f"{CSI}35m"
    CYAN = f"{CSI}36m"
    WHITE = f"{CSI}37m"
    GREY = f"{CSI}90m"
    BRIGHT_RED = f"{CSI}91m"
    BRIGHT_GREEN = f"{CSI}92m"
    BRIGHT_YELLOW = f"{CSI}99m"
    BRIGHT_BLUE = f"{CSI}94m"
    BRIGHT_MAGENTA = f"{CSI}95m"
    BRIGHT_CYAN = f"{CSI}96m"
    BRIGHT_WHITE = f"{CSI}97m"


class ColorHandler(logging.StreamHandler):
    _log_colors: dict[int, str] = {
        logging.DEBUG: ANSI.GREEN,
        logging.INFO: ANSI.YELLOW,
        logging.WARNING: ANSI.RED,
        logging.ERROR: ANSI.RED,
        logging.CRITICAL: ANSI.RED,
    }

    _fmt = logging.Formatter("[%(levelname).1s] %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        message = self._fmt.format(record)
        return f"{self._log_colors[record.levelno]}{message}{ANSI.RESET}"


class NameSpace(argparse.Namespace):
    search_term: str
    verbosity: int
    detailed: bool


def parse_args(
    argv: Sequence[str] | None = None,
) -> tuple[argparse.ArgumentParser, NameSpace]:
    parser = argparse.ArgumentParser(
        description="Search ip adresses using RIPE DB"
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        action="count",
        default=0,
        help="increase verbosity level",
    )
    parser.add_argument(
        "--detailed",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="show detailed results",
    )
    parser.add_argument("search_term", help="search text")

    return parser, parser.parse_args(argv)


class ApiError(Exception):
    message: str = "An unexpected error has occurred"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.message
        super().__init__(self.message)


# class NotFound(ApiError):
#     message = "Not Found"


class SearchResult(NamedTuple):
    total: int
    start: int
    items: list[list[tuple[str, str]]]


@dataclass
class SearchClient:
    session: requests.Session | None = None
    api_url: str = "https://apps.db.ripe.net/db-web-ui/api/rest"

    def __post_init__(self):
        self.session = self.session or requests.session()

    def _get_search_params(self) -> dict[str, Any]:
        return {
            "facet": "true",
            "format": "xml",
            "hl": "true",
            "q": "",
            "start": 0,
            "wt": "json",
        }

    def _get_headers(self) -> dict[str, str]:
        return {"accept": "application/json"}

    def request(
        self, method: str, endpoint: str, *args: Any, **kwargs: Any
    ) -> dict:
        try:
            r = self.session.request(
                method, self.api_url + endpoint, *args, **kwargs
            )
            return r.json()
        except requests.JSONDecodeError as ex:
            raise ApiError() from ex

    def _normalize_docs(self, data: dict) -> list[list[tuple[str, str]]]:
        return [
            [
                (str_data["str"]["name"], str_data["str"].get("value", ""))
                for str_data in doc["doc"]["strs"]
            ]
            for doc in data["result"].get("docs", [])
        ]

    def search(self, arg: dict[str, Any] = {}, **params: Any) -> SearchResult:
        params = self._get_search_params() | arg | params

        _LOG.debug(f"search {params=}")

        data = self.request(
            "GET",
            "/fulltextsearch/select",
            params,
            headers=self._get_headers(),
        )

        assert data["result"]["name"] == "response"

        return SearchResult(
            total=data["result"]["numFound"],
            start=data["result"]["start"],
            items=self._normalize_docs(data),
        )


def get_networks(
    s: str,
) -> Iterable[ipaddress.IPv4Network] | Iterable[ipaddress.IPv6Network]:
    _LOG.debug("parse networks: %s", s)
    try:
        start_ip, end_ip = map(
            ipaddress.ip_address, map(str.strip, s.split("-"))
        )
        yield from ipaddress.summarize_address_range(start_ip, end_ip)
    except ValueError:
        try:
            yield ipaddress.ip_network(s)
        except ValueError:
            raise ValueError("invalid network: " + s)


def inetnum2dict(data: list[tuple[str, str]]) -> dict[str, str | list[str]]:
    # Некоторые поля встречаются более одного раза
    # $ whois -t inetnum | grep multiple | cut -d: -f1 | jq --raw-input . | jq --slurp .
    multiple_fields = [
        "descr",
        # фактически это поле не встречается более одного раза
        # "country",
        "language",
        "admin-c",
        "tech-c",
        "remarks",
        "notify",
        "mnt-by",
        "mnt-lower",
        "mnt-domains",
        "mnt-routes",
        "mnt-irt",
    ]

    rv = {}

    for key, value in data:
        if key in multiple_fields:
            rv.setdefault(key, [])
            rv[key].append(value)
        else:
            assert key not in rv
            rv[key] = value

    return rv


def main(argv: Sequence[str] | None = None) -> None:
    parser, args = parse_args(argv=argv)

    if not (search_term := args.search_term.strip()):
        parser.error("empty search text")

    logging_level = max(
        logging.DEBUG,
        logging.WARNING - args.verbosity * logging.DEBUG,
    )

    # logging.basicConfig(level=logging_level, handlers=[ColorHandler()])

    _LOG.setLevel(logging_level)
    _LOG.addHandler(ColorHandler())

    client = SearchClient()

    for start in itertools.count(step=10):
        search_result = client.search(
            q=f'("{search_term}") AND (object-type:inet6num OR object-type:inetnum)',
            start=start,
        )
        for item in search_result.items:
            item = inetnum2dict(item)
            _LOG.debug(item)
            assert item["object-type"] in ("inetnum", "inet6num")
            try:
                networks = list(get_networks(item["lookup-key"]))
                if args.detailed:
                    json.dump(
                        {
                            "networks": list(map(str, networks)),
                            "num_addresses": sum(
                                net.num_addresses for net in networks
                            ),
                            "item": item,
                        },
                        sys.stdout,
                    )
                    sys.stdout.write(os.linesep)
                else:
                    for net in networks:
                        print(net)
            except Exception as ex:
                _LOG.warning(ex)
        if start + len(search_result.items) >= search_result.total:
            break

    _LOG.info("Finished!")


if __name__ == "__main__":
    sys.exit(main())
