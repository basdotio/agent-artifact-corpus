---
name: gum-jsx
description: Create plots, diagrams, and other visualizations with the "gum.jsx" language.
---

# Introduction

The `gum.jsx` language allows for the elegant and concise creation of SVG visualizations. It has a React-like JSX syntax. When interpreted, it produces pure SVG of a specified size. It is a library of `Element` derived components such as `Circle`, `Stack`, `Plot`, `Network`, and many more. Some of these map closely to standard SVG objects, while others are higher level abstractions and layout containers. You can add standard SVG attributes (like `fill`, `stroke`, `stroke-width`, `opacity`, etc.) to any `Element` component and they will be applied to the resulting SVG.

*Proportional values*: In most cases, values are passed in proportional floating point terms. So to place an object in the center of its parent, you would specify `pos = [0.5, 0.5]`, with the size specified by `size`. When dealing with inherently absolute concepts like `stroke-width`, standard SVG units are used, and numerical values assumed to be specified in pixels. Most `Element` objects fill the standard coordinate space `[0, 0, 1, 1]` by default. To reposition them, either pass the appropriate internal arguments (such as `pos` or `size`) or use a layout component such as `Box` or `Stack` to arrange them.

*Aspect ratio*: Any `Element` object can have an aspect ratio `aspect`. If `aspect` is not defined, it will stretch to fit any box, while if `aspect` is defined it will be sized so as to fit within the specified rectangle while maintaining its aspect ratio. However, when `expand` is set to `true`, the element will be sized to cover the specified rectangle, while maintaining its aspect ratio.

*Subunit arguments*: For compound elements that inherit `Group`, some keyword arguments are passed down to the constituent parts. For instance, in [Plot](/docs/Plot), one can specify arguments intended for the `XAxis` unit by prefixing them with `xaxis-`. For example, setting the `stroke-width` for this subunit can be achieved with `xaxis-stroke-width`.

*Functional approach*: Avoid explicit for loops. There are `numpy`-like functions such as `range` and `linspace` for generating arrays, `zip` for combining arrays, and `palette` for interpolating colors. Additionally, you can use `map` to generate a list of elements (such as bars for a bar plot).

*Style tips*: There will be cases where a user prompt does not fully specify every detail. In these cases, use your best judgment and consider the following suggestions:
  - Text should be legible and not overlap. Usually a text element `ysize` of about `0.1` to `0.2` works well
  - Points and other small features should be visible but not overwhelming. Usually a size of about `0.03` is good for small features
  - The figure should have appropriate outer margins so that extended features like tick labels do not get cut off. Usually a margin of about `0.1` to `0.2` works well. The best way to create outer margins is to wrap the final output in a `Box` or `Frame` component
  - When the aspect ratio of the figure is not determined, a good default is to use `2` for things like plots and diagrams
  - The top-level `<svg>` element will have `fill="none"` and `stroke="black"` applied automatically, so you only need to specify these attributes when they differ from these defaults

# Examples

Below are some examples of user prompts and code output. In these examples, we try to highlight the most common use cases for the library, as well as some of the common pitfalls that one might encounter.

**Example 1: Basic Frame**

Let's start with a very simple example that creates a blue circle (`aspect = 1`) and encloses it in a rounded frame. In general, `Box` is an extremely useful component, as its child class `Frame`, which simply adds a default `border = 1`. This closely mirrors the behavior of a typical HTML element with Tailwind-like syntax.

*Prompt*: Create a blue circle that is enclosed in a rounded box. It should mostly fill the box, but not completely.

*Generated code*:
```jsx
<Frame padding margin rounded>
  <Circle fill={blue} />
</Frame>
```

Here we used boolean defaults for `padding`, `margin`, and `rounded`. These will get mapped to `padding={0.1}`, `margin={0.1}`, and `rounded={0.1}` respectively. This adds a little bit of a Tailwind-like flavor and is used throughout the library. Adding a `margin` on the outside is usually good so things like borders don't get clipped.

**Example 2: Symbolic Plot**

Now let's do a more complex example that uses a higher level component that is not a standard SVG element. In this case, we use `Plot`, which is a `Graph` subclass that adds axes (with `Axis`/`HAxis`/`VAxis`), labels, and other plot-specific features.

*Prompt*: Create a simple plot of a sine wave titled "Sine Wave" with dashed grid lines.

*Generated code*:
```jsx
<Plot aspect={2} margin={0.2} ylim={[-1.5, 1.5]} title="Sine Wave" grid grid-stroke-dasharray={4}>
  <SymLine fy={sin} xlim={[0, 2*pi]} />
</Plot>
```

Notice how we can pass arguments to sub-components using prefixing. Here we set the `stroke-dasharray` for the grid lines to `4`. For convenience, `Plot` accepts `Box` arguments such as `margin`, `border`, etc.

**Example 3: Custom Component**

Creating custom components is a powerful way to avoid code duplication and to make your code more readable and maintainable. Here we create a `Squire` component that is a `Square` with a default `rounded` border. Then we use this component to create two squares side by side.

*Prompt*: Create two rounded boxes side by side. Left one should be blue, right one should be red.

*Generated code*:
```jsx
const Squire = (attr) => <Square rounded {...attr} />
return <HStack spacing>
  <Squire fill={blue} />
  <Squire fill={red} />
</HStack>
```

Note: Because this is two squares (`aspect = 1`) stacked side by side, the `HStack` will have an aspect ratio of `2`. You can also use the `VStack` component to stack elements vertically. If you wish to override aspect-based sizing, you can use the `stack-size` argument to specify the size of the child elements.

**Example 4: Modular Approach**

Now let's cover a VERY IMPORTANT method of using custom components. We want to create modular and parameterizable components that can be reused in a variety of ways. Here we create a `Star` component that specifies its `Spline` path in internal coordinates, and we then pass the `pos`/`size` arguments to the component to position and scale the star.

*Prompt*: Create a semi-random starfield with about 10 yellow stars.

*Generated code*:
```jsx
const aster = [
  [0.5, 0], [0.65, 0.35],
  [1, 0.5], [0.65, 0.65],
  [0.5, 1], [0.35, 0.65],
  [0, 0.5], [0.35, 0.35],
]
const points = [
  [0.15, 0.20], [0.72, 0.12], [0.45, 0.55],
  [0.88, 0.68], [0.30, 0.80], [0.60, 0.35],
  [0.10, 0.58], [0.82, 0.42], [0.50, 0.90],
  [0.25, 0.10],
]
const Star = (attr) =>
  <Spline size={0.06} aspect closed points={aster} {...attr} />
return <Box border rounded fill={gray}>
  {points.map(p => <Star pos={p} fill={yellow} />)}
</Box>
```

Note: By creating a reusable `Star` component that accepts `pos`/`size` arguments, we can easily create a starfield by mapping over `points`. This offloads the logic of adding and scaling the spline coordinates in `aster` to the positions listed in `points`.

**Example 5: Stacking Layouts**

Stacking components can be tricky. If all your children have well-defined aspect ratios, it's often quite straightforward. But even in that case, you may want to override the default aspect-based sizing. Let's look at the case of a wide figure with a short text label underneath it.

```jsx
<VStack spacing={0.05}>
  <Rect rounded aspect={5} fill={blue} />
  <Text stack-size={0.2}>Hello World!</Text>
</VStack>
```

Without specifying `stack-size`, the `Text` element would be quite large (it has an aspect ratio of around `6`). By specifying `stack-size`, we can force the text to be smaller. Because it will be thinner than its assigned rectangle, we need to take a stance on how to justify it. By default it will be centered, but this can be overridden with the `justify` argument.

# Utilities

Here are the handy array functions provided by the library. All of these mimic the behavior of their counterparts in Python and `numpy`. This can be useful for generating `Element` objects from arrays:
```typescript
function zip(...arrs: any[]): any[]
function range(start: number, end: number, step: number): number[]
function linspace(start: number, end: number, num: number): number[]
function enumerate(x: any[]): any[]
function repeat(x: any, n: number): any[]
function lingrid(xlim: range, ylim: range, N: number): number[][]
```

Some of the most commonly used mathematical constants are pre-defined in the global scope:
```javascript
const e = Math.E // base of the natural logarithm
const pi = Math.PI // ratio of circumference to diameter
const phi = (1 + sqrt(5)) / 2 // golden ratio
const r2d = 180 / Math.PI // conversion from radians to degrees
const d2r = Math.PI / 180 // conversion from degrees to radians
```

Additionally, there is a default `gum.jsx` color palette that is pre-defined in the global scope, but you can also use any valid CSS color string:
```javascript
const none = 'none'
const white = '#ffffff'
const black = '#000000'
const blue = '#1e88e5'
const red = '#ff0d57'
const green = '#4caf50'
const yellow = '#ffb300'
const purple = '#9c27b0'
const gray = '#f0f0f0'
```

To interpolate colors between color values, you can use these functions:
```typescript
function interp(c1: string, c2: string, x: number): string
function palette(c1: string, c2: string, clim: range): number => string
```

# Documentation

Below is the full documentation for the core `gum.jsx` components: `Element`, `Group`, and `Box`. All of the other components are derived from these and many use them as sub-components. Understanding these three components will give you a good foundation for working with the library.

## Element

The base class for all `gum.jsx` objects. You will usually not be working with this object directly unless you are implementing your own custom elements. An **Element** has a few methods that can be overriden, each of which takes a **Context** object as an argument. The vast majority of implementations will override only `props` and `inner` (for non-unary elements).

The position and size of an element are specified in the internal coordinates (`coord`) of its parent, which defaults to the unit square. Rectangles are always specified in `[left, top, right, bottom]` format. You can also specify the placement by specifying `pos` and `size` or various combinations of `xsize`/`ysize`. When not specified, `rect` defaults to the unit square.

Parameters:
- `tag` = `g` — the SVG tag associated with this element
- `unary` = `false` — whether there is inner text for this element
- `aspect` = `null` — the width to height ratio for this element
- `pos` — the desired position of the center of the child's rectangle
- `size` ­— the desired size of the child's rectangle (can be single number or pair)
- `xsize`/`ysize` ­— specify the size for a specific dimension (and expand the other)
- `rect` — a fully specified rectangle to place the child in (this will override `pos`/`size`)
- `aspect` — the aspect ratio of the child's rectangle
- `expand` — when `true`, instead of embedding the child within `rect`, it will make the child just large enough to fully contain `rect`
- `align` — how to align the child when it doesn't fit exactly within `rect`, options are `left`, `right`, `center`, or a fractional position (can set vertical and horizontal separately with a pair)
- `rotate` — how much to rotate the child by (degrees counterclockwise)
- `spin` — like rotate but will maintain the same size
- `flex` ­— override to set `aspect = null`
- `...` = `{}` — additional attributes that are included in `props`

Methods:
- `props(ctx)` — returns a dictionary of attributes for the SVG element. The default implementation returns the non-null `attr` passed to the constructor
- `inner(ctx)` — returns the inner text of the SVG element (for non-unary). Defaults to returing empty string
- `svg(ctx)` — returns the rendered SVG of the element as a `String`. Default implementation constructs SVG from `tag`, `unary`, `props`, and `inner`

**Example**

Prompt: create a custom triangle element called `Tri` and use it to create a triangle with a gray fill

Generated code:
```jsx
const Tri = ({ pos0, pos1, pos2, ...attr }) => <Shape {...attr} points={[pos0, pos1, pos2]} />
return <Tri pos0={[0.5, 0.1]} pos1={[0.9, 0.9]} pos2={[0.1, 0.9]} fill={gray} />
```

## Group

*Inherits*: **Element**

This is the main container class that all compound elements are derived from. It accepts a list of child elements and attempts to place them according to their declared properties. Child placement positions are specified in the group's internal coordinates (`coord`), which defaults to the unit square. The coordinate space is specified in `[left, top, right, bottom]` format.

The child's `aspect` is an important determinant of its placement. When it has a `null` aspect, it will fit exactly in the given `rect`. However, when it does have an aspect, it needs to be adjusted in the case that the given `rect` does not have the same aspect. The `expand` and `align` specification arguments govern how this adjustment is made.

Parameters:
- `children` = `[]` — a list of child elements
- `aspect` = `null` — the aspect ratio of the group's rectangle (can pass `'auto'` to infer from the children)
- `coord` = `[0, 0, 1, 1]` — the internal coordinate space to use for child elements (can pass `'auto'` to contain children's rects)
- `clip` = `false` — clip children to the group's rectangle if `true` (or a custom shape if specified)

**Example**

Prompt: a square in the top left and a circle in the bottom right

Generated code:
```jsx
<Group>
  <Rectangle pos={[0.3, 0.3]} size={0.2} spin={15} />
  <Ellipse pos={[0.7, 0.7]} size={0.2} />
</Group>
```

## Box

*Inherits*: **Group** > **Element**

This is a simple container class allowing you to add padding, margins, and a border to a single **Element**. It's pretty versatile and is often used to set up the outermost positioning of a figure. Mirroring the standard CSS definitions, padding is space inside the border and margin is space outside the border. This has no border by default, but there is a specialized subclass of this called **Frame** that defaults to `border = 1`.

**Box** can be pretty handly in various situations. It is differentiated from **Group** in that it will adopt the `aspect` of the child element. This is useful if you want to do something like shift an element up or down by a certain amount while maintaining its aspect ratio. Simply wrap it in a **Box** and set child's `pos` to the desired offset.

There are multiple ways to specify padding and margins. If given as a scalar, it is constant across all sides. If two values are given, they correspond to the horizontal and vertical sides. If four values are given, they correspond to `[left, top, right, bottom]`.

The `adjust` flag controls whether padding/margins are adjusted for the aspect ratio. If `true`, horizontal and vertical components are scaled so that their ratio is equal to the `child` element's aspect ratio. This yields padding/margins of constant apparent size regardless of aspect ratio. If `false`, the inputs are used as-is.

Parameters:
- `padding` = `0` / `0.1` — the padding to be added (inside border)
- `margin` = `0` / `0.1` — the margin to be added (outside border)
- `border` = `0` / `1` — the border width to use (stroke in pixels)
- `rounded` = `0` / `0.1` — the border rounding to use (proportional to the box size)
- `fill` = `null` — the background color to use (default is no fill)
- `adjust` = `true` — whether to adjust values for aspect ratio
- `shape` = `Rect` — the shape class to use for the border
- `clip` = `false` — whether to clip the contents to the border shape

Subunit names:
- `border` — keywords to pass to border, such as `stroke` or `stroke-dasharray`

**Example**

Prompt: the text "hello!" in a frame with a dashed border and rounded corners

Generated code:
```jsx
<Box padding border rounded border-stroke-dasharray={5}>
  <Text>hello!</Text>
</Box>
```

# References

Below is a list of topics to reference for documentation and usage examples for the various components. Every `gum.jsx` component is documented here. Your code must either use these components or create its own custom components. Before using a component, be sure to read the relevant reference to fully understand its parameters and capabilities.

## Layout

**File**: [layout](references/layout.md)

These are the raw layout components that assist you in arranging elements in a figure. They typically take a list of child elements and arrange them in a specified way. `Box` is a simple container element that can be used to add padding, border, and rounded corners to a group of elements.

`Stack` lets you arrange elements in a vertical or horizontal stack (like `flexbox` in CSS) in a way that respects the aspect ratio of the child elements. Typically you would use the specialized subclasses `VStack` and `HStack` for vertical and horizontal stacks, respectively. `Grid` does something similar but for a 2D grid of rows and columns (like `grid` in CSS).

`Points` is different in that it takes a list of locations and arranges a given element at each of those locations (with the default element being `Dot`, a solid filled `Circle`).

**Components**:
- *Box*: a box with a padding, border, and rounded corners
- *Stack*/*VStack*/*HStack*: arrange elements vertically or horizontally
- *Grid*: arrange elements in a grid of specified size
- *Points*: arrange one element at each of a list of locations

## Shapes

**File**: [shapes](references/shapes.md)

These are the basic geometric shapes that can be used to create more complex figures. Both `Rect` and `Ellipse` are aspectless by default but can be given an aspect ratio to control their shape (i.e., a circle is an `Ellipse` with an aspect of `1`).

`Line` is actually more general than just a single straight line. It can be used to draw piecewise linear paths by passing a list of points. For the case of simple unit lines, use `UnitLine` and its specialized variants `VLine` and `HLine` instead. For closed paths, either pass `closed` to `Line` or use `Shape` instead.

For multi-segment Bézier splines, `Spline` is the way to go. It takes a list of control points and draws a smooth cubic spline through them. You can control the tension of the spline with the `curve` parameter (default is `0.5`). This also accepts a `closed` parameter to draw a closed spline.

**Components**:
- *Rect*: a rectangle
- *Ellipse*: an ellipse
- *Line*/*Shape*: a piecewise linear path (possibly closed)
- *Spline*: a multi-segment Bézier spline (possibly closed)
- *UnitLine*/*VLine*/*HLine*: a single unit line
- *Arrow*: a straight line arrow between two points

## Text

**File**: [text](references/text.md)

These are components that can be used to create text elements. `Text` is a fairly sophisticated component that handles text wrapping, line spacing, and other text-related features. You can specify the wrap width (in "ems", that is, in proportion to the line height) with the `wrap` parameter and the alignment with the `justify` parameter. Feel free to intersperse non-text elements with text elements to create more complex layouts.

`TextStack` is a simple component that stacks text elements vertically. Specifying a `wrap` width will cause every child element to be wrapped to the specified width. You can specify the vertical spacing between the elements with the `spacing` parameter. The `TitleFrame` is a `Frame` subclass that automatically adds a boxed title to the top of the frame. Finally, `Slide` is basically a `TextStack` wrapped in a `TitleFrame`.

`Latex` does what it sounds like: it renders a single LaTeX equation. This uses MathJax under the hood, so it supports most but not all inline LaTeX features.

**Components**:
- *Text*: a text element with wrapping
- *TextStack*: a stack of text elements
- *TitleFrame*: a frame with a title
- *Slide*: a slide with a title and content

## Math

**File**: [math](references/math.md)

These are components for creating mathematical expressions. By far the most common usage is to pass a LaTeX style math expression to the `Latex` component. However, you can get very fine grained control over the layout of mathematical expressions with `MathText` as your outer wrapper and the `SupSub`, `Frac`, and `Bracket` components.

**Components**:
- *Latex*: a single LaTeX equation from a string
- *MathText*: display a list of math components
- *SupSub*: a superscript and/or subscript
- *Frac*: a fraction (numerator/denominator)
- *Bracket*: auto-sized brackets (round, square, curly, angle, or custom)

## Symbolic

**File**: [symbolic](references/symbolic.md)

These components allow you to plot functions symbolically. That is, they accept functions as arguments and plot them accordingly. Functions can be specified as [x => y], [y => x], or [t => (x,y)]. You can control the range over which the domain is sampled with the `tlim`/`xlim`/`ylim` parameters. You can also control the number of samples to take with the `N` parameter.

These clearly extend their non-`Sym` counterparts by adding the ability to plot functions symbolically. The only additional element is `SymFill`, which plots a filled area between two functions. For this one, passing a constant to either `fy1` or `fy2` is equivalent to passing a constant function.

**Components**:
- *SymPoints*: plot points functionally
- *SymLine*/*SymShape*: plot a curve functionally (possibly closed)
- *SymSpline*: plot a Bézier spline functionally (possibly closed)
- *SymFill*: plot a filled area between two functions

## Plotting

**File**: [plotting](references/plotting.md)

There are components for creating various types of plots. The core element is `Graph`, which is a container element that accepts a list of children to plot over a specified coordinate system (`xlim`/`ylim`/`coord`). `Plot` is a `Graph` subclass that adds axes (with `Axis`/`HAxis`/`VAxis`), labels, and other plot-specific features. `BarPlot` is a help element that wraps a `Bars` element inside of a `Plot`.

The `Plot` element in particular is highly customizable, and you can pass arguments to sub-components using `axis`/`label`/`title` prefixes. For instance, to specify the stroke width of the x-axis, you can use `xaxis-stroke-width`. This logic applies to other types of compound components as well.

**Components**:
- *Graph*: a graph containing multiple elements with a specified coordinate system
- *Plot*: a plot containing a graph, axes, and labels
- *Axis*/*HAxis*/*VAxis*: a single axis for a plot
- *Bars*/*BarPlot*: a bar plot (bare or wrapped in a `Plot`)

## Networks

**File**: [networks](references/networks.md)

These are components for creating network diagrams. The core element is `Network`, which is a container element that accepts a list of `Node`s and `Edge`s, as well as potentially other elements like labels. A `Node` can specify an `id` to be used to reference it from an `Edge` as either the source (`from`) or destination (`to`). Default values for `Node` and `Edge` arguments can be specified with `node-` and `edge-` prefixed arguments passed to the `Network` element.

The `Edge` element has a `dir1` and `dir2` parameter to specify the direction of the arrowhead for the source and destination nodes, respectively. You can also toggle arrowheads on either side with `arrow`/`from-arrow`/`to-arrow` or specify the `curve` parameter to control the curvature of the edge.

**Components**:
- *ArrowSpline*: a curved path with optional arrowheads at either or both ends
- *Node*: a node in a network
- *Edge*: an edge in a network
- *Network*: a network containing nodes and edges

## Utilities

**File**: [utilities](references/utilities.md)

These are the helper functions that are available in the library. They are not components themselves, but they are useful for creating and manipulating data. Many of them mimic the behavior of their counterparts in Python and `numpy` and are useful for generating `Element` objects from arrays. There are also some commonly used mathematical constants and tools for interpolating colors.

**Components**:
- *Math*: mathematical functions
- *Arrays*: array operations
- *Colors*: color operations

# Gallery

There is a gallery of more complex examples available. Each is a single markdown file with a complete `gum.jsx` code example and accompanying text description. These are available in the `references/gala` directory. Here is a brief description of each along with a list of the main elements used:

- [Atomic Orbitals](references/gala/atomic_orbitals.md): a slide with polar graphs of the s, p, and d atomic orbitals (**Graph**, **SymSpline**)
- [Complex Plot](references/gala/complex_plot.md): a plot of a complex function showing the solutions to a parameterized quadratic equation (**Plot**, **SymSpline**, **Mesh2D**)
- [Flux Capacitance](references/gala/flux_capacitance.md): a relatively simple line and shaded area plot (**Plot**, **SymLine**, **SymFill**)
- [Macro Economy](references/gala/macro_economy.md): a diagram of a macro economy (**Network**, **Edge**, **Node**, **Text**)
- [Metal Grid](references/gala/metal_grid.md): a stylized grid of metal squares (**Grid**, **Spline**, **Frame**)
- [Pendulum Physics](references/gala/pendulum_physics.md): a physics diagram of a pendulum (**Arc**, **Arrow**, **Line**, **Latex**)
- [Plot Manual](references/gala/plot_manual.md): a simple example of a plot manual diagram (**Plot**, **Axis**, **Mesh**)
- [Polygon Slide](references/gala/polygon_slide.md): a simple example of a polygon slide diagram (**SymShape**, **Grid**, **Stack**)
- [Punk Rock](references/gala/punk_rock.md): a logo-style text block (**TextFrame**, **Stack**)
- [Set Theory](references/gala/set_theory.md): a mathematical diagram of nested sets (**Text**, **Frame**, **Group**)
- [Slick Bars](references/gala/slick_bars.md): a bar chart with a custom plot style (**Plot**, **Bars**, **Span**)
- [Spline Star](references/gala/spline_star.md): a parameterized star shape (**Spline**, **Frame**)
- [Stokes Theorem](references/gala/stokes_theorem.md): a slide depicting Stokes' theorem (**Spline** , **Arrow**, **Latex**)
- [The Nexus](references/gala/the_nexus.md): a plot of damped cosine functions (**Plot**, **SymSpline**)

# Using CLI commands

To test the output of a particular `gum.jsx` snippet or file, you can pipe it to the `gum-cli` command, which is assumed to be installed globally. If you have vision capabilities, this can be useful for see the actual output of the code, either in SVG or PNG format. Even without vision, one can infer properties of the output by reading the SVG output directly.

For one off tests, pipe the code using `echo`. It is recommended that you use single quotes as the outer delimiter, to accommodate code that includes double quotes for component properties (e.g. `justify="left"`).

For more difficult tasks, use a file and `cat` it in. Using a file allows you to view and refine your code repeatedly. If you wish to avoid output redirection to a file, use the `-o` option to write to a file.

In general, it makes a lot of sense to write a draft to a file, view its output, then refine the code until you're satisfied. This way you can start simple and add complexity as needed.

**Examples:**
```bash
# Generate SVG from a gum.jsx snippet
echo '<Rectangle rounded fill={blue} />' | gum-cli -f svg > output.svg

# Generate PNG from a gum.jsx snippet
echo '<Rectangle rounded fill={blue} />' | gum-cli -f png > output.png

# Generate SVG from a .jsx file
cat test.jsx | gum-cli -f svg > output.svg

# Generate PNG from a .jsx file
cat test.jsx | gum-cli -f png > output.png

# Generate SVG from a .jsx file without output redirection
cat test.jsx | gum-cli -f svg -o output.svg

# Generate PNG from a .jsx file without output redirection
cat test.jsx | gum-cli -f png -o output.png
```

**CLI options:**
- `-s, --size <size>`: size of the SVG (default: 1000)
- `-w, --width <width>`: width of the PNG (default: null)
- `-h, --height <height>`: height of the PNG (default: null)
- `-f, --format <format>`: format: svg or png (default: null)
- `-t, --theme <theme>`: theme to use (default: light)
- `-b, --background <color>`: background color (default: white)
- `-o, --output <output>`: output file (default: null)

# Using in TypeScript

You can use gum.jsx directly in TypeScript/JavaScript code by importing from the `gum-jsx` package. This is useful for programmatic generation, integration into other tools, or when you want to avoid the CLI.

## Evaluating JSX strings

The `evaluateGum` function from `gum-jsx/eval` parses a JSX string and returns an `Svg` element tree. Call `.svg()` on the result to get an SVG string.

```typescript
import { evaluateGum } from 'gum-jsx/eval'
import { rasterizeSvg } from 'gum-jsx/render'

// parse JSX string into element tree, then render to SVG
const tree = evaluateGum('<Rectangle rounded fill={blue} />')
const svg = tree.svg()

// render to PNG buffer
const png = rasterizeSvg(svg)
```

The `evaluateGum` function accepts options for theme, size, and extra context variables:

```typescript
const tree = evaluateGum(code, {
    theme: 'light',     // 'light' or 'dark'
    size: 500,          // SVG size (or [width, height])
    context: { data },  // extra variables available in the JSX code
})
```

## Using components directly

You can also construct components directly by importing them from `gum-jsx` and calling their constructors. Each component takes a single args object.

```typescript
import { Svg, Rectangle, Circle, HStack, Text, blue, red, white } from 'gum-jsx'

// create elements by calling constructors directly
const rect = new Rectangle({ rounded: true, fill: blue })
const circle = new Circle({ fill: red })
const label = new Text({ children: 'Hello', fill: white })

// compose into a layout
const layout = new HStack({ children: [rect, circle, label] })

// wrap in Svg and render
const tree = new Svg({ children: [layout], size: 500 })
const svg = tree.svg()
```

When constructing manually, note that:
- `children` is always passed as an array in the args object
- Constants like `blue`, `red`, `none`, etc. are exported from `gum-jsx`
- Utility functions like `range`, `linspace`, `zip` are also available from `gum-jsx`
- Call `.svg()` on the top-level `Svg` element to get the SVG string output

## Rendering to PNG

Use `rasterizeSvg` from `gum-jsx/render` to convert an SVG string to a PNG buffer:

```typescript
import { rasterizeSvg } from 'gum-jsx/render'
import { writeFileSync } from 'fs'

const png = rasterizeSvg(svg, {
    width: 800,       // output width in pixels
    height: 600,      // output height in pixels
    background: '#ffffff',
})

writeFileSync('output.png', png)
```
