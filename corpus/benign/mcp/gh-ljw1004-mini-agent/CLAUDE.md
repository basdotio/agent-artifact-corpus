# Mini_agent

## File structure and development

Files:
- mini_agent.py -- main entrypoint for agentic loop
- core_tools.py -- MCP server with tools, hooks and system prompts
- typedefs.py -- type definitions
- utils.py -- common helpers used by agentic loop
- test/*.py -- various unit tests
- test/sample_data -- directory with immutable sample data

Codebase:
- uses litellm library, to make calls to different LLMs in a uniform way
- uses watchdog, to be able to notify about file changes
- uses mcp, for some common tool definitions
- uses pyright, for typechecking in strict mode
- uses pytest, for testing

Running and testing:
- Set up venv and install dependencies:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
- On subsequent use, just `source venv/bin/activate`.
- Run the agentic loop:
```
OPENAI_API_KEY=redacted    ./mini_agent.py --model gpt-4.1
GEMINI_API_KEY=redacted    ./mini_agent.py --model gemini/gemini-2.5-pro
ANTHROPIC_API_KEY=redacted ./mini_agent.py --model anthropic/claude-sonnet-4-20250514
```
- Test the mcp server:
   - `npx @modelcontextprotocol/inspector --cli ./core_tools.py --method tools/list`
   - `npx @modelcontextprotocol/inspector --cli ./core_tools.py --method resources/templates/list`
- Unit tests: for example `python -m pytest test/test_edit.py`



## Codebase style and guidelines

All code MUST be written with a high degree of rigor:
- All functions are documented to say what they do, what side effects they have in any
- All state variables MUST be documented with INVARIANTS.
  Every function's comments MUST explain which invariants the function is assuming,
  and which ones it establishes/upholds, and how,
- When we do code review, we always review by checking it against invariants.
- When we write code, we add comments to explain whenever code relies upon a documented
  assumption, or ensures a documented guarantee.

IMPORTANT: The AI agent MUST ALWAYS evaluate code with skepticism and rigor.

- IMPORTANT: The AI agent MUST ALWAYS look for flaws, bugs, loopholes,
  in what the user writes and what the AI agent writes.
- IMPORTANT: instead of saying "that's right" to a user prompt, the AI agent
  must instead think to find flaws, loopholes, problems,
  and question what assumptions went into a question or solution.
- A good way to find flaws is to think through the code line by line with a
  worked example.

Example: instead of saying "That's right!" say "This approach seems to
avoid {problem-we-identified}, but has a flaw is that it is non-idiomatic,
and it hasn't considered the edge case of {counter-example}."

Coding style: All code must also be clean, documented and minimal. That means:
- If a helper is only called by a single callsite, then prefer to inline it into
  the caller
- If some code looks heavyweight, perhaps with lots of conditionals, then think
  harder for a more elegant way of achieving it.
- Code should have comments, and functions should have docstrings.
  The best comments are ones that introduce invariants, or prove that invariants
  are being upheld, or indicate which invariants the code relies upon.
- Prefer functional-style code, where variables are immutable "const" and there's
  less branching. Prefer to use ternary expressions "x if b else y" rather than
  separate lines and assignments, if doing so allows for immutable variables.

## Testing conventions

IMPORTANT: Tests must NEVER modify or delete files in the working directory.
- The test/sample_data directory contains permanent test fixtures that must NEVER be deleted
- Tests must NEVER alter the contents of any file in the working directory
- Tests can ONLY create temporary files in the system tmp directory (e.g., using Python's tempfile module)
- Any test that needs to create files should use tempfile.mkdtemp() or similar
- Any test cleanup should only remove files that the test itself created in tmp directories

Here is an example of rigorous quality code. It covers all the signs of rigor:
- was the code as simple as could be?
- does the code work all edge cases, and does it include proof/evidence
  that we identified all possible edge cases and that it handled them all?
- were the classes and data-structures the right fit?
- was logic abstracted out into functions at the right time, not too much,
  not too little?
- for mutable state, were the correct invariants identified, established,
  maintained, proved
- did we correctly identify the big-O issues and come up with suitable solutions?
- was async concurrency and re-entrancy handled correctly

```
/**
 * This function is like fetch(), but it deals with OAuth2 code-flow authentication:
 * - It sends a header "Authorization: Bearer <access_token>" using the access_token in localStorage
 * - If this fails with 401 Unauthorized, it attempts to refresh the access token and try again.
 * - If someone else is busy doing a refresh, it waits for the refresh to finish before trying.
 *
 * <quality>Here we discuss invariants, including the mutable state 'access_token'</quality>
 * INVARIANT: even with are multiple async callers, only one will attempt to refresh the access token at a time
 * INVARIANT: if refreshing fails, then access_token and refresh_token will be cleared, and all underway and
 *            future calls will fail
 *
 * One parameter differs from fetch(): `retryOn429` is called in response to 429 Too Many Requests;
 * if it returns true then we try again, and if it returns false then we give up.
 *
 * <quality>Here we demonstrate that we've considered every possible edge case</quality>
 * The return value is either a successful response, or an error. Two special errors will only occur under
 * specific circumstances: 401 Unauthorized only happens if our attempt to refresh failed (or another async
 * flow attempted the refresh and it failed); and 429 Too Many Requests only happens if retryOn429 returned false.
 */
export async function authFetch(url: string, retryOn429: () => boolean, options?: RequestInit): Promise<Response> {
    // <quality>Abstracted out this function at the right time, because it had enough logic that shouldn't be re-written</quality>
    // <quality>Code is as simple as can be: this helper has no callers other than authFetch, so we inline it.</quality>
    function f(): Promise<Response> {
        const accessToken = localStorage.getItem('access_token');
        if (!accessToken) return Promise.resolve(new Response('Unauthorized: no access_token', { status: 401, statusText: 'Unauthorized' }));
        options = options ? { ...options } : {};
        options.headers = new Headers(options.headers);
        options.headers.set('Authorization', `Bearer ${accessToken}`);
        return myFetch(url, retryOn429, options);
    }

    const CLIENT_ID = localStorage.getItem('client_id');
    if (!CLIENT_ID) return Promise.resolve(new Response('Bad request: no client_id', { status: 400, statusText: 'Bad Request' }));
    if (AUTH_REFRESH_SIGNAL.willSomeoneSignal) await AUTH_REFRESH_SIGNAL.wait();
    const r = await f();
    if (r.status !== 401) return r;

    // 401 Unauthorized.
    <quality>We are considering re-entrancy, with the possibility that a concurrent caller will be the one who refreshes</quality>
    if (AUTH_REFRESH_SIGNAL.willSomeoneSignal) {
        await AUTH_REFRESH_SIGNAL.wait();  // wait until they finished their refresh
        return f();
    }
    // We'll do the refresh
    AUTH_REFRESH_SIGNAL.willSomeoneSignal = true;
    try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) return Promise.resolve(new Response('Unauthorized: no refresh_token', { status: 401, statusText: 'Unauthorized' }));
        const url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token';
        const r = await myFetch(url, noRetryOn429, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                client_id: CLIENT_ID,
                refresh_token: refreshToken,
                grant_type: 'refresh_token',
                scope: 'files.readwrite offline_access',
            }).toString()
        });
        if (!r.ok) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            return r;
        }
        const tokenData = await r.json();
        localStorage.setItem('access_token', tokenData.access_token);
        localStorage.setItem('refresh_token', tokenData.refresh_token);
    } catch (e) {
        return errorResponse(url, e);
    } finally {
        AUTH_REFRESH_SIGNAL.signal();
    }
    return f();
}
```


## AI assistant interaction rules

- IMPORTANT. The AI assistant MUST give advice only (no code edits) in response to user questions.
  Example: "what's wrong" or "what's the correct way" or "how could we fix" are
  brainstorming questions and should only result in advice.
  On the other hand, "please fix it" or "please implement" or "go ahead" are
  explicit user asks and should result in code edits.
- Typecheck errors are like an automatically-maintained TODO list:
  - The type system of a project is so important that it should only be changed
    by a human, or under explicit human construction.
    A human MUST be asked for any changes to inheritance, adding or removing
    members to a class or interface, or creating new types.
  - If the AI assistant made changes that revealed pre-existing typecheck errors, then
    it must leave them for now and the user will decide later when
    and how to address them.
  - If the AI assistant made changes where there were errors due to a mismatch between
    new code and existing code, then it should again leave them for the user
    to decide.
  - If the AI assistant made changes where the new code has typecheck errors within itself,
    then it should address them immedaitely.
