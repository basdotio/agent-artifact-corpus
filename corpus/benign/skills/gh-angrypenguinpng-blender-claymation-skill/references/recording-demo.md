# Recording a demo of the result (macOS + OBS, optional)

This makes a clean screen recording of the finished film playing in the Claude desktop app, with the
chat on the left and the player artifact on the right. Record **only the final playback**, never the build.

## One-time OBS setup

1. OBS → Tools → WebSocket Server Settings: enable the server and copy the password.
   Export it as `OBS_WS_PASSWORD` (never write it into files).
2. Create a scene named `Claude App Demo` with a **macOS Screen Capture** source named
   `Claude App Capture`. Set Method to **Application Capture** and Application to **Claude**. Application
   capture follows the app even when windows move, and it leaves other apps' windows out.
3. Grant OBS Screen Recording permission (System Settings → Privacy & Security).

`scripts/obs.js` needs Node 22+ (built-in WebSocket) or `npm i ws` in `scripts/`.

## Before the take

- Collapse the app's sidebar so chat history isn't visible (`set_sidebar_collapsed` if you have it,
  otherwise ask the user).
- Open the artifact beside the chat and make sure the film is playing. A maximized window with a wide
  artifact pane looks best. Ask the user to drag the pane if you can't.
- The chat should end on the finished result. Scroll or stop typing before you record.

## The take

```bash
OBS_WS_PASSWORD=... $SKILL/scripts/record_window.sh 45 out/demo.mp4 Claude
```

The script:

1. Reads the window's bounds.
2. Crops the OBS source to them and scales to fit the canvas.
3. Records for N seconds.
4. Crops the pillarbox or letterbox off, so the output is the window edge to edge.
5. Drops audio and moves the raw OBS file next to the output.

The player loops, so record a little longer than the films and trim to where the first film starts.
Find the cut point by pulling single frames around the transition:

```bash
for t in 5 6 7; do ffmpeg -loglevel error -ss $t -i out/demo.mp4 -frames:v 1 /tmp/t$t.png; done
ffmpeg -ss 6.2 -i out/demo.mp4 -t 40 -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart out/demo_cut.mp4
```
