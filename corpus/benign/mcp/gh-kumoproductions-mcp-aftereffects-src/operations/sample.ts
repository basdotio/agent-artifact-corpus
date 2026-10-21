// Sampling — one read that answers "what is where, when": per-time values of
// chosen properties across the layers of one or more comps, with each
// layer's active state. Covers value probes, visible-layer listings, and
// match-cut checks (sample both comps, compare the rows).

import { registerOp, jsxFail, jsxVal } from "../registry.js";

const DEFAULT_PROPERTIES = [
  ["Transform", "Anchor Point"],
  ["Transform", "Position"],
  ["Transform", "Scale"],
  ["Transform", "Rotation"],
  ["Transform", "Opacity"],
];

registerOp({
  name: "comp.sample",
  category: "comp",
  readOnly: true,
  description:
    "Sample property values at several times across layers of one or more comps in ONE call. Each row says whether the layer is active at that time (enabled and inside its in/out span) and gives the post-expression value of every requested property (default: the five transform properties). Use it to verify motion, list what is visible when, or compare two comps for a match cut.",
  params: [
    {
      name: "comp",
      type: "any",
      description: "Comp name/id, pattern ('shot_*'), or array of those",
      required: true,
    },
    { name: "times", type: "array", description: "Times in seconds to sample", required: true },
    {
      name: "layer",
      type: "any",
      description:
        "Layer filter: index | name | { id } | 'selected' | 'all' | array (default 'all')",
      required: false,
      default: "all",
    },
    {
      name: "properties",
      type: "array",
      description:
        'Property paths to read, e.g. [["Transform","Position"], ["Effects","Slider Control","Slider"]] (default: the five transform properties)',
      required: false,
    },
    {
      name: "activeOnly",
      type: "boolean",
      description: "Omit layers that are not active at the sampled time (default false)",
      required: false,
      default: false,
    },
  ],
  toJsx(args) {
    const times = Array.isArray(args.times) ? (args.times as unknown[]) : [];
    if (times.length === 0 || !times.every((t) => typeof t === "number")) {
      return jsxFail("times must be a non-empty array of numbers");
    }
    const props = (args.properties ?? DEFAULT_PROPERTIES) as unknown[];
    if (!Array.isArray(props) || !props.every((p) => Array.isArray(p) && p.length > 0)) {
      return jsxFail("properties must be an array of property paths (arrays)");
    }
    return `
            var _comps = AE.findComps(${jsxVal(args.comp)});
            if (_comps.length === 0) return { ok: false, error: "no comps matched" };
            var _times = ${jsxVal(times)};
            var _paths = ${jsxVal(props)};
            var _activeOnly = ${jsxVal(args.activeOnly === true)};
            var _out = [];
            for (var _ci = 0; _ci < _comps.length; _ci++) {
                var _c = _comps[_ci];
                var _layers = AE.resolveLayers(_c, ${jsxVal(args.layer ?? "all")});
                var _samples = [];
                for (var _ti = 0; _ti < _times.length; _ti++) {
                    var _t = _times[_ti];
                    var _rows = [];
                    for (var _li = 0; _li < _layers.length; _li++) {
                        var _l = _layers[_li];
                        var _active = _l.enabled && _t >= _l.inPoint && _t < _l.outPoint;
                        if (_activeOnly && !_active) continue;
                        var _row = { index: _l.index, name: _l.name, active: _active, values: {} };
                        for (var _pi = 0; _pi < _paths.length; _pi++) {
                            var _p = AE.propertyAtPath(_l, _paths[_pi]);
                            var _key = _paths[_pi].join("/");
                            if (!_p || _p.propertyType !== PropertyType.PROPERTY) { _row.values[_key] = null; continue; }
                            try { _row.values[_key] = AE.valueToJson(AE.readValue(_p, _t)); }
                            catch (eV) { _row.values[_key] = null; }
                        }
                        _rows.push(_row);
                    }
                    _samples.push({ time: _t, layers: _rows });
                }
                _out.push({ comp: _c.name, id: _c.id, samples: _samples });
            }
            return { ok: true, comps: _out };
        `;
  },
});
