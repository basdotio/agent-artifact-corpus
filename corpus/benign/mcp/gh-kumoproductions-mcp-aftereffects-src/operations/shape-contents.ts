// Shape-contents operations — the ones that look INSIDE a shape layer
// instead of adding to it: per-group bounds, bulk recolor, structural
// signatures, splitting groups into layers, and turning imported vector
// (Illustrator) layers into shape layers.
//
// Every op here that reads or edits several layers takes the same `layer`
// vocabulary as transform.set / property.set: index | name | { id } |
// 'selected' | 'all' | an array of those.

import { registerOp, jsxFail, jsxVal, jsxCompPreamble, jsxCompLayerPreamble } from "../registry.js";

const LAYER_TARGET_PARAM = {
  name: "layer",
  type: "any" as const,
  description: "Layer index, name, { id }, 'selected', 'all', or an array of those (shape layers)",
  required: true,
};

registerOp({
  name: "shape.group_bounds",
  category: "shape",
  readOnly: true,
  description:
    "Bounds of each top-level vector group of a shape layer, in LAYER space with the group's own transform applied — what you need to split, align, or anchor per part. Geometry-based (exact for paths/rects/ellipses; strokes padded in; stars and path modifiers such as Trim/Repeater are listed in `approximate`). Also reports the whole layer's bounds.",
  params: [
    { name: "comp", type: "any", description: "Comp name or id", required: true },
    LAYER_TARGET_PARAM,
    {
      name: "time",
      type: "number",
      description: "Evaluate animated paths/transforms at this time (default: current value)",
      required: false,
    },
    {
      name: "includeStroke",
      type: "boolean",
      description: "Pad by half the widest stroke (default true)",
      required: false,
      default: true,
    },
  ],
  toJsx(args) {
    return `
            ${jsxCompPreamble(args)}
            var _layers = AE.resolveLayers(_comp, ${jsxVal(args.layer)});
            if (_layers.length === 0) return { ok: false, error: "no layers matched" };
            var _opts = { time: ${jsxVal(args.time ?? null)}, includeStroke: ${jsxVal(args.includeStroke !== false)} };
            var _out = [];
            for (var _li = 0; _li < _layers.length; _li++) {
                var _l = _layers[_li];
                if (!(_l instanceof ShapeLayer)) { _out.push({ index: _l.index, name: _l.name, ok: false, error: "not a shape layer" }); continue; }
                var _contents = _l.property("Contents");
                var _groups = [];
                for (var _gi = 1; _gi <= _contents.numProperties; _gi++) {
                    var _g = _contents.property(_gi);
                    if (_g.matchName !== "ADBE Vector Group") continue;
                    var _b = AE.shapeGroupBounds(_g, _opts);
                    _b.index = _gi;
                    _b.name = _g.name;
                    _groups.push(_b);
                }
                _out.push({ index: _l.index, name: _l.name, ok: true, layer: AE.shapeLayerBounds(_l, _opts), groups: _groups });
            }
            return { ok: true, count: _out.length, layers: _out };
        `;
  },
});

registerOp({
  name: "shape.recolor",
  category: "shape",
  description:
    "Replace fill and/or stroke colors throughout a shape layer's contents (any nesting depth). Either `color` (paint everything one color — silhouettes) or `map` ([{ from, to }] — per-color substitution, matched within `tolerance`). Colors are [r,g,b] 0-1 (alpha optional).",
  params: [
    { name: "comp", type: "any", description: "Comp name or id", required: true },
    LAYER_TARGET_PARAM,
    {
      name: "target",
      type: "string",
      description: "fill|stroke|both (default both)",
      required: false,
      default: "both",
    },
    {
      name: "color",
      type: "array",
      description: "[r,g,b] — set every matching fill/stroke to this color",
      required: false,
    },
    {
      name: "map",
      type: "array",
      description: "[{ from: [r,g,b], to: [r,g,b] }, …] — replace only colors that match `from`",
      required: false,
    },
    {
      name: "tolerance",
      type: "number",
      description: "Per-channel match tolerance for `map` (default 0.01)",
      required: false,
      default: 0.01,
    },
  ],
  toJsx(args) {
    if (args.color === undefined && args.map === undefined) {
      return jsxFail("give either color (recolor everything) or map (per-color substitution)");
    }
    return `
            ${jsxCompPreamble(args)}
            var _layers = AE.resolveLayers(_comp, ${jsxVal(args.layer)});
            if (_layers.length === 0) return { ok: false, error: "no layers matched" };
            var _target = ${jsxVal(args.target ?? "both")};
            if (_target !== "fill" && _target !== "stroke" && _target !== "both") return { ok: false, error: "target must be fill|stroke|both" };
            var _opts = { target: _target, color: ${jsxVal(args.color ?? null)}, map: ${jsxVal(args.map ?? null)}, tolerance: ${jsxVal(args.tolerance ?? 0.01)} };
            var _out = [];
            var _total = 0;
            for (var _li = 0; _li < _layers.length; _li++) {
                var _l = _layers[_li];
                if (!(_l instanceof ShapeLayer)) { _out.push({ index: _l.index, name: _l.name, ok: false, error: "not a shape layer" }); continue; }
                var _r = AE.recolorContents(_l.property("Contents"), _opts);
                _total += _r.changed;
                _out.push({ index: _l.index, name: _l.name, ok: true, changed: _r.changed, visited: _r.visited });
            }
            return { ok: true, changed: _total, layers: _out };
        `;
  },
});

registerOp({
  name: "shape.signature",
  category: "shape",
  readOnly: true,
  description:
    "Structural hash of a shape layer's contents and of each top-level group — matchNames plus rounded values, NO display names — so identical artwork hashes the same even after renaming. Use it to find duplicate layers when merging comps, or to check that a copy still matches its source.",
  params: [
    { name: "comp", type: "any", description: "Comp name or id", required: true },
    LAYER_TARGET_PARAM,
    {
      name: "precision",
      type: "number",
      description: "Decimal places kept when rounding values (default 2)",
      required: false,
      default: 2,
    },
    {
      name: "time",
      type: "number",
      description: "Evaluate animated values at this time (default: current value)",
      required: false,
    },
    {
      name: "includeLayerTransform",
      type: "boolean",
      description:
        "Also hash the layer's Transform group (default false — copies usually differ only in position)",
      required: false,
      default: false,
    },
  ],
  toJsx(args) {
    return `
            ${jsxCompPreamble(args)}
            var _layers = AE.resolveLayers(_comp, ${jsxVal(args.layer)});
            if (_layers.length === 0) return { ok: false, error: "no layers matched" };
            var _prec = ${jsxVal(args.precision ?? 2)};
            var _t = ${jsxVal(args.time ?? null)};
            var _withXf = ${jsxVal(args.includeLayerTransform === true)};
            var _out = [];
            for (var _li = 0; _li < _layers.length; _li++) {
                var _l = _layers[_li];
                if (!(_l instanceof ShapeLayer)) { _out.push({ index: _l.index, name: _l.name, ok: false, error: "not a shape layer" }); continue; }
                var _contents = _l.property("Contents");
                var _canon = AE.canonicalGroup(_contents, _prec, _t);
                if (_withXf) _canon += "|xf:" + AE.canonicalGroup(_l.property("Transform"), _prec, _t);
                var _groups = [];
                for (var _gi = 1; _gi <= _contents.numProperties; _gi++) {
                    var _g = _contents.property(_gi);
                    _groups.push({ index: _gi, name: _g.name, matchName: _g.matchName, signature: AE.hashString(AE.canonicalGroup(_g, _prec, _t)) });
                }
                _out.push({ index: _l.index, name: _l.name, ok: true, signature: AE.hashString(_canon), groups: _groups });
            }
            return { ok: true, count: _out.length, layers: _out };
        `;
  },
});

registerOp({
  name: "layer.split_groups",
  category: "layer",
  description:
    "Split a shape layer into one layer per top-level vector group (letters of a word, parts of a character), keeping every group's transform, fills and strokes. New layers stack in group order directly above the original. `anchor` re-anchors each new layer to its own artwork without moving it on screen.",
  params: [
    { name: "comp", type: "any", description: "Comp name or id", required: true },
    {
      name: "layer",
      type: "any",
      description: "1-based layer index, name, or { id } (a shape layer)",
      required: true,
    },
    {
      name: "groups",
      type: "array",
      description: "1-based indices of the groups to split out (default: every top-level group)",
      required: false,
    },
    {
      name: "anchor",
      type: "string",
      description:
        "keep | center | topLeft | topCenter | topRight | centerLeft | centerRight | bottomLeft | bottomCenter | bottomRight — anchor each new layer on its own bounds (default keep)",
      required: false,
      default: "keep",
    },
    {
      name: "nameTemplate",
      type: "string",
      description: "Name for each new layer; tokens {group}, {layer}, {index} (default '{group}')",
      required: false,
      default: "{group}",
    },
    {
      name: "keepOriginal",
      type: "boolean",
      description: "Leave the source layer in place (default false: it is removed once split)",
      required: false,
      default: false,
    },
  ],
  toJsx(args) {
    return `
            ${jsxCompLayerPreamble(args)}
            if (!(_layer instanceof ShapeLayer)) return { ok: false, error: "not a shape layer" };
            var _anchor = ${jsxVal(args.anchor ?? "keep")};
            if (_anchor !== "keep" && !AE.ANCHOR_PRESETS.hasOwnProperty(_anchor)) return { ok: false, error: "unknown anchor preset '" + _anchor + "'" };
            var _tpl = ${jsxVal(args.nameTemplate ?? "{group}")};
            var _contents = _layer.property("Contents");
            var _want = ${jsxVal(args.groups ?? null)};
            var _indices = [];
            if (_want === null) {
                for (var _gi = 1; _gi <= _contents.numProperties; _gi++) {
                    if (_contents.property(_gi).matchName === "ADBE Vector Group") _indices.push(_gi);
                }
            } else {
                for (var _wi = 0; _wi < _want.length; _wi++) {
                    var _w = _want[_wi];
                    if (_w < 1 || _w > _contents.numProperties) return { ok: false, error: "group index " + _w + " out of range (layer has " + _contents.numProperties + ")" };
                    _indices.push(_w);
                }
            }
            if (_indices.length === 0) return { ok: false, error: "no vector groups to split" };
            var _srcName = _layer.name;
            var _created = [];
            // duplicate() lands directly above the original, so each copy
            // slips in BELOW the copies made before it: creating the groups in
            // order leaves group 1 on top and the last group just above the
            // original, matching the render order inside the layer.
            for (var _k = 0; _k < _indices.length; _k++) {
                var _keep = _indices[_k];
                var _dup = _layer.duplicate();
                var _dc = _dup.property("Contents");
                for (var _ri = _dc.numProperties; _ri >= 1; _ri--) {
                    if (_ri !== _keep) _dc.property(_ri).remove();
                }
                var _grp = _dc.property(1);
                var _gname = _grp.name;
                _dup.name = _tpl.replace(/\\{group\\}/g, _gname).replace(/\\{layer\\}/g, _srcName).replace(/\\{index\\}/g, String(_keep));
                var _entry = { index: _dup.index, name: _dup.name, group: _gname, groupIndex: _keep };
                if (_anchor !== "keep") {
                    var _b = AE.shapeGroupBounds(_grp, {});
                    if (_b.empty) {
                        _entry.warning = "group has no geometry; anchor left unchanged";
                    } else {
                        var _pt = AE.pointInRect(_b, _anchor);
                        var _mv = AE.moveAnchor(_dup, _pt);
                        _entry.anchorPoint = _mv.anchorPoint;
                        if (_mv.warnings.length) _entry.warning = _mv.warnings.join("; ");
                    }
                }
                _created.push(_entry);
            }
            if (!${jsxVal(args.keepOriginal === true)}) _layer.remove();
            for (var _ci = 0; _ci < _created.length; _ci++) {
                _created[_ci].index = AE.findLayerInComp(_comp, _created[_ci].name) ? AE.findLayerInComp(_comp, _created[_ci].name).index : _created[_ci].index;
            }
            return { ok: true, source: _srcName, created: _created.length, layers: _created };
        `;
  },
});

registerOp({
  name: "layer.convert_to_shapes",
  category: "layer",
  description:
    "Run 'Create Shapes from Vector Layer' on imported Illustrator/vector layers: each becomes a shape layer directly above the original (which AE switches off). By default the ' Outlines' suffix AE appends is stripped; removeSource deletes the vector layers, removeFootage also deletes their footage items when nothing else uses them. Note: the shape layers can arrive with Position dimensions SEPARATED — every write in this server handles that.",
  params: [
    { name: "comp", type: "any", description: "Comp name or id", required: true },
    LAYER_TARGET_PARAM,
    {
      name: "stripSuffix",
      type: "boolean",
      description:
        "Rename the new layer to the original's name (drop ' Outlines' / localized suffix). Default true",
      required: false,
      default: true,
    },
    {
      name: "removeSource",
      type: "boolean",
      description: "Delete the original vector layer after conversion (default false)",
      required: false,
      default: false,
    },
    {
      name: "removeFootage",
      type: "boolean",
      description:
        "With removeSource: also delete the footage item when no other layer uses it (default false)",
      required: false,
      default: false,
    },
  ],
  toJsx(args) {
    return `
            ${jsxCompPreamble(args)}
            var _layers = AE.resolveLayers(_comp, ${jsxVal(args.layer)});
            if (_layers.length === 0) return { ok: false, error: "no layers matched" };
            var _cmd = 0;
            try { _cmd = app.findMenuCommandId("Create Shapes from Vector Layer"); } catch (eFind) {}
            // Menu names are localized; the id is not (3973 on every AE since CS6).
            if (!_cmd) _cmd = 3973;
            var _sources = [];
            for (var _si = 0; _si < _layers.length; _si++) {
                if (!(_layers[_si] instanceof AVLayer) || !_layers[_si].source) return { ok: false, error: "layer '" + _layers[_si].name + "' is not a footage layer" };
                _sources.push(_layers[_si]);
            }
            var _out = [];
            var _strip = ${jsxVal(args.stripSuffix !== false)};
            var _rmSrc = ${jsxVal(args.removeSource === true)};
            var _rmFoot = ${jsxVal(args.removeFootage === true)};
            try { _comp.openInViewer(); } catch (eV) {}
            for (var _i = 0; _i < _sources.length; _i++) {
                var _src = _sources[_i];
                var _srcName = _src.name;
                var _foot = _src.source;
                var _snap = AE.layerIdSnapshot(_comp);
                AE.withSelection(_comp, [_src], function () { app.executeCommand(_cmd); });
                var _added = AE.layersSince(_comp, _snap);
                var _shape = null;
                for (var _ai = 0; _ai < _added.length; _ai++) {
                    if (_added[_ai] instanceof ShapeLayer) { _shape = _added[_ai]; break; }
                }
                if (!_shape) { _out.push({ source: _srcName, ok: false, error: "the command created no shape layer (is the layer a vector footage layer?)" }); continue; }
                var _entry = { source: _srcName, ok: true, index: _shape.index, name: _shape.name, originalName: _shape.name };
                if (_strip) {
                    var _clean = _shape.name.replace(/\\s*Outlines$/, "").replace(/\\s*(の)?アウトライン$/, "");
                    if (_clean.length === 0) _clean = _srcName;
                    _shape.name = _clean;
                    _entry.name = _shape.name;
                }
                if (_rmSrc) {
                    _src.remove();
                    _entry.sourceRemoved = true;
                    if (_rmFoot && _foot) {
                        var _used = 0;
                        try { _used = _foot.usedIn.length; } catch (eU) { _used = 1; }
                        if (_used === 0) { try { _foot.remove(); _entry.footageRemoved = true; } catch (eF) { _entry.footageRemoved = false; } }
                        else _entry.footageRemoved = false;
                    }
                    _entry.index = _shape.index;
                }
                _out.push(_entry);
            }
            var _failed = 0;
            for (var _fi = 0; _fi < _out.length; _fi++) if (!_out[_fi].ok) _failed++;
            return { ok: _failed === 0, error: _failed === 0 ? null : (_failed + " of " + _out.length + " layers did not convert"), converted: _out.length - _failed, layers: _out };
        `;
  },
});
