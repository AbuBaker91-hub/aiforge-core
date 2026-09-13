"""Manual smoke test for the local embedder (downloads the model once).

    python -m aiforge_core.embed.smoke
"""

from . import Embedder


def main() -> None:
    sentences = [
        "The invoice total is due at closing.",
        "Payment for the invoice must be made by the closing date.",
        "Hiking backpacks come in 40 and 60 liter sizes.",
    ]
    embedder = Embedder()
    vectors = embedder.embed(sentences)

    def cos(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=True))

    best = max(
        ((i, j) for i in range(len(sentences)) for j in range(i + 1, len(sentences))),
        key=lambda p: cos(vectors[p[0]], vectors[p[1]]),
    )
    print(f"dims={len(vectors[0])}")
    print(f"nearest pair:\n  {sentences[best[0]]}\n  {sentences[best[1]]}")


if __name__ == "__main__":
    main()
