## Manifestos

Manifestos are fetched from the Manifesto Project via [their
API](https://manifesto-project.wzb.eu/information/documents/api).

### Usage

    python download_manifestos.py

Creates `german_manifestos/` and downloads full-texts into it for the period
`MANIFESTO_START_DATE` until today.

For example for "Bündnis‘90/Die Grünen" (id=41113) we get:

    41113_201709.json
    41113_201709_text.txt
    41113_202109.json
    41113_202109_text.txt
    41113_202502.json
    41113_202502_text.txt


Additionally we get:

    index.json           # metadata about manifestos
    parties.json         # rich info about german parties
    parties_summary.csv  # short info about german parties
    summary.csv          # downloads summary
