# Chime Gemini CLI Extension

Get audible notifications from your Gemini CLI.

## Installation

Install the Chime extension by running the following command from your terminal:

```
gemini extensions install https://github.com/rebekahx23/chime
```

# OR pin to your tagged release
```
gemini extensions install https://github.com/rebekahx23/chime --ref v0.1.6
```

Install Gemini CLI to try it out [Gemini CLI installation instructions](https://github.com/google-gemini/gemini-cli/blob/main/README.md#installation).

This extension provides a `chime` tool that plays a simple completion chime. This is used to notify you when Gemini has finished a task, is waiting for your input, or has completed a long-running operation.

## Usage

The extension works in two ways:

### 1. Automatic Chimes

Gemini will automatically play a chime to notify you of certain events:

*   **Task Completion:** A chime will play when Gemini has finished a task.
*   **User Input Required:** A chime will play when Gemini is waiting for your confirmation or input.
*   **Long-Running Tasks:** A chime will play when a long-running task has been completed.

### 2. Manual Chime

You can manually trigger a chime by using the following command:

```
/chime
```

or

add `chime` after your prompt to trigger the chime sound.

## Muting the Chime

To mute the chime, you can set the `GEMINI_CHIME_MUTE` environment variable to `1`.

```
export GEMINI_CHIME_MUTE=1
```

## Limitations

The chime extension works best for actions that do not require user confirmation. It functions as a "prehook", meaning the chime will sound *before* the action is executed. This is because there is currently no official "hooks" system in the Gemini CLI. For more information, see this feature request: [Implement a Hooks System for Custom Automation and Workflow Integration](https://github.com/google-gemini/gemini-cli/issues/2779).
