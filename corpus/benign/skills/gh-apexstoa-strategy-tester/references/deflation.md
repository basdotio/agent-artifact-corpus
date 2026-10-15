# PSR and DSR

Read this when the user asks how PSR or DSR is computed, or a `deflate.py` line needs explaining.

The best of many versions of an idea with nothing in it looks good because it was picked for
looking good. The Deflated Sharpe Ratio (Bailey and Lopez de Prado, 2014) compares the chosen cell
with what the luckiest of N unskilled cells is expected to show.

## Units

Every Sharpe ratio here is per observation, and an observation is one event-day's net return. An
annualised Sharpe must first be divided by the square root of the periods per year. A typed `--sr`
above 1 is refused unless `--sr-is-per-observation` is given: it would mean t exceeds sqrt(n).

## Formulas

```
SR     = mean / sd                         sd with n - 1; skew and kurt are the third and fourth
                                           standardised moments (raw kurtosis: a normal has 3)
R      = 1 - skew*SR + (kurt - 1)/4 * SR^2
PSR(b) = Phi( (SR - b) * sqrt(n - 1) / sqrt(R) )       chance the true Sharpe is above b
SR0    = std_trials * Emax(N)                          expected best of N unskilled cells
DSR    = PSR(SR0)
MinTRL = 1 + R * ( z / (SR - b) )^2                    observations for PSR(b) to reach z
```

Phi is the standard normal distribution function; z is 1.644854 for 95%. Negative skew and fat tails
raise R and lower PSR.

- **N** is read from the lock (declared cells, earlier variants and the amend penalty) and cannot
  be typed in `--exp` mode. No "effective number" of correlated cells is estimated: it can be tuned.
- **Emax(N)** is the larger of two figures, both printed. The paper's closed form is
  `(1 - g) * PhiInv(1 - 1/N) + g * PhiInv(1 - 1/(N*e))` with g = 0.5772156649. The exact expected
  maximum of N standard normals is computed by numerical integration. At N = 2 the closed form
  gives 0.519755 against an exact 0.564190, about 8% low; from N = 3 up it is at or above the
  exact one. With N = 1 it is 0: `one trial: nothing to deflate, DSR equals PSR(0)`.
- **std_trials** is the larger of the measured standard deviation of the declared cells' Sharpes
  and the floor `1 / sqrt(n - 1)`, the spread a Sharpe estimated from n observations has under no
  skill. Both are printed. The floor stops a tiny grid, or a grid of near-identical cells, from
  switching the deflation off. It makes small grids strict: the development t needed is at least
  1.65 at N = 1, 2.21 at 2, 2.70 at 4, 2.95 at 6, 3.17 at 9 and 3.63 at 24, more when the
  measured spread is above the floor: cells that differ in kind are far apart by construction, and
  a real effect that passes alone can then end INCONCLUSIVE. The grid is chosen before the freeze.

## Days needed

`deflate.py` prints the event days that would reach the gate at the observed Sharpe: the larger of
MinTRL against the measured benchmark and `1 + ((z*sqrt(R) + Emax) / SR)^2`, rounded up. At or
below the benchmark: `no number of days is enough at this Sharpe`. At or below zero: no figure.

## The sensitivity line

`deflate.py` prints the lag-1 autocorrelation rho of the series and, when rho is positive,
`Phi(SR * sqrt(n * (1 - rho) / (1 + rho)))` as a first-order adjustment. It is outside the
published DSR and is never used in a gate. A `WARNING:` line appears when rho is beyond
`2 / sqrt(n)` either way: the days are then not independent, and the user should be told.

## A case worked by hand

Ten returns: `0.01, -0.02, 0.03, 0.00, 0.02, -0.01, 0.04, -0.03, 0.02, 0.01`.

- Sum 0.07, mean 0.007. Sum of squared deviations 0.00441, sample variance 0.00049, sd 0.022136,
  so SR = 0.007 / 0.022136 = 0.316228.
- Population variance 0.000441, sigma 0.021. Third central moment -2.304e-6, skew -0.248785.
  Fourth central moment 4.01457e-7, kurt 2.064248.
- R = 1 + 0.248785 * 0.316228 + (1.064248 / 4) * 0.1 = 1.105279, square root 1.051323.
- PSR(0) = Phi(0.316228 * 3 / 1.051323) = Phi(0.902371) = 0.816570.
- As the best of N = 600 with a trial spread of 0.05: Emax = 0.422784 * 2.935199 + 0.577216 *
  3.232699 = 3.106921, SR0 = 0.155346, DSR = Phi((0.316228 - 0.155346) * 3 / 1.051323) =
  Phi(0.459084) = 0.676913.
- `deflate.py` would not use 0.05 here. With ten observations the floor is 1 / sqrt(9) = 0.333333,
  so SR0 = 1.035640 and DSR = 0.0200. Ten observations prove nothing either way.

A larger case: SR 0.12 over 400 observations (t = 2.4), skew -0.3, kurtosis 4.5. PSR(0) is 0.9904,
which reads as a clear pass. As the best of 600 with a typed spread of 0.05, the floor
1 / sqrt(399) = 0.050063 applies, SR0 is 0.155541, above the observed Sharpe, and DSR is 0.2441:
no number of further days at that Sharpe would make it a pass.

## Published check values the scripts reproduce

- DSR paper: SR = 2.5 / sqrt(250) = 0.158114, n = 1250, skew -3, kurt 10, trial spread
  sqrt(1/500). N = 100 gives SR0 0.113172 and DSR 0.900397; N = 46 gives SR0 0.100362 and DSR
  0.950502; with skew 0, kurt 3 and N = 88, DSR is 0.950491.
- PSR paper: mean 0.036, sd 0.079, skew -2.448, kurt 10.164. PSR(0) is 0.9127 at n = 24 and
  0.9530 at n = 36.
- MinTRL: SR 0.1 with normal returns needs 272.907 observations, so 273 days.

## A finished return list

For someone who arrives with returns and no experiment folder there are two stand-alone forms:

```
python3 <skill>/scripts/deflate.py --returns r.csv --column ret --trials N [--grid-sharpes g.csv --grid-column sharpe]
python3 <skill>/scripts/deflate.py --sr S --n n --skew k --kurt K --trials N [--trials-sr-std s]
```

Their output starts with `N was typed by hand and is not bound to a frozen declaration`; repeat
that with the figure. A DSR quoted without its N is not a DSR.
