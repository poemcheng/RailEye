/* RailEye projected, north-up, square-cell terrain grids. Coordinates and heights are metres. */
(function (root) {
  'use strict';

  const finite = Number.isFinite;
  // Clockwise from north also defines how exact ties between downhill gradients are resolved.
  const neighbors = [[0,-1], [1,-1], [1,0], [1,1], [0,1], [-1,1], [-1,0], [-1,-1]];

  function checkGrid(g) {
    if (!g || !Number.isSafeInteger(g.cols) || !Number.isSafeInteger(g.rows) ||
        g.cols < 1 || g.rows < 1 || !Number.isSafeInteger(g.cols * g.rows) ||
        !g.values || g.values.length !== g.cols * g.rows ||
        !finite(g.cellSize) || g.cellSize <= 0 || !finite(g.x0) || !finite(g.y0)) {
      throw new Error('INVALID_GRID');
    }
  }

  function validIndex(g, i) {
    return Number.isInteger(i) && i >= 0 && i < g.values.length;
  }

  function downstream(g, index) {
    if (!finite(g.values[index])) return {next: -1, stop: 'nodata'};
    const col = index % g.cols;
    const row = Math.floor(index / g.cols);
    if (!col || !row || col === g.cols - 1 || row === g.rows - 1) {
      return {next: -1, stop: 'edge'};
    }
    let next = -1;
    let steepest = 0;
    let hasLevelNeighbor = false;
    for (const [dx, dy] of neighbors) {
      const i = index + dy * g.cols + dx;
      if (!finite(g.values[i])) return {next: -1, stop: 'nodata'};
      const drop = g.values[index] - g.values[i];
      if (drop === 0) hasLevelNeighbor = true;
      // All gradients share the same positive cellSize denominator.
      const gradient = drop / (dx && dy ? Math.SQRT2 : 1);
      if (gradient > steepest) {
        steepest = gradient;
        next = i;
      }
    }
    if (next !== -1) return {next, stop: null};
    return {next: -1, stop: hasLevelNeighbor ? 'flat' : 'sink'};
  }

  function route(g, startIndex) {
    checkGrid(g);
    if (!validIndex(g, startIndex)) return {indices: [], stop: 'invalid'};
    if (!finite(g.values[startIndex])) return {indices: [], stop: 'nodata'};
    const indices = [];
    let i = startIndex;
    // Each move drops strictly in elevation, so a path cannot revisit a cell.
    while (true) {
      indices.push(i);
      const step = downstream(g, i);
      if (step.next < 0) return {indices, stop: step.stop};
      i = step.next;
    }
  }

  function drainage(g) {
    checkGrid(g);
    const n = g.values.length;
    const next = new Int32Array(n).fill(-1);
    const area = new Float64Array(n).fill(NaN);
    const partial = new Uint8Array(n);
    const inflows = new Uint8Array(n);
    const cellArea = g.cellSize * g.cellSize;
    for (let i = 0; i < n; i++) {
      if (!finite(g.values[i])) { partial[i] = 1; continue; }
      area[i] = cellArea;
      const step = downstream(g, i);
      next[i] = step.next;
      if (step.next >= 0) inflows[step.next]++;
      if (step.stop !== 'edge' && step.stop !== 'nodata') continue;
      partial[i] = 1;
      // A censored cell may have continued into a known cell. Conservatively
      // flag every eligible receiving neighbor, then propagate along valid D8 paths.
      const col = i % g.cols;
      const row = Math.floor(i / g.cols);
      for (const [dx, dy] of neighbors) {
        const x = col + dx, y = row + dy;
        if (x < 0 || x >= g.cols || y < 0 || y >= g.rows) continue;
        const j = y * g.cols + x;
        if (finite(g.values[j]) && g.values[j] <= g.values[i]) partial[j] = 1;
      }
    }
    // Topological order avoids sorting elevations or recursively visiting large catchments.
    const ready = new Int32Array(n);
    let tail = 0;
    for (let i = 0; i < n; i++) {
      if (finite(area[i]) && inflows[i] === 0) ready[tail++] = i;
    }
    for (let head = 0; head < tail; head++) {
      const i = ready[head], j = next[i];
      if (j < 0) continue;
      area[j] += area[i];
      if (partial[i]) partial[j] = 1;
      if (--inflows[j] === 0) ready[tail++] = j;
    }
    return {next, area, partial};
  }

  function profile(g, vertices) {
    checkGrid(g);
    if (!Array.isArray(vertices) || !vertices.every(i => validIndex(g, i))) {
      throw new Error('INVALID_PROFILE_VERTICES');
    }
    if (!vertices.length) return [];
    const start = vertices[0];
    const z = i => finite(g.values[i]) ? g.values[i] : null;
    const samples = [{
      distance: 0, elevation: z(start),
      x: g.x0 + (start % g.cols) * g.cellSize,
      y: g.y0 - Math.floor(start / g.cols) * g.cellSize
    }];
    let total = 0;

    for (let k = 1; k < vertices.length; k++) {
      const a = vertices[k - 1], b = vertices[k];
      if (a === b) continue;
      const sx = a % g.cols, sy = Math.floor(a / g.cols);
      const dx = b % g.cols - sx, dy = Math.floor(b / g.cols) - sy;
      const nx = Math.abs(dx), ny = Math.abs(dy);
      const length = g.cellSize * Math.hypot(dx, dy);
      let ix = 0, iy = 0, enter = 0;
      // Visit every pixel crossed over a nonzero length. An exact corner
      // crossing visits the diagonal cell. Each interior sample is at the
      // midpoint of the chord inside that pixel and carries its native height.
      while (ix < nx || iy < ny) {
        const tx = ix < nx ? (2 * ix + 1) / (2 * nx) : Infinity;
        const ty = iy < ny ? (2 * iy + 1) / (2 * ny) : Infinity;
        const leave = Math.min(tx, ty);
        if (ix || iy) addSample((enter + leave) / 2);
        if (tx <= ty) ix++;
        if (ty <= tx) iy++;
        enter = leave;
      }
      addSample(1);
      total += length;

      function addSample(t) {
        const pixel = (sy + Math.sign(dy) * iy) * g.cols + sx + Math.sign(dx) * ix;
        samples.push({
          distance: total + length * t,
          elevation: z(pixel),
          x: g.x0 + (sx + dx * t) * g.cellSize,
          y: g.y0 - (sy + dy * t) * g.cellSize
        });
      }
    }
    return samples;
  }

  // ESRI ASCII has no CRS or unit declaration. Callers must confirm these before analysis.
  function parseAscii(text) {
    const maxCells = 1000000;
    if (typeof text !== 'string' || text.length > 16 * 1024 * 1024) throw new Error('ASCII_SIZE');
    const tokens = text.trim().split(/\s+/u);
    const keys = new Set(['ncols','nrows','cellsize','xllcorner','yllcorner','xllcenter','yllcenter','nodata_value']);
    const header = Object.create(null);
    let p = 0;
    function number(s) {
      if (typeof s !== 'string' || !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(s) || !finite(Number(s))) {
        throw new Error('ASCII_NUMBER');
      }
      return Number(s);
    }
    while (p < tokens.length && keys.has(tokens[p].toLowerCase())) {
      const key = tokens[p++].toLowerCase();
      if (key in header) throw new Error('ASCII_DUPLICATE_HEADER');
      header[key] = number(tokens[p++]);
    }
    const {ncols: cols, nrows: rows, cellsize: cellSize} = header;
    if (!Number.isSafeInteger(cols) || !Number.isSafeInteger(rows) || cols < 1 || rows < 1 ||
        cols * rows > maxCells || !finite(cellSize) || cellSize <= 0) throw new Error('ASCII_GEOMETRY');
    const corner = 'xllcorner' in header && 'yllcorner' in header;
    const center = 'xllcenter' in header && 'yllcenter' in header;
    if ((corner && ('xllcenter' in header || 'yllcenter' in header)) ||
        (center && ('xllcorner' in header || 'yllcorner' in header)) || (!center && !corner)) {
      throw new Error('ASCII_ORIGIN');
    }
    if (tokens.length - p !== cols * rows) throw new Error('ASCII_CELL_COUNT');
    const values = new Array(cols * rows);
    const missing = header.nodata_value ?? -9999;
    for (let i = 0; i < values.length; i++) {
      const v = number(tokens[p++]);
      values[i] = v === missing ? null : v;
    }
    const x0 = corner ? header.xllcorner + cellSize / 2 : header.xllcenter;
    const south = corner ? header.yllcorner + cellSize / 2 : header.yllcenter;
    const g = {cols, rows, cellSize, x0, y0: south + (rows - 1) * cellSize, values};
    checkGrid(g);
    return g;
  }

  const api = {route, drainage, profile, parseAscii};
  root.RailTerrain = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(globalThis);
