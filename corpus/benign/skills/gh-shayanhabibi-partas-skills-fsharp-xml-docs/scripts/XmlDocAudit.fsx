// XML-doc audit for F# sources. Requires FSharp.Compiler.Service to be referenced before `#load`:
// `audit.fsx` does that for `dotnet fsi`; SKILL.md shows the SageFs form.

open System
open System.IO
open System.Xml.Linq
open FSharp.Compiler.CodeAnalysis
open FSharp.Compiler.Diagnostics
open FSharp.Compiler.Syntax
open FSharp.Compiler.Text
open FSharp.Compiler.Xml
open Microsoft.FSharp.Reflection

type Finding =
    { File: string
      Line: int
      Kind: string
      Message: string }

/// <summary>Tags from the Microsoft F# XML-doc reference plus the Partas additions.</summary>
let allowedTags =
    set [ "summary"; "remarks"; "param"; "typeparam"; "returns"; "exception"; "seealso"
          "para"; "code"; "paramref"; "typeparamref"; "c"; "see"
          "example"; "include" ]

let checker = lazy (FSharpChecker.Create())

let private sourceOf (path: string) = SourceText.ofString (File.ReadAllText path)

/// <summary>Every non-empty doc on a module, type, member, union case or record field.</summary>
/// <remarks>
/// Parses against FCS 43.12 (.NET 10 SDK) and 43.13 (.NET 11 SDK). Record fields match by position:
/// the field is <c>recordFields</c> in 43.12 and <c>recordFieldsAndSpreads</c> in 43.13.
/// </remarks>
let docsOf (input: ParsedInput) : XmlDoc list =
    let doc (x: PreXmlDoc) = x.ToXmlDoc(false, None)
    let fieldDoc (o: obj) =
        match o with
        | :? SynField as f -> let (SynField(xmlDoc = x)) = f in [ doc x ]
        | _ -> []
    let simpleRepr (repr: SynTypeDefnSimpleRepr) =
        match repr with
        | SynTypeDefnSimpleRepr.Union(unionCases = cs) -> cs |> List.map (fun (SynUnionCase(xmlDoc = x)) -> doc x)
        | SynTypeDefnSimpleRepr.Record(_, fs, _) ->
            fs |> List.collect (fun f ->
                match box f with
                | :? SynField -> fieldDoc (box f)
                | o when FSharpType.IsUnion(o.GetType(), true) ->
                    snd (FSharpValue.GetUnionFields(o, o.GetType(), true)) |> List.ofArray |> List.collect fieldDoc
                | _ -> [])
        | _ -> []
    let binding (SynBinding(xmlDoc = x)) = doc x
    let members (ms: SynMemberDefn list) =
        ms |> List.collect (function
            | SynMemberDefn.Member(memberDefn = b) -> [ binding b ]
            | SynMemberDefn.AbstractSlot(slotSig = SynValSig(xmlDoc = x)) -> [ doc x ]
            | SynMemberDefn.AutoProperty(xmlDoc = x) -> [ doc x ]
            | SynMemberDefn.ImplicitCtor(xmlDoc = x) -> [ doc x ]
            | _ -> [])
    let typeDefn (SynTypeDefn(typeInfo = SynComponentInfo(xmlDoc = x); typeRepr = repr; members = ms)) =
        let inner =
            match repr with
            | SynTypeDefnRepr.ObjectModel(members = m) -> members m
            | SynTypeDefnRepr.Simple(r, _) -> simpleRepr r
            | _ -> []
        doc x :: inner @ members ms
    let rec decls (ds: SynModuleDecl list) =
        ds |> List.collect (function
            | SynModuleDecl.Let(bindings = bs) -> bs |> List.map binding
            | SynModuleDecl.NestedModule(moduleInfo = SynComponentInfo(xmlDoc = x); decls = inner) -> doc x :: decls inner
            | SynModuleDecl.Types(typeDefns = tds) -> tds |> List.collect typeDefn
            | _ -> [])
    let memberSig = function
        | SynMemberSig.Member(memberSig = SynValSig(xmlDoc = x)) -> [ doc x ]
        | _ -> []
    let typeDefnSig (SynTypeDefnSig(typeInfo = SynComponentInfo(xmlDoc = x); typeRepr = repr; members = ms)) =
        let inner =
            match repr with
            | SynTypeDefnSigRepr.ObjectModel(memberSigs = m) -> m |> List.collect memberSig
            | SynTypeDefnSigRepr.Simple(r, _) -> simpleRepr r
            | _ -> []
        doc x :: inner @ (ms |> List.collect memberSig)
    let rec sigDecls (ds: SynModuleSigDecl list) =
        ds |> List.collect (function
            | SynModuleSigDecl.Val(valSig = SynValSig(xmlDoc = x)) -> [ doc x ]
            | SynModuleSigDecl.NestedModule(moduleInfo = SynComponentInfo(xmlDoc = x); moduleDecls = inner) -> doc x :: sigDecls inner
            | SynModuleSigDecl.Types(types = tds) -> tds |> List.collect typeDefnSig
            | _ -> [])
    let all =
        match input with
        | ParsedInput.ImplFile f ->
            f.Contents |> List.collect (fun (SynModuleOrNamespace(decls = ds; xmlDoc = x)) -> doc x :: decls ds)
        | ParsedInput.SigFile f ->
            f.Contents |> List.collect (fun (SynModuleOrNamespaceSig(decls = ds; xmlDoc = x)) -> doc x :: sigDecls ds)
    all |> List.filter (fun d -> not d.IsEmpty)

let private attr (e: XElement) (name: string) =
    match e.Attribute(XName.Get name) with
    | null -> None
    | a -> Some a.Value

/// <summary>
/// Problems with each <c>include</c> in a doc: a missing or malformed file or a <c>path</c> that
/// selects nothing, at the include's line; included fragments outside the tag conventions, at the
/// fragment's line in the XML file.
/// </summary>
/// <remarks>
/// <c>file</c> resolves against the source file's directory. A fragment shared by many includes yields
/// identical findings, which <c>auditWith</c> collapses. An include that resolves is never reported:
/// expansion before .NET 11 is out of the audit's scope.
/// </remarks>
let includeFindings (file: string) (docLine: int) (root: XElement) : Finding list =
    let dir = Path.GetDirectoryName(Path.GetFullPath file)
    [ for inc in root.Descendants(XName.Get "include") do
          let line = docLine + (inc :> System.Xml.IXmlLineInfo).LineNumber - 1
          let at kind message = { File = file; Line = line; Kind = kind; Message = message }
          match attr inc "file", attr inc "path" with
          | Some rel, Some xpath ->
              let target = Path.Combine(dir, rel)
              match (try Ok(XDocument.Load(target, LoadOptions.SetLineInfo)) with e -> Error e) with
              | Error(:? FileNotFoundException | :? DirectoryNotFoundException) ->
                  at "include-unresolved" (sprintf "file %s does not exist" rel)
              | Error e -> at "include-unresolved" (sprintf "%s is not well-formed XML: %s" rel e.Message)
              | Ok xml ->
                  match (try Ok(List.ofSeq (System.Xml.XPath.Extensions.XPathSelectElements(xml, xpath))) with e -> Error e.Message) with
                  | Error e -> at "include-unresolved" (sprintf "path %s cannot select elements: %s" xpath e)
                  | Ok [] -> at "include-unresolved" (sprintf "path %s selects nothing in %s" xpath rel)
                  | Ok fragments ->
                      let inXml (e: XElement) kind message =
                          { File = Path.GetFullPath target; Line = (e :> System.Xml.IXmlLineInfo).LineNumber
                            Kind = kind; Message = message }
                      for f in fragments do
                          for e in Seq.append [ f ] (f.Descendants()) do
                              if e.Name.LocalName = "code" && (attr e "lang").IsNone then
                                  inXml e "code-lang" "<code> in an included fragment has no lang attribute"
                              if Seq.isEmpty (e.Ancestors(XName.Get "code")) && not (allowedTags.Contains e.Name.LocalName) then
                                  inXml e "non-standard-tag" (sprintf "<%s> in an included fragment is outside the tag set" e.Name.LocalName)
          | _ -> at "include-unresolved" "<include> needs both file and path attributes" ]

/// <summary>Findings the compiler never reports: shape and tag conventions.</summary>
let conventionFindings (file: string) (d: XmlDoc) : Finding list =
    let at kind message = { File = file; Line = d.Range.StartLine; Kind = kind; Message = message }
    let text = String.Join("\n", d.UnprocessedLines)
    if not (text.TrimStart().StartsWith "<") then
        [ at "bare-doc" "doc has no <summary>; bare /// text is summary-only and unchecked" ]
    else
        match (try Some(XElement.Parse("<doc>" + text + "</doc>", LoadOptions.SetLineInfo)) with _ -> None) with
        | None -> [] // FS3390 reports malformed XML with a better position.
        | Some root ->
            let children (n: string) = root.Elements(XName.Get n) |> List.ofSeq
            let outsideCode (e: XElement) = e.Ancestors(XName.Get "code") |> Seq.isEmpty
            [ if List.isEmpty (children "summary") then
                  at "missing-summary" "doc has tags but no <summary>"
              for p in children "param" @ children "typeparam" do
                  if String.IsNullOrWhiteSpace p.Value then
                      at "empty-param" (sprintf "<%s name=\"%s\"> is empty" p.Name.LocalName (defaultArg (attr p "name") "?"))
              for s in children "summary" @ children "returns" do
                  if String.IsNullOrWhiteSpace s.Value && Seq.isEmpty (s.Elements()) then
                      at "empty-tag" (sprintf "<%s> is empty" s.Name.LocalName)
              for c in root.Descendants(XName.Get "code") do
                  if (attr c "lang").IsNone then
                      at "code-lang" "<code> has no lang attribute; use lang=\"fsharp\""
              for e in root.Descendants() do
                  if outsideCode e && not (allowedTags.Contains e.Name.LocalName) then
                      at "non-standard-tag" (sprintf "<%s> is outside the Microsoft/Partas tag set" e.Name.LocalName)
              yield! includeFindings file d.Range.StartLine root ]

/// <summary>FS3390 diagnostics: malformed XML, unknown and undocumented <c>param</c> names.</summary>
/// <remarks>
/// Type-checks the file alone, as a script. Unresolved project references do not suppress FS3390,
/// so the result matches a project build for these warnings.
/// </remarks>
let compilerFindings (file: string) : Finding list =
    let source = sourceOf file
    let asScript = file + ".fsx"
    let options, _ =
        checker.Value.GetProjectOptionsFromScript(asScript, source, otherFlags = [| "--warnon:3390" |])
        |> Async.RunSynchronously
    match checker.Value.ParseAndCheckFileInProject(asScript, 0, source, options) |> Async.RunSynchronously with
    | _, FSharpCheckFileAnswer.Succeeded r ->
        r.Diagnostics
        |> Array.filter (fun d -> d.ErrorNumber = 3390)
        |> Array.map (fun d -> { File = file; Line = d.StartLine; Kind = "FS3390"; Message = d.Message })
        |> List.ofArray
    | _, FSharpCheckFileAnswer.Aborted -> [ { File = file; Line = 0; Kind = "aborted"; Message = "type-check aborted" } ]

/// <summary>
/// <c>max_line_length</c> from the nearest <c>.editorconfig</c> section matching F# files, walking
/// up from the file until a <c>root = true</c> file; 150 when none sets it.
/// </summary>
let lineWidth (file: string) : int =
    let fsSection (h: string) = h = "*" || h.Contains "fs"
    let rec walk (dir: DirectoryInfo) =
        if isNull dir then 150
        else
            let cfg = Path.Combine(dir.FullName, ".editorconfig")
            let lines = if File.Exists cfg then File.ReadAllLines cfg else [||]
            let setting (key: string) =
                lines
                |> Array.fold (fun (inFs, found) (l: string) ->
                    let t = l.Trim()
                    if t.StartsWith "[" then fsSection (t.Trim('[', ']')), found
                    elif inFs && t.StartsWith key && t.Contains "=" then inFs, Some(t.Split('=').[1].Trim())
                    else inFs, found) (true, None)
                |> snd
            match setting "max_line_length" |> Option.bind (fun v -> match Int32.TryParse v with | true, n -> Some n | _ -> None) with
            | Some n -> n
            | None when lines |> Array.exists (fun l -> l.Replace(" ", "").ToLowerInvariant() = "root=true") -> 150
            | None -> walk dir.Parent
    walk (FileInfo file).Directory

/// <summary><c>///</c> lines wider than <c>lineWidth</c>, outside <c>code</c> blocks.</summary>
/// <remarks>A line whose text is one unbreakable token, such as a lone cref tag, is exempt.</remarks>
let longLines (file: string) : Finding list =
    let limit = lineWidth file
    let unbreakable (text: string) =
        let outsideQuotes = Text.RegularExpressions.Regex.Replace(text, "\"[^\"]*\"", "\"\"")
        not (outsideQuotes.Trim().Contains " " && outsideQuotes.Trim().Split(' ').Length > 2)
    File.ReadAllLines file
    |> Array.mapi (fun i l -> i + 1, l)
    |> Array.fold (fun (inCode, acc) (n, l: string) ->
        let t = l.Trim()
        let isDoc = t.StartsWith "///"
        let body = if isDoc then t.Substring(3).Trim() else ""
        let opens = isDoc && body.Contains "<code"
        let closes = isDoc && body.Contains "</code>"
        let inCodeNow = inCode || opens
        let acc =
            if isDoc && not inCodeNow && l.TrimEnd().Length > limit && not (unbreakable body) then
                { File = file; Line = n; Kind = "long-line"; Message = sprintf "doc line is %d chars; limit %d" (l.TrimEnd().Length) limit } :: acc
            else acc
        (isDoc && inCodeNow && not closes), acc) (false, [])
    |> snd
    |> List.rev

let conventionFindingsOf (file: string) : Finding list =
    let options = { FSharpParsingOptions.Default with SourceFiles = [| file |] }
    let parsed = checker.Value.ParseFile(file, sourceOf file, options) |> Async.RunSynchronously
    (docsOf parsed.ParseTree |> List.collect (conventionFindings file)) @ longLines file

/// <summary>Convention findings plus FS3390, sorted by line.</summary>
/// <param name="compiler">Include FS3390; costs a type-check per file.</param>
/// <param name="file">An <c>.fs</c> or <c>.fsi</c> path.</param>
let auditFile (compiler: bool) (file: string) : Finding list =
    let fs3390 = if compiler then compilerFindings file else []
    conventionFindingsOf file @ fs3390 |> List.sortBy (fun f -> f.Line, f.Kind)

/// <summary>
/// True for a file carrying an <c>auto-generated</c> or <c>Generated by</c> header in its first
/// ten lines, a <c>.g.fs</c> name, or a path through <c>fable_modules</c> or <c>Generated</c>.
/// </summary>
let isGenerated (file: string) : bool =
    let segments = file.Split([| '\\'; '/' |])
    let header = File.ReadLines file |> Seq.truncate 10 |> String.concat "\n"
    file.EndsWith ".g.fs"
    || segments |> Array.exists (fun s -> s = "fable_modules" || s = "Generated")
    || header.Contains("auto-generated", StringComparison.OrdinalIgnoreCase)
    || header.Contains("Generated by", StringComparison.OrdinalIgnoreCase)

/// <summary>F# sources under each path; <c>bin</c>, <c>obj</c> and <c>node_modules</c> are skipped.</summary>
/// <remarks>A path named directly is always included, generated or not.</remarks>
/// <param name="includeGenerated">Keep generated files found while walking a directory.</param>
/// <param name="paths">Files and directories to audit.</param>
let sourcesUnder (includeGenerated: bool) (paths: string seq) : string list =
    let skipped (f: string) =
        f.Split([| '\\'; '/' |]) |> Array.exists (fun s -> s = "bin" || s = "obj" || s = "node_modules")
    [ for p in paths do
          if File.Exists p then Path.GetFullPath p
          elif Directory.Exists p then
              for f in Directory.EnumerateFiles(p, "*.fs*", SearchOption.AllDirectories) do
                  if (f.EndsWith ".fs" || f.EndsWith ".fsi") && not (skipped f) && (includeGenerated || not (isGenerated f)) then
                      Path.GetFullPath f ]

/// <summary>Audits every source under <c>paths</c>; generated files are skipped unless <c>includeGenerated</c>.</summary>
let auditWith (compiler: bool) (includeGenerated: bool) (paths: string seq) : Finding list =
    sourcesUnder includeGenerated paths
    |> List.toArray
    |> Array.Parallel.collect (auditFile compiler >> List.toArray)
    |> Array.distinct
    |> List.ofArray

/// <summary>Audits hand-written sources under <c>paths</c>.</summary>
let audit (compiler: bool) (paths: string seq) : Finding list = auditWith compiler false paths

/// <summary>Every doc block in a file with its line range and the declaration line that follows it.</summary>
/// <remarks>Lets a reviewer read all docs without paging through the code between them.</remarks>
let docListing (file: string) : string =
    let lines = File.ReadAllLines file
    let options = { FSharpParsingOptions.Default with SourceFiles = [| file |] }
    let parsed = checker.Value.ParseFile(file, sourceOf file, options) |> Async.RunSynchronously
    let declAfter (endLine: int) =
        lines
        |> Seq.skip (min endLine lines.Length)
        |> Seq.tryFind (fun l -> let t = l.Trim() in t <> "" && not (t.StartsWith "[<"))
        |> Option.map (fun l -> l.Trim())
        |> Option.defaultValue ""
    docsOf parsed.ParseTree
    |> List.sortBy (fun d -> d.Range.StartLine)
    |> List.map (fun d ->
        let body = d.UnprocessedLines |> Array.map (fun l -> "    " + l.Trim()) |> String.concat "\n"
        sprintf "L%d-%d: %s\n%s" d.Range.StartLine d.Range.EndLine (declAfter d.Range.EndLine) body)
    |> List.append [ "== " + file ]
    |> String.concat "\n"

/// <summary>
/// Code lines that differ between <c>original</c> and <c>edited</c>, ignoring <c>///</c> lines, blank
/// lines, a byte-order mark and line endings. Empty means the edit was comment-only.
/// </summary>
let codeChanges (original: string) (edited: string) : Finding list =
    let code (f: string) =
        File.ReadAllLines f
        |> Array.mapi (fun i l -> i + 1, l.TrimStart('﻿').TrimEnd())
        |> Array.filter (fun (_, l) -> l <> "" && not (l.TrimStart().StartsWith "///"))
    let a, b = code original, code edited
    let removed = a |> Array.filter (fun (_, l) -> not (b |> Array.exists (snd >> (=) l)))
    let added = b |> Array.filter (fun (_, l) -> not (a |> Array.exists (snd >> (=) l)))
    [ for n, l in removed -> { File = original; Line = n; Kind = "code-removed"; Message = l.Trim() }
      for n, l in added -> { File = edited; Line = n; Kind = "code-added"; Message = l.Trim() } ]

/// <summary>One <c>file(line): kind: message</c> line per finding, then a count by kind.</summary>
let report (findings: Finding list) : string =
    let lines = findings |> List.map (fun f -> sprintf "%s(%d): %s: %s" f.File f.Line f.Kind f.Message)
    let counts = findings |> List.countBy (fun f -> f.Kind) |> List.map (fun (k, n) -> sprintf "  %s: %d" k n)
    String.Join("\n", lines @ [ sprintf "%d finding(s)" findings.Length ] @ counts)
