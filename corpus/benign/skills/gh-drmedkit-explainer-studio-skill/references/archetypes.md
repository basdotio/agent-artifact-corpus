# The six archetypes

Pick the one whose object makes the concept visible. The scaffold (`new-topic.mjs --archetype`) gives each a stand-in
subject, a model with self-checks and the same page/film plumbing; replace the subject and the model, keep the contract.

## 1. machine: the device is the concept
- **Find the object**: the real device whose working is the idea, cut open (four-stroke engine, dynamo/motor, fridge,
  crash car, longcase clock). Ask: which moving part, if the reader watched only it, would teach the concept?
- **Figure must contain**: the cutaway machine on a test bench with its supports, the moving parts posed by the model
  (piston, crank, valves; coil, brushes; escapement), what flows through it made visible (charges, refrigerant, gas),
  the instruments a workshop would bolt on (indicator, scope, gauges, load cells).
- **Instruments**: an indicator diagram or cycle chart, energy books (in = out + losses), a trace against time, a
  performance curve (motor curve, COP against lift).
- **Worked examples**: `four-stroke`, `generator` (Faraday + Lenz on one constant k = N·B·A; energy books close
  exactly), `heat-pump` (p-h diagram with a moving parcel), `pendulum-clock`, `crumple-zone`.
- **Scaffold stand-in**: a brass flywheel spun up by a constant torque against bearing friction.

## 2. bench: a classic experiment on a bench
- **Find the object**: the historical or school apparatus, on an optical bench / lab bench with its real meters
  (photoelectric tube with ammeter and retarding voltage; a camera and candle on a rail; double slit; Cavendish
  torsion balance).
- **Figure must contain**: the bench (rail, ruler, carriers, clamps), the apparatus cut where the physics happens, the
  source, the detector, and the meters the experimenter reads.
- **Instruments**: the measured curve as the experimenter would plot it (I-V, stopping voltage against frequency, blur
  against distance), the meter readings, a ghost of the textbook prediction.
- **Worked examples**: `photoelectric`, `camera-lens` (every ray traced surface by surface; 12 self-checks).
- **Scaffold stand-in**: a carriage on rails pulled by a thread over a pulley block (constant force, rolling friction).

## 3. micro: the concept lives at particle level
- **Find the object**: a real container or sample (a gas cylinder with a piston, a wire, a cup of water, a cabinet)
  with a **magnifier window** in which the particles are drawn and move by the model; the macroscopic meter (gauge,
  thermometer, ammeter) sits on the container and reads the same model.
- **Figure must contain**: the container on its bench, the window (a lens/porthole with its frame), particles that are
  countable, the macro instrument, and a control the reader can turn (heat, piston, voltage).
- **Instruments**: a histogram (speeds, energy shares), a counter (wall hits, ways W), the macro quantity against time
  converging to its theory value.
- **Worked example**: the second-law **marble cabinet**: a wooden cabinet with two blocks
  of oscillators (an Einstein solid: rows of little cups), energy quanta as marbles that hop at random between cups,
  a mechanical ways-counter showing W for the current split and S = k ln W, a rewind button (the film runs the hops
  backwards and the viewer sees how unlikely that is), small N (marbles visibly flow back) against large N (they never
  do); bridge to the fridge (heat-pump) and the engine / Carnot (four-stroke). Model: exact multiplicities
  Ω(N, q) = C(q + N − 1, q) for both blocks, the most probable split, the spread shrinking as 1/√N.
- **Scaffold stand-in**: argon atoms in a 20 × 12 nm window; counted wall hits converge to the pressure 2 KE_x / A.

## 4. field: invisible fields and space
- **Find the object**: a table or tray that makes the field visible with real stuff: a lattice of small compasses,
  iron filings on a glass plate, a rubber-sheet table with rolling balls, a tank with field probes.
- **Figure must contain**: the tray/table, the sources (magnets, charged spheres, masses) that the reader can move,
  the many small indicators (needles, filings, a grid that dips), a probe with a meter.
- **Instruments**: field magnitude at the probe, a field-line or potential plot with the probe marked, force on a test
  object, a falloff graph (1/r², 1/r³ on log axes).
- **Concrete design (gravity)**: a stretched rubber sheet over a ring frame with a grid printed on it; steel balls of
  different masses sit in the dips; a marble rolled across curves around them; a depth gauge on a bridge over the sheet
  reads the dip. Model: membrane deflection from point loads (log potential in 2D), with the honest caveat that the
  sheet is an analogue.
- **Scaffold stand-in**: a bar magnet (two poles) sliding through a lattice of 44 compasses plus the Earth's field;
  checked against the dipole far field.

## 5. chart: math-heavy topics, graphs (AP calculus and kin)
- **Find the object**: a real pen recorder or plotter whose pen is driven by a physical system beside it, so the graph
  is drawn as the system moves: a strip-chart recorder on a mass-spring, a drum barograph, an X-Y plotter whose two arms
  are the two variables, a planimeter tracing an area (integration), a slope gauge riding the curve (derivative).
- **Figure must contain**: the recorder (paper, rollers, pen carriage on its rail, the drive), the system it records,
  and the linkage between them, so the reader sees which motion becomes which axis.
- **Instruments**: the drawn curve itself, plus the derived curve (slope, area so far) on a second pen or panel, and
  readouts of the values at the pen.
- **Concrete design (derivative and integral)**: a two-pen strip-chart recorder: pen 1 records a cart's position from
  a string potentiometer, pen 2 its velocity from a tachometer wheel; a planimeter on the bench integrates pen 2 back
  to pen 1. The film poses the pen exactly where the slope is zero on the word "zero".
- **Scaffold stand-in**: a strip-chart recorder drawing a damped oscillator x(t) (closed form checked against RK4).

## 6. investigation: practices and engineering design
- **Find the object**: a workbench with ONE concrete investigation set up on it (a drop tower and a stopwatch, a ramp
  with light gates, a model bridge being load-tested, a bottle rocket on a launch rail) and a **logbook** that fills
  in trial by trial. The film follows the investigation: question, variables, trials, the spread, the conclusion.
- **Figure must contain**: the set-up with its measuring tools (ruler, gates, scale, stopwatch), the variable the reader
  changes, and the logbook as an instrument (rows appearing, a mean and a spread).
- **Instruments**: the logbook table, a scatter of trials with error bars, the fitted line or the design target.
- **Concrete design (engineering)**: a bridge test rig: a balsa truss across two supports, a hanger with slotted
  masses, a dial gauge under mid-span, the logbook of load against deflection until the first member buckles; the model
  is the truss's member forces and Euler buckling of the top chord.
- **Scaffold stand-in**: a drop tower (post, arm, release clamp, ball, pad, light gate), a stopwatch, a logbook; the
  model is free fall with quadratic drag (closed form; energy books close).
