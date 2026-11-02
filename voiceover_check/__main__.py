"""Usage:
  python -m voiceover_check script.txt --words words.json
  python -m voiceover_check script.txt --audio voiceover.mp3
Exit code: 0 if the voiceover matches, 1 if anything needs a listen, 2 on bad input.
"""
import argparse, sys
from .core import compare, load_script, load_words


def transcribe(path, model):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("--audio needs faster-whisper: pip install faster-whisper")
    segments, _ = WhisperModel(model, compute_type="int8").transcribe(path, word_timestamps=True)
    return [(w.word, w.start) for s in segments for w in s.words]


def clock(seconds):
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def main():
    ap = argparse.ArgumentParser(prog="voiceover_check", description="Find words a voiceover added, dropped or changed.")
    ap.add_argument("script", help="a text file, or a folder of .txt files")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--audio", help="voiceover audio, transcribed on your machine")
    src.add_argument("--words", help="existing transcript as JSON with word timings")
    ap.add_argument("--model", default="small", help="speech model for --audio (default: small)")
    a = ap.parse_args()
    try:
        text = load_script(a.script)
        timed = load_words(a.words) if a.words else transcribe(a.audio, a.model)
    except (OSError, ValueError, KeyError) as e:
        print(f"Could not read input: {e}", file=sys.stderr)
        sys.exit(2)
    score, flags = compare(text, timed)
    print(f"match {score:.1%}, {len(flags)} to check")
    for f in flags:
        print(f"  {clock(f.seconds):>6}  {f.kind:<8} wrote: {f.wrote or '-'}  |  heard: {f.heard or '-'}")
    sys.exit(1 if flags else 0)


if __name__ == "__main__":
    main()
