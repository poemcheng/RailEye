const assert = require('node:assert/strict');
const {test} = require('node:test');
const T = require('../terrain-core.js');

function grid(cols, rows, makeValue, cellSize = 20) {
  const values = Array.from({length: rows * cols}, (_, i) =>
    makeValue(i % cols, Math.floor(i / cols)));
  return {cols, rows, cellSize, x0: 230000, y0: 2700000, values};
}

test('D8 follows the steepest gradient in physical distance', () => {
  const g = grid(5, 5, () => 20);
  g.values[12] = 10;
  g.values[13] = 5;
  g.values[18] = 4; // A greater raw drop, but 6/sqrt(2) < 5.
  assert.deepEqual(T.route(g, 12), {indices: [12,13,18], stop: 'sink'});
  g.values[18] = 2;
  assert.deepEqual(T.route(g, 12), {indices: [12,18], stop: 'sink'});
});

test('flat, pit, edge, invalid selection and missing start are explicit', () => {
  const g = grid(5, 5, () => 4);
  assert.deepEqual(T.route(g, 12), {indices: [12], stop: 'flat'});
  g.values[12] = -2;
  assert.equal(T.route(g, 12).stop, 'sink');
  assert.deepEqual(T.route(g, 0), {indices: [0], stop: 'edge'});
  for (const i of [25,-1,2.5,undefined]) assert.deepEqual(T.route(g, i), {indices: [], stop: 'invalid'});
  g.values[13] = null;
  assert.deepEqual(T.route(g, 13), {indices: [], stop: 'nodata'});
  assert.deepEqual(T.route(g, 12), {indices: [12], stop: 'nodata'});
});

test('integer 0 is a measured height; exact D8 gradient ties resolve clockwise from north', () => {
  const g = grid(5, 5, () => 20);
  g.values[12] = 10;
  g.values[7] = 0;
  g.values[13] = 0;
  assert.deepEqual(T.route(g,12).indices, [12,7]);
});

test('contributing area uses square metres, clips at the edge, and propagates uncertainty', () => {
  const g = grid(7, 7, x => 100 - x, 20);
  const {next, area, partial} = T.drainage(g);
  const row = 3 * g.cols;
  assert.deepEqual(T.route(g, row + 1), {
    indices: [1,2,3,4,5,6].map(x => row + x), stop: 'edge'
  });
  assert.equal(next[row], -1);
  assert.equal(next[row + 1], row + 2);
  assert.equal(area[row + 1], 400);
  assert.equal(area[row + 3], 1200);
  assert.equal(area[row + 6], 2400);
  assert.equal(partial[row + 3], 1);
  assert.equal(area.reduce((sum, a, i) => sum + (next[i] === -1 ? a : 0), 0), 49 * 400);
});

test('convergent upstream areas are accumulated once; a complete enclosed headwater stays unflagged', () => {
  const g = grid(7, 7, (x,y) => (x === 0 || y === 0 || x === 6 || y === 6)
    ? -100 : -Math.max(Math.abs(x-3), Math.abs(y-3)));
  const drainage = T.drainage(g);
  assert.equal(drainage.partial[24], 0);
  assert.equal(drainage.area[24], 400);
  const sink = grid(7,7,(x,y) => (x - 3)**2 + (y - 3)**2);
  assert.equal(T.drainage(sink).area[24], 25 * 400);
});

test('nodata and its uncertain drainage cannot create a downhill path through a hole', () => {
  const g = grid(7, 7, x => 100 - x);
  g.values[3 * 7 + 3] = null;
  const d = T.drainage(g);
  assert(Number.isNaN(d.area[24]));
  assert.equal(d.next[24], -1);
  assert.equal(d.next[23], -1);
  assert.equal(d.partial[25], 1);
  assert.equal(d.partial[26], 1);
});

test('profile follows metre coordinates in the supplied direction and retains bends once', () => {
  const g = grid(5, 5, (x,y) => y * 5 + x);
  g.values[1] = null;
  const s = T.profile(g,[0,2,2,12]);
  assert.deepEqual(s.map(p => p.elevation), [0,null,2,7,12]);
  assert.deepEqual(s.map(p => p.distance), [0,20,40,60,80]);
  assert.deepEqual(s.map(p => p.y), [2700000,2700000,2700000,2699980,2699960]);
  assert.equal(s.at(-1).x, 230040);
  const diagonal = T.profile(g,[12,0]);
  assert.deepEqual(diagonal.map(p => p.elevation), [12,6,0]);
  assert(Math.abs(diagonal.at(-1).distance - 40 * Math.SQRT2) < 1e-10);
});

test('short traversals through a masked cell still produce an explicit profile gap', () => {
  const g = grid(5, 3, (x,y) => y * 5 + x);
  g.values[1] = null;
  const f = T.profile(g, [0,14]);
  const r = T.profile(g, [14,0]);
  assert.deepEqual(f.map(p => p.elevation), [0,null,6,7,8,13,14]);
  assert.deepEqual(r.map(p => p.elevation).reverse(), f.map(p => p.elevation));
  assert(f.every((p,i) => !i || p.distance > f[i-1].distance));
  assert.deepEqual(T.profile(g,[]), []);
  assert.deepEqual(T.profile(g,[0,0]).map(p => p.elevation), [0]);
  assert.throws(() => T.profile(g,[15]), /INVALID_PROFILE_VERTICES/);
});

test('ASCII variant origin, row direction, decimal input and nodata normalize to the same grid', () => {
  const h = 'NCOLS 2\nNROWS 2\nCELLSIZE 20\n';
  const a = T.parseAscii(h + 'xllcorner 100 yllcorner 200\nNODATA_value -9999\n.5 0\n-9.999e3 -3');
  const b = T.parseAscii('\ufeff' + h + 'YLLCENTER 210 XLLCENTER 110\n.5 0 -9999 -3');
  assert.deepEqual(a, b);
  assert.deepEqual(a,{cols:2,rows:2,cellSize:20,x0:110,y0:230,values:[.5,0,null,-3]});
});

test('malformed inputs fail before analysis', () => {
  const h = 'ncols 2 nrows 2 xllcorner 0 yllcorner 0 cellsize 1 ';
  for (const replacement of [
    '0 1 2', '0 1 2 3 4', '0 1 NaN 3', '0 1 0x1 3', '0 1 Infinity 3',
    'nrows 2 0 1 2 3', 'xllcenter 0 0 1 2 3'
  ]) assert.throws(() => T.parseAscii(h + replacement));
  for (const revision of [
    h.replace('yllcorner', 'yllcenter'), h.replace('ncols 2','ncols 1.5'),
    h.replace('ncols 2','ncols 1000000'), h.replace('cellsize 1','cellsize -1')
  ]) assert.throws(() => T.parseAscii(revision + '0 1 2 3'));
  assert.throws(() => T.route({values:[]}, 0), /INVALID_GRID/);
  assert.throws(() => T.drainage({...grid(2,2,() => 0),values:[0]}), /INVALID_GRID/);
});
