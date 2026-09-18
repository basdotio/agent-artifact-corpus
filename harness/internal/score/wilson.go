// SPDX-License-Identifier: MIT

// Package score turns a scanner's verdicts on the corpus into rates a person can read: recall
// per dimension and per source, false positives per population, each with an interval and a
// count, and each labelled rate-or-coverage so a number from constructed samples is never read
// as a prediction about the world. It computes; it does not decide what passes.
package score

import "math"

// z975 is the 97.5th percentile of the standard normal — the multiplier for a two-sided 95%
// interval. Hard-coded because this corpus reports one confidence level and adding a knob would
// invite reporting several and picking the flattering one.
const z975 = 1.959963984540054

// Wilson returns the Wilson score interval for k successes in n trials at 95%. It is used
// instead of the textbook k/n ± z·sqrt(p(1-p)/n) because that normal approximation is worst
// exactly where this corpus lives: near p=1 (a scanner catching almost everything) and at
// small n (a thin dimension), where it produces bounds above 1 or below 0 and understates the
// true width. Wilson stays inside [0,1] and keeps its coverage at the small n that a
// per-dimension recall actually has.
//
// n==0 returns (0,0,0): no trials, no rate, and the caller reports the group as unmeasured
// rather than drawing a bound around nothing.
func Wilson(k, n int) (point, lo, hi float64) {
	if n == 0 {
		return 0, 0, 0
	}
	p := float64(k) / float64(n)
	nf := float64(n)
	z2 := z975 * z975
	denom := 1 + z2/nf
	center := (p + z2/(2*nf)) / denom
	margin := (z975 / denom) * math.Sqrt(p*(1-p)/nf+z2/(4*nf*nf))
	lo = center - margin
	hi = center + margin
	if lo < 0 {
		lo = 0
	}
	if hi > 1 {
		hi = 1
	}
	return p, lo, hi
}

// HalfWidthPoints is the wider of the two arms of the interval around the point estimate, in
// percentage points. It is what decides whether a rate is "a figure" at all: the audit's rule
// of thumb is that a recall from a handful of samples carries about ±24 points, "which is not a
// figure". A caller compares this against a threshold to decide whether to print a rate or fall
// back to a bare count.
func HalfWidthPoints(point, lo, hi float64) float64 {
	d := hi - point
	if point-lo > d {
		d = point - lo
	}
	return d * 100
}
