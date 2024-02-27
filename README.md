# ripe-ip-search

Tool to search ip addresses using RIPE DB. It uses [fulltext search API](https://apps.db.ripe.net/db-web-ui/fulltextsearch) and help to find ip addresses owned by companies. Useful for port scanning and etc.

Installation:

```bash
# latest pypi version
pipx install ripe-ip-search

# latest github commit
pipx install --force git+https://github.com/s3rgeym/ripe-ip-search.git
```

Example:

```bash
❯ ripe-ip-search --details alfa bank --no-banner -vv
[D] search params={'facet': 'true', 'format': 'xml', 'hl': 'true', 'q': '("alfa bank") AND (object-type:inetnum OR object-type:inet6num)', 'start': 0, 'wt': 'json'}
[D] {'primary-key': '5985055', 'object-type': 'inetnum', 'lookup-key': '82.208.88.232 - 82.208.88.239', 'inetnum': '82.208.88.232 - 82.208.88.239', 'netname': 'ALFABANK-NN-NET', 'descr': ['Personal network for OAO ALFA-BANK', '', ''], 'country': ['RU'], 'admin-c': ['VP1858-RIPE'], 'tech-c': ['VP1858-RIPE'], 'status': 'ASSIGNED PA', 'notify': ['VPypin@AlfaBank.ru'], 'mnt-by': ['NMTS-MNT'], 'created': '2007-11-16T06:31:17Z', 'last-modified': '2018-01-22T06:12:09Z'}
{"networks": ["82.208.88.232/29"], "num_addresses": 8, "details": {"primary-key": "5985055", "object-type": "inetnum", "lookup-key": "82.208.88.232 - 82.208.88.239", "inetnum": "82.208.88.232 - 82.208.88.239", "netname": "ALFABANK-NN-NET", "descr": ["Personal network for OAO ALFA-BANK", "", ""], "country": ["RU"], "admin-c": ["VP1858-RIPE"], "tech-c": ["VP1858-RIPE"], "status": "ASSIGNED PA", "notify": ["VPypin@AlfaBank.ru"], "mnt-by": ["NMTS-MNT"], "created": "2007-11-16T06:31:17Z", "last-modified": "2018-01-22T06:12:09Z"}}
```

| Used flag | Description |
| --- | --- |
| `--details` | output results in JSON instead list of cidrs |
| `-vv` | debug |

See more:

```bash
ripe-ip-search -h
```

If you are looking for self-hosted ripe db search, you can try [this](https://github.com/s3rgeym/ripe-db-search).
