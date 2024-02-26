# ripe-ip-search

Tool to search ip addresses using RIPE DB. It uses [fulltext search API](https://apps.db.ripe.net/db-web-ui/fulltextsearch) and help to find ip addresses owned by companies. Useful for port scanning and etc.

Installation:

```bash
# latest pypi version
pipx install ripe-ip-search

# latest github commit
pipx install --force git+https://github.com/s3rgeym/ripe-ip-search.git
```

Usage:

![image](https://github.com/s3rgeym/ripe-ip-search/assets/12753171/8dbe9e2d-7b27-4da7-bde5-4a1fd4cc6e73)

Use `--details` flag to output results in JSONL.

Example JSONL output:

```json
{"networks": ["5.45.214.128/25"], "num_addresses": 128, "details": {"primary-key": "19167233", "object-type": "inetnum", "lookup-key": "5.45.214.128 - 5.45.214.255", "inetnum": "5.45.214.128 - 5.45.214.255", "netname": "YANDEX-5-45-214-128", "descr": ["Yandex enterprise network"], "country": ["RU"], "org": "ORG-YA1-RIPE", "admin-c": ["YNDX1-RIPE"], "tech-c": ["YNDX1-RIPE"], "status": "ASSIGNED PA", "remarks": ["INFRA-AW"], "mnt-by": ["YANDEX-MNT"], "created": "2018-05-31T11:35:46Z", "last-modified": "2022-04-05T15:29:12Z"}}
```

Also useful `-vv` to debug.

If you are looking for self-hosted ripe db search, you can try [this](https://github.com/s3rgeym/ripe-db-search).
