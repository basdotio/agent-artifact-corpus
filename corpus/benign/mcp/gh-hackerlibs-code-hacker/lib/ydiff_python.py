#!/usr/bin/env python3
"""ydiff_python - Language-aware structural diff for Python programs.

Inspired by ydiff (Yin Wang). Uses Python's ast module for parsing,
then performs structural tree comparison with move detection.
Outputs an interactive side-by-side HTML diff.

Usage:
    python ydiff_python.py file1.py file2.py
"""

import ast
import sys
import os
import subprocess

sys.setrecursionlimit(50000)


# ================================================================
#                       Data Structures
# ================================================================

class Node:
    """AST node for structural comparison."""
    __slots__ = ['type', 'start', 'end', 'elts', 'size', 'ctx', 'def_name']

    def __init__(self, ntype, start, end, elts, def_name=None):
        self.type = ntype       # node type string
        self.start = start      # char offset in source
        self.end = end          # char offset in source
        self.elts = elts        # str for leaves, list[Node] for compounds
        self.size = None        # memoized token count
        self.ctx = None         # context name for move detection
        self.def_name = def_name


class Change:
    """A single change between two programs."""
    __slots__ = ['old', 'new', 'cost', 'type']

    def __init__(self, old, new, cost, change_type):
        self.old = old
        self.new = new
        self.cost = cost
        self.type = change_type  # 'ins', 'del', 'mov'


class Tag:
    """HTML tag marker for output generation."""
    __slots__ = ['tag', 'idx', 'start']

    def __init__(self, tag, idx, start):
        self.tag = tag      # HTML tag string
        self.idx = idx      # position in source text
        self.start = start  # for sort ordering (-1 for open tags)


# ================================================================
#                       Node Utilities
# ================================================================

def node_size(node):
    """Compute size of a node (number of leaf tokens)."""
    if isinstance(node, Node):
        if node.size is not None:
            return node.size
        if isinstance(node.elts, str):
            node.size = 1
            return 1
        s = sum(node_size(c) for c in node.elts)
        node.size = s
        return s
    if isinstance(node, list):
        return sum(node_size(c) for c in node)
    return 0


def set_node_context(node, ctx):
    """Set context names for move detection."""
    if isinstance(node, list):
        for n in node:
            set_node_context(n, ctx)
    elif isinstance(node, Node):
        name = node.def_name or ctx
        node.ctx = name
        if isinstance(node.elts, list):
            set_node_context(node.elts, name)


def get_name(node):
    """Get definition name from a node."""
    if isinstance(node, Node):
        return node.def_name
    return None


def get_type(node):
    """Get the type of a node."""
    if isinstance(node, Node):
        return node.type
    return None


def same_def(e1, e2):
    """Check if two nodes are definitions of the same thing."""
    if get_type(e1) != get_type(e2):
        return False
    n1, n2 = get_name(e1), get_name(e2)
    return n1 is not None and n2 is not None and n1 == n2


def node_sort_key(node):
    """Sort key: named defs first (by name), then by position."""
    name = get_name(node)
    if name:
        return (0, name, 0)
    return (1, '', node.start if isinstance(node, Node) else 0)


# ================================================================
#                     Change Utilities
# ================================================================

def make_ins(node):
    return [Change(None, node, node_size(node), 'ins')]


def make_del(node):
    return [Change(node, None, node_size(node), 'del')]


def make_mov(node1, node2, cost):
    return [Change(node1, node2, cost, 'mov')]


def make_total(node1, node2):
    s1, s2 = node_size(node1), node_size(node2)
    return make_del(node1) + make_ins(node2), s1 + s2


# ================================================================
#                      Python Parser
# ================================================================

def compute_line_starts(text):
    """Compute character offsets for the start of each line."""
    starts = [0]
    for i, c in enumerate(text):
        if c == '\n':
            starts.append(i + 1)
    return starts


def pos_to_offset(line_starts, lineno, col_offset):
    """Convert (1-based lineno, 0-based col_offset) to char offset."""
    if lineno < 1 or lineno > len(line_starts):
        return 0
    return line_starts[lineno - 1] + col_offset


def parse_python(text):
    """Parse Python source text into a Node tree."""
    tree = ast.parse(text)
    ls = compute_line_starts(text)
    return _convert(tree, text, ls)


def _get_span(n, ls):
    """Get (start, end) char offsets for an AST node."""
    lineno = getattr(n, 'lineno', None)
    if lineno is None:
        return None, None
    start = pos_to_offset(ls, lineno, getattr(n, 'col_offset', 0))
    end_ln = getattr(n, 'end_lineno', lineno)
    end_col = getattr(n, 'end_col_offset', getattr(n, 'col_offset', 0))
    end = pos_to_offset(ls, end_ln, end_col) if end_ln else start
    return start, end


def _convert(n, text, ls):
    """Convert an ast node to our Node format."""
    if n is None:
        return None

    # Module: top-level container
    if isinstance(n, ast.Module):
        children = [_convert(c, text, ls) for c in n.body]
        children = [c for c in children if c is not None]
        return Node('Module', 0, len(text), children)

    # Skip singleton context/operator nodes (Load, Store, Add, etc.)
    if isinstance(n, (ast.expr_context, ast.boolop, ast.operator,
                      ast.unaryop, ast.cmpop)):
        return None

    start, end = _get_span(n, ls)
    if start is None:
        return _convert_no_pos(n, text, ls)

    ntype = type(n).__name__

    # --- Leaf nodes ---
    if isinstance(n, ast.Name):
        return Node('token', start, end, n.id)

    if isinstance(n, ast.Constant):
        raw = text[start:end]
        if isinstance(n.value, str):
            return Node('str', start, end, raw)
        return Node('token', start, end, raw)

    if isinstance(n, ast.arg):
        return Node('token', start, end, n.arg)

    if isinstance(n, ast.alias):
        return Node('token', start, end, text[start:end])

    # --- Definition nodes (with def_name) ---
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        children = _collect_children(n, text, ls)
        return Node(ntype, start, end, children, def_name=n.name)

    if isinstance(n, ast.ClassDef):
        children = _collect_children(n, text, ls)
        return Node(ntype, start, end, children, def_name=n.name)

    if isinstance(n, ast.Assign):
        children = _collect_children(n, text, ls)
        def_name = None
        if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            def_name = n.targets[0].id
        return Node(ntype, start, end, children, def_name=def_name)

    # --- Generic compound node ---
    children = _collect_children(n, text, ls)
    if not children:
        raw = text[start:end]
        if raw.strip():
            return Node(ntype, start, end, raw)
        return Node(ntype, start, end, ntype)
    return Node(ntype, start, end, children)


def _convert_no_pos(n, text, ls):
    """Convert a node without position info (e.g., ast.arguments)."""
    children = []
    for child in ast.iter_child_nodes(n):
        c = _convert(child, text, ls)
        if c is not None:
            children.append(c)
    if not children:
        return None
    if len(children) == 1:
        return children[0]
    starts = [c.start for c in children]
    ends = [c.end for c in children]
    return Node(type(n).__name__, min(starts), max(ends), children)


def _collect_children(n, text, ls):
    """Collect all converted child nodes of an AST node."""
    children = []
    for child in ast.iter_child_nodes(n):
        c = _convert(child, text, ls)
        if c is not None:
            children.append(c)
    return children


# ================================================================
#                       Diff Algorithm
# ================================================================

# Parameters
MOVE_SIZE = 5
INNER_MOVE_SIZE = 2
MEMO_NODE_SIZE = 2

# Global state
_diff_hash = {}
_moving = False
_progress_count = 0


def diff(node1, node2):
    """Main diff function. Returns list of Changes."""
    global _diff_hash, _moving, _progress_count

    s1, s2 = node_size(node1), node_size(node2)
    print(f"[info] size of program 1: {s1}")
    print(f"[info] size of program 2: {s2}")

    set_node_context(node1, 'top')
    set_node_context(node2, 'top')

    print("[diffing]")
    _diff_hash = {}
    _moving = False
    _progress_count = 0

    changes, cost = diff_node(node1, node2)

    print(f"\n[moving]")
    _diff_hash = {}
    changes = find_moves(changes)

    print(f"\n[finished]")
    return changes


def diff_node(node1, node2):
    """Compare two nodes. Returns (changes, cost)."""
    global _diff_hash, _progress_count

    _progress_count += 1
    if _progress_count % 10000 == 0:
        print('.', end='', flush=True)

    # Check memo
    key = (id(node1), id(node2))
    if key in _diff_hash:
        return _diff_hash[key]

    def memo(changes, cost):
        if node_size(node1) > MEMO_NODE_SIZE and node_size(node2) > MEMO_NODE_SIZE:
            _diff_hash[key] = (changes, cost)
        return changes, cost

    def try_extract(changes, cost):
        if not _moving or cost == 0:
            return memo(changes, cost)
        m, c = diff_extract(node1, node2)
        if m is not None:
            return memo(m, c)
        return memo(changes, cost)

    # Both leaves of same type: compare strings
    if (isinstance(node1, Node) and isinstance(node2, Node)
            and isinstance(node1.elts, str) and isinstance(node2.elts, str)
            and node1.type == node2.type):
        if node1.elts == node2.elts:
            return memo(make_mov(node1, node2, 0), 0)
        else:
            changes, cost = make_total(node1, node2)
            return try_extract(changes, cost)

    # Both compound nodes of same type: diff children
    if (isinstance(node1, Node) and isinstance(node2, Node)
            and isinstance(node1.elts, list) and isinstance(node2.elts, list)
            and get_type(node1) == get_type(node2)):
        m, c = diff_list(node1.elts, node2.elts)
        return try_extract(m, c)

    # Different types or mixed leaf/compound: total change
    changes, cost = make_total(node1, node2)
    return try_extract(changes, cost)


def diff_list(ls1, ls2):
    """Compare two lists of nodes using dynamic programming."""
    ls1 = sorted(ls1, key=node_sort_key)
    ls2 = sorted(ls2, key=node_sort_key)
    memo = {}
    return _diff_list_rec(memo, ls1, ls2, 0, 0)


def _diff_list_rec(memo, ls1, ls2, i, j):
    """Recursive DP helper for list comparison."""
    key = (i, j)
    if key in memo:
        return memo[key]

    n1, n2 = len(ls1), len(ls2)

    if i >= n1 and j >= n2:
        result = ([], 0)
    elif i >= n1:
        changes = []
        cost = 0
        for k in range(j, n2):
            changes.extend(make_ins(ls2[k]))
            cost += node_size(ls2[k])
        result = (changes, cost)
    elif j >= n2:
        changes = []
        cost = 0
        for k in range(i, n1):
            changes.extend(make_del(ls1[k]))
            cost += node_size(ls1[k])
        result = (changes, cost)
    else:
        # Try matching head-to-head
        m0, c0 = diff_node(ls1[i], ls2[j])
        m1, c1 = _diff_list_rec(memo, ls1, ls2, i + 1, j + 1)

        if c0 == 0 or same_def(ls1[i], ls2[j]):
            result = (m0 + m1, c0 + c1)
        else:
            # Try skipping from each side
            m2, c2 = _diff_list_rec(memo, ls1, ls2, i + 1, j)
            m3, c3 = _diff_list_rec(memo, ls1, ls2, i, j + 1)
            cost2 = c2 + node_size(ls1[i])
            cost3 = c3 + node_size(ls2[j])

            if cost2 <= cost3:
                result = (make_del(ls1[i]) + m2, cost2)
            else:
                result = (make_ins(ls2[j]) + m3, cost3)

    memo[key] = result
    return result


# ================================================================
#                      Move Detection
# ================================================================

def big_node(node):
    return node_size(node) >= MOVE_SIZE


def same_ctx(x, y):
    return (isinstance(x, Node) and isinstance(y, Node)
            and x.ctx is not None and y.ctx is not None
            and node_size(x) >= INNER_MOVE_SIZE
            and node_size(y) >= INNER_MOVE_SIZE
            and x.ctx == y.ctx)


def diff_extract(node1, node2):
    """Try to find node1 inside node2 or vice versa."""
    if not (isinstance(node1, Node) and isinstance(node2, Node)):
        return None, None
    if not (same_ctx(node1, node2) or (big_node(node1) and big_node(node2))):
        return None, None

    if node_size(node1) <= node_size(node2):
        if isinstance(node2.elts, list):
            for child in node2.elts:
                m0, c0 = diff_node(node1, child)
                if (same_def(node1, child)
                        or (c0 == 0 and (big_node(node1) or same_ctx(node1, child)))):
                    frame = _extract_frame(node2, child, make_ins)
                    return m0 + frame, c0
    else:
        if isinstance(node1.elts, list):
            for child in node1.elts:
                m0, c0 = diff_node(child, node2)
                if (same_def(child, node2)
                        or (c0 == 0 and (big_node(node2) or same_ctx(child, node2)))):
                    frame = _extract_frame(node1, child, make_del)
                    return m0 + frame, c0

    return None, None


def _extract_frame(parent, excluded, change_fn):
    """Extract changes for everything in parent except the excluded child."""
    if isinstance(parent.elts, list):
        changes = []
        for e in parent.elts:
            if e is not excluded:
                changes.extend(change_fn(e))
        return changes
    return []


def find_moves(changes):
    """Iteratively find moved code among deletions and insertions."""
    global _moving, _diff_hash

    _moving = True
    _diff_hash = {}

    workset = list(changes)
    finished = []

    while True:
        dels = [c for c in workset if c.type == 'del' and big_node(c.old)]
        adds = [c for c in workset if c.type == 'ins' and big_node(c.new)]

        if not dels or not adds:
            return workset + finished

        rest = [c for c in workset if c not in dels and c not in adds]

        ls1 = sorted([c.old for c in dels], key=node_sort_key)
        ls2 = sorted([c.new for c in adds], key=node_sort_key)

        m, c = diff_list(ls1, ls2)
        new_moves = [ch for ch in m if ch.type == 'mov']

        if not new_moves:
            return workset + finished

        new_changes = [ch for ch in m if ch.type != 'mov']
        workset = new_changes
        finished = new_moves + rest + finished


# ================================================================
#                     HTML Generation
# ================================================================

_uid_counter = 0
_uid_map = {}


def uid(node):
    """Get a unique ID for a node."""
    global _uid_counter
    nid = id(node)
    if nid not in _uid_map:
        _uid_counter += 1
        _uid_map[nid] = _uid_counter
    return _uid_map[nid]


def escape_text(s):
    """Escape a string for HTML."""
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;')
             .replace("'", '&#39;'))


def change_class(change):
    if change.type == 'mov':
        return 'm'
    if change.type == 'del':
        return 'd'
    if change.type == 'ins':
        return 'i'
    return 'u'


def change_tags(changes, side):
    """Generate HTML tags for changes on one side."""
    tags = []
    for c in changes:
        key = c.old if side == 'left' else c.new
        if key is None or key.start == key.end:
            continue

        if c.old is not None and c.new is not None:
            me = c.old if side == 'left' else c.new
            other = c.new if side == 'left' else c.old
            cls = change_class(c)
            open_tag = f"<a id='{uid(me)}' tid='{uid(other)}' class='{cls}'>"
            close_tag = "</a>"
        else:
            cls = change_class(c)
            open_tag = f"<span class='{cls}'>"
            close_tag = "</span>"

        tags.append(Tag(open_tag, key.start, -1))
        tags.append(Tag(close_tag, key.end, key.start))
    return tags


def tag_sort_key(t):
    """Sort: by position, then close tags before open tags at same position."""
    return (t.idx, -t.start)


def apply_tags(text, tags):
    """Apply HTML tags into source text."""
    tags = sorted(tags, key=tag_sort_key)
    result = []
    prev = 0

    for tag in tags:
        if tag.idx > prev:
            result.append(escape_text(text[prev:tag.idx]))
            prev = tag.idx
        result.append(tag.tag)

    if prev < len(text):
        result.append(escape_text(text[prev:]))

    return ''.join(result)


DIFF_CSS = """\
.d { border: solid 1px #CC929A; border-radius: 3px; background-color: #FCBFBA; }
.i { border: solid 1px #73BE73; border-radius: 3px; background-color: #98FB98; }
.c { border: solid 1px #8AADB8; background-color: LightBlue; border-radius: 3px; cursor: pointer; }
.m { border: solid 1px #A9A9A9; border-radius: 3px; cursor: crosshair; }
.u { border: solid 1px #A9A9A9; border-radius: 4px; cursor: crosshair; }
div.src {
    width: 48%; height: 98%; overflow: scroll; float: left;
    padding: 0.5%; border: solid 2px LightGrey; border-radius: 5px;
}
pre { line-height: 200%; }
::-webkit-scrollbar { width: 10px; }
::-webkit-scrollbar-track {
    -webkit-box-shadow: inset 0 0 6px rgba(0,0,0,0.3); border-radius: 10px;
}
::-webkit-scrollbar-thumb {
    border-radius: 10px;
    -webkit-box-shadow: inset 0 0 6px rgba(0,0,0,0.5);
}
"""

NAV_JS = """\
window['$']=function(a){return document.getElementById(a)};
var minStep=10,nSteps=30,stepInterval=10,blockRange=5;
var nodeHLColor='#C9B0A9',bgColor='',bodyBlockedColor='#FAF0E6';
var eventCount={'left':0,'right':0},moving=false;
var matchId1='leftstart',matchId2='rightstart',cTimeout;
function sign(x){return x>0?1:x<0?-1:0;}
function elementPosition(id){
  var obj=$(id),l=0,t=0;
  if(obj&&obj.offsetParent){l=obj.offsetLeft;t=obj.offsetTop;
    while(obj=obj.offsetParent){l+=obj.offsetLeft;t+=obj.offsetTop;}}
  return{x:l,y:t};
}
function scrollCheck(c,dx,dy){
  var oT=c.scrollTop,oL=c.scrollLeft;c.scrollTop+=dy;c.scrollLeft+=dx;
  var aX=c.scrollLeft-oL,aY=c.scrollTop-oT;
  if((Math.abs(dx)>blockRange&&aX===0)||(Math.abs(dy)>blockRange&&aY===0)){
    c.style.backgroundColor=bodyBlockedColor;return true;
  }else{eventCount[c.id]+=1;c.style.backgroundColor=bgColor;return false;}
}
function getContainer(e){
  while(e&&e.tagName!=='DIV')e=e.parentElement||e.parentNode;return e;
}
function matchWindow(lid,tid,n){
  moving=true;
  var l=$(lid),t=$(tid),lc=getContainer(l),tc=getContainer(t);
  var lp=elementPosition(lid).y-lc.scrollTop;
  var tp=elementPosition(tid).y-tc.scrollTop;
  var dy=tp-lp,dx=lc.scrollLeft-tc.scrollLeft;
  if(dy===0&&dx===0){clearTimeout(cTimeout);moving=false;}
  else if(n<=1){scrollCheck(tc,dx,dy);moving=false;}
  else{
    var ss=Math.floor(Math.abs(dy)/n);
    var ms=Math.min(minStep,Math.abs(dy));
    var step=(Math.abs(ss)<minStep?ms:ss)*sign(dy);
    var blocked=scrollCheck(tc,dx,step);
    if(!blocked){cTimeout=setTimeout(function(){
      matchWindow(lid,tid,Math.floor(dy/step)-1);
    },stepInterval);}else{clearTimeout(cTimeout);moving=false;}
  }
}
var highlighted=[];
function putHL(id,c){var e=$(id);if(e){e.style.backgroundColor=c;
  if(c!==bgColor)highlighted.push(id);}}
function clearHL(){for(var i=0;i<highlighted.length;i++)putHL(highlighted[i],bgColor);
  highlighted=[];}
function highlight(me,lid,tid){clearHL();putHL(lid,nodeHLColor);putHL(tid,nodeHLColor);}
function instantMove(me){
  me.style.backgroundColor=bgColor;
  if(!moving&&eventCount[me.id]===0){
    if(me.id==='left')matchWindow(matchId1,matchId2,1);
    else matchWindow(matchId2,matchId1,1);
  }
  if(eventCount[me.id]>0)eventCount[me.id]-=1;
}
function getTarget(x){x=x||window.event;return x.target||x.srcElement;}
window.onload=function(){
  var tags=document.getElementsByTagName('A');
  for(var i=0;i<tags.length;i++){
    tags[i].onmouseover=function(e){
      var t=getTarget(e),lid=t.id,tid=t.getAttribute('tid');
      var c=getContainer(t);highlight(c,lid,tid);
    };
    tags[i].onclick=function(e){
      var t=getTarget(e),lid=t.id,tid=t.getAttribute('tid');
      var c=getContainer(t);highlight(c,lid,tid);
      if(c.id==='left'){matchId1=lid;matchId2=tid;}
      else{matchId1=tid;matchId2=lid;}
      matchWindow(lid,tid,nSteps);
    };
  }
  tags=document.getElementsByTagName('DIV');
  for(var i=0;i<tags.length;i++){
    tags[i].onscroll=function(e){instantMove(getTarget(e));};
  }
};
"""


def base_name(path):
    name = os.path.basename(path)
    dot = name.rfind('.')
    return name[:dot] if dot >= 0 else name


def htmlize(changes, file1, file2, text1, text2):
    """Generate interactive HTML diff output."""
    global _uid_counter, _uid_map
    _uid_counter = 0
    _uid_map = {}

    tags1 = change_tags(changes, 'left')
    tags2 = change_tags(changes, 'right')

    tagged1 = apply_tags(text1, tags1)
    tagged2 = apply_tags(text2, tags2)

    out_file = f"{base_name(file1)}-{base_name(file2)}.html"

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("<!DOCTYPE html>\n<html>\n<head>\n")
        f.write('<meta charset="utf-8">\n')
        f.write(f"<title>{base_name(file1)} vs {base_name(file2)}</title>\n")
        f.write(f"<style>\n{DIFF_CSS}</style>\n")
        f.write(f"<script>\n{NAV_JS}</script>\n")
        f.write("</head>\n<body>\n")

        f.write('<div id="left" class="src">\n<pre>\n')
        f.write("<a id='leftstart' tid='rightstart'></a>")
        f.write(tagged1)
        f.write("\n</pre>\n</div>\n")

        f.write('<div id="right" class="src">\n<pre>\n')
        f.write("<a id='rightstart' tid='leftstart'></a>")
        f.write(tagged2)
        f.write("\n</pre>\n</div>\n")

        f.write("</body>\n</html>\n")

    print(f"[output] {out_file}")
    return out_file


# ================================================================
#                      Git Helpers
# ================================================================

def git_run(args, cwd):
    """Run a git command and return stdout."""
    r = subprocess.run(['git'] + args, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def git_commit_info(project_dir, commit_id):
    """Get commit metadata."""
    out = git_run(['log', '-1', '--format=%H%n%h%n%an%n%ai%n%s', commit_id],
                  cwd=project_dir)
    lines = out.strip().split('\n')
    return {
        'hash': lines[0],
        'short_hash': lines[1],
        'author': lines[2],
        'date': lines[3],
        'message': lines[4] if len(lines) > 4 else '',
    }


def git_changed_files(project_dir, commit_id):
    """Get list of (status, old_path, new_path) for files changed in a commit."""
    # Check if this is the initial commit (no parent)
    r = subprocess.run(['git', 'rev-parse', f'{commit_id}^'],
                       capture_output=True, text=True, cwd=project_dir)
    if r.returncode != 0:
        # Initial commit: diff against empty tree
        out = git_run(['diff-tree', '--no-commit-id', '-r', '--name-status',
                       '--root', commit_id], cwd=project_dir)
    else:
        out = git_run(['diff', '--name-status', f'{commit_id}^', commit_id],
                      cwd=project_dir)
    files = []
    for line in out.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        status = parts[0][0]
        if status in ('R', 'C'):
            files.append((status, parts[1], parts[2]))
        elif status == 'A':
            files.append((status, None, parts[1]))
        elif status == 'D':
            files.append((status, parts[1], None))
        else:
            files.append((status, parts[1], parts[1]))
    return files


def git_file_content(project_dir, commit_id, file_path):
    """Get file content at a specific commit. Returns '' if not found."""
    r = subprocess.run(
        ['git', 'show', f'{commit_id}:{file_path}'],
        capture_output=True, text=True, cwd=project_dir
    )
    return r.stdout if r.returncode == 0 else ''


# ================================================================
#              Commit Diff - Multi-file Report
# ================================================================

COMMIT_CSS = """\
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; overflow: hidden; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
       background: #1e1e2e; color: #cdd6f4; }
.commit-header {
    background: #181825; padding: 16px 24px; border-bottom: 1px solid #313244;
}
.commit-header h2 { font-size: 18px; color: #89b4fa; margin-bottom: 6px; }
.commit-header .meta { font-size: 13px; color: #a6adc8; }
.commit-header .stats { font-size: 13px; color: #a6adc8; margin-top: 4px; }
.layout { display: flex; height: calc(100vh - 90px); min-height: 0; }
.file-nav {
    width: 280px; min-width: 200px; background: #181825;
    border-right: 1px solid #313244; overflow-y: auto; padding: 8px 0;
    flex-shrink: 0;
}
.file-item {
    padding: 6px 16px; cursor: pointer; font-size: 13px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    border-left: 3px solid transparent;
}
.file-item:hover { background: #313244; }
.file-item.active { background: #313244; border-left-color: #89b4fa; color: #89b4fa; }
.file-item .st { display: inline-block; width: 20px; font-weight: bold; }
.st-M { color: #fab387; }
.st-A { color: #a6e3a1; }
.st-D { color: #f38ba8; }
.st-R { color: #89b4fa; }
.file-content {
    flex: 1; overflow: hidden; display: flex; flex-direction: column; min-width: 0;
}
.file-title {
    padding: 8px 16px; font-size: 14px; font-weight: 600;
    background: #11111b; border-bottom: 1px solid #313244; color: #cba6f7;
    flex-shrink: 0;
}
.diff-area {
    flex: 1; display: flex; overflow: hidden; min-height: 0;
}
.file-diff {
    display: none; flex-direction: column; flex: 1;
    min-height: 0; overflow: hidden;
}
.file-diff.active { display: flex; }
.file-note {
    flex: 1; display: flex; align-items: center; justify-content: center;
    color: #6c7086; font-size: 15px;
}
/* Left pane: old version, red tint */
.diff-area div.src-left {
    width: 50%; overflow: auto; float: none;
    padding: 0 8px; border: none; border-radius: 0;
    border-right: 1px solid #313244;
    background: #2a1f1f;
}
/* Right pane: new version, green tint */
.diff-area div.src-right {
    width: 50%; overflow: auto; float: none;
    padding: 0 8px; border: none; border-radius: 0;
    background: #1f2a1f;
}
.diff-area pre {
    color: #cdd6f4; font-size: 13px; line-height: 180%;
    white-space: pre-wrap; word-wrap: break-word;
}
/* Deletion highlights (left pane) */
.diff-area .d {
    background-color: rgba(248,113,133,0.35); border: solid 1px #f38ba8;
    border-radius: 3px;
}
/* Insertion highlights (right pane) */
.diff-area .i {
    background-color: rgba(134,239,172,0.30); border: solid 1px #a6e3a1;
    border-radius: 3px;
}
/* Move/match highlights */
.diff-area .m {
    background-color: rgba(137,180,250,0.15); border: solid 1px #585b70;
    border-radius: 3px; cursor: crosshair;
}
"""

COMMIT_NAV_JS = """\
window['$']=function(a){return document.getElementById(a)};
var minStep=10,nSteps=30,stepInterval=10,blockRange=5;
var nodeHLColor='rgba(201,176,169,0.5)',bgColor='',bodyBlockedColor='rgba(250,240,230,0.1)';
var eventCount={},moving=false;
var matchId1=null,matchId2=null,cTimeout;
function sign(x){return x>0?1:x<0?-1:0;}
function elementPosition(id){
  var obj=$(id),l=0,t=0;
  if(obj&&obj.offsetParent){l=obj.offsetLeft;t=obj.offsetTop;
    while(obj=obj.offsetParent){l+=obj.offsetLeft;t+=obj.offsetTop;}}
  return{x:l,y:t};
}
function scrollCheck(c,dx,dy){
  var oT=c.scrollTop,oL=c.scrollLeft;c.scrollTop+=dy;c.scrollLeft+=dx;
  var aX=c.scrollLeft-oL,aY=c.scrollTop-oT;
  if(!eventCount[c.id])eventCount[c.id]=0;
  if((Math.abs(dx)>blockRange&&aX===0)||(Math.abs(dy)>blockRange&&aY===0)){
    c.style.backgroundColor=bodyBlockedColor;return true;
  }else{eventCount[c.id]+=1;c.style.backgroundColor=bgColor;return false;}
}
function getContainer(e){
  while(e&&!e.classList.contains('src-left')&&!e.classList.contains('src-right'))
    e=e.parentElement||e.parentNode;return e;
}
function getSide(c){return c.id.startsWith('left')?'left':'right';}
function matchWindow(lid,tid,n){
  moving=true;var l=$(lid),t=$(tid);
  if(!l||!t){moving=false;return;}
  var lc=getContainer(l),tc=getContainer(t);
  if(!lc||!tc){moving=false;return;}
  var lp=elementPosition(lid).y-lc.scrollTop;
  var tp=elementPosition(tid).y-tc.scrollTop;
  var dy=tp-lp,dx=lc.scrollLeft-tc.scrollLeft;
  if(dy===0&&dx===0){clearTimeout(cTimeout);moving=false;}
  else if(n<=1){scrollCheck(tc,dx,dy);moving=false;}
  else{
    var ss=Math.floor(Math.abs(dy)/n);
    var ms=Math.min(minStep,Math.abs(dy));
    var step=(Math.abs(ss)<minStep?ms:ss)*sign(dy);
    var blocked=scrollCheck(tc,dx,step);
    if(!blocked){cTimeout=setTimeout(function(){
      matchWindow(lid,tid,Math.floor(dy/step)-1);
    },stepInterval);}else{clearTimeout(cTimeout);moving=false;}
  }
}
var highlighted=[];
function putHL(id,c){var e=$(id);if(e){e.style.backgroundColor=c;
  if(c!==bgColor)highlighted.push(id);}}
function clearHL(){for(var i=0;i<highlighted.length;i++)putHL(highlighted[i],bgColor);
  highlighted=[];}
function highlight(me,lid,tid){clearHL();putHL(lid,nodeHLColor);putHL(tid,nodeHLColor);}
function instantMove(me){
  me.style.backgroundColor=bgColor;
  if(!eventCount[me.id])eventCount[me.id]=0;
  if(!moving&&eventCount[me.id]===0){
    if(matchId1&&matchId2){
      if(getSide(me)==='left')matchWindow(matchId1,matchId2,1);
      else matchWindow(matchId2,matchId1,1);
    }
  }
  if(eventCount[me.id]>0)eventCount[me.id]-=1;
}
function getTarget(x){x=x||window.event;return x.target||x.srcElement;}
function showFile(idx){
  var items=document.querySelectorAll('.file-item');
  var diffs=document.querySelectorAll('.file-diff');
  for(var i=0;i<items.length;i++){
    items[i].classList.remove('active');
    diffs[i].classList.remove('active');
  }
  items[idx].classList.add('active');
  diffs[idx].classList.add('active');
  matchId1=null;matchId2=null;
}
function bindNav(){
  var tags=document.getElementsByTagName('A');
  for(var i=0;i<tags.length;i++){
    tags[i].onmouseover=function(e){
      var t=getTarget(e),lid=t.id,tid=t.getAttribute('tid');
      if(!lid||!tid)return;
      var c=getContainer(t);highlight(c,lid,tid);
    };
    tags[i].onclick=function(e){
      var t=getTarget(e),lid=t.id,tid=t.getAttribute('tid');
      if(!lid||!tid)return;
      var c=getContainer(t);highlight(c,lid,tid);
      if(getSide(c)==='left'){matchId1=lid;matchId2=tid;}
      else{matchId1=tid;matchId2=lid;}
      matchWindow(lid,tid,nSteps);
    };
  }
  var divs=document.querySelectorAll('.src-left,.src-right');
  for(var i=0;i<divs.length;i++){
    divs[i].onscroll=function(e){instantMove(getTarget(e));};
  }
}
window.onload=function(){bindNav();};
"""


def diff_file_pair(text1, text2, filepath):
    """Diff two versions of a file. Returns (changes, tagged1, tagged2)."""
    global _uid_counter, _uid_map, _diff_hash, _moving, _progress_count

    if not text1 and not text2:
        return None, '', ''

    node1 = parse_python(text1) if text1 else Node('Module', 0, 0, [])
    node2 = parse_python(text2) if text2 else Node('Module', 0, 0, [])

    print(f"  [diff] {filepath}")
    _diff_hash = {}
    _moving = False
    _progress_count = 0

    s1, s2 = node_size(node1), node_size(node2)
    set_node_context(node1, 'top')
    set_node_context(node2, 'top')

    changes, cost = diff_node(node1, node2)
    _diff_hash = {}
    changes = find_moves(changes)

    tags1 = change_tags(changes, 'left')
    tags2 = change_tags(changes, 'right')
    tagged1 = apply_tags(text1, tags1)
    tagged2 = apply_tags(text2, tags2)
    return changes, tagged1, tagged2


def diff_commit(project_dir, commit_id, output=None):
    """Generate a multi-file diff report for a git commit."""
    global _uid_counter, _uid_map

    project_dir = os.path.abspath(project_dir)
    info = git_commit_info(project_dir, commit_id)
    changed = git_changed_files(project_dir, commit_id)

    print(f"[commit] {info['short_hash']} - {info['message']}")
    print(f"[files]  {len(changed)} files changed")

    # Process each file
    file_diffs = []  # (status, display_path, tagged1, tagged2, is_python)
    _uid_counter = 0
    _uid_map = {}

    for status, old_path, new_path in changed:
        display_path = new_path or old_path
        is_py = display_path.endswith('.py')

        if status == 'R':
            display_path = f"{old_path} \u2192 {new_path}"

        if not is_py:
            file_diffs.append((status, display_path, '', '', False))
            continue

        text1 = git_file_content(project_dir, f'{commit_id}^', old_path) if old_path else ''
        text2 = git_file_content(project_dir, commit_id, new_path) if new_path else ''

        try:
            _, tagged1, tagged2 = diff_file_pair(text1, text2, display_path)
            file_diffs.append((status, display_path, tagged1, tagged2, True))
        except SyntaxError as e:
            print(f"  [skip] {display_path}: parse error - {e}")
            file_diffs.append((status, display_path, '', '', False))

    # Generate HTML report
    out_file = output or f"commit-{info['short_hash']}.html"
    py_count = sum(1 for *_, is_py in file_diffs if is_py)

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("<!DOCTYPE html>\n<html>\n<head>\n")
        f.write('<meta charset="utf-8">\n')
        f.write(f"<title>Commit {info['short_hash']} - {escape_text(info['message'])}</title>\n")
        f.write(f"<style>\n{COMMIT_CSS}</style>\n")
        f.write(f"<script>\n{COMMIT_NAV_JS}</script>\n")
        f.write("</head>\n<body>\n")

        # Header
        f.write('<div class="commit-header">\n')
        f.write(f'  <h2>{info["short_hash"]} - {escape_text(info["message"])}</h2>\n')
        f.write(f'  <div class="meta">{escape_text(info["author"])} | {info["date"]}</div>\n')
        f.write(f'  <div class="stats">{len(changed)} files changed, '
                f'{py_count} Python files with structural diff</div>\n')
        f.write('</div>\n')

        # Layout
        f.write('<div class="layout">\n')

        # Sidebar
        f.write('<div class="file-nav">\n')
        for i, (status, path, *_) in enumerate(file_diffs):
            active = ' active' if i == 0 else ''
            f.write(f'  <div class="file-item{active}" onclick="showFile({i})">'
                    f'<span class="st st-{status}">{status}</span> '
                    f'{escape_text(path)}</div>\n')
        f.write('</div>\n')

        # File diffs
        f.write('<div class="file-content">\n')
        for i, (status, path, tagged1, tagged2, is_py) in enumerate(file_diffs):
            active = ' active' if i == 0 else ''
            f.write(f'<div class="file-diff{active}" id="fdiff-{i}">\n')
            f.write(f'  <div class="file-title">{escape_text(path)}</div>\n')

            if not is_py:
                label = {'A': 'added', 'D': 'deleted', 'M': 'modified', 'R': 'renamed'}
                f.write(f'  <div class="file-note">Non-Python file {label.get(status, "changed")}'
                        f' (structural diff not available)</div>\n')
            else:
                f.write('  <div class="diff-area">\n')
                f.write(f'    <div id="left-{i}" class="src-left"><pre>')
                f.write(tagged1)
                f.write('</pre></div>\n')
                f.write(f'    <div id="right-{i}" class="src-right"><pre>')
                f.write(tagged2)
                f.write('</pre></div>\n')
                f.write('  </div>\n')

            f.write('</div>\n')
        f.write('</div>\n')  # file-content
        f.write('</div>\n')  # layout
        f.write("</body>\n</html>\n")

    print(f"[output] {out_file}")
    return out_file


# ================================================================
#                          Main
# ================================================================

def diff_python(file1, file2):
    """Compare two Python files and generate HTML diff."""
    with open(file1, 'r', encoding='utf-8') as f:
        text1 = f.read()
    with open(file2, 'r', encoding='utf-8') as f:
        text2 = f.read()

    node1 = parse_python(text1)
    node2 = parse_python(text2)

    changes = diff(node1, node2)
    return htmlize(changes, file1, file2, text1, text2)


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--commit':
        # Commit mode: ydiff_python.py --commit <project_dir> <commit_id> [output.html]
        if len(sys.argv) < 4:
            print(f"Usage: {sys.argv[0]} --commit <project_dir> <commit_id> [output.html]")
            sys.exit(1)
        project_dir = sys.argv[2]
        commit_id = sys.argv[3]
        output = sys.argv[4] if len(sys.argv) > 4 else None
        diff_commit(project_dir, commit_id, output)
    elif len(sys.argv) == 3:
        # File mode: ydiff_python.py <file1.py> <file2.py>
        diff_python(sys.argv[1], sys.argv[2])
    else:
        print(f"Usage:")
        print(f"  {sys.argv[0]} <file1.py> <file2.py>              # compare two files")
        print(f"  {sys.argv[0]} --commit <project_dir> <commit_id>  # diff a git commit")
        sys.exit(1)


if __name__ == '__main__':
    main()
