# RM13 TextVQA quality data

`textvqa_v0.5.1_calibration20_final200/manifest.json` records the frozen
calibration and held-out final QIDs, official validation references, source
archive members, and SHA-256 for every acquired JPEG. The downloader reads the
official TextVQA v0.5.1 validation annotation and image archive; it verifies the
frozen split hash and each image's JPEG signature before writing the manifest.

The source is the [TextVQA dataset](https://textvqa.org/dataset/), distributed
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The images and
annotations are from the official validation release; the manifest selects a
subset and records its provenance. This is a held-out validation screen, not
the official test split.

Acquire the files with:

```sh
python3 experiments/rm13/scripts/acquire_quality_images.py
```

For an interrupted acquisition with no completed `manifest.json`, resume with
`--resume`. Existing files are compared with the official archive before they
are reused.
