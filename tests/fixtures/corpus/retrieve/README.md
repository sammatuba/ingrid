# Retrieval fixture: a synthetic compendium

Everything here is **fictional**: the issuer, titles, dates and every word of the five documents.
No real document byte is committed. The files are written in the shape of
[the corpus register](../../../../docs/work/corpus/register-2026-10.json) so that
`scripts/corpus/passages.py` reads them exactly as it reads the real compendium, and
[tests/test_corpus_retrieve.py](../../../test_corpus_retrieve.py) checks the result.

| File | What it is |
|---|---|
| `register.json` | five document entries with the cover dates, file names and SHA-256s the tool checks |
| `archive.bin` | a stand-in for the compendium archive, so the archive digest check runs; it is not an archive |
| `documents/Synthetic_Alpha_Manual_1.0_final.txt` | cover publication stated: compilable, 15 passages |
| `documents/Synthetic_Beta_Manual_2.0_final.txt` | only a posting date on the cover: compilable, 15 passages |
| `documents/Synthetic_Delta_Manual_05Mar2026_final.txt` | no cover date, one day date in the file name: compilable, 10 passages |
| `documents/Synthetic_Gamma_Notes_final.txt` | no date anywhere: refused as `publication_unstated`, recorded excluded, 10 passages counted as withheld stubs |
| `documents/Synthetic_Epsilon_Manual_1.0_final.txt` | publication after the snapshot date: refused as `publication_after_snapshot` |

The documents are plain text in the market-manual grammar (`SECTION n`, `n.n` headings), so
the tests do not depend on a PDF reader. Page cutting and the 2,000-character split are tested
on text the test builds itself.
