#!/usr/bin/env node
// Review sheets for the primitive test fixtures: previews/bake3d/fixtures/<model id>.color.png
// (and .mask.png when the model has a team material): eight full cells (s ... se) on a
// checkerboard with the foot anchor marked. Test fixtures only, not product art. `--check`
// rebakes and fails when any committed sheet differs byte-for-byte.
// Usage: node tools/assets/bake3d/preview.mjs [--check] [--deps <web/game dir>] [--chromium <exe>]
import { mkdtemp, readFile, rm, writeFile, mkdir } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { bake } from './bake.mjs';
import { encodePng } from './lib/png.mjs';
import { openRenderer } from './lib/render.mjs';
import { contactSheet } from './lib/sheet.mjs';

const TOOL = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(TOOL, '../../..');
const OUT = path.join(REPO, 'previews/bake3d/fixtures');
const FIXTURES = ['primitive-building', 'direction-probe', 'light-probe-sphere'];

async function main(argv) {
  const opts = { check: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--check') opts.check = true;
    else if (argv[i] === '--deps' && argv[i + 1]) opts.depsRoot = argv[++i];
    else if (argv[i] === '--chromium' && argv[i + 1]) opts.executablePath = argv[++i];
    else throw new Error(`usage: preview.mjs [--check] [--deps <dir>] [--chromium <exe>] (bad argument ${argv[i]})`);
  }
  const configBytes = await readFile(path.join(TOOL, 'config.provisional.json'));
  const config = JSON.parse(configBytes);
  const tmp = await mkdtemp(path.join(os.tmpdir(), 'bake3d-preview-'));
  const renderer = await openRenderer({ depsRoot: opts.depsRoot, executablePath: opts.executablePath ?? process.env.BAKE3D_CHROMIUM_PATH });
  const stale = [];
  let count = 0;
  try {
    if (!opts.check) await mkdir(OUT, { recursive: true });
    for (const name of FIXTURES) {
      const modelBytes = await readFile(path.join(TOOL, 'fixtures', `${name}.json`));
      const model = JSON.parse(modelBytes);
      const { manifest, raw } = await bake({ config, model, configBytes, modelBytes, outDir: path.join(tmp, name), renderer });
      const passes = Object.values(model.materials).some((m) => m.team) ? ['color', 'mask'] : ['color'];
      for (const pass of passes) {
        const cells = manifest.frames.map((f) => raw[f.direction][pass]);
        const s = contactSheet(cells, { width: config.cell.width, height: config.cell.height, anchor: config.anchor, scale: 2 });
        const png = encodePng(s.width, s.height, s.rgba);
        const file = path.join(OUT, `${model.id}.${pass}.png`);
        count++;
        if (opts.check) {
          const current = await readFile(file).catch(() => null);
          if (!current || !current.equals(png)) stale.push(path.relative(REPO, file));
        } else {
          await writeFile(file, png);
        }
      }
    }
  } finally {
    await renderer.close();
    await rm(tmp, { recursive: true, force: true });
  }
  if (stale.length) throw new Error(`preview drift (rebake differs from committed bytes): ${stale.join(', ')}`);
  console.log(`${opts.check ? 'checked' : 'wrote'} ${count} preview sheets in ${path.relative(REPO, OUT)} (${renderer.env.browser}, ${renderer.env.glRenderer})`);
}

main(process.argv.slice(2)).catch((e) => {
  console.error(e.message);
  process.exitCode = 1;
});
