/* MODELS-1: run src/grid/models.js against a minimal document and print what it writes.

   The Python test passes the served page's own four headings and status words as one JSON
   argument, and the script's path as the second. The shim supplies the three members the
   script touches (querySelectorAll, getElementById, documentElement.setAttribute), so the
   composed line is proven against the page and not against a copy of it. No DOM library and
   no network. */
import {readFileSync} from 'node:fs';

const [cardsJson, scriptPath] = process.argv.slice(2);
const cards = JSON.parse(cardsJson).map(({name, word}) => ({
  querySelector(selector) {
    if (selector === 'h2') return {textContent: name};
    if (selector === '.md-status-word') return {textContent: word};
    return null;
  },
}));
const summary = {textContent: ''};
const written = {};
const document = {
  querySelectorAll: (selector) => (selector === '.md-card' ? cards : []),
  getElementById: (id) => (id === 'md-summary' ? summary : null),
  documentElement: {setAttribute: (key, value) => { written[key] = value; }},
};
new Function('document', readFileSync(scriptPath, 'utf8'))(document);
process.stdout.write(JSON.stringify({summary: summary.textContent, written}));
