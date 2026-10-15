# Typography: display type and scroll-fill text

## Display type: tight tracking, dimmed half, metallic gradient

*Why:* Large type at default tracking looks loose and amateur. Tightening by 3–7% makes words read as shapes, the way a logo does. Dimming half the headline creates a reading order.

```css
.display{font-family:var(--font-display);font-weight:400;font-size:clamp(44px,6.5vw,96px);line-height:1.05;letter-spacing:-.05em;text-wrap:balance}
.display .dim{color:rgb(255 255 255/.5)}                 /* "Automate <span class=dim>smarter,</span> grow faster." */
.display-metal{background:linear-gradient(132deg,#43484D 11%,#292C2E 79%);-webkit-background-clip:text;background-clip:text;color:transparent}
.display-fade{background:linear-gradient(180deg,#fff 30%,rgb(255 255 255/.35));-webkit-background-clip:text;background-clip:text;color:transparent}
.eyebrow-num{font:500 13px/1 "IBM Plex Mono",monospace;letter-spacing:.04em;text-transform:uppercase;color:rgb(255 255 255/.5)}
```
Letter-spacing guide: 48px → −0.04em, 64px → −0.05em, 96px → −0.03 to −0.05em, 140px → −0.07em. Body text stays at 0.

If the headline is split with SplitText, put the gradient on the split pieces, not the parent (see Gotchas in `shared/motion.md`).

## Scroll-fill text

*Why:* Text that "inks in" as you scroll rewards reading and paces the page. Adon does it with a hard-stop gradient clipped to text, so it's crisp per line, not a blurry fade.

```css
.fill-text{font-size:clamp(36px,6vw,90px);line-height:.95;letter-spacing:-.05em}
.fill-text .line{
  background:linear-gradient(to right,var(--ink) 50%,var(--dim) 50%);
  background-size:200% 100%;background-position:100% 0;
  -webkit-background-clip:text;background-clip:text;color:transparent;display:inline}
```
```js
// split into lines (SplitText, autoSplit so it re-measures on resize), then ONE sequential timeline per block:
gsap.utils.toArray('.fill-text').forEach(el => SplitText.create(el, {
  type: 'lines', linesClass: 'line', autoSplit: true,
  onSplit: self => {
    const tl = gsap.timeline({ defaults: { ease: 'none' },
      scrollTrigger: { trigger: el, start: 'top 80%', end: 'bottom 40%', scrub: 0.5 } });
    self.lines.forEach(l => tl.to(l, { backgroundPosition: '0% 0', duration: 1 }));  // equal slices, one after another
    return tl;
  }
}));
```
**Strictly line by line, never several at once.** Do NOT give each line its own ScrollTrigger: neighbouring lines are only one line-height apart, so their start/end ranges overlap and two or three lines fill simultaneously, which reads as a muddy wave instead of reading. One trigger on the whole block + a timeline of back-to-back tweens (`duration:1`, no overlap, no position offsets) guarantees line N is fully inked before line N+1 begins. `scrub:0.5` adds a little inertia so the fill glides instead of tracking the scrollbar 1:1. For a longer block, give the trigger more scroll distance (`end:'bottom 30%'` or `+=` a multiple of the block height) so each line has room to breathe. Weight each line's `duration` by its character count if line lengths vary a lot, so the fill speed stays constant.

Optional soft leading edge (still one line at a time): `background:linear-gradient(to right,var(--ink) 45%,var(--dim) 55%)`, so the ink edge feathers instead of cutting hard.

On dark: `--ink:#fff; --dim:rgb(255 255 255/.2)`.

## Word-by-word fill with semantic keyword colors (and inline mascot)

*Why:* A flat grey→black fill is elegant but anonymous. When the one or two nouns that carry the meaning take the color of what they *are* (a link in blue, code in purple, the action word in green), the sentence teaches the product while it is read, and the page gets color without a second accent. The color is a code, so use it only on those words. Default to the accent green alone; add blue/purple only when the product really deals with links or code.

**Contrast:** keyword colors are text, so they must pass 4.5:1 against the card they sit on. Bright "UI" greens/blues/purples (e.g. `#2FD07F`, `#4A9BEA`, `#A66BEF`) only reach 2–3.5:1 on white or cream. Use the darkened tokens from your direction's `style.md` (Warm Playful: `--k-copy:#1F7A4A`, `--k-link:#1E6FC2`, `--k-code:#7B44C9`). If you need a different hue, darken it until it passes; quick check in the console:
```js
const L=h=>{const c=h.match(/\w\w/g).map(x=>{x=parseInt(x,16)/255;return x<=.03928?x/12.92:((x+.055)/1.055)**2.4});return .2126*c[0]+.7152*c[1]+.0722*c[2]};
const ratio=(a,b)=>{const[x,y]=[L(a),L(b)].sort((p,q)=>q-p);return (x+.05)/(y+.05)};  // ratio('1F7A4A','FFFFFF') → 5.33
```

```html
<p class="sf">You <b class="k-copy">copy</b> something important. <img class="sf-mascot" src="m1.png" alt=""></p>
<p class="sf">A <b class="k-link">link</b>. A piece of <b class="k-code">code</b>. Something you'll need again in five minutes.</p>
```
```css
.sf{font-size:clamp(28px,3.6vw,44px);line-height:1.2;letter-spacing:-.02em;font-weight:500}
.sf .w{color:rgb(29 29 31/.14);transition:color .3s}           /* unread */
.sf .w.on{color:var(--ink)}                                    /* read */
.sf .w.on.k-copy{color:var(--k-copy)} .sf .w.on.k-link{color:var(--k-link)} .sf .w.on.k-code{color:var(--k-code)}
.sf b{font-weight:800}
.sf-mascot{height:1.4em;vertical-align:-.35em;margin-left:.2em;opacity:0;scale:.8;transition:.4s cubic-bezier(.22,1,.36,1)}
.sf-mascot.on{opacity:1;scale:1}
```
```js
// wrap each word in .w (keep the <b> classes on the wrapper), then turn words on by scroll progress through the card
const words=[...card.querySelectorAll('.w')];
addEventListener('scroll',()=>{
  const r=card.getBoundingClientRect(), p=Math.min(1,Math.max(0,(innerHeight*.75-r.top)/(r.height*.8)));
  const n=Math.round(p*words.length); words.forEach((w,i)=>w.classList.toggle('on',i<n));
  // a mascot appears once the word right before it has been read
  card.querySelectorAll('.sf-mascot').forEach(m=>m.classList.toggle('on',!!m.previousElementSibling?.classList.contains('on')));
},{passive:true});
```
Simpler variant: toggle `.on` per **sentence** instead of per word. Keep at most 3 colored words per card, and keep contrast of the unread state intentionally low (this text is not essential until it is read; make sure the *final* state passes 4.5:1 for every word, colored keywords included (see Contrast above), and that the text is fully visible with `prefers-reduced-motion` or no JS). Unlike the GSAP line-by-line fill above, this one uses plain scroll math, so it works inside `position:sticky` cards without ScrollTrigger pin conflicts.
