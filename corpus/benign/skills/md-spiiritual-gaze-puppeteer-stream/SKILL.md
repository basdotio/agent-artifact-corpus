---
name: puppeteer-stream
description: How to use the puppeteer-stream library and how to integrate it with a discord streaming bot
---

# puppeteer-stream

An Extension for Puppeteer to retrieve audio and/or video streams of a page

<a href="https://www.npmjs.com/package/puppeteer-stream">
	<img src="https://img.shields.io/npm/v/puppeteer-stream">
</a>

## Recording video/audio from video conferencing calls

If you’re looking to use this repo to retrieve video or audio streams from meeting platforms like Zoom, Google Meet, Microsoft Teams, consider checking out [Recall.ai](https://www.recall.ai/?utm_source=github&utm_medium=sponsorship&utm_campaign=puppeteer-stream), an API for meeting recording.

## Installation

```
npm i puppeteer-stream
# or "yarn add puppeteer-stream"
```

## Usage

### Import

For ES5

```js
const { launch, getStream } = require("puppeteer-stream");
```

or for ES6

```js
import { launch, getStream } from "puppeteer-stream";
```

### Launch

The method [`launch(options)`](https://github.com/SamuelScheit/puppeteer-stream/blob/main/src/PuppeteerStream.ts#L16) takes additional to the original [puppeteer launch function](https://github.com/puppeteer/puppeteer/blob/puppeteer-v20.7.2/docs/api/puppeteer.puppeteernode.launch.md), the following options

```ts
{
	allowIncognito?: boolean, // to be able to use incognito mode
	startDelay?: number, // to fix rarely occurring "Error: net::ERR_BLOCKED_BY_CLIENT at chrome-extension://jjndjgheafjngoipoacpjgeicjeomjli/options.html", set and increase number (in ms). Default: 250 ms
	closeDelay?: number, // to fix rarely occurring TargetCloseError, set and increase number (in ms)
	extensionPath?: string, // used internally to load the puppeteer-stream browser extension (needed for electron https://github.com/SamuelScheit/puppeteer-stream/issues/137)
	enableExtensions?: string array, // load additional extensions from disk
}
```

and returns a `Promise<`[`Browser`](https://github.com/SamuelScheit/puppeteer-stream/blob/beb7d50dbae8069cd7e42eb17dbe99174c56e3a6/src/PuppeteerStream.ts#L126)`>`

#### Headless

Works also in headless mode (no gui needed), just set `headless: "new"` in the [launch options](#launch)

### Get Stream

The method [`getStream(options)`](https://github.com/SamuelScheit/puppeteer-stream/blob/beb7d50dbae8069cd7e42eb17dbe99174c56e3a6/src/PuppeteerStream.ts#L208) takes the following options

```ts
{
	audio: boolean, // whether or not to enable audio
	video: boolean, // whether or not to enable video
	mimeType?: string, // optional mime type of the stream, e.g. "audio/webm" or "video/webm"
	audioBitsPerSecond?: number, // The chosen bitrate for the audio component of the media.
	videoBitsPerSecond?: number, // The chosen bitrate for the video component of the media.
	bitsPerSecond?: number, // The chosen bitrate for the audio and video components of the media. This can be specified instead of the above two properties. If this is specified along with one or the other of the above properties, this will be used for the one that isn't specified.
	frameSize?: number, // The number of milliseconds to record into each packet.
  	videoConstraints: {
		mandatory?: MediaTrackConstraints,
		optional?: MediaTrackConstraints
	},
	audioConstraints: {
		mandatory?: MediaTrackConstraints,
		optional?: MediaTrackConstraints
	},
}
```

and returns a `Promise<`[`Readable`](https://github.com/SamuelScheit/puppeteer-stream/blob/beb7d50dbae8069cd7e42eb17dbe99174c56e3a6/src/PuppeteerStream.ts#L288)`>`

For a detailed documentation of the `mimeType`, `audioBitsPerSecond`, `videoBitsPerSecond`, `bitsPerSecond`, `frameSize` properties have a look at the [HTML5 MediaRecorder Options](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder/MediaRecorder) and for the `videoConstraints` and `audioConstraints` properties have a look at the [MediaTrackConstraints](https://developer.mozilla.org/en-US/docs/Web/API/MediaTrackConstraints).

## Example

### [Save Stream to File:](/examples/file.js)

```js
const { launch, getStream, wss } = require("puppeteer-stream");
const fs = require("fs");

const file = fs.createWriteStream(__dirname + "/test.webm");

async function test() {
	const browser = await launch({
		executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
		// or on linux: "google-chrome-stable"
		// or on mac: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
		defaultViewport: {
			width: 1920,
			height: 1080,
		},
	});

	const page = await browser.newPage();
	await page.goto("https://www.youtube.com/embed/9bZkp7q19f0?autoplay=1");
	const stream = await getStream(page, { audio: true, video: true });
	console.log("recording");

	stream.pipe(file);
	setTimeout(async () => {
		await stream.destroy();
		file.close();
		console.log("finished");

		await browser.close();
		(await wss).close();
	}, 1000 * 10);
}

test();
```

### [Stream to Discord](/examples/discord.js)

### [Stream Spotify](https://www.npmjs.com/package/spotify-playback-sdk-node)

### [Use puppeteer-extra plugins](/examples/puppeteer-extra.js)


### Streaming to Discord

import { Client, StageChannel } from 'discord.js-selfbot-v13';
import { Streamer, Utils, prepareStream, playStream } from "@dank074/discord-video-stream";
import { executablePath } from 'puppeteer';
import { launch, getStream } from 'puppeteer-stream';
import config from "./config.json" with {type: "json"};

type BrowserOptions = {
    width: number,
    height: number
}

const streamer = new Streamer(new Client());
let browser: Awaited<ReturnType<typeof launch>>;

// ready event
streamer.client.on("ready", () => {
    console.log(`--- ${streamer.client.user?.tag} is ready ---`);
});

let controller: AbortController;

// message event
streamer.client.on("messageCreate", async (msg) => {
    if (msg.author.bot) return;

    if (!config.acceptedAuthors.includes(msg.author.id)) return;

    if (!msg.content) return;

    if (msg.content.startsWith("$play-screen")) {
        const args = msg.content.split(" ");
        if (args.length < 2) return;

        const url = args[1];

        if (!url) return;

        const channel = msg.author.voice?.channel;

        if (!channel) return;

        console.log(`Attempting to join voice channel ${msg.guildId}/${channel.id}`);
        await streamer.joinVoice(msg.guildId!, channel.id);

        if (channel instanceof StageChannel)
        {
            await streamer.client.user?.voice?.setSuppressed(false);
        }

        controller?.abort();
        controller = new AbortController();
        await streamPuppeteer(url, streamer, {
            width: config.streamOpts.width,
            height: config.streamOpts.height
        }, controller.signal);
    } else if (msg.content.startsWith("$disconnect")) {
        controller?.abort();
        streamer.leaveVoice();
    } 
})

// login
streamer.client.login(config.token);

async function streamPuppeteer(url: string, streamer: Streamer, opts: BrowserOptions, cancelSignal?: AbortSignal) {
    cancelSignal?.throwIfAborted();
    cancelSignal?.addEventListener("abort", () => {
        browser.close();
    }, { once: true });
    browser = await launch({
        defaultViewport: {
            width: opts.width,
            height: opts.height,
        },
        executablePath: executablePath()
    });

    const page = await browser.newPage();
    await page.goto(url);

    const stream = await getStream(page, { audio: true, video: true, mimeType: "video/webm;codecs=vp8,opus" }); 

    try {
        const { command, output } = prepareStream(stream, {
            frameRate: config.streamOpts.fps,
            bitrateVideo: config.streamOpts.bitrateKbps,
            bitrateVideoMax: config.streamOpts.maxBitrateKbps,
            hardwareAcceleratedDecoding: config.streamOpts.hardware_acceleration,
            videoCodec: Utils.normalizeVideoCodec(config.streamOpts.videoCodec)
        }, cancelSignal);
        command.on("error", (err, stdout, stderr) => {
            console.log("An error occurred with ffmpeg");
            console.log(err)
        });
        
        await playStream(output, streamer, {
            // Use this to catch up with ffmpeg
            readrateInitialBurst: 10
        }, cancelSignal);
        console.log("Finished playing video");
    } catch (e) {
        console.log(e);
    }
}
