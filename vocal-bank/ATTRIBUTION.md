# VocalSet attribution and reuse

This bank contains edited excerpts from **VocalSet: A Singing Voice Dataset**, by **Julia Wilkins, Prem Seetharaman, Alison Wahl and Bryan Pardo**, Northwestern University, 2018.

- Original dataset: https://doi.org/10.5281/zenodo.1442513
- Original archive used: VocalSet11.zip, published MD5 `0c09396242f946e7111ad7d8fc649b81`.
- Dataset license: **Creative Commons Attribution 4.0 International (CC BY 4.0)**, as identified by the original Zenodo record's API. See SOURCE_LICENSE.json.
- License: https://creativecommons.org/licenses/by/4.0/ ; full legal code: https://creativecommons.org/licenses/by/4.0/legalcode
- Paper: https://ismir2018.ircam.fr/doc/pdfs/114_Paper.pdf

Changes made for Cantabile: selected sustained note excerpts; estimated/refined pitch; removed DC offset; adjusted level; added fades; baked sustain-loop crossfades; created SFZ mappings, metadata, previews and arrangements. Each sample has its original recording path, source time interval, source SHA-256, output SHA-256, estimated pitch and loop positions in manifest.json. Original ZIP members were checked against their CRC values. The full multi-gigabyte archive was not downloaded, so no full-archive MD5 verification is claimed.

CC BY 4.0 permits sharing and adaptation, including commercial reuse, subject to its terms. Preserve appropriate credit, the license link, and a note of modifications. Do not imply that the researchers or singers endorse your work. This bank adds no extra restrictions to the CC BY material.

Suggested credit:

> Contains edited VocalSet recordings by Julia Wilkins, Prem Seetharaman, Alison Wahl and Bryan Pardo (2018), used under CC BY 4.0. Samples were excerpted, level-adjusted and looped for Cantabile. https://doi.org/10.5281/zenodo.1442513 · https://creativecommons.org/licenses/by/4.0/

Singer IDs and voice types come from the dataset's readme; singers remain anonymous. The readme identifies F1–F9 and M1–M11. Its tentative classifications for M4 and M7 are preserved. Sampled pitch coverage is measured material, not a claim about a singer's full comfortable or classical range.

This sampled bank contains no Hanami or TIGER model weights or generated samples. The separate neural voices in the Cantabile application retain their own terms in THIRD_PARTY.md; this bank's CC BY license does not apply to those dependencies.
