#!/usr/bin/env node
/** Export the checked-in frontend literal, preserving every WardrobeItem field. */
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import vm from 'node:vm';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const sourcePath = path.join(root, 'src/data/initialWardrobe.ts');
const destination = path.resolve(process.argv[2] || path.join(root, 'rag/data/wardrobe_seed.json'));
const source = await readFile(sourcePath, 'utf8');
// This script evaluates only our trusted, checked-in data literal, never uploads.
// Reject all syntax beyond its single import and array declaration.
const match = source.match(/^\s*import\s+type\s+\{\s*WardrobeItem\s*\}\s+from\s+['"][^'"]+['"];\s*export\s+const\s+INITIAL_WARDROBE\s*:\s*WardrobeItem\[\]\s*=\s*(\[[\s\S]*\]);\s*$/u);
if (!match) throw new Error('The frontend seed format changed; review the exporter before running.');
const items = vm.runInNewContext(`(${match[1]})`, Object.create(null), { timeout: 1000 });
if (!Array.isArray(items) || !items.length || items.some((item) => typeof item.id !== 'string' || typeof item.category !== 'string')) {
  throw new Error('Invalid frontend wardrobe literal.');
}
if (new Set(items.map((item) => item.id)).size !== items.length) throw new Error('Duplicate frontend wardrobe IDs.');
await mkdir(path.dirname(destination), { recursive: true });
await writeFile(destination, `${JSON.stringify(items, null, 2)}\n`, 'utf8');
if (!process.argv[2]) {
  // Demonstration annotations, kept out of the exact seed and research corpus.
  // The temperature cutoff is a sample outfit rule, not a certified property.
  const demoWeather = {
    'item-1': {temperature_min: 12},
    'item-2': {windproof: false},
    'item-5': {temperature_min: 0, temperature_max: 18},
    'item-6': {temperature_min: 0, temperature_max: 22, windproof: true},
  };
  const annotatedItems = items.map(item => demoWeather[item.id]
    ? {...item, weather: demoWeather[item.id]}
    : item);
  await writeFile(path.join(path.dirname(destination), 'wardrobe_demo_weather.json'),
    `${JSON.stringify(annotatedItems, null, 2)}\n`, 'utf8');
  const profiles = {
    wardrobe_demo_three: ['item-1', 'item-4', 'item-8'],
    wardrobe_demo_missing_shoes: ['item-1', 'item-4', 'item-2'],
  };
  for (const [name, ids] of Object.entries(profiles)) {
    const profile = ids.map(id => items.find(item => item.id === id));
    if (profile.some(item => !item)) throw new Error(`Missing item for ${name}`);
    await writeFile(path.join(path.dirname(destination), `${name}.json`), `${JSON.stringify(profile, null, 2)}\n`, 'utf8');
  }
}
process.stdout.write(`Exported ${items.length} canonical frontend items to ${destination}\n`);
