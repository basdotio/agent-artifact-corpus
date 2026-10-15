# Tailwind CSS

These rules add to the general ones in `SKILL.md`. They apply wherever you write or edit Tailwind classes: `className` and `class` attributes, `cn()`, `clsx()`, `cva()`, and `@apply`, in any framework.

## Canonical classes only

Every Tailwind class must be in its canonical form, meaning the shortest standard way Tailwind writes that style. A non-canonical class still works, but it hides a theme value behind an arbitrary one and makes the same style look different from file to file.

| Non-canonical          | Canonical      |
| ---------------------- | -------------- |
| `w-[1rem] h-[1rem]`    | `size-4`       |
| `mt-[0.5rem]`          | `mt-2`         |
| `px-4 py-4`            | `p-4`          |
| `!font-bold`           | `font-bold!`   |
| `bg-[var(--brand)]`    | `bg-(--brand)` |
| `[&>*]:p-2`            | `*:p-2`        |
| `flex flex`            | `flex`         |

## Check and fix, every time

You will not spot every non-canonical class by eye, so check them with Tailwind's own tool after every change that touches classes. Fix every class it reports. This step is required, not optional.

1. From the project root, pass each class string you wrote or edited to `canonicalize`, one string per argument. Point `--css` at the project's CSS entry, which is the file with `@import "tailwindcss"`, so that custom theme values count.

   ```sh
   npx -y @tailwindcss/cli canonicalize --css src/index.css --format jsonl \
     "w-[1rem] h-[1rem] p-4" \
     "px-4 py-4 !font-bold"
   ```

   ```
   {"input":"w-[1rem] h-[1rem] p-4","output":"size-4 p-4","changed":true}
   {"input":"px-4 py-4 !font-bold","output":"p-4 font-bold!","changed":true}
   ```

2. For every line with `"changed":true`, replace the class string in the code with `output` exactly as given. The output also sorts the classes, which is expected.
3. If a class string is built from parts (a conditional inside `cn()` or a template literal), check each static part as its own string.
4. Run the check again until nothing comes back changed.

If the project's ESLint config already enables `better-tailwindcss/enforce-canonical-classes`, running the linter with `--fix` does the same job.

## Tailwind v3

The `canonicalize` command needs Tailwind v4. In a v3 project, check by hand against the table above: use a theme value instead of an arbitrary one that equals it, merge pairs that have a shorthand (`w` and `h` into `size`, `px` and `py` into `p`), and drop duplicates. Do not apply v4 syntax to v3: `!font-bold` and `bg-[var(--brand)]` are correct there.

## Before you finish

Say in your report that you ran the canonical check and which classes it changed.
