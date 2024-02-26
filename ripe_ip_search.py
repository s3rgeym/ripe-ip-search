#!/usr/bin/env python
import requests
import argparse

import sys
from typing import (
    Sequence,
    Any,
    NamedTuple,
    Iterable,
    TypedDict,
    NotRequired,
    Literal,
)
from dataclasses import dataclass
from urllib.parse import urljoin
from functools import cached_property, partial
import logging
import itertools
import ipaddress
import json
import os
import time

__version__ = "0.1.9"
__author__ = "Sergey M"

_LOG = logging.getLogger(__name__)

print_stderr = partial(print, file=sys.stderr)

# for font in $(ls -1 /usr/share/figlet/ | sed '/[-_]/d' | sed 's/\..*$//g'); do toilet -f "$font" "$(basename $PWD)"; done
BANNER = r"""
      _                  _                                     _
 _ __(_)_ __   ___      (_)_ __        ___  ___  __ _ _ __ ___| |__
| '__| | '_ \ / _ \_____| | '_ \ _____/ __|/ _ \/ _` | '__/ __| '_ \
| |  | | |_) |  __/_____| | |_) |_____\__ \  __/ (_| | | | (__| | | |
|_|  |_| .__/ \___|     |_| .__/      |___/\___|\__,_|_|  \___|_| |_|
       |_|                |_|
"""


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
    details: bool
    banner: bool
    delay: float


def parse_args(
    argv: Sequence[str] | None = None,
) -> tuple[argparse.ArgumentParser, NameSpace]:
    parser = argparse.ArgumentParser(
        description="Search ip adresses using RIPE DB",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--banner",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="show banner",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.334,
        help="delay between requests in seconds",
    )
    parser.add_argument(
        "--details",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="show details",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        action="count",
        default=0,
        help="increase verbosity level",
    )
    parser.add_argument("search_term", nargs="+", help="search text")

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


class InetnumDict(
    TypedDict(
        "_InetnumDict",
        {
            "object-type": Literal["inetnum", "inet6num"],
            "primary-key": str,
            "lookup-key": str,
        },
    )
):
    country: NotRequired[list[str]]
    inetnum: NotRequired[str]
    inet6num: NotRequired[str]
    netname: NotRequired[str]
    descr: NotRequired[list[str]]
    notify: NotRequired[list[str]]
    remarks: NotRequired[list[str]]
    status: NotRequired[str]
    ...


@dataclass
class SearchClient:
    request_delay: float = 0.3
    session: requests.Session | None = None
    api_url: str = "https://apps.db.ripe.net/db-web-ui/api/rest"
    last_request: float = 0.0

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

    @cached_property
    def referer(self) -> str:
        return urljoin(self.api_url, "/db-web-ui/fulltextsearch")

    def _get_headers(self) -> dict[str, str]:
        # по факту нужен только один заголовок
        # return {"accept": "application/json"}
        return {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json; charset=utf-8",
            "Referer": self.referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }

    def request(
        self, method: str, endpoint: str, *args: Any, **kwargs: Any
    ) -> dict:
        try:
            if (
                dt := self.last_request - time.monotonic() + self.request_delay
            ) > 0:
                _LOG.debug("wait before request: %.3fs", dt)
                time.sleep(dt)
            r = self.session.request(
                method,
                self.api_url + endpoint,
                *args,
                headers=self._get_headers(),
                **kwargs,
            )
            return r.json()
        except requests.JSONDecodeError as ex:
            raise ApiError() from ex
        finally:
            self.last_request = time.monotonic()

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
        )

        assert data["result"]["name"] == "response"

        return SearchResult(
            total=data["result"]["numFound"],
            start=data["result"]["start"],
            items=self._normalize_docs(data),
        )

    def _inetnum2dict(self, data: list[tuple[str, str]]) -> InetnumDict:
        # Некоторые поля встречаются более одного раза
        # $ whois -t inetnum | grep multiple | cut -d: -f1 | jq --raw-input . | jq --slurp .
        multiple_fields = [
            "descr",
            # я думал, что country не может дублироваться, но все же нашел такую запись
            "country",
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
                assert key not in rv, f"duplcated key: {key}"
                rv[key] = value

        return rv

    def _quote(self, s: str) -> str:
        # как оказалось кавычки необязательны
        return s if s.isalnum() else '"' + s.replace('"', r"\"") + '"'

    def search_inetnums(self, search_term: str) -> Iterable[InetnumDict]:
        step = 10
        for start in itertools.count(step=step):
            search_result = self.search(
                q=f"({self._quote(search_term)}) AND (object-type:inetnum OR object-type:inet6num)",
                start=start,
            )
            assert step >= len(search_result.items)
            yield from map(self._inetnum2dict, search_result.items)
            processed = start + len(search_result.items)
            _LOG.debug(
                "search results processed: %d/%d",
                processed,
                search_result.total,
            )
            if processed >= search_result.total:
                break


def get_networks(
    s: str,
) -> Iterable[ipaddress.IPv4Network] | Iterable[ipaddress.IPv6Network]:
    # _LOG.debug("parse networks: %s", s)
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


def main(argv: Sequence[str] | None = None) -> int | None:
    parser, args = parse_args(argv=argv)

    if not (search_term := " ".join(args.search_term).strip()):
        parser.error("empty search text")

    logging_level = max(
        logging.DEBUG,
        logging.WARNING - args.verbosity * logging.DEBUG,
    )

    # logging.basicConfig(level=logging_level, handlers=[ColorHandler()])

    _LOG.setLevel(logging_level)
    _LOG.addHandler(ColorHandler())

    if args.banner:
        print_stderr(BANNER)

    try:
        client = SearchClient(request_delay=args.delay)
        for item in client.search_inetnums(search_term=search_term):
            _LOG.debug(item)
            assert item["object-type"] in ("inetnum", "inet6num")
            # try:
            networks = list(get_networks(item["lookup-key"]))
            if args.details:
                json.dump(
                    {
                        "networks": list(map(str, networks)),
                        "num_addresses": sum(
                            net.num_addresses for net in networks
                        ),
                        "details": item,
                    },
                    sys.stdout,
                )
                sys.stdout.write(os.linesep)
            else:
                for net in networks:
                    print(net)
            # тут я отлавливал ошибку с неправильным ip range, но лучше пусть свалится
            # except Exception as ex:
            #     _LOG.warning(ex)
        _LOG.info("Finished!")
    except KeyboardInterrupt:
        _LOG.critical("Search interrupted by user")
        return 1


if __name__ == "__main__":
    sys.exit(main())
