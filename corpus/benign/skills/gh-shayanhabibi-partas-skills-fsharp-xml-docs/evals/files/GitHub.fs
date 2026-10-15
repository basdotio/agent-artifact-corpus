module Partas.GitNet.GitHub

open System.Text.Encodings.Web
open LibGit2Sharp.FSharp

let private remote = function GitHubRemote remote -> remote

let urlRoot =
    remote
    >> _.Url
    >> fun url ->
        if url.EndsWith(".git")
        then url[..url.Length - 5]
        else url
open Partas.Tools.SepochSemver
/// Creates urls from a github remote or urlroot.
type UrlFactory(urlRoot: string) =
    // We include all delimiters, to proof against any changes to the spec.
    let encoder: string -> string =
        String.collect (function
            | Spec.scopeOpeningDelimiter -> encodedScopeOpeningDelimiter
            | Spec.scopeClosingDelimiter -> encodedScopeClosingDelimiter
            | Spec.sepochOpeningDelimiter -> string encodedSepochOpeningDelimiter
            | Spec.sepochClosingDelimiter -> string encodedSepochClosingDelimiter
            | c -> string c
            )
    let compareBase = urlRoot + "/compare/"
    let commitBase = urlRoot + "/commit/"
    
    member this.Create(commit: Commit) =
        commit
        |> Commit.sha
        |> sprintf "%s%s" commitBase
    member this.Create(commit: Commit, commit2: Commit) =
        let makeSha = Commit.sha >> _.Substring(0,7)
        (makeSha commit, makeSha commit2)
        ||> sprintf "%s%s...%s" compareBase
    member this.Create(tag: Tag) =
        tag
        |> Tag.name
        |> encoder
        |> sprintf "%s%s...HEAD" compareBase
    member this.Create(commit: GitNetCommit) =
        this.Create(commit |> GitNetCommit.git)
    member this.Create(commit: GitNetCommit, commit2: GitNetCommit) =
        this.Create(commit |> GitNetCommit.git, commit2 |> GitNetCommit.git)
    member this.Create(tag: GitNetTag) =
        this.Create(tag |> GitNetTag.git)
    member this.Create(tag: Tag, tag2: Tag) =
        (tag
         |> Tag.name
         |> encoder,
         tag2
         |> Tag.name
         |> encoder )
        ||> sprintf "%s%s...%s" compareBase
    member this.Create(tag: GitNetTag, tag2: GitNetTag) =
        this.Create(tag |> GitNetTag.git, tag2 |> GitNetTag.git)
    member this.CreateCommit(sha: string) =
        sha |> sprintf "%s%s" commitBase
    member this.CreateAuthor(author: string) =
        author |> sprintf "https://github.com/%s"
    new (ghRemote: GitHubRemote) = UrlFactory(urlRoot ghRemote)

module UrlFactory =
    module Author =
        let fromString (factory: UrlFactory) author = factory.CreateAuthor(author)
    module Commit =
        let fromSha (factory: UrlFactory) sha = factory.CreateCommit(sha)
        let fromGitNetCommit (factory: UrlFactory) (commit: GitNetCommit) = factory.Create(commit)
        let fromCommit (factory: UrlFactory) (commit: Commit) = factory.Create(commit)
