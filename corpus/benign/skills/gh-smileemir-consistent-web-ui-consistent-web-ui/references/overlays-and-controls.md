# Controls, overlays and notifications

Read when you build or change buttons, fields, toolbars, selects, menus, dialogs, drawers, popovers or toast notifications.

## Contents

1. Layers: only the top layer moves and responds
2. Controls in a row
3. Buttons
4. Selects, menus and dropdowns
5. Dialogs and drawers
6. Toast notifications
7. Check it on the page

## 1. Layers: only the top layer moves and responds

Every layer has a place in the layer scale (the theme's layer roles) and a fixed behaviour.

| Layer | Examples | Behaviour |
| --- | --- | --- |
| Page | content | Scrolls normally. |
| Sticky | header, purchase bar | The page scrolls under it. The bar is opaque. |
| Non-modal overlay | menu, select list, popover, tooltip, toast | The page keeps working. The overlay is opaque, and a click on it never reaches the page. The first click outside an open menu only closes it. |
| Modal | dialog, drawer, full-screen menu, bottom sheet | The page behind does not scroll and is inert: no click, hover or Tab. A backdrop dims it and takes the clicks. |

- **Opaque surfaces:**
  - every layer over content has an opaque background, or a blur so strong that the text below cannot be read and contrast still holds;
  - text under a layer never mixes with the layer's own text.
- **Scroll:**
  - while a modal is open, lock the page with `overflow: hidden` on the root;
  - keep the scrollbar's space with `scrollbar-gutter: stable`, so nothing jumps;
  - the overlay's own scroll area uses `overscroll-behavior: contain`.
- **Input:**
  - a native `<dialog>` opened with `showModal()` makes the page inert by itself;
  - a custom modal needs `inert` on the rest of the page and a backdrop that covers the whole screen.
- **Order:**
  - a menu inside a dialog opens above the dialog;
  - a toast shown while a modal is open appears inside the modal's layer, so it is on top and clickable;
  - a layer never opens behind the element it belongs to.
- **Test on the page:** open each overlay together with the others that can be open at the same time, and check the order on screen. Then run `scripts/ui_check.js`.

## 2. Controls in a row

- **One size per row:** everything that shares a row (search, select, buttons, view toggles, pagination) uses one height (`--control-height`: 32, 40 or 48 px), one corner radius and one text size. Their centres line up.
- **Fields:** each field has a visible label, the same border, padding and focus ring. The toolbar search is the one exception: its icon and placeholder already say what it does, so its label may be visually hidden.
- **Toggle groups** (grid/list, day/week) are a segmented control of the same height. The pressed option has `aria-pressed="true"` and uses the brand colour.
- **Template:** `assets/templates/controls.html`.

## 3. Buttons

- **Variants:**
  - primary: one per task block;
  - secondary: other actions;
  - quiet: low-emphasis actions next to a secondary one;
  - danger: destructive actions.
- **Sizes:** small, medium and large, from the control heights.
- **Side by side:** buttons share height, radius, padding and text size. They differ only by variant.
- **States:**
  - hover changes colour only;
  - focus uses the shared focus ring, never an underline or a border that the other buttons do not have;
  - pressed may scale to 0.98;
  - disabled keeps its shape, and the reason is written next to it.
- **Icons:** 16–20 px, from the project's icon set. An arrow that means "go" follows the text; a command icon comes before it.
- **Buttons and links:** something that goes to another page is a link, even when it looks like a button. Something that acts on the current page is a button.

## 4. Selects, menus and dropdowns

- **Closed:** a select looks like the other fields (height, padding, border, radius, type), with a chevron from the project's icon set.
- **Open list:**
  - uses the theme's surface, border, radius, shadow and type;
  - shows a clear mark on the selected option, and a highlight for hover and keyboard;
  - is opaque and stays at least 8 px inside the screen;
  - opens upwards when there is no room below.
- **How to build it:**
  - use the project's accessible select, menu or combobox component if it has one;
  - otherwise enhance the native `<select>` with `appearance: base-select`, as in the template, and keep the native list as the fallback. The native list is fine on phones;
  - never ship a list made of `div`s without full keyboard support (arrows, Enter, Escape, type-ahead) and screen-reader support.
- **Menus vs selects:** a list of actions is a menu (`role="menu"`, from the component library). A list of values is a select or listbox.
- **Outside clicks:** the first click outside an open menu or list closes it and does nothing else.

## 5. Dialogs and drawers

- **When to use a dialog:** for a focused task, or a short look at a detail without leaving the page. Long content, many fields, or anything people want to link to belongs on a page.
- **Size:**
  - small, 400 px: confirmations;
  - medium, 560 px: quick views and short forms;
  - large, 720 px.
  - The height follows the content, up to about 85% of the screen.
- **Structure:** a header (title and a quiet close button), a body, and a footer with the actions.
  - Only the body scrolls, and only when the content is really long.
  - The header and the footer stay visible.
- **Media:** capped at about a third of the screen height (`object-fit: cover`), so the text and actions show without scrolling.
- **Closing:**
  - a quiet icon button in the header, about 36–40 px, with a 20 px icon;
  - Escape;
  - a click on the backdrop, for content dialogs;
  - a content dialog does not repeat a "Close" button in its footer;
  - forms with input and destructive confirmations do not close on a backdrop click.
- **Focus:**
  - on opening, focus goes to the title (screen readers announce it) or the first field; in a destructive confirmation, to Cancel;
  - the focus ring shows for the keyboard only;
  - Tab stays inside the dialog;
  - on closing, focus returns to the button that opened it.
- **Confirmation wording:** see [help-and-ui-text.md](help-and-ui-text.md). The title names the action and the object, the body states the consequence, and the confirm button repeats the verb.
- **Drawers and bottom sheets** follow the same rules. On phones a dialog may become a bottom sheet with the actions at the bottom.
- **Motion:** about 200–300 ms, a fade with an 8 px rise; closing is quicker; no motion under reduced motion.
- **Template:** `assets/templates/dialog.html`.

## 6. Toast notifications

- **When:** a toast reports the result of an action the person just took ("Changes saved", "Item removed" with an Undo). An error that blocks a task belongs next to the field or in the form; a toast may repeat it.
- **Look:**
  - the brand's surface, border, radius, type and icons;
  - status shows as a small coloured icon;
  - no full-colour blocks, gradients or emoji.
- **Position:**
  - bottom right on desktop, bottom centre on phones, the same for the whole product;
  - above safe areas and sticky bottom bars (`--toast-offset`);
  - never over the main action.
- **Layer:** above the page. While a modal is open, inside the modal's layer.
- **Count:** at most three at once.
- **Timing:**
  - success and info leave after about 5 seconds, warnings after about 8;
  - the timer pauses on hover or focus;
  - errors stay until the person closes them;
  - every toast has a close button.
- **Words:** what happened, in the past tense, plus at most one action. Never report success before the real confirmation.
- **Announcements:** `role="status"` for success and info, `role="alert"` for errors.
- **Template:** `assets/templates/toast.html`.

## 7. Check it on the page

Open each overlay, then run `scripts/ui_check.js`. In Playwright: `page.addScriptTag({ path })`, then `page.evaluate(() => uiCheck())`.

It reports:

- controls in one row with different heights, radii or text sizes;
- a page that scrolls behind an open modal;
- clicks outside a modal that reach the page;
- see-through overlays and sticky bars;
- covered or cut-off overlays;
- dialogs that are too tall, scroll as a whole or hide their actions;
- oversized media and close buttons;
- focus outside an open modal.

Fix every issue, or write down why the design needs it. Then check by hand what a script cannot see: the order when two layers can be open at once, keyboard use, and phone widths.
