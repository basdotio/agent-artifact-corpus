-- osascript render.applescript <deck.pptx> <out> [pdf]
-- Keynote is the macOS renderer (no LibreOffice there); it reads .pptx directly.
-- `open` does NOT reliably return the document for an imported .pptx (it once returned an "unmerge id" object,
-- and `export` sent to that object crashed Keynote). So: open, wait until a document with OUR file's
-- name exists that was not open before, and address that one. Never touch other open documents — the user may
-- have unsaved work in them.
on run argv
	set src to POSIX file (item 1 of argv)
	set dst to POSIX file (item 2 of argv)
	set AppleScript's text item delimiters to "/"
	set fname to last text item of (item 1 of argv)
	set AppleScript's text item delimiters to "."
	set stem to first text item of fname
	set AppleScript's text item delimiters to ""
	-- Cold start: `tell application "Keynote" to activate` did NOT launch a quit Keynote from a script run
	-- (-600 "application isn't running"; `open -ga` launched it). Launch hidden with open, then wait
	-- until it answers a harmless question before doing anything.
	do shell script "open -ga Keynote"
	repeat 60 times
		try
			tell application "Keynote" to count documents
			exit repeat
		on error
			delay 1
		end try
	end repeat
	-- A locked or sleeping screen leaves Keynote answering nothing: every event then waits out the default 120 s
	-- and fails with -1712. Long decks need more than 120 s to export, so raise the limit and translate the failure.
	try
		with timeout of 600 seconds
			my exportDeck(src, dst, fname, stem, (count of argv) > 2)
		end timeout
	on error msg number n
		if n is -1712 then error "Keynote cannot export while the screen is locked or asleep (AppleEvent timeout, -1712) — unlock the Mac and keep it awake (caffeinate -d), then retry" number n
		error msg number n
	end try
end run

on exportDeck(src, dst, fname, stem, asPdf)
	tell application "Keynote"
		-- Ids of documents already open: the one we want is the document that was NOT there before `open`.
		-- (A name match is not enough — another open deck can share the name or its prefix.)
		set priorIds to id of every document
		open src
		set d to missing value
		repeat 60 times
			repeat with doc in documents
				if (id of doc) is not in priorIds and name of doc starts with stem then set d to contents of doc
			end repeat
			if d is not missing value then exit repeat
			delay 1
		end repeat
		if d is missing value then error "Keynote did not open " & fname
		delay 2
		if asPdf then
			export d to dst as PDF
		else
			export d to dst as slide images with properties {image format:PNG, skipped slides:false}
		end if
		close d saving no
	end tell
end exportDeck
