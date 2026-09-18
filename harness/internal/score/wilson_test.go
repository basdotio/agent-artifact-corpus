// SPDX-License-Identifier: MIT

package score

import (
	"math"
	"testing"
)

func TestWilsonKnownInterval(t *testing.T) {
	// 9 of 10 at 95% is a standard textbook case: Wilson gives roughly [0.596, 0.982],
	// nothing like the normal approximation's 0.9 ± 0.186 = [0.714, 1.086] which runs past 1.
	p, lo, hi := Wilson(9, 10)
	if math.Abs(p-0.9) > 1e-9 {
		t.Errorf("point = %v, want 0.9", p)
	}
	if math.Abs(lo-0.5958) > 0.01 {
		t.Errorf("lo = %v, want ~0.596", lo)
	}
	if math.Abs(hi-0.9821) > 0.01 {
		t.Errorf("hi = %v, want ~0.982", hi)
	}
}

func TestWilsonStaysInUnitInterval(t *testing.T) {
	// The whole reason for Wilson over the normal approximation: at the extremes the bounds
	// must not leave [0,1], where a scanner catching everything or nothing actually sits.
	for _, tc := range []struct{ k, n int }{{10, 10}, {0, 10}, {1, 3}, {0, 1}} {
		_, lo, hi := Wilson(tc.k, tc.n)
		if lo < 0 || hi > 1 {
			t.Errorf("Wilson(%d,%d) = [%v,%v], escaped [0,1]", tc.k, tc.n, lo, hi)
		}
	}
}

func TestWilsonZeroTrials(t *testing.T) {
	// No trials is not a rate of zero — it is no measurement, and the caller must be able to
	// tell the two apart.
	p, lo, hi := Wilson(0, 0)
	if p != 0 || lo != 0 || hi != 0 {
		t.Errorf("Wilson(0,0) = (%v,%v,%v), want all zero as the unmeasured sentinel", p, lo, hi)
	}
}

func TestHalfWidthShrinksWithN(t *testing.T) {
	// A dimension with more samples must report a tighter figure; this is the entire argument
	// for reporting per-dimension n beside every rate.
	_, lo6, hi6 := Wilson(5, 6)
	_, lo60, hi60 := Wilson(50, 60)
	small := HalfWidthPoints(5.0/6, lo6, hi6)
	big := HalfWidthPoints(50.0/60, lo60, hi60)
	if big >= small {
		t.Errorf("half-width at n=60 (%v) not tighter than at n=6 (%v)", big, small)
	}
}
