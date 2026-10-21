package main

import (
	"errors"
	"fmt"
	"hash/fnv"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

// Allowed values. Reads accept any value; writes through the tool are
// validated against these. Areas is set by the -areas flag.
var (
	Statuses   = []string{"inbox", "todo", "doing", "blocked", "review", "done", "wontfix"}
	Types      = []string{"bug", "feature", "chore"}
	Priorities = []string{"p1", "p2", "p3"}
	Areas      = []string{"web", "server", "docs", "infra"}
	Sources    = []string{"devnote", "human", "agent"}
)

// MinToolID is the lowest id the tool hands out. Lower ids are free for hand-made tickets.
const MinToolID = 1000

// Ticket is the JSON view of one ticket file.
type Ticket struct {
	ID          int               `json:"id"`
	Title       string            `json:"title"`
	Type        string            `json:"type"`
	Status      string            `json:"status"`
	Priority    string            `json:"priority"`
	Area        string            `json:"area"`
	Created     string            `json:"created"`
	Updated     string            `json:"updated"`
	Source      string            `json:"source"`
	URL         string            `json:"url,omitempty"`
	Selector    string            `json:"selector,omitempty"`
	ElementText string            `json:"element_text,omitempty"`
	Viewport    string            `json:"viewport,omitempty"`
	Screenshot  string            `json:"screenshot,omitempty"`
	Images      []string          `json:"images,omitempty"` // "assets/<name>" paths: the screenshot field plus image links in the body
	Extra       map[string]string `json:"extra,omitempty"`  // unknown frontmatter fields, read-only
	Body        string            `json:"body"`             // markdown before "## Notes"
	Notes       string            `json:"notes"`            // markdown after "## Notes"
	File        string            `json:"file"`             // file name inside the tickets dir
}

var knownKeys = map[string]bool{"id": true, "title": true, "type": true, "status": true, "priority": true,
	"area": true, "created": true, "updated": true, "source": true, "url": true, "selector": true,
	"element_text": true, "viewport": true, "screenshot": true}

// ---- file format ----

// doc is one ticket file split so that untouched bytes stay untouched:
// head ("---\n") + front lines (each with its newline) + close ("---\n") + body.
type doc struct {
	head  string
	front []string
	close string
	body  string
}

func parseDoc(s string) *doc {
	first, rest, ok := strings.Cut(s, "\n")
	if !ok || strings.TrimRight(first, "\r") != "---" {
		return &doc{body: s}
	}
	d := &doc{head: first + "\n"}
	for len(rest) > 0 {
		line, after, hasNL := strings.Cut(rest, "\n")
		if strings.TrimRight(line, "\r") == "---" {
			d.close = line
			if hasNL {
				d.close += "\n"
			}
			d.body = after
			return d
		}
		if hasNL {
			line += "\n"
		}
		d.front = append(d.front, line)
		rest = after
	}
	// No closing delimiter: not frontmatter after all.
	return &doc{body: s}
}

func (d *doc) String() string {
	if d.head == "" {
		return d.body
	}
	return d.head + strings.Join(d.front, "") + d.close + d.body
}

var keyRe = regexp.MustCompile(`^([A-Za-z0-9_-]+):(.*)$`)

// splitLine returns key, value and the untouched tail (inline comment and
// line ending) for a top-level "key: value" line.
func splitLine(line string) (key, val, tail string, ok bool) {
	eol := ""
	for _, e := range []string{"\r\n", "\n"} {
		if strings.HasSuffix(line, e) {
			eol, line = e, strings.TrimSuffix(line, e)
			break
		}
	}
	m := keyRe.FindStringSubmatch(line)
	if m == nil {
		return "", "", "", false
	}
	raw := m[2]
	trimmed := strings.TrimLeft(raw, " \t")
	if trimmed != "" && (trimmed[0] == '"' || trimmed[0] == '\'') {
		if end := closingQuote(trimmed); end > 0 {
			return m[1], unquote(trimmed[:end+1]), trimmed[end+1:] + eol, true
		}
	}
	// Unquoted: an inline comment starts at whitespace followed by '#'.
	v, comment := raw, ""
	for i := 1; i < len(raw); i++ {
		if raw[i] == '#' && (raw[i-1] == ' ' || raw[i-1] == '\t') {
			v, comment = raw[:i], raw[i:]
			// keep the spacing before the comment with the comment
			t := strings.TrimRight(v, " \t")
			comment = v[len(t):] + comment
			v = t
			break
		}
	}
	return m[1], strings.TrimSpace(v), comment + eol, true
}

func closingQuote(s string) int {
	q := s[0]
	for i := 1; i < len(s); i++ {
		switch {
		case q == '"' && s[i] == '\\':
			i++
		case q == '\'' && s[i] == '\'' && i+1 < len(s) && s[i+1] == '\'':
			i++
		case s[i] == q:
			return i
		}
	}
	return -1
}

func unquote(s string) string {
	if s[0] == '\'' {
		return strings.ReplaceAll(s[1:len(s)-1], "''", "'")
	}
	if u, err := strconv.Unquote(s); err == nil {
		return u
	}
	return s[1 : len(s)-1]
}

// formatValue writes v plainly when YAML would read it back unchanged,
// and double-quoted otherwise.
func formatValue(v string) string {
	if v == "" {
		return `""`
	}
	plain := !strings.ContainsAny(v[:1], "\"'[]{}>|*&!%@`#,?:-") &&
		strings.TrimSpace(v) == v &&
		!strings.Contains(v, ": ") && !strings.Contains(v, " #") && !strings.HasSuffix(v, ":") &&
		!strings.ContainsAny(v, "\n\r\t\\")
	if plain {
		switch strings.ToLower(v) {
		case "true", "false", "yes", "no", "null", "~", "on", "off":
			plain = false
		}
	}
	if plain {
		return v
	}
	return strconv.Quote(v)
}

func (d *doc) fields() map[string]string {
	vals := map[string]string{}
	for _, l := range d.front {
		if k, v, _, ok := splitLine(l); ok {
			vals[k] = v
		}
	}
	return vals
}

// set replaces the value of key in place (keeping its comment), or appends
// a new line when the key is missing. An empty value on a missing key is a no-op.
func (d *doc) set(key, val string) {
	if d.head == "" {
		d.head, d.close = "---\n", "---\n"
	}
	for i, l := range d.front {
		if k, _, tail, ok := splitLine(l); ok && k == key {
			d.front[i] = key + ": " + formatValue(val) + tail
			return
		}
	}
	if val == "" {
		return
	}
	if n := len(d.front); n > 0 && !strings.HasSuffix(d.front[n-1], "\n") {
		d.front[n-1] += "\n"
	}
	d.front = append(d.front, key+": "+formatValue(val)+"\n")
}

// splitBody separates the description from the "## Notes" section.
func splitBody(body string) (desc, notes string) {
	lines := strings.SplitAfter(body, "\n")
	off := 0
	for _, l := range lines {
		if strings.TrimSpace(l) == "## Notes" {
			return body[:off], body[off:]
		}
		off += len(l)
	}
	return body, ""
}

func notesText(section string) string {
	_, after, _ := strings.Cut(section, "\n")
	return strings.Trim(after, "\n")
}

// def sets *p to v when it is empty.
func def(p *string, v string) {
	if *p == "" {
		*p = v
	}
}

func toTicket(name string, d *doc) Ticket {
	f := d.fields()
	t := Ticket{File: name, Title: f["title"], Type: f["type"], Status: f["status"], Priority: f["priority"],
		Area: f["area"], Created: f["created"], Updated: f["updated"], Source: f["source"], URL: f["url"],
		Selector: f["selector"], ElementText: f["element_text"], Viewport: f["viewport"], Screenshot: f["screenshot"]}
	t.ID, _ = strconv.Atoi(f["id"])
	if t.ID <= 0 {
		t.ID = idFromName(name)
	}
	if t.Title == "" {
		t.Title = strings.ReplaceAll(strings.TrimPrefix(strings.TrimSuffix(name, ".md"), fmt.Sprintf("%04d-", t.ID)), "-", " ")
	}
	def(&t.Status, "inbox")
	def(&t.Type, "chore")
	def(&t.Priority, "p2")
	def(&t.Updated, t.Created)
	for k, v := range f {
		if !knownKeys[k] {
			if t.Extra == nil {
				t.Extra = map[string]string{}
			}
			t.Extra[k] = v
		}
	}
	desc, notes := splitBody(d.body)
	t.Body = strings.Trim(desc, "\n")
	t.Notes = notesText(notes)
	t.Images = images(t)
	return t
}

var namePrefix = regexp.MustCompile(`^(\d+)`)

func idFromName(name string) int {
	n, _ := strconv.Atoi(namePrefix.FindString(name))
	return n
}

var slugRe = regexp.MustCompile(`[^a-z0-9]+`)

func slugify(title string) string {
	s := strings.Trim(slugRe.ReplaceAllString(strings.ToLower(title), "-"), "-")
	if len(s) > 48 {
		s = s[:48]
		if i := strings.LastIndexByte(s, '-'); i > 20 {
			s = s[:i]
		}
		s = strings.Trim(s, "-")
	}
	if s == "" {
		s = "ticket"
	}
	return s
}

// ---- store ----

type Store struct {
	Dir string
	Now func() time.Time
	mu  sync.Mutex // in-process; flock on the directory covers other processes
}

func NewStore(dir string) *Store {
	return &Store{Dir: dir, Now: time.Now}
}

var ErrNotFound = errors.New("ticket not found")

func (s *Store) stamp() string { return s.Now().UTC().Truncate(time.Second).Format(time.RFC3339) }

// lock serialises writers, including the CLI running beside the server.
// ponytail: flock is unix-only, which is fine for a dev tool on macOS/Linux.
func (s *Store) lock() (func(), error) {
	s.mu.Lock()
	f, err := os.Open(s.Dir)
	if err == nil {
		err = syscall.Flock(int(f.Fd()), syscall.LOCK_EX)
	}
	if err != nil {
		if f != nil {
			f.Close()
		}
		s.mu.Unlock()
		return nil, err
	}
	return func() { syscall.Flock(int(f.Fd()), syscall.LOCK_UN); f.Close(); s.mu.Unlock() }, nil
}

func (s *Store) files() ([]string, error) {
	ents, err := os.ReadDir(s.Dir)
	if err != nil {
		return nil, err
	}
	var out []string
	for _, e := range ents {
		n := e.Name()
		if !e.IsDir() && strings.HasSuffix(n, ".md") && !strings.HasPrefix(n, ".") && namePrefix.MatchString(n) {
			out = append(out, n)
		}
	}
	return out, nil
}

// List reads every ticket file fresh. Files that fail to read are skipped.
func (s *Store) List() ([]Ticket, error) {
	names, err := s.files()
	if err != nil {
		return nil, err
	}
	out := make([]Ticket, 0, len(names))
	for _, n := range names {
		b, err := os.ReadFile(filepath.Join(s.Dir, n))
		if err != nil {
			continue
		}
		out = append(out, toTicket(n, parseDoc(string(b))))
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

// Version changes whenever any ticket file changes; the board polls it.
func (s *Store) Version() string {
	names, _ := s.files()
	var b strings.Builder
	for _, n := range names {
		if fi, err := os.Stat(filepath.Join(s.Dir, n)); err == nil {
			fmt.Fprintf(&b, "%s:%d:%d;", n, fi.Size(), fi.ModTime().UnixNano())
		}
	}
	h := fnv.New64a()
	h.Write([]byte(b.String()))
	return fmt.Sprintf("%x", h.Sum64())
}

func (s *Store) find(id int) (string, *doc, error) {
	if id <= 0 {
		return "", nil, ErrNotFound
	}
	names, err := s.files()
	if err != nil {
		return "", nil, err
	}
	for _, n := range names {
		b, err := os.ReadFile(filepath.Join(s.Dir, n))
		if err != nil {
			continue
		}
		d := parseDoc(string(b))
		if toTicket(n, d).ID == id {
			return n, d, nil
		}
	}
	return "", nil, ErrNotFound
}

func (s *Store) Get(id int) (Ticket, error) {
	n, d, err := s.find(id)
	if err != nil {
		return Ticket{}, err
	}
	return toTicket(n, d), nil
}

func (s *Store) nextID() (int, error) {
	names, err := s.files()
	if err != nil {
		return 0, err
	}
	max := MinToolID - 1
	for _, n := range names {
		id := idFromName(n)
		if b, err := os.ReadFile(filepath.Join(s.Dir, n)); err == nil {
			if t := toTicket(n, parseDoc(string(b))); t.ID > id {
				id = t.ID
			}
		}
		if id > max {
			max = id
		}
	}
	return max + 1, nil
}

func writeAtomic(path string, data []byte) error {
	f, err := os.CreateTemp(filepath.Dir(path), ".tmp-ticket-*")
	if err != nil {
		return err
	}
	tmp := f.Name()
	err = f.Chmod(0o644)
	if err == nil {
		_, err = f.Write(data)
	}
	if err == nil {
		err = f.Sync()
	}
	if cerr := f.Close(); err == nil {
		err = cerr
	}
	if err == nil {
		err = os.Rename(tmp, path)
	}
	if err != nil {
		os.Remove(tmp)
	}
	return err
}

// NewTicket holds the fields a creator may set.
type NewTicket struct {
	Title       string `json:"title"`
	Type        string `json:"type"`
	Status      string `json:"status"`
	Priority    string `json:"priority"`
	Area        string `json:"area"`
	Source      string `json:"source"`
	Body        string `json:"body"`
	URL         string `json:"url"`
	Selector    string `json:"selector"`
	ElementText string `json:"element_text"`
	Viewport    string `json:"viewport"`
}

func oneOf(field, v string, allowed []string) error {
	for _, a := range allowed {
		if v == a {
			return nil
		}
	}
	return fmt.Errorf("%s must be one of %s", field, strings.Join(allowed, ", "))
}

func cleanTitle(t string) (string, error) {
	t = oneLine(t, 200)
	if t == "" {
		return "", errors.New("title is required")
	}
	return t, nil
}

func (s *Store) Create(n NewTicket) (Ticket, error) {
	def(&n.Type, "bug")
	def(&n.Status, "inbox")
	def(&n.Priority, "p2")
	def(&n.Area, Areas[0])
	def(&n.Source, "human")
	var err error
	if n.Title, err = cleanTitle(n.Title); err != nil {
		return Ticket{}, err
	}
	for _, c := range []struct {
		f, v string
		a    []string
	}{{"type", n.Type, Types}, {"status", n.Status, Statuses}, {"priority", n.Priority, Priorities},
		{"area", n.Area, Areas}, {"source", n.Source, Sources}} {
		if err := oneOf(c.f, c.v, c.a); err != nil {
			return Ticket{}, err
		}
	}
	unlock, err := s.lock()
	if err != nil {
		return Ticket{}, err
	}
	defer unlock()
	id, err := s.nextID()
	if err != nil {
		return Ticket{}, err
	}
	now := s.stamp()
	d := &doc{}
	for _, kv := range [][2]string{{"id", strconv.Itoa(id)}, {"title", n.Title}, {"type", n.Type},
		{"status", n.Status}, {"priority", n.Priority}, {"area", n.Area}, {"created", now}, {"updated", now},
		{"source", n.Source}, {"url", n.URL}, {"selector", n.Selector},
		{"element_text", oneLine(n.ElementText, 120)}, {"viewport", n.Viewport}} {
		d.set(kv[0], kv[1])
	}
	body := strings.Trim(n.Body, "\n")
	if body != "" {
		body += "\n"
	}
	d.body = "\n" + body
	name := fmt.Sprintf("%04d-%s.md", id, slugify(n.Title))
	if err := writeAtomic(filepath.Join(s.Dir, name), []byte(d.String())); err != nil {
		return Ticket{}, err
	}
	return toTicket(name, d), nil
}

func oneLine(s string, max int) string {
	s = strings.Join(strings.Fields(s), " ")
	if r := []rune(s); len(r) > max {
		s = string(r[:max])
	}
	return s
}

// Patch holds optional changes. Body replaces the description only; the
// Notes section is append-only through AddNote.
type Patch struct {
	Title    *string `json:"title"`
	Type     *string `json:"type"`
	Status   *string `json:"status"`
	Priority *string `json:"priority"`
	Area     *string `json:"area"`
	Body     *string `json:"body"`
}

func (s *Store) Update(id int, p Patch) (Ticket, error) {
	if p.Title != nil {
		t, err := cleanTitle(*p.Title)
		if err != nil {
			return Ticket{}, err
		}
		p.Title = &t
	}
	for _, c := range []struct {
		f string
		v *string
		a []string
	}{{"type", p.Type, Types}, {"status", p.Status, Statuses}, {"priority", p.Priority, Priorities}, {"area", p.Area, Areas}} {
		if c.v != nil {
			if err := oneOf(c.f, *c.v, c.a); err != nil {
				return Ticket{}, err
			}
		}
	}
	return s.modify(id, func(d *doc) error {
		for _, kv := range []struct {
			k string
			v *string
		}{{"title", p.Title}, {"type", p.Type}, {"status", p.Status}, {"priority", p.Priority}, {"area", p.Area}} {
			if kv.v != nil {
				d.set(kv.k, *kv.v)
			}
		}
		if p.Body != nil {
			_, notes := splitBody(d.body)
			b := strings.Trim(*p.Body, "\n")
			nb := "\n"
			if b != "" {
				nb += b + "\n"
			}
			if notes != "" {
				nb += "\n" + notes
			}
			d.body = nb
		}
		return nil
	})
}

// AddNote appends a dated line to "## Notes", creating the section if needed.
func (s *Store) AddNote(id int, text, by string) (Ticket, error) {
	text = strings.TrimSpace(text)
	if text == "" {
		return Ticket{}, errors.New("note text is required")
	}
	by = oneLine(by, 40)
	return s.modify(id, func(d *doc) error {
		_, notes := splitBody(d.body)
		b := strings.TrimRight(d.body, "\n") + "\n"
		if notes == "" {
			b += "\n## Notes\n"
		}
		stamp := s.Now().UTC().Format("2006-01-02 15:04Z")
		if by != "" {
			stamp += " (" + by + ")"
		}
		d.body = b + "\n- " + stamp + ": " + strings.ReplaceAll(text, "\n", "\n  ") + "\n"
		return nil
	})
}

var imageExt = map[string]string{"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}

var imageLink = regexp.MustCompile(`!\[[^\]]*\]\((assets/[A-Za-z0-9._-]+)\)`)

func images(t Ticket) []string {
	var out []string
	seen := map[string]bool{}
	add := func(p string) {
		if !seen[p] {
			seen[p] = true
			out = append(out, p)
		}
	}
	if strings.HasPrefix(t.Screenshot, "tickets/assets/") {
		add(strings.TrimPrefix(t.Screenshot, "tickets/"))
	}
	for _, m := range imageLink.FindAllStringSubmatch(t.Body, -1) {
		add(m[1])
	}
	return out
}

// AddImage saves a PNG, JPEG or WebP as assets/<id>.<ext>, then <id>-2.<ext>
// and so on, links it in the description and fills the screenshot field if
// it is empty. It returns the saved path relative to the tickets dir.
func (s *Store) AddImage(id int, data []byte) (Ticket, string, error) {
	ext, ok := imageExt[http.DetectContentType(data)]
	if !ok {
		return Ticket{}, "", errors.New("image must be PNG, JPEG or WebP")
	}
	var rel string
	t, err := s.modify(id, func(d *doc) error {
		dir := filepath.Join(s.Dir, "assets")
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return err
		}
		// The name comes from the numeric id only, never from the request.
		base := fmt.Sprintf("%04d", id)
		for n := 2; ; n++ {
			if m, _ := filepath.Glob(filepath.Join(dir, base+".*")); len(m) == 0 {
				break
			}
			base = fmt.Sprintf("%04d-%d", id, n)
		}
		rel = "assets/" + base + ext
		if err := writeAtomic(filepath.Join(s.Dir, rel), data); err != nil {
			return err
		}
		if d.fields()["screenshot"] == "" {
			d.set("screenshot", "tickets/"+rel)
		}
		desc, notes := splitBody(d.body)
		desc = strings.TrimRight(desc, "\n")
		if desc != "" {
			desc += "\n"
		}
		d.body = desc + "\n![Screenshot](" + rel + ")\n"
		if notes != "" {
			d.body += "\n" + notes
		}
		return nil
	})
	return t, "tickets/" + rel, err
}

func (s *Store) modify(id int, fn func(*doc) error) (Ticket, error) {
	unlock, err := s.lock()
	if err != nil {
		return Ticket{}, err
	}
	defer unlock()
	name, d, err := s.find(id)
	if err != nil {
		return Ticket{}, err
	}
	if err := fn(d); err != nil {
		return Ticket{}, err
	}
	d.set("updated", s.stamp())
	if err := writeAtomic(filepath.Join(s.Dir, name), []byte(d.String())); err != nil {
		return Ticket{}, err
	}
	return toTicket(name, d), nil
}
