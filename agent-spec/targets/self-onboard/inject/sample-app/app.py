"""Simple word counter app — used as a sample project for onboarding tests."""
import sys


def count_words(text: str) -> dict:
    """Count word frequencies in text, case-insensitive."""
    words = text.lower().split()
    counts = {}
    for w in words:
        w = w.strip(".,!?;:'\"")
        if w:
            counts[w] = counts.get(w, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 app.py <filename>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        text = f.read()
    counts = count_words(text)
    print(f"Total unique words: {len(counts)}")
    for word, count in list(counts.items())[:10]:
        print(f"  {word}: {count}")


if __name__ == "__main__":
    main()
