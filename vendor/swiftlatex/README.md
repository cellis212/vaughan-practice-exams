# SwiftLaTeX pdfTeX engine

`swiftlatexpdftex.js` and `swiftlatexpdftex.wasm` are pdfTeX 1.40.21
compiled to WebAssembly by the [SwiftLaTeX](https://github.com/SwiftLaTeX/SwiftLaTeX)
project, copied unmodified from release
[v20022022](https://github.com/SwiftLaTeX/SwiftLaTeX/releases/tag/v20022022)
(`20-02-2022.zip`). Source code: https://github.com/SwiftLaTeX/SwiftLaTeX.
License: GNU AGPL v3 (`LICENSE`).

SHA-256:

- `swiftlatexpdftex.js`: `019ccf66c2981cc3a371ca8983f8a0f191952e28b5df3c0b41c2e3ed80f9be65`
- `swiftlatexpdftex.wasm`: `154d08cbb298191cefe1bdd9e47a909d60fc7a96fce5f2319bfc6878c5b61cf1`

`offline-worker.js` is ours: it starts the engine as a Web Worker and keeps it
from contacting SwiftLaTeX's (now offline) package server, because the page
supplies every TeX file itself from `assets/texlive-bundle.tar.gz`. That bundle
is built by `tools/build_texlive_bundle.py`.

The generator uses this engine only when `latex.ytotech.com` fails; see the
main README.
