# Before and after

Pairs taken from Partas repositories. Each "after" was written by re-reading the code, not the
old doc.

## Empty params and copied exception text (Partas.GitNet, SepochSemver)

Before:

```fsharp
/// <summary>
/// Strict SemVer parsing; with no <c>v</c> prefix allowed.
/// </summary>
/// <param name="input"></param>
/// <exception cref="System.ArgumentException">style is not a valid Semver.SemVersionStyles value.</exception>
/// <exception cref="System.ArgumentNullException">version is null.</exception>
/// <exception cref="System.FormatException">The version is invalid or not in a format compliant with style.</exception>
let strictParseSepochSemver input =
```

Problems: an empty `<param>`; three `<exception>` lines copied from `SemVersion.Parse`, where
`style` is a constant here (so the `ArgumentException` cannot occur) and the text names
parameters this function does not have; short crefs, which F# does not resolve.

After:

```fsharp
/// <summary>Parses an optional Sepoch prefix followed by strict SemVer 2.0; a <c>v</c> prefix is rejected.</summary>
/// <exception cref="T:System.FormatException">The version after the Sepoch is not strict SemVer 2.0.</exception>
let strictParseSepochSemver input =
```

`input` has no constraint beyond its type, so it gets no `<param>`.

## `<br/>` as paragraph break (Partas.GitNet, Config)

Before:

```fsharp
/// <summary>
/// Title > FileName<br/><br/>
/// The scope is derived from the title of the project if present; otherwise, the file name is used.
/// </summary>
| Auto
```

After:

```fsharp
/// <summary>The scope is the project's title when it has one, otherwise its file name.</summary>
| Auto
```

The `Title > FileName` shorthand said the same thing as the sentence; the sentence alone is
clearer, and the unescaped `>` was fragile.

## Argument for the design instead of the contract (Partas.Build)

Before:

```fsharp
/// <summary>
/// The generation itself. Shared by the stage and the CLI command, so neither can drift from
/// the other.
/// </summary>
```

"Shared by the stage and the CLI command, so neither can drift" argues the design is right
(premise-then-inference). A caller needs what it generates and when it fails.

After:

```fsharp
/// <summary>Writes the external-annotations XML for <c>assembly</c> to <c>output</c>.</summary>
/// <remarks>Members the filter cannot annotate are skipped with a warning, or fail the run under <c>--strict</c>.</remarks>
```

## Code example without `lang`, and `<br/>` (Partas.Solid)

Before:

```fsharp
/// <summary>
/// Calling the setter updates the Signal (triggering dependents to rerun) if the value actually changed.
/// <br/>The setter takes either the new value for the signal or a function that maps the previous value of the signal to a new value as its only argument. The updated value is also returned by the setter.
/// </summary>
/// <remarks>
/// To pass a handler that maps the previous value, call Invoke on the setter.
/// <code>
/// let index,setIndex = createSignal(0)
/// setIndex.Invoke(fun x -> x + 1)
/// </code>
/// To access the returned value, use <c>.InvokeGet</c>
/// </remarks>
type Setter<'T> = 'T -> unit
```

After:

```fsharp
/// <summary>
/// Sets the signal's value; dependents rerun only when the value changes.
/// <para>Pass a mapping of the previous value with <c>.Invoke</c>; read the new value back with <c>.InvokeGet</c>.</para>
/// </summary>
/// <example>
/// <code lang="fsharp">
/// let index, setIndex = createSignal 0
/// setIndex.Invoke(fun x -> x + 1)
/// </code>
/// </example>
type Setter<'T> = 'T -> unit
```

## Nothing to say

```fsharp
/// <summary>The empty set.</summary>
static member Empty = ...
```

A private member whose name and type say it all gets no doc. A public one keeps a one-line
summary so the tooltip is not blank, and stays this short unless there is a real fact to add.
Do not pad it with claims of ordinary good practice ("never mutated", "thread-safe") that the
codebase already guarantees everywhere.
