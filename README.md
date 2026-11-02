# voiceover-check

AI voices sometimes skip a word, repeat one, or say a different number. If "did not" becomes "did", your sentence means the opposite, and you might not hear it until after you publish.

This tool compares a voiceover with its script and tells you where they differ, with the time to check.

I'm a marketer, not a developer. I built the first version with Claude Code while making videos for my YouTube channel, because listening back to every line for every video takes too long.

## What it looks like

I wrote [a short script](examples/script.txt), then made [a voiceover with 5 mistakes in it](examples/wrong-voiceover.mp3) on purpose:

```
match 91.3%, 5 to check
    0:01  MISSING  wrote: do not  |  heard: -
    0:08  CHANGED  wrote: 200  |  heard: 2000
    0:17  EXTRA    wrote: -  |  heard: referral
    0:19  CHANGED  wrote: 65  |  heard: 95
    0:27  CHANGED  wrote: they already know you  |  heard: slash pause
```

It caught all 5. On [the correct version](examples/correct-voiceover.mp3) it reports `match 100.0%, 0 to check`. That's one short test, not a guarantee.

## Try it

You need Python 3.9 or newer.

```bash
git clone https://github.com/Psamuelcole/voiceover-check
cd voiceover-check
pip install faster-whisper
python3 -m voiceover_check examples/script.txt --audio examples/wrong-voiceover.mp3
```

The first run downloads a free speech model. After that, your audio is transcribed on your own computer, not uploaded by this tool.

Use your own files the same way. The script can be one text file or a folder of `.txt` files, read in name order:

```bash
python3 -m voiceover_check my-script.txt --audio my-voiceover.mp3
```

If you already have a transcript with word timings, you don't need the speech model:

```bash
python3 -m voiceover_check my-script.txt --words words.json
```

`words.json` can be a list, or an object with a `words` list. Each item needs the word and its start time, as `w` and `s` or as `word` and `start`.

## What it ignores

It won't flag differences that sound the same:

- Numbers: "two thousand and sixteen" and "2016", "sixty five percent" and "65%", "$2.1 billion" and "two point one billion dollars"
- Spacing: "startup" and "start up"
- Apostrophes: "customers" and "customer's"
- Pronunciation markup: `[Lagos](/lˈAɡɔs/)` counts as "Lagos"

## What it gets wrong

A flag means "go and listen here". It doesn't always mean the voice made a mistake.

- **Names cause false alarms.** The speech model often mishears unusual names, especially African ones. The voice may be right when the tool says it isn't.
- **It can't hear pronunciation.** If the right word is said badly, it won't notice.
- **It can miss a mistake.** If the speech model "corrects" a voice error while transcribing, the two will match.
- **Small differences can show up.** You may see "neighbours" and "neighbors", or "you're" and "you are".
- **English only for now.** Number matching is written for English.

## Use it in a script

The command exits with `0` if everything matches, `1` if something needs a listen, and `2` if it couldn't read your files. That lets you stop a video build before it renders a bad voiceover.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

MIT licence. Built with [Claude Code](https://claude.com/claude-code).
