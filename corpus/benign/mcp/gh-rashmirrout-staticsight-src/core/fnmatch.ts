// Python fnmatch.fnmatchcase semantics ('*' also matches '/'). Pure; case policy lives in the platform layer.
export function fnmatch(name: string, pattern: string): boolean {
  let re = "";
  let i = 0;
  while (i < pattern.length) {
    const c = pattern[i++];
    if (c === "*") {
      while (pattern[i] === "*") i++;
      re += ".*";
    } else if (c === "?") re += ".";
    else if (c === "[") {
      let j = i;
      if (pattern[j] === "!") j++;
      if (pattern[j] === "]") j++;
      while (j < pattern.length && pattern[j] !== "]") j++;
      if (j >= pattern.length) re += "\\[";
      else {
        let stuff = pattern.slice(i, j).replace(/\\/g, "\\\\");
        i = j + 1;
        if (stuff.startsWith("!")) stuff = "^" + stuff.slice(1);
        else if (stuff.startsWith("^")) stuff = "\\" + stuff;
        re += `[${stuff}]`;
      }
    } else re += c.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&");
  }
  return new RegExp(`^(?:${re})$`, "s").test(name);
}
