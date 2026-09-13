from aiforge_core.embed import DIM, StubEmbedder


def test_same_text_same_vector():
    e = StubEmbedder()
    assert e.embed_one("hello world") == e.embed_one("hello world")


def test_vector_length_is_384():
    assert len(StubEmbedder().embed_one("anything at all")) == DIM


def test_similar_texts_are_closer_than_unrelated():
    e = StubEmbedder()

    def cos(a, b):
        return sum(x * y for x, y in zip(a, b, strict=True))

    close = cos(e.embed_one("the invoice total amount"), e.embed_one("total invoice amount due"))
    far = cos(e.embed_one("the invoice total amount"), e.embed_one("green hiking backpack"))
    assert close > far
