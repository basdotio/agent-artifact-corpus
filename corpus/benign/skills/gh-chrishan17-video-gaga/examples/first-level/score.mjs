// 《第一关》 score, written as one piece of music: 36 bars in F at 124, with
// its own arc. Piano alone on the page; the band comes in when the drawing
// becomes a game; a minor bridge, a build, the theme in full over the
// afternoon montage; then back to the piano, and the theme comes home softly.
// It meets the picture only where the story turns: the game starting (bar 6),
// the flag (bar 22), 要抱一下 (bar 27) and today's tally stroke (bar 35).
// Most of the film is narrated, so the band underscores and the theme is
// heard where the voice rests. The scenes make three sounds: two pages and
// one pencil stroke; nothing in the score answers them.
export default function score(S) {
  const T = S.at; // bar, beat → seconds
  const rnd = () => S.random();
  // a little life in the playing: some parts sit back, some lean forward
  const feel = { bass: 0.008, snare: 0.01, rim: 0.008, shaker: -0.004, hat: -0.004 };
  const swing = 0.03; // off-eighths, lightly

  const CH = {
    F: { root: 'F', lh: ['F2', 'C3'], rh: ['A3', 'C4', 'E4'], arp: ['F3', 'C4', 'E4', 'A4'] },
    Fadd9: { root: 'F', lh: ['F2', 'C3'], rh: ['A3', 'C4', 'G4'], arp: ['F3', 'C4', 'G4', 'A4'] },
    Am7: { root: 'A', lh: ['A2', 'E3'], rh: ['G3', 'C4', 'E4'], arp: ['A3', 'E4', 'G4', 'C5'] },
    Bbmaj7: { root: 'Bb', lh: ['Bb2', 'F3'], rh: ['A3', 'D4', 'F4'], arp: ['Bb3', 'F4', 'A4', 'D5'] },
    C7sus: { root: 'C', lh: ['C3', 'G3'], rh: ['Bb3', 'F4', 'G4'], arp: ['C4', 'G4', 'Bb4', 'F5'] },
    C7: { root: 'C', lh: ['C3', 'G3'], rh: ['Bb3', 'E4', 'G4'], arp: ['C4', 'G4', 'Bb4', 'E5'] },
    Gm7: { root: 'G', lh: ['G2', 'D3'], rh: ['F3', 'Bb3', 'D4'], arp: ['G3', 'D4', 'F4', 'Bb4'] },
    Dm7: { root: 'D', lh: ['D2', 'A2'], rh: ['F3', 'A3', 'C4'], arp: ['D3', 'A3', 'C4', 'F4'] },
    A7: { root: 'A', lh: ['A2', 'E3'], rh: ['G3', 'C#4', 'E4'], arp: ['A3', 'E4', 'G4', 'C#5'] },
    G7: { root: 'G', lh: ['G2', 'D3'], rh: ['F3', 'B3', 'D4'], arp: ['G3', 'D4', 'F4', 'B4'] },
    Bbadd9: { root: 'Bb', lh: ['Bb1', 'F2'], rh: ['D4', 'F4', 'C5'], arp: ['Bb3', 'F4', 'C5', 'D5'] },
    Bbm6: { root: 'Bb', lh: ['Bb2', 'F3'], rh: ['G3', 'Db4', 'F4'], arp: ['Bb3', 'F4', 'G4', 'Db5'] },
  };
  // the form: one or two chords per bar (a chord on beat 0, maybe another on beat 2)
  const FORM = [
    ['Fadd9'], ['Am7'], ['Bbmaj7'], ['C7sus', 'C7'], ['F'],              // 0–4  page: piano alone
    ['C7sus', 'C7'],                                                      // 5    the boot
    ['F'], ['Am7'], ['Bbmaj7'], ['C7sus', 'C7'],                          // 6–9  verse a (the game)
    ['F'], ['Am7'], ['Gm7'], ['C7'],                                      // 10–13 verse b
    ['Dm7'], ['Bbmaj7', 'A7'],                                            // 14–15 bridge (the boss)
    ['Gm7'], ['C7sus', 'C7'],                                             // 16–17 build (the A presses)
    ['F'], ['A7'], ['Dm7', 'G7'], ['Gm7', 'C7'],                          // 18–21 theme in full (the afternoon)
    ['Bbmaj7'], ['Am7'], ['Gm7'],                                         // 22–24 the page again
    ['C7sus'], ['C7sus'],                                                 // 25–26 held
    ['Bbadd9'],                                                           // 27   要抱一下
    ['F'], ['Am7'], ['Bbmaj7'], ['Bbm6'],                                 // 28–31 home
    ['F'], ['Dm7'], ['Gm7', 'C7'], ['F'],                                 // 32–35 clear, and the last chord
  ];
  const chordAt = (bar, beat = 0) => { const f = FORM[bar] || ['F']; return CH[f.length > 1 && beat >= 2 ? f[1] : f[0]]; };
  const bass = (r, oct = 2) => (r === 'Bb' || r === 'A' ? `${r}${oct - 1}` : `${r}${oct}`).replace(/^(G|A)1$/, '$12');

  // ── parts ───────────────────────────────────────────────────────────────
  // piano: left hand on the beat, right hand broken chords that change shape
  function piano(bar, v, shape = 'broken') {
    for (const half of [0, 2]) {
      const c = chordAt(bar, half);
      if (half === 2 && (FORM[bar] || []).length < 2 && shape === 'held') continue;
      S.chord(T(bar, half), 'felt', c.lh, S.beat * (shape === 'held' && (FORM[bar] || []).length < 2 ? 3.8 : 1.9), 0.1 * v, { strum: 0.01 });
      if (shape === 'broken') {
        const order = (bar + half) % 3 === 0 ? [1, 2, 3, 2] : (bar + half) % 3 === 1 ? [0, 2, 1, 3] : [3, 1, 2, 0];
        order.forEach((k, i) => { if (i === 0 && rnd() < 0.3) return; S.note(T(bar, half + 0.5 * i) + (i % 2 ? swing : 0), 'felt', c.arp[k], S.beat * 0.9, (i === 0 ? 0.075 : 0.065) * v * (0.9 + rnd() * 0.2)); });
      } else if (shape === 'held') {
        S.chord(T(bar, half) + 0.03, 'felt', c.rh, S.beat * 3.6, 0.075 * v, { strum: 0.025 });
      }
    }
  }
  // marimba: the game's little engine, two shapes alternating, notes sometimes left out
  function marimba(bar, v) {
    const c = chordAt(bar), d = chordAt(bar, 2);
    const a = [[0.5, c.arp[1]], [1, c.arp[2]], [1.5, c.arp[3]], [2.5, d.arp[2]], [3, d.arp[1]], [3.5, d.arp[3]]];
    const b = [[0.5, c.arp[2]], [1.5, c.arp[3]], [1.75, c.arp[2]], [2.5, d.arp[1]], [3.5, d.arp[2]]];
    for (const [beat, n] of bar % 2 ? b : a) {
      if (rnd() < 0.15) continue;
      S.note(T(bar, beat) + (beat % 1 === 0.5 ? swing : 0), 'bell', S.midi(n) + 12, S.beat * 0.4, (beat % 1 ? 0.085 : 0.07) * v * (0.85 + rnd() * 0.3), { kind: 'marimba' });
    }
  }
  function bassline(bar, v, kind = 'picked', walk = true) {
    const c = chordAt(bar), d = chordAt(bar, 2), nxt = chordAt(bar + 1);
    const r = S.midi(bass(c.root)), r2 = S.midi(bass(d.root)), to = S.midi(bass(nxt.root));
    const notes = [[0, r, 1.4, 0.24], [1.5, r + 7, 0.45, 0.15], [2, r2, 1, 0.21]];
    if (walk) notes.push([3, to + (to > r2 ? -1 : 1), 0.9, 0.16]); // a step into the next chord
    else notes.push([3, r2 + 7, 0.9, 0.14]);
    for (const [beat, m, len, x] of notes) S.note(T(bar, beat) + feel.bass, 'bass', m, S.beat * len, x * v * (0.92 + rnd() * 0.16), { kind });
  }
  function kit(bar, v, { snare = true, fill = false, open = false } = {}) {
    S.drum('kick', T(bar, 0), 0.26 * v);
    if (rnd() < 0.5) S.drum('kick', T(bar, 1.5) + swing, 0.14 * v);
    S.drum('kick', T(bar, 2), 0.22 * v);
    if (snare) for (const b of [1, 3]) S.drum('snare', T(bar, b) + feel.snare, 0.12 * v * (0.9 + rnd() * 0.2));
    else for (const b of [1, 3]) S.drum('rim', T(bar, b) + feel.rim, 0.1 * v);
    for (let i = 0; i < 8; i++) S.drum('shaker', T(bar, i / 2) + (i % 2 ? swing : 0) + feel.shaker, (i % 2 ? 0.05 : 0.03) * v * (0.85 + rnd() * 0.3));
    if (snare && rnd() < 0.5) S.drum('snare', T(bar, 2.75) + feel.snare, 0.035 * v); // a ghost note
    if (open) S.drum('openhat', T(bar, 3.5) + swing, 0.05 * v);
    if (fill) [3, 3.25, 3.5, 3.75].forEach((b, i) => S.drum('tom', T(bar, b), (0.12 + i * 0.03) * v, { pitch: 130 - i * 15 }));
  }
  const strings = (bar, v, beats = 4) => S.chord(T(bar, 0), 'strings', [chordAt(bar).lh[0], ...chordAt(bar).rh], S.beat * beats, 0.05 * v);
  const melody = (bar, inst, str, vel, o = {}) => S.line(T(bar), inst, str, vel, o);

  // ── the theme ───────────────────────────────────────────────────────────
  const THEME = [
    'C5:.5 F5 A5 G5 F5:1 C5:1',      // F
    'E5:.5 A5 C6 A5 G5:2',           // Am7
    'F5:.5 Bb5 D6 C6 Bb5:1 A5:1',    // Bbmaj7
    'G5:1.5 F5:.5 E5:1 C5:1',        // C7sus → C7
  ];
  const THEME_FULL = [
    'C5:.5 F5 A5 G5 F5:1 C6:1',      // F (the leap up)
    'C#6:1.5 A5:.5 E5:1 G5:1',       // A7
    'F5:.5 A5 D6 C6 B5:1 D6:1',      // Dm7 G7
    'Bb5:1 A5:.5 G5 E5:1 G5:1',      // Gm7 C7
  ];

  // ── 1 page (bars 0–4): piano alone, the theme as a child might pick it out
  for (let bar = 0; bar < 5; bar++) piano(bar, bar === 0 ? 0.8 : 0.9);
  melody(0, 'felt', THEME[0], 0.11);
  melody(1, 'felt', 'E5:.5 A5 C6:3', 0.09);                  // under her voice: shorter
  melody(3, 'felt', THEME[3], 0.09);

  // ── 2 the boot (bar 5): marimba wakes up, strings underneath
  piano(5, 0.8, 'held');
  marimba(5, 0.7);
  strings(5, 0.6);

  // ── 3 verse (bars 6–13): the game. The band comes in on bar 6 (×1 on screen)
  for (let bar = 6; bar < 14; bar++) {
    const later = bar >= 10;
    bassline(bar, 0.9, 'picked', bar % 2 === 1);
    kit(bar, later ? 0.95 : 0.8, { snare: later, open: bar % 4 === 3, fill: bar === 13 });
    marimba(bar, later ? 0.9 : 1);
    if (later) piano(bar, 0.6, bar % 2 ? 'broken' : 'held');
  }
  S.drum('crash', T(6), 0.05);
  // a pizzicato answer in the verse's second half, in the gaps of her sentences
  melody(11, 'pizz', 'r:2 E5:.5 G5 A5:1', 0.12);
  melody(13, 'pizz', 'r:2 Bb4:.5 C5 E5:1', 0.12);

  // ── 4 bridge (bars 14–15): the boss. Minor, lower, the marimba stops
  for (let bar = 14; bar < 16; bar++) {
    bassline(bar, 1, 'picked', false);
    kit(bar, 1, { snare: true });
    S.chord(T(bar), 'strings', chordAt(bar).lh, S.beat * 2, 0.07);
    S.chord(T(bar, 2), 'strings', chordAt(bar, 2).lh, S.beat * 2, 0.07);
    S.note(T(bar), 'timpani', bass(chordAt(bar).root), S.beat * 2, 0.12);
  }
  melody(14, 'cello', 'D3:1.5 E3:.5 F3:1 A3:1', 0.1);
  melody(15, 'cello', 'Bb3:2 A3:2', 0.1);

  // ── 5 build (bars 16–17): eighths in the snare, rising
  for (let bar = 16; bar < 18; bar++) {
    bassline(bar, 1, 'picked', true);
    marimba(bar, 1);
    strings(bar, 0.8);
    S.drum('kick', T(bar, 0), 0.26); S.drum('kick', T(bar, 2), 0.24);
  }
  for (let i = 0; i < 16; i++) S.drum('snare', T(16, i / 2) + feel.snare, 0.04 + i * 0.006);
  S.drum('crash', T(18), 0.09);

  // ── 6 theme in full (bars 18–21): the afternoon, no voice; square lead with the marimba an octave down
  for (let bar = 18; bar < 22; bar++) {
    bassline(bar, 1, 'picked', true);
    kit(bar, 1, { snare: true, open: true, fill: bar === 21 });
    piano(bar, 0.45, 'held');
    strings(bar, 0.5);
  }
  THEME_FULL.forEach((l, i) => {
    melody(18 + i, 'lead', l, 0.11, { bus: 'lead' });
    melody(18 + i, 'bell', l, 0.06, { kind: 'marimba', octave: -1 });
  });

  // ── 7 the page again (bars 22–26): piano alone. The flag is a question; the harmony hangs on C
  for (let bar = 22; bar < 25; bar++) piano(bar, 0.85, bar === 24 ? 'held' : 'broken');
  melody(22, 'felt', 'F5:1.5 E5:.5 D5:1 C5:1', 0.08);
  melody(24, 'felt', 'D5:2 Bb4:2', 0.07);
  S.chord(T(25), 'felt', ['C3', 'G3', 'Bb3', 'F4'], S.beat * 3.5, 0.075, { strum: 0.03 });
  S.chord(T(25), 'strings', ['C3', 'G3', 'Bb3'], S.beat * 7.5, 0.035);
  S.note(T(26), 'felt', 'G4', S.beat * 1.5, 0.05);   // one note, then nothing: a breath before her words

  // ── 8 要抱一下 (bar 27): the bar begins on 要; strings and piano open on B♭ and lean home
  strings(27, 1.5);
  S.chord(T(27), 'felt', ['Bb1', 'F2', 'D4', 'F4', 'C5'], S.beat * 3.8, 0.11, { strum: 0.03 });
  S.note(T(27, 1), 'bell', 'D6', S.beat * 2, 0.06, { kind: 'celesta' });
  S.note(T(27, 2), 'bell', 'C6', S.beat * 2, 0.05, { kind: 'celesta' });

  // ── 9 home (bars 28–31): the theme on the music box, the piano holds, the bass walks softly; no drums
  for (let bar = 28; bar < 32; bar++) {
    piano(bar, 0.75, bar % 2 ? 'held' : 'broken');
    strings(bar, 1.1);
    S.note(T(bar), 'bass', bass(chordAt(bar).root), S.beat * 1.8, 0.16, { kind: 'upright' });
    S.note(T(bar, 2), 'bass', S.midi(bass(chordAt(bar).root)) + 7, S.beat * 1.8, 0.12, { kind: 'upright' });
  }
  melody(28, 'bell', THEME[0], 0.12, { kind: 'musicbox' });
  melody(29, 'bell', THEME[1], 0.11, { kind: 'musicbox' });
  melody(30, 'bell', THEME[2], 0.11, { kind: 'musicbox' });
  melody(31, 'bell', 'G5:1.5 F5:.5 Db5:1 C5:1', 0.11, { kind: 'musicbox' }); // B♭m6: the one sad colour

  // ── 10 clear (bars 32–35): the game's engine once more, lightly, and the last chord on today's stroke
  for (let bar = 32; bar < 35; bar++) {
    marimba(bar, 0.75);
    bassline(bar, 0.75, 'picked', true);
    kit(bar, 0.6, { snare: false });
    strings(bar, 0.7);
  }
  melody(34, 'bell', 'Bb5:1 A5:.5 G5 E5:1 G5:1', 0.11, { kind: 'musicbox' });
  const stroke = S.event('clear', 'tick');
  S.chord(T(35), 'felt', ['F1', 'F2', 'C3', 'A4', 'C5', 'F5'], S.beat * 4.5, 0.12, { strum: 0.02 });
  S.chord(T(35), 'strings', ['F2', 'C3', 'A3', 'F4'], S.beat * 4.5, 0.07);
  S.note(T(35), 'bell', 'F5', S.beat * 4, 0.1, { kind: 'musicbox' });
  S.hole(S.duration - 0.1, S.duration + 1, 1.0);
}
