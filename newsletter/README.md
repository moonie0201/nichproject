# Stibee Newsletter Pipeline

`content_curator.py` scans recent Hugo posts, builds Stibee-ready newsletter HTML, and can optionally archive the issue into Hugo.

## Local run

```bash
python3 newsletter/content_curator.py --root . --days 7 --limit 8 --publish-hugo
```

Outputs are written to `newsletter/out/`:

- `weekly-YYYY-MM-DD.html`: Stibee-ready HTML body
- `weekly-YYYY-MM-DD.md`: editor review copy
- `weekly-YYYY-MM-DD.json`: machine-readable payload
- `weekly-YYYY-MM-DD.csv`: post inventory for QA/manual upload

## Stibee draft or send

Set credentials in the runtime environment:

```bash
export STIBEE_API_KEY="..."
export STIBEE_LIST_ID="..."
export STIBEE_SENDER_NAME="InvestIQs Weekly"
export STIBEE_SENDER_EMAIL="weekly@investiqs.com"
export STIBEE_SEND_TIME_TYPE="draft"
python3 newsletter/content_curator.py --root . --send-stibee
```

Use `STIBEE_SEND_TIME_TYPE=immediately` only after editorial review.

## Schedule

Recommended cron for the approved weekly cadence:

```cron
0 7 * * 5 cd /home/mh/ocstorage/workspace/nichproject && /usr/bin/python3 newsletter/content_curator.py --root . --days 7 --limit 8 --publish-hugo >> newsletter/out/cron.log 2>&1
```

The same schedule is checked in as `newsletter/stibee_weekly.cron`.

The existing n8n workflow pattern can call the same command through the bridge, or use the generated HTML/JSON files as the Stibee campaign body.
