// Web Worker wrapper around the SwiftLaTeX pdfTeX engine (swiftlatexpdftex.js,
// unmodified). The engine fetches any TeX file it does not have from
// SwiftLaTeX's package server, which is no longer online. The page preloads
// every file the exams need (assets/texlive-bundle.tar.gz), so those lookups
// are answered "not found" (the engine's 301 convention) without touching the
// network. All other requests, such as loading the .wasm, pass through.

const SWIFTLATEX_PACKAGE_SERVER = "https://texlive2.swiftlatex.com/";
const NetworkXHR = self.XMLHttpRequest;

self.XMLHttpRequest = class extends NetworkXHR {
  open(method, url, ...rest) {
    this.offline = String(url).startsWith(SWIFTLATEX_PACKAGE_SERVER);
    if (!this.offline) super.open(method, url, ...rest);
  }
  send(body) {
    if (!this.offline) super.send(body);
  }
  get status() {
    return this.offline ? 301 : super.status;
  }
};

importScripts("swiftlatexpdftex.js");
