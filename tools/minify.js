// tools/minify.js — minifikacja frontendu do katalogu build/stage
// rejestr_usterek.html: HTML + inline JS (terser) + inline CSS (clean-css)
// translations.js: terser
// Użycie: node tools/minify.js [--out build/stage]
const { minify } = require("html-minifier-terser");
const terser = require("terser");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const OUT = process.argv.includes("--out")
  ? process.argv[process.argv.indexOf("--out") + 1]
  : path.join(ROOT, "build", "stage");

async function main() {
  fs.mkdirSync(OUT, { recursive: true });

  const htmlSrc = fs.readFileSync(path.join(ROOT, "rejestr_usterek.html"), "utf8");
  console.log(`[minify] rejestr_usterek.html: ${htmlSrc.length} znaków`);
  const htmlOut = await minify(htmlSrc, {
    collapseWhitespace: true,
    conservativeCollapse: false,
    removeComments: true,
    minifyCSS: true,
    minifyJS: {
      compress: { passes: 2 },
      mangle: true,
      format: { comments: false },
    },
  });
  fs.writeFileSync(path.join(OUT, "rejestr_usterek.html"), htmlOut, "utf8");
  console.log(`[minify]   -> ${htmlOut.length} znaków (${Math.round(100 * htmlOut.length / htmlSrc.length)}%)`);

  const jsSrc = fs.readFileSync(path.join(ROOT, "translations.js"), "utf8");
  console.log(`[minify] translations.js: ${jsSrc.length} znaków`);
  const jsOut = await terser.minify(jsSrc, {
    compress: { passes: 2 },
    mangle: false, // klucze tłumaczeń muszą zostać czytelne jako nazwy własności
    format: { comments: false },
  });
  if (jsOut.error) throw jsOut.error;
  fs.writeFileSync(path.join(OUT, "translations.js"), jsOut.code, "utf8");
  console.log(`[minify]   -> ${jsOut.code.length} znaków (${Math.round(100 * jsOut.code.length / jsSrc.length)}%)`);
}

main().catch((e) => {
  console.error("[minify] BŁĄD:", e.message || e);
  process.exit(1);
});
