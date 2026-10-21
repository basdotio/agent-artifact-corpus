package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

const agentFile = `---
id: 150
title: "Rail pill: jumps when switching"
type: bug            # bug | feature | chore
status: inbox        # inbox | todo | doing | review | done | wontfix
priority: p2
area: web
custom_owner: agent-7   # unknown field, keep me
tags: [a, b]
links:
  - https://example.com/a
created: 2026-10-16T18:04:00Z
updated: 2026-10-16T18:04:00Z
source: agent
# Present when source is devnote:
selector: "nav.rail > button:nth-child(2)"
---

Body line one.
  indented   line	with tab

## Notes

- earlier note
`

func fixedStore(t *testing.T) *Store {
	t.Helper()
	s := NewStore(t.TempDir())
	s.Now = func() time.Time { return time.Date(2026, 10, 17, 9, 30, 0, 0, time.UTC) }
	return s
}

func writeFile(t *testing.T, s *Store, name, content string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(s.Dir, name), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func readFile(t *testing.T, s *Store, name string) string {
	t.Helper()
	b, err := os.ReadFile(filepath.Join(s.Dir, name))
	if err != nil {
		t.Fatal(err)
	}
	return string(b)
}

func TestRoundTripUnchanged(t *testing.T) {
	for _, in := range []string{agentFile, "no frontmatter at all\n", "---\nid: 3\n---\n", "---\r\nid: 4\r\n---\r\nbody\r\n", "---\nunclosed: yes\n"} {
		if got := parseDoc(in).String(); got != in {
			t.Errorf("round trip changed bytes:\n%q\n%q", in, got)
		}
	}
}

func TestParseFields(t *testing.T) {
	tk := toTicket("0150-rail.md", parseDoc(agentFile))
	if tk.ID != 150 || tk.Title != "Rail pill: jumps when switching" || tk.Type != "bug" || tk.Status != "inbox" {
		t.Fatalf("bad parse: %+v", tk)
	}
	if tk.Selector != "nav.rail > button:nth-child(2)" {
		t.Fatalf("selector %q", tk.Selector)
	}
	if tk.Extra["custom_owner"] != "agent-7" || tk.Extra["tags"] != "[a, b]" {
		t.Fatalf("extra %v", tk.Extra)
	}
	if tk.Body != "Body line one.\n  indented   line\twith tab" || tk.Notes != "- earlier note" {
		t.Fatalf("body %q notes %q", tk.Body, tk.Notes)
	}
	// Missing fields default; id falls back to the file name.
	m := toTicket("0207-some-thing.md", parseDoc("---\nfoo: bar\n---\nhi\n"))
	if m.ID != 207 || m.Title != "some thing" || m.Status != "inbox" || m.Type != "chore" || m.Priority != "p2" {
		t.Fatalf("defaults: %+v", m)
	}
}

func TestUpdateKeepsEverythingElse(t *testing.T) {
	s := fixedStore(t)
	writeFile(t, s, "0150-rail.md", agentFile)
	st := "todo"
	if _, err := s.Update(150, Patch{Status: &st}); err != nil {
		t.Fatal(err)
	}
	want := strings.Replace(agentFile, "status: inbox        #", "status: todo        #", 1)
	want = strings.Replace(want, "updated: 2026-10-16T18:04:00Z", "updated: 2026-10-17T09:30:00Z", 1)
	if got := readFile(t, s, "0150-rail.md"); got != want {
		t.Fatalf("update rewrote more than status and updated:\n%s", got)
	}

	// Editing the body keeps the Notes section; adding a note appends.
	b := "New body."
	if _, err := s.Update(150, Patch{Body: &b}); err != nil {
		t.Fatal(err)
	}
	if _, err := s.AddNote(150, "second\nline two", "human"); err != nil {
		t.Fatal(err)
	}
	got := readFile(t, s, "0150-rail.md")
	wantTail := "---\n\nNew body.\n\n## Notes\n\n- earlier note\n\n- 2026-10-17 09:30Z (human): second\n  line two\n"
	if !strings.HasSuffix(got, wantTail) {
		t.Fatalf("body/notes wrong:\n%s", got)
	}

	bad := "closed"
	if _, err := s.Update(150, Patch{Status: &bad}); err == nil {
		t.Fatal("invalid status accepted")
	}
}

func TestAddNoteCreatesSection(t *testing.T) {
	s := fixedStore(t)
	writeFile(t, s, "0101-x.md", "---\nid: 101\ntitle: X\n---\n\nHello.\n")
	if _, err := s.AddNote(101, "found it", ""); err != nil {
		t.Fatal(err)
	}
	want := "---\nid: 101\ntitle: X\nupdated: 2026-10-17T09:30:00Z\n---\n\nHello.\n\n## Notes\n\n- 2026-10-17 09:30Z: found it\n"
	if got := readFile(t, s, "0101-x.md"); got != want {
		t.Fatalf("got:\n%q", got)
	}
}

func TestCreateFormatAndQuoting(t *testing.T) {
	s := fixedStore(t)
	tk, err := s.Create(NewTicket{Title: "feat: Selector #2 breaks", Type: "feature", Area: "web", Source: "devnote",
		Selector: `div[aria-label="x"] > a`, URL: "http://localhost:5173/#/c/a", ElementText: "  hi\n there ", Body: "Line"})
	if err != nil {
		t.Fatal(err)
	}
	if tk.File != "1000-feat-selector-2-breaks.md" {
		t.Fatalf("file %q", tk.File)
	}
	want := `---
id: 1000
title: "feat: Selector #2 breaks"
type: feature
status: inbox
priority: p2
area: web
created: 2026-10-17T09:30:00Z
updated: 2026-10-17T09:30:00Z
source: devnote
url: http://localhost:5173/#/c/a
selector: div[aria-label="x"] > a
element_text: hi there
---

Line
`
	if got := readFile(t, s, tk.File); got != want {
		t.Fatalf("got:\n%s", got)
	}
	if fi, _ := os.Stat(filepath.Join(s.Dir, tk.File)); fi.Mode().Perm() != 0o644 {
		t.Fatalf("mode %v, want 0644", fi.Mode().Perm())
	}
	back, _ := s.Get(1000)
	if back.Title != "feat: Selector #2 breaks" || back.Selector != `div[aria-label="x"] > a` {
		t.Fatalf("quoting did not round trip: %+v", back)
	}
	if _, err := s.Create(NewTicket{Title: "  "}); err == nil {
		t.Fatal("empty title accepted")
	}
	if _, err := s.Create(NewTicket{Title: "x", Area: "nowhere"}); err == nil {
		t.Fatal("bad area accepted")
	}
}

func TestIDAllocation(t *testing.T) {
	s := fixedStore(t)
	writeFile(t, s, "0150-a.md", "---\nid: 150\n---\n")
	// Two stores on one directory stand in for the server plus the CLI;
	// only the directory flock keeps them apart.
	other := NewStore(s.Dir)
	var wg sync.WaitGroup
	var mu sync.Mutex
	ids := map[int]bool{}
	for i := 0; i < 30; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			st := s
			if i%2 == 1 {
				st = other
			}
			tk, err := st.Create(NewTicket{Title: fmt.Sprintf("note %d", i)})
			if err != nil {
				t.Error(err)
				return
			}
			mu.Lock()
			ids[tk.ID] = true
			mu.Unlock()
		}(i)
	}
	wg.Wait()
	for id := 1000; id < 1030; id++ {
		if !ids[id] {
			t.Fatalf("missing id %d; got %v", id, ids)
		}
	}
	// Above 1000 the next id is max+1, even when only the file name says so.
	writeFile(t, s, "1500-b.md", "no frontmatter\n")
	tk, err := s.Create(NewTicket{Title: "after"})
	if err != nil || tk.ID != 1501 {
		t.Fatalf("got %d %v, want 1501", tk.ID, err)
	}
}

func do(h http.Handler, method, path, origin, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	r.Host = "localhost:8090"
	if origin != "" {
		r.Header.Set("Origin", origin)
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestAPI(t *testing.T) {
	s := fixedStore(t)
	writeFile(t, s, "0150-rail.md", agentFile)
	h := newServer(s, false, io.Discard)

	w := do(h, "POST", "/api/tickets", "", `{"title":"Button overlaps","area":"web","source":"devnote","url":"http://localhost:5173/?debug=1#/c/x"}`)
	if w.Code != 201 {
		t.Fatalf("create %d %s", w.Code, w.Body)
	}
	w = do(h, "PATCH", "/api/tickets/1000", "", `{"status":"doing","priority":"p1"}`)
	var tk Ticket
	json.Unmarshal(w.Body.Bytes(), &tk)
	if w.Code != 200 || tk.Status != "doing" || tk.Priority != "p1" || tk.Title != "Button overlaps" {
		t.Fatalf("patch %d %s", w.Code, w.Body)
	}
	if got := readFile(t, s, "1000-button-overlaps.md"); !strings.Contains(got, "\nstatus: doing\n") || !strings.Contains(got, "\npriority: p1\n") {
		t.Fatalf("patch not on disk:\n%s", got)
	}
	for _, c := range []struct {
		body string
		code int
	}{{`{"status":"nope"}`, 400}, {`{"bogus":1}`, 400}, {`not json`, 400}} {
		if w := do(h, "PATCH", "/api/tickets/1000", "", c.body); w.Code != c.code {
			t.Errorf("PATCH %s: %d", c.body, w.Code)
		}
	}
	if w := do(h, "PATCH", "/api/tickets/999", "", `{"status":"todo"}`); w.Code != 404 {
		t.Errorf("missing ticket: %d", w.Code)
	}
	if w := do(h, "POST", "/api/tickets/1000/notes", "", `{"text":"hello","by":"human"}`); w.Code != 200 || !strings.Contains(w.Body.String(), "(human): hello") {
		t.Errorf("note: %d %s", w.Code, w.Body)
	}

	// Filters: url ignores the query string; status takes a list.
	var list []Ticket
	json.Unmarshal(do(h, "GET", "/api/tickets?url="+"http%3A%2F%2Flocalhost%3A5173%2F%23%2Fc%2Fx", "", "").Body.Bytes(), &list)
	if len(list) != 1 || list[0].ID != 1000 {
		t.Fatalf("url filter: %+v", list)
	}
	json.Unmarshal(do(h, "GET", "/api/tickets?status=inbox,todo", "", "").Body.Bytes(), &list)
	if len(list) != 1 || list[0].ID != 150 {
		t.Fatalf("status filter: %+v", list)
	}
	if w := do(h, "GET", "/", "", ""); w.Code != 200 || !strings.Contains(w.Body.String(), "Button overlaps") {
		t.Fatalf("board %d", w.Code)
	}
}

func TestEvents(t *testing.T) {
	s := fixedStore(t)
	var out bytes.Buffer
	h := newServer(s, false, &out)
	do(h, "POST", "/api/tickets", "", `{"title":"Say \"hi\"","area":"web"}`)
	do(h, "PATCH", "/api/tickets/1000", "", `{"status":"review","priority":"p2"}`) // p2 is unchanged
	do(h, "PATCH", "/api/tickets/1000", "", `{"title":"New"}`)
	do(h, "PATCH", "/api/tickets/1000", "", `{"status":"review"}`) // no change, no line
	do(h, "POST", "/api/tickets/1000/notes", "", `{"text":"`+strings.Repeat("a", 130)+`\nb"}`)
	do(h, "POST", "/api/tickets/1000/screenshot", "", "\x89PNG\r\n\x1a\n")
	do(h, "PATCH", "/api/tickets/1000", "", `{"status":"bogus"}`) // failed writes print nothing
	if _, err := s.AddNote(1000, "cli", "agent"); err != nil {    // store writes print nothing
		t.Fatal(err)
	}
	want := `EVENT created #1000 bug web p2 "Say \"hi\""
EVENT updated #1000 status=review
EVENT updated #1000 title="New"
EVENT note #1000 "` + strings.Repeat("a", 120) + `"
EVENT screenshot #1000 tickets/assets/1000.png
`
	if out.String() != want {
		t.Fatalf("events:\n%s\nwant:\n%s", out.String(), want)
	}
}

func TestSetAreas(t *testing.T) {
	defer func(a []string) { Areas = a }(Areas)
	setAreas(" ios, api ,,")
	s := fixedStore(t)
	if tk, err := s.Create(NewTicket{Title: "x"}); err != nil || tk.Area != "ios" {
		t.Fatalf("default area: %+v %v", tk, err)
	}
	if _, err := s.Create(NewTicket{Title: "x", Area: "web"}); err == nil {
		t.Fatal("area outside -areas accepted")
	}
	setAreas("")
	if len(Areas) != 2 || Areas[1] != "api" {
		t.Fatalf("empty list changed areas: %v", Areas)
	}
}

func TestCORSAndHosts(t *testing.T) {
	for o, want := range map[string]bool{
		"http://localhost:5173": true, "http://127.0.0.1:8081": true, "http://localhost": true,
		"http://app.myapp.localhost:1355": true, "http://evil.localhost.com": false,
		"https://localhost:5173": false, "http://localhost.evil.com": false, "http://evil.com": false,
		"http://127.0.0.1.nip.io:80": false, "null": false, "http://user@localhost:1": false,
	} {
		if allowedOrigin(o) != want {
			t.Errorf("allowedOrigin(%q) = %v", o, !want)
		}
	}
	tailnetHost = "box.example.ts.net"
	t.Cleanup(func() { tailnetHost = "" })
	for o, want := range map[string]bool{"https://box.example.ts.net:18081": true, "https://evil.ts.net": false, "http://box.example.ts.net": false} {
		if allowedOrigin(o) != want {
			t.Errorf("allowedOrigin(%q) = %v", o, !want)
		}
	}
	if !loopbackHost("box.example.ts.net:18090") || loopbackHost("other.example.ts.net") {
		t.Error("tailnet host check")
	}
	h := newServer(fixedStore(t), false, io.Discard)
	w := do(h, "OPTIONS", "/api/tickets", "http://localhost:5173", "")
	if w.Code != 204 || w.Header().Get("Access-Control-Allow-Origin") != "http://localhost:5173" {
		t.Fatalf("preflight %d %v", w.Code, w.Header())
	}
	w = do(h, "POST", "/api/tickets", "http://evil.com", `{"title":"x"}`)
	if w.Code != 403 || w.Header().Get("Access-Control-Allow-Origin") != "" {
		t.Fatalf("evil origin %d", w.Code)
	}
	r := httptest.NewRequest("GET", "/api/tickets", nil)
	r.Host = "rebind.evil.com:8090"
	rw := httptest.NewRecorder()
	h.ServeHTTP(rw, r)
	if rw.Code != 403 {
		t.Fatalf("rebinding host got %d", rw.Code)
	}
	r.Host = "tickets.myapp.localhost:1355"
	rw = httptest.NewRecorder()
	h.ServeHTTP(rw, r)
	if rw.Code != 200 {
		t.Fatalf("portless host got %d", rw.Code)
	}
}

func TestListenAddrs(t *testing.T) {
	if a, err := listenAddrs(":8090", false); err != nil || len(a) != 2 || a[0] != "127.0.0.1:8090" || a[1] != "[::1]:8090" {
		t.Fatalf("%v %v", a, err)
	}
	for _, bad := range []string{"0.0.0.0:8090", "[::]:8090", "192.168.1.5:8090", "example.com:8090"} {
		if _, err := listenAddrs(bad, false); err == nil {
			t.Errorf("%s accepted without -unsafe-listen-any", bad)
		}
	}
	if a, err := listenAddrs("0.0.0.0:8090", true); err != nil || a[0] != "0.0.0.0:8090" {
		t.Fatalf("unsafe: %v %v", a, err)
	}
	if a, _ := listenAddrs("127.0.0.1:9", false); len(a) != 1 {
		t.Fatalf("loopback ip: %v", a)
	}
}

func TestTraversalAndScreenshots(t *testing.T) {
	s := fixedStore(t)
	h := newServer(s, false, io.Discard)
	writeFile(t, s, "0150-rail.md", agentFile)
	os.WriteFile(filepath.Join(filepath.Dir(s.Dir), "secret.txt"), []byte("secret"), 0o644)

	for _, p := range []string{"/api/tickets/..%2F..%2Fsecret.txt", "/api/tickets/150%2F..", "/api/tickets/-1", "/api/tickets/0150.md", "/api/tickets/1e3"} {
		if w := do(h, "GET", p, "", ""); w.Code == 200 {
			t.Errorf("GET %s returned 200", p)
		}
	}
	if w := do(h, "POST", "/api/tickets/..%2Fx/screenshot", "", "\x89PNG\r\n\x1a\n"); w.Code != 400 {
		t.Errorf("traversal screenshot id: %d", w.Code)
	}
	for _, p := range []string{"/assets/../secret.txt", "/assets/..%2Fsecret.txt", "/assets/%2e%2e/secret.txt"} {
		if w := do(h, "GET", p, "", ""); strings.Contains(w.Body.String(), "secret") && w.Code == 200 {
			t.Errorf("GET %s leaked a file", p)
		}
	}

	png := "\x89PNG\r\n\x1a\nrest"
	if w := do(h, "POST", "/api/tickets/150/screenshot", "", "GIF89a"); w.Code != 400 {
		t.Errorf("non-png: %d", w.Code)
	}
	if w := do(h, "POST", "/api/tickets/150/screenshot", "", png+strings.Repeat("x", maxScreenshot)); w.Code != 413 {
		t.Errorf("oversize: %d", w.Code)
	}
	if w := do(h, "POST", "/api/tickets/777/screenshot", "", png); w.Code != 404 {
		t.Errorf("missing ticket: %d", w.Code)
	}
	if w := do(h, "POST", "/api/tickets/150/screenshot", "", png); w.Code != 200 {
		t.Fatalf("screenshot: %d %s", w.Code, w.Body)
	}
	if b, _ := os.ReadFile(filepath.Join(s.Dir, "assets", "0150.png")); !bytes.Equal(b, []byte(png)) {
		t.Fatal("screenshot not saved at assets/0150.png")
	}
	if !strings.Contains(readFile(t, s, "0150-rail.md"), "\nscreenshot: tickets/assets/0150.png\n") {
		t.Fatal("screenshot field not set")
	}
	if w := do(h, "GET", "/assets/0150.png", "", ""); w.Code != 200 || w.Body.String() != png {
		t.Fatalf("serving screenshot: %d", w.Code)
	}
	// More images get -2, -3... whatever the type; the field keeps the first.
	jpeg, webp := "\xff\xd8\xff\xe0rest", "RIFF\x00\x00\x00\x00WEBPVP8 rest"
	for _, b := range []string{png, jpeg, webp} {
		if w := do(h, "POST", "/api/tickets/150/screenshot", "", b); w.Code != 200 {
			t.Fatalf("image %q: %d %s", b[:4], w.Code, w.Body)
		}
	}
	for name, want := range map[string]string{"0150-2.png": png, "0150-3.jpg": jpeg, "0150-4.webp": webp} {
		if b, _ := os.ReadFile(filepath.Join(s.Dir, "assets", name)); string(b) != want {
			t.Errorf("assets/%s = %q", name, b)
		}
	}
	got := readFile(t, s, "0150-rail.md")
	if !strings.Contains(got, "\nscreenshot: tickets/assets/0150.png\n") {
		t.Fatal("screenshot field changed")
	}
	if !strings.Contains(got, "  indented   line\twith tab\n\n![Screenshot](assets/0150.png)\n\n![Screenshot](assets/0150-2.png)\n\n![Screenshot](assets/0150-3.jpg)\n\n![Screenshot](assets/0150-4.webp)\n\n## Notes\n") {
		t.Fatalf("image links not in the description:\n%s", got)
	}
	tk, _ := s.Get(150)
	if strings.Join(tk.Images, " ") != "assets/0150.png assets/0150-2.png assets/0150-3.jpg assets/0150-4.webp" {
		t.Fatalf("images: %v", tk.Images)
	}
}

func TestSamePage(t *testing.T) {
	for _, c := range []struct {
		a, b string
		want bool
	}{
		{"http://localhost:5173/#/c/x", "http://localhost:5173/?q=1#/c/x", true},
		{"http://localhost:5173/a/", "http://localhost:5173/a", true},
		{"http://localhost:5173/#/c/x", "http://localhost:5173/#/c/y", false},
		{"http://localhost:5173/", "http://localhost:8081/", false},
	} {
		if samePage(c.a, c.b) != c.want {
			t.Errorf("samePage(%q, %q) != %v", c.a, c.b, c.want)
		}
	}
}

func TestCLI(t *testing.T) {
	s := fixedStore(t)
	var out bytes.Buffer
	run := func(args ...string) string {
		out.Reset()
		if err := runCLI(append(args, "--dir", s.Dir), strings.NewReader("from stdin\n"), &out); err != nil {
			t.Fatalf("%v: %v", args, err)
		}
		return out.String()
	}
	if got := run("new", "--title", "CLI ticket", "--type", "chore", "--area", "infra", "--body", "-"); !strings.HasPrefix(got, "created #1000 ") {
		t.Fatalf("new: %q", got)
	}
	run("mv", "1000", "todo")
	run("note", "1000", "picked up", "--by", "agent-x")
	if got := run("ls", "--status", "todo"); !strings.Contains(got, "1000  todo") {
		t.Fatalf("ls: %q", got)
	}
	got := run("show", "1000")
	for _, want := range []string{"status: todo", "source: agent", "from stdin", "(agent-x): picked up"} {
		if !strings.Contains(got, want) {
			t.Fatalf("show missing %q:\n%s", want, got)
		}
	}
	run("mv", "1000", "blocked")
	if got := run("ls", "--status", "blocked"); !strings.Contains(got, "1000  blocked") {
		t.Fatalf("ls blocked: %q", got)
	}
	if c := columns(nil); c[2].Status != "doing" || c[3].Status != "blocked" || c[3].Label != "Blocked" || c[4].Status != "review" {
		t.Fatalf("blocked column not between doing and review: %+v", c)
	}
	if err := runCLI([]string{"mv", "1000", "closed", "--dir", s.Dir}, nil, &out); err == nil {
		t.Fatal("bad status accepted")
	}
}

func multipartReq(t *testing.T, fields map[string]string, files ...string) *http.Request {
	t.Helper()
	var buf bytes.Buffer
	mw := multipart.NewWriter(&buf)
	for k, v := range fields {
		mw.WriteField(k, v)
	}
	for i, f := range files {
		fw, _ := mw.CreateFormFile("image", fmt.Sprintf("IMG_%d.png", i))
		io.WriteString(fw, f)
	}
	mw.Close()
	r := httptest.NewRequest("POST", "/api/notes", &buf)
	r.Host = "localhost:8090"
	r.Header.Set("Content-Type", mw.FormDataContentType())
	return r
}

func TestNotesEndpoint(t *testing.T) {
	s := fixedStore(t)
	var out bytes.Buffer
	h := newServer(s, false, &out)
	send := func(r *http.Request) *httptest.ResponseRecorder {
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		return w
	}
	png, jpeg := "\x89PNG\r\n\x1a\nrest", "\xff\xd8\xff\xe0rest"
	many := make([]string, maxNoteImages+1)
	for i := range many {
		many[i] = png
	}

	// Bad input creates nothing.
	for name, c := range map[string]struct {
		r    *http.Request
		code int
	}{
		"empty":    {multipartReq(t, map[string]string{"title": "  ", "body": "\n"}), 400},
		"gif":      {multipartReq(t, map[string]string{"title": "x"}, "GIF89a"), 400},
		"too big":  {multipartReq(t, map[string]string{"title": "x"}, png+strings.Repeat("x", maxScreenshot)), 413},
		"too many": {multipartReq(t, map[string]string{"title": "x"}, many...), 413},
		"one bad":  {multipartReq(t, map[string]string{"title": "x"}, png, "GIF89a"), 400},
	} {
		if w := send(c.r); w.Code != c.code {
			t.Errorf("%s: %d %s", name, w.Code, w.Body)
		}
	}
	if w := do(h, "POST", "/api/notes", "", `{"title":"x"}`); w.Code != 400 {
		t.Errorf("json: %d", w.Code)
	}
	if ts, _ := s.List(); len(ts) != 0 || out.Len() != 0 {
		t.Fatalf("bad input created tickets: %v %q", ts, out.String())
	}
	if _, err := os.Stat(filepath.Join(s.Dir, "assets")); err == nil {
		t.Fatal("bad input saved images")
	}

	// A Shortcut request: multi-line note, two screenshots.
	w := send(multipartReq(t, map[string]string{"title": "Button overlaps\nOn the settings page."}, png, jpeg))
	if w.Code != 201 || w.Body.String() != "Ticket #1000 created: Button overlaps\n" {
		t.Fatalf("create: %d %q", w.Code, w.Body)
	}
	got := readFile(t, s, "1000-button-overlaps.md")
	for _, want := range []string{"\nstatus: inbox\n", "\nsource: human\n", "\nscreenshot: tickets/assets/1000.png\n",
		"\nOn the settings page.\n\n![Screenshot](assets/1000.png)\n\n![Screenshot](assets/1000-2.jpg)\n"} {
		if !strings.Contains(got, want) {
			t.Fatalf("ticket missing %q:\n%s", want, got)
		}
	}
	for name, want := range map[string]string{"1000.png": png, "1000-2.jpg": jpeg} {
		if b, _ := os.ReadFile(filepath.Join(s.Dir, "assets", name)); string(b) != want {
			t.Errorf("assets/%s = %q", name, b)
		}
	}
	if !strings.Contains(out.String(), "EVENT created #1000 ") || !strings.Contains(out.String(), "EVENT screenshot #1000 tickets/assets/1000-2.jpg") {
		t.Fatalf("events: %q", out.String())
	}

	// An image alone gets a placeholder title; text alone needs no image.
	if w := send(multipartReq(t, nil, png)); w.Code != 201 || !strings.Contains(w.Body.String(), "#1001 created: Screenshot") {
		t.Fatalf("image only: %d %q", w.Code, w.Body)
	}
	if w := send(multipartReq(t, map[string]string{"body": "Body only\nmore"})); w.Code != 201 || !strings.Contains(w.Body.String(), "#1002 created: Body only") {
		t.Fatalf("text only: %d %q", w.Code, w.Body)
	}

	// Browsers from other sites stay out; the phone page names the tailnet address.
	r := multipartReq(t, map[string]string{"title": "x"})
	r.Header.Set("Origin", "https://evil.example")
	if w := send(r); w.Code != 403 {
		t.Fatalf("foreign origin: %d", w.Code)
	}
	defer func(h string) { tailnetHost = h }(tailnetHost)
	tailnetHost = "box.tail.ts.net"
	r = httptest.NewRequest("GET", "/phone", nil)
	r.Host = "box.tail.ts.net:18090"
	if w := send(r); w.Code != 200 || !strings.Contains(w.Body.String(), "<code>https://box.tail.ts.net:18090/api/notes</code>") {
		t.Fatalf("phone page: %d %s", w.Code, w.Body)
	}
}
