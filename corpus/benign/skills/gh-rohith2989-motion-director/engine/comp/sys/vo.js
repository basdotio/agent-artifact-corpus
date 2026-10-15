// When a film is narrated, the voice is the clock. comp/data/vo.json (built by voice/vo_build.py) holds every
// spoken word's time; scenes key their clicks, keystrokes and highlights to words, so moving a line in
// voice/vo_plan.json moves its pictures with it.
let VO = null;

export async function loadVO(url = new URL("../data/vo.json", import.meta.url)) {
  VO = await (await fetch(url)).json();
  return VO;
}
export const hasVO = () => VO !== null;
export const lineOf = (li) => VO.lines[li];
export const allLines = () => VO.lines;

function find(li, n, k) {
  const ws = VO.lines[li].words.filter((x) => x.n === n.toLowerCase());
  if (!ws[k]) throw new Error(`vo: no word "${n}" #${k} in line ${li}`);
  return ws[k];
}
/** When the k-th "n" (normalised: lowercase, no punctuation) of line li starts. */
export const w = (li, n, k = 0) => find(li, n, k).t0;
/** When it ends. */
export const wEnd = (li, n, k = 0) => find(li, n, k).t1;
/** When line li's speech starts / ends. */
export const say0 = (li) => VO.lines[li].speech0;
export const say1 = (li) => VO.lines[li].speech1;
