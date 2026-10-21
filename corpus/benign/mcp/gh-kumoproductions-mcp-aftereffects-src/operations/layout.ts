// Layout and timing operations — the "arrange many things at once" layer of
// the registry: anchors, in/out points, visibility schedules, stacking order,
// comp resizing, renaming. Everything here that edits layers takes the same
// `layer` vocabulary as transform.set / property.set: index | name | { id } |
// 'selected' | 'all' | an array of those.

import { registerOp, jsxFail, jsxVal, jsxCompPreamble } from "../registry.js";

const LAYER_TARGET_PARAM = {
  name: "layer",
  type: "any" as const,
  description: "Layer index, name, { id }, 'selected', 'all', or an array of those",
  required: true,
};

registerOp({
  name: "layer.set_anchor",
  category: "layer",
  description:
    "Move the anchor point WITHOUT moving the layer on screen (Position is compensated through Scale/Rotation; Position keyframes are all shifted). Address the anchor by preset on the layer's rendered bounds (sourceRectAtTime), by an explicit layer-space point, or by an offset from the current anchor.",
  params: [
    { name: "comp", type: "any", description: "Comp name or id", required: true },
    LAYER_TARGET_PARAM,
    {
      name: "preset",
      type: "string",
      description:
        "center | topLeft | topCenter | topRight | centerLeft | centerRight | bottomLeft | bottomCenter | bottomRight",
      required: false,
    },
    {
      name: "point",
      type: "array",
      description: "[x, y] (or [x, y, z]) explicit anchor in layer space",
      required: false,
    },
    {
      name: "offset",
      type: "array",
      description: "[dx, dy] added to the current anchor",
      required: false,
    },
    {
      name: "time",
      type: "number",
      description:
        "Time at which the bounds are measured for a preset (default: current comp time)",
      required: false,
    },
  ],
  toJsx(args) {
    const modes = [args.preset, args.point, args.offset].filter((v) => v !== undefined).length;
    if (modes !== 1) {
      return jsxFail("give exactly one of preset, point, or offset");
    }
    return `
            ${jsxCompPreamble(args)}
            var _layers = AE.resolveLayers(_comp, ${jsxVal(args.layer)});
            if (_layers.length === 0) return { ok: false, error: "no layers matched" };
            var _preset = ${jsxVal(args.preset ?? null)};
            if (_preset !== null && !AE.ANCHOR_PRESETS.hasOwnProperty(_preset)) return { ok: false, error: "unknown preset '" + _preset + "'" };
            var _point = ${jsxVal(args.point ?? null)};
            var _offset = ${jsxVal(args.offset ?? null)};
            var _t = ${jsxVal(args.time ?? null)};
            if (_t === null) _t = _comp.time;
            var _out = [];
            var _failed = 0;
            for (var _li = 0; _li < _layers.length; _li++) {
                var _l = _layers[_li];
                var _target = null;
                try {
                    if (_preset !== null) {
                        var _rect = AE.layerRect(_l, _t);
                        if (!_rect) throw new Error("layer has no measurable bounds");
                        _target = AE.pointInRect(_rect, _preset);
                    } else if (_point !== null) {
                        _target = _point;
                    } else {
                        var _cur = _l.transform.anchorPoint.value;
                        _target = [_cur[0] + (_offset[0] || 0), _cur[1] + (_offset[1] || 0)];
                        if (_cur.length > 2) _target.push(_cur[2] + (_offset[2] || 0));
                    }
                    var _r = AE.moveAnchor(_l, _target);
                    _out.push({ index: _l.index, name: _l.name, ok: true, anchorPoint: _r.anchorPoint, positionDelta: _r.positionDelta, positionKeysShifted: _r.positionKeysShifted, warnings: _r.warnings });
                } catch (eA) {
                    _failed++;
                    _out.push({ index: _l.index, name: _l.name, ok: false, error: AE.errText(eA) });
                }
            }
            return { ok: _failed === 0, error: _failed === 0 ? null : (_failed + " of " + _out.length + " layers failed"), count: _out.length, layers: _out };
        `;
  },
});

registerOp({
  name: "layer.set_timing",
  category: "layer",
  description:
    "Set a layer's timing in one call: shift (relative move of the whole layer), startTime, inPoint, outPoint ('comp' = comp start / comp end — e.g. to extend a layer copied out of a shorter comp), stretch. Applied in that order; AE clamps in/out to the source for footage.",
  params: [
    { name: "comp", type: "any", description: "Comp name or id", required: true },
    LAYER_TARGET_PARAM,
    {
      name: "shift",
      type: "number",
      description: "Seconds to move the layer by (in/out points follow)",
      required: false,
    },
    { name: "startTime", type: "number", description: "Absolute layer start", required: false },
    {
      name: "inPoint",
      type: "any",
      description: "In point in seconds, or 'comp' for the comp start (0)",
      required: false,
    },
    {
      name: "outPoint",
      type: "any",
      description: "Out point in seconds, or 'comp' for the comp end (comp.duration)",
      required: false,
    },
    { name: "stretch", type: "number", description: "Time stretch in percent", required: false },
  ],
  toJsx(args) {
    const sets: string[] = [];
    if (args.shift !== undefined) sets.push(`_l.startTime = _l.startTime + ${jsxVal(args.shift)};`);
    if (args.startTime !== undefined) sets.push(`_l.startTime = ${jsxVal(args.startTime)};`);
    if (args.inPoint !== undefined)
      sets.push(`_l.inPoint = (${jsxVal(args.inPoint)} === "comp") ? 0 : ${jsxVal(args.inPoint)};`);
    if (args.outPoint !== undefined)
      sets.push(
        `_l.outPoint = (${jsxVal(args.outPoint)} === "comp") ? _comp.duration : ${jsxVal(args.outPoint)};`,
      );
    if (args.stretch !== undefined) sets.push(`_l.stretch = ${jsxVal(args.stretch)};`);
    if (sets.length === 0) {
      return jsxFail("give at least one of shift, startTime, inPoint, outPoint, stretch");
    }
    const inBad = typeof args.inPoint === "string" && args.inPoint !== "comp";
    const outBad = typeof args.outPoint === "string" && args.outPoint !== "comp";
    if (inBad || outBad) {
      return jsxFail("inPoint/outPoint must be a number or 'comp'");
    }
    return `
            ${jsxCompPreamble(args)}
            var _layers = AE.resolveLayers(_comp, ${jsxVal(args.layer)});
            if (_layers.length === 0) return { ok: false, error: "no layers matched" };
            var _out = [];
            var _failed = 0;
            for (var _li = 0; _li < _layers.length; _li++) {
                var _l = _layers[_li];
                try {
                    ${sets.join("\n                    ")}
                    _out.push({ index: _l.index, name: _l.name, ok: true, startTime: _l.startTime, inPoint: _l.inPoint, outPoint: _l.outPoint, stretch: _l.stretch });
                } catch (eT) {
                    _failed++;
                    _out.push({ index: _l.index, name: _l.name, ok: false, error: AE.errText(eT) });
                }
            }
            return { ok: _failed === 0, error: _failed === 0 ? null : (_failed + " of " + _out.length + " layers failed"), count: _out.length, layers: _out };
        `;
  },
});

registerOp({
  name: "layer.set_visibility_schedule",
  category: "layer",
  description:
    "Show layers only during given time ranges — sequential pops, material swaps, flip-books — in one call. mode 'opacity' (default) writes HOLD opacity keys (on inside each range, off outside; existing opacity keys replaced); mode 'inOut' sets in/out points (one range per layer).",
  params: [
    { name: "comp", type: "any", description: "Comp name or id", required: true },
    {
      name: "entries",
      type: "array",
      description:
        "[{ layer, ranges: [[start, end], …] }] — layer accepts the usual index | name | { id } | 'selected' | 'all' | array",
      required: true,
    },
    {
      name: "mode",
      type: "string",
      description: "opacity|inOut (default opacity)",
      required: false,
      default: "opacity",
    },
    {
      name: "onValue",
      type: "number",
      description: "Opacity inside the ranges (default 100)",
      required: false,
      default: 100,
    },
    {
      name: "offValue",
      type: "number",
      description: "Opacity outside the ranges (default 0)",
      required: false,
      default: 0,
    },
  ],
  toJsx(args) {
    const mode = args.mode ?? "opacity";
    if (mode !== "opacity" && mode !== "inOut") {
      return jsxFail("mode must be opacity|inOut");
    }
    const entries = Array.isArray(args.entries) ? (args.entries as unknown[]) : [];
    for (const [i, entry] of entries.entries()) {
      const e = entry as { layer?: unknown; ranges?: unknown };
      if (!e || typeof e !== "object" || e.layer === undefined || !Array.isArray(e.ranges)) {
        return jsxFail(`entries[${i}] must be { layer, ranges: [[start, end], …] }`);
      }
      for (const [j, range] of (e.ranges as unknown[]).entries()) {
        if (
          !Array.isArray(range) ||
          range.length !== 2 ||
          typeof range[0] !== "number" ||
          typeof range[1] !== "number" ||
          !(range[1] > range[0])
        ) {
          return jsxFail(`entries[${i}].ranges[${j}] must be [start, end] with end > start`);
        }
      }
      if (mode === "inOut" && (e.ranges as unknown[]).length !== 1) {
        return jsxFail(`entries[${i}]: mode 'inOut' takes exactly one range per entry`);
      }
    }
    return `
            ${jsxCompPreamble(args)}
            var _entries = ${jsxVal(entries)};
            var _mode = ${jsxVal(mode)};
            var _on = ${jsxVal(args.onValue ?? 100)};
            var _off = ${jsxVal(args.offValue ?? 0)};
            var _out = [];
            var _failed = 0;
            for (var _ei = 0; _ei < _entries.length; _ei++) {
                var _e = _entries[_ei];
                var _layers = AE.resolveLayers(_comp, _e.layer);
                if (_layers.length === 0) { _failed++; _out.push({ entry: _ei, ok: false, error: "no layers matched " + String(_e.layer) }); continue; }
                var _ranges = _e.ranges.slice(0);
                _ranges.sort(function (a, b) { return a[0] - b[0]; });
                for (var _li = 0; _li < _layers.length; _li++) {
                    var _l = _layers[_li];
                    try {
                        if (_mode === "inOut") {
                            _l.inPoint = _ranges[0][0];
                            _l.outPoint = _ranges[0][1];
                            _out.push({ entry: _ei, index: _l.index, name: _l.name, ok: true, inPoint: _l.inPoint, outPoint: _l.outPoint });
                        } else {
                            var _op = _l.transform.opacity;
                            var _specs = [];
                            if (_ranges[0][0] > 0) _specs.push({ time: 0, value: _off, interp: "hold" });
                            for (var _ri = 0; _ri < _ranges.length; _ri++) {
                                _specs.push({ time: _ranges[_ri][0], value: _on, interp: "hold" });
                                _specs.push({ time: _ranges[_ri][1], value: _off, interp: "hold" });
                            }
                            var _r = AE.applyKeySpecs(_op, _specs, { replace: true });
                            _out.push({ entry: _ei, index: _l.index, name: _l.name, ok: true, numKeys: _r.numKeys, warnings: _r.warnings });
                        }
                    } catch (eS) {
                        _failed++;
                        _out.push({ entry: _ei, index: _l.index, name: _l.name, ok: false, error: AE.errText(eS) });
                    }
                }
            }
            return { ok: _failed === 0, error: _failed === 0 ? null : (_failed + " entries failed"), count: _out.length, layers: _out };
        `;
  },
});

registerOp({
  name: "comp.set_layer_order",
  category: "comp",
  description:
    "Arrange layers by listing them top to bottom. The listed layers occupy startIndex.. in that order; unlisted layers keep their relative order below (or above) them.",
  params: [
    { name: "comp", type: "any", description: "Comp name or id", required: true },
    {
      name: "layers",
      type: "array",
      description: "Layer references (index | name | { id }), top first",
      required: true,
    },
    {
      name: "startIndex",
      type: "number",
      description: "1-based index the first listed layer lands on (default 1 = top)",
      required: false,
      default: 1,
    },
  ],
  toJsx(args) {
    return `
            ${jsxCompPreamble(args)}
            var _refs = ${jsxVal(args.layers)};
            var _start = ${jsxVal(args.startIndex ?? 1)};
            var _targets = [];
            var _seen = {};
            for (var _ri = 0; _ri < _refs.length; _ri++) {
                var _l = AE.findLayerInComp(_comp, _refs[_ri]);
                if (!_l) return { ok: false, error: "no layer matching " + String(_refs[_ri]) };
                var _key = "k" + _l.index;
                if (_seen.hasOwnProperty(_key)) return { ok: false, error: "layer '" + _l.name + "' listed twice" };
                _seen[_key] = true;
                _targets.push(_l);
            }
            if (_start < 1 || _start + _targets.length - 1 > _comp.numLayers) return { ok: false, error: "startIndex " + _start + " leaves no room for " + _targets.length + " layers (comp has " + _comp.numLayers + ")" };
            for (var _ti = 0; _ti < _targets.length; _ti++) AE.moveLayerToIndex(_targets[_ti], _start + _ti);
            var _order = [];
            for (var _oi = 1; _oi <= _comp.numLayers; _oi++) _order.push(_comp.layer(_oi).name);
            return { ok: true, moved: _targets.length, order: _order };
        `;
  },
});

registerOp({
  name: "comp.resize",
  category: "comp",
  description:
    "Change a comp's size and keep its content where it was: every unparented layer's Position (keyframes included, separated dimensions handled) is offset so the content stays pinned to `anchor` — 'center' keeps it centred, 'topLeft' keeps the top-left corner, etc. Children follow their parents. Comp accepts a name, id, pattern, or array.",
  params: [
    {
      name: "comp",
      type: "any",
      description: "Comp name/id, pattern ('shot_*'), or array of those",
      required: true,
    },
    { name: "width", type: "number", description: "New width in px", required: false },
    { name: "height", type: "number", description: "New height in px", required: false },
    {
      name: "anchor",
      type: "string",
      description:
        "Where the existing content stays pinned: center | topLeft | topCenter | topRight | centerLeft | centerRight | bottomLeft | bottomCenter | bottomRight (default center)",
      required: false,
      default: "center",
    },
    {
      name: "offset",
      type: "array",
      description: "[dx, dy] explicit offset applied to every unparented layer instead of `anchor`",
      required: false,
    },
  ],
  toJsx(args) {
    if (args.width === undefined && args.height === undefined) {
      return jsxFail("give width and/or height");
    }
    return `
            var _comps = AE.findComps(${jsxVal(args.comp)});
            if (_comps.length === 0) return { ok: false, error: "no comps matched" };
            var _anchor = ${jsxVal(args.anchor ?? "center")};
            if (!AE.ANCHOR_PRESETS.hasOwnProperty(_anchor)) return { ok: false, error: "unknown anchor '" + _anchor + "'" };
            var _explicit = ${jsxVal(args.offset ?? null)};
            var _out = [];
            for (var _ci = 0; _ci < _comps.length; _ci++) {
                var _c = _comps[_ci];
                var _oldW = _c.width, _oldH = _c.height;
                var _newW = ${jsxVal(args.width ?? null)};
                var _newH = ${jsxVal(args.height ?? null)};
                if (_newW === null) _newW = _oldW;
                if (_newH === null) _newH = _oldH;
                var _f = AE.ANCHOR_PRESETS[_anchor];
                var _d = _explicit !== null ? [_explicit[0] || 0, _explicit[1] || 0] : [(_newW - _oldW) * _f[0], (_newH - _oldH) * _f[1]];
                _c.width = _newW;
                _c.height = _newH;
                var _moved = 0;
                var _warn = [];
                for (var _li = 1; _li <= _c.numLayers; _li++) {
                    var _l = _c.layer(_li);
                    if (_l.parent) continue;
                    var _pos = null;
                    try { _pos = _l.transform.position; } catch (eP) {}
                    if (!_pos) continue;
                    try { AE.offsetValue(_pos, [_d[0], _d[1]]); _moved++; }
                    catch (eO) { _warn.push(_l.name + ": " + AE.errText(eO)); }
                    if (_l instanceof CameraLayer || _l instanceof LightLayer) {
                        try { var _poi = _l.transform.pointOfInterest; if (_poi) AE.offsetValue(_poi, [_d[0], _d[1]]); } catch (ePoi) {}
                    }
                }
                _out.push({ comp: _c.name, from: [_oldW, _oldH], to: [_c.width, _c.height], offset: _d, layersMoved: _moved, warnings: _warn });
            }
            return { ok: true, comps: _out };
        `;
  },
});

registerOp({
  name: "project.rename",
  category: "project",
  description:
    "Rename project items and/or layers in bulk: an exact `map` ({ from: to }) or a regex `pattern` + `replacement` ($1 works). scope 'items' covers comps, footage and folders; 'layers' covers layers in every comp (or the comps matched by `comp`). dryRun previews without renaming.",
  params: [
    {
      name: "scope",
      type: "string",
      description: "items|layers|all (default all)",
      required: false,
      default: "all",
    },
    { name: "map", type: "object", description: "{ 'old name': 'new name', … }", required: false },
    {
      name: "pattern",
      type: "string",
      description: "Regular expression (JavaScript syntax) applied to each name",
      required: false,
    },
    {
      name: "replacement",
      type: "string",
      description: "Replacement for `pattern` matches ($1… for groups)",
      required: false,
    },
    {
      name: "flags",
      type: "string",
      description: "Regex flags: any of g, i, m (default 'g')",
      required: false,
      default: "g",
    },
    {
      name: "comp",
      type: "any",
      description: "Restrict layer renames to these comps (name/id/pattern/array; default all)",
      required: false,
    },
    {
      name: "itemTypes",
      type: "array",
      description: "Restrict item renames to these types: CompItem|FootageItem|FolderItem",
      required: false,
    },
    {
      name: "dryRun",
      type: "boolean",
      description: "Report what would change without renaming (default false)",
      required: false,
      default: false,
    },
  ],
  toJsx(args) {
    const scope = args.scope ?? "all";
    if (scope !== "items" && scope !== "layers" && scope !== "all") {
      return jsxFail("scope must be items|layers|all");
    }
    const hasMap = args.map !== undefined;
    const hasPattern = args.pattern !== undefined;
    if (hasMap === hasPattern) {
      return jsxFail("give exactly one of map or pattern (+ replacement)");
    }
    const flags = String(args.flags ?? "g");
    if (hasPattern) {
      if (args.replacement === undefined) {
        return jsxFail("pattern needs a replacement");
      }
      if (!/^[gim]*$/.test(flags)) {
        return jsxFail("flags may only contain g, i, m");
      }
      try {
        RegExp(String(args.pattern), flags);
      } catch (regexErr) {
        const msg = regexErr instanceof Error ? regexErr.message : String(regexErr);
        return jsxFail(`invalid pattern: ${msg}`);
      }
    }
    return `
            var _scope = ${jsxVal(scope)};
            var _map = ${jsxVal(args.map ?? null)};
            var _re = ${hasPattern ? `new RegExp(${jsxVal(args.pattern)}, ${jsxVal(flags)})` : "null"};
            var _repl = ${jsxVal(args.replacement ?? "")};
            var _types = ${jsxVal(args.itemTypes ?? null)};
            var _dry = ${jsxVal(args.dryRun === true)};
            function _next(name) {
                if (_map !== null) return (_map.hasOwnProperty(name) && typeof _map[name] === "string") ? _map[name] : name;
                _re.lastIndex = 0;
                return name.replace(_re, _repl);
            }
            function _typeOk(t) {
                if (_types === null) return true;
                for (var _ti = 0; _ti < _types.length; _ti++) if (_types[_ti] === t) return true;
                return false;
            }
            var _changes = [];
            var _failed = 0;
            if (_scope !== "layers") {
                for (var _ii = 1; _ii <= app.project.numItems; _ii++) {
                    var _it = app.project.item(_ii);
                    var _t = AE.itemTypeName(_it);
                    if (!_typeOk(_t)) continue;
                    var _to = _next(_it.name);
                    if (_to === _it.name) continue;
                    var _ch = { kind: "item", type: _t, id: _it.id, from: _it.name, to: _to };
                    if (!_dry) { try { _it.name = _to; _ch.applied = true; } catch (eI) { _failed++; _ch.applied = false; _ch.error = AE.errText(eI); } }
                    _changes.push(_ch);
                }
            }
            if (_scope !== "items") {
                var _comps = AE.findComps(${args.comp !== undefined ? jsxVal(args.comp) : '"*"'});
                for (var _ci = 0; _ci < _comps.length; _ci++) {
                    var _c = _comps[_ci];
                    for (var _li = 1; _li <= _c.numLayers; _li++) {
                        var _l = _c.layer(_li);
                        var _lto = _next(_l.name);
                        if (_lto === _l.name) continue;
                        var _lch = { kind: "layer", comp: _c.name, index: _li, from: _l.name, to: _lto };
                        if (!_dry) { try { _l.name = _lto; _lch.applied = true; } catch (eL) { _failed++; _lch.applied = false; _lch.error = AE.errText(eL); } }
                        _changes.push(_lch);
                    }
                }
            }
            return { ok: _failed === 0, error: _failed === 0 ? null : (_failed + " renames failed"), dryRun: _dry, count: _changes.length, changes: _changes };
        `;
  },
});
