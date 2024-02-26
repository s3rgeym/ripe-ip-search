# ripe-ip-search

Search ip addresses using RIPE DB. It uses [fulltext search API](https://apps.db.ripe.net/db-web-ui/fulltextsearch).

Installation:

```bash
pipx install ripe-ip-search

git clone https://github.com/s3rgeym/ripe-ip-search.git
pipx install .

pipx install git+https://github.com/s3rgeym/ripe-ip-search.git
```

Example:

```bash
$ ripe-ip-search 'sberbank'
94.25.75.0/24
91.217.194.0/24
109.124.69.104/30
...
46.38.35.56/30
```

Use `--details` flag to output results in JSONL.

Example JSONL output:

```json
{"networks": ["46.38.35.56/30"], "num_addresses": 4, "details": {"primary-key": "10344800", "object-type": "inetnum", "lookup-key": "46.38.35.56 - 46.38.35.59", "inetnum": "46.38.35.56 - 46.38.35.59", "netname": "TEL-NET-10873", "descr": ["object-KRASNOGORSKRECHNAYA8, client-Aktsionernij kommercheskij Sberegatelnij bank Rossijskoj Federatsii otkritoe aktsionernoe obshestvo, Sberbank Rossii OAO"], "country": "RU", "admin-c": ["AVB160-RIPE"], "tech-c": ["AVB160-RIPE"], "status": "ASSIGNED PA", "notify": ["kalex@tel.ru"], "mnt-by": ["TEL-NET-MNT"], "created": "2011-12-02T05:24:21Z", "last-modified": "2011-12-02T05:24:21Z"}}
```

If you are looking for self-hosted ripe db search, you can try [this](https://github.com/s3rgeym/ripe-db-search).
