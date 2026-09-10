# Documents

Drop the files you want Kinetic to search here — annual reports, 10-K/10-Q
filings, fund fact sheets, research notes, exported spreadsheets.

Supported: `.pdf`, `.txt`, `.md`, `.csv`, `.html`, `.json`

Index them with either:

```bash
python scripts/ingest.py
```

or the **Knowledge → Ingest the documents folder** button in the app.

Re-ingesting a file replaces its previous chunks, so it is safe to run again
after editing a document.
