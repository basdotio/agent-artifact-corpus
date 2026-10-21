import re
from db_context.utils import wrap_untrusted


def test_wrap_untrusted_basic():
    data = "Hello World"
    wrapped = wrap_untrusted(data)
    assert "Hello World" in wrapped
    assert "<untrusted-data-" in wrapped
    # Appears multiple times (intro, opening tag, closing tag); ensure at least one and all share same UUID
    occurrences = re.findall(r"<untrusted-data-([0-9a-f-]+)>", wrapped)
    assert occurrences, "No untrusted-data opening tags found"
    closing = re.findall(r"</untrusted-data-([0-9a-f-]+)>", wrapped)
    assert closing, "No closing tag found"
    # All UUIDs should match the first one
    first = occurrences[0]
    assert all(o == first for o in occurrences)
    assert all(c == first for c in closing)


def test_wrap_untrusted_escapes_angle_brackets():
    data = "<script>alert('x')</script>"
    wrapped = wrap_untrusted(data)
    assert "<script>" not in wrapped  # raw should be escaped
    assert "&lt;script&gt;" in wrapped


def test_wrap_untrusted_unique_ids():
    w1 = wrap_untrusted("one")
    w2 = wrap_untrusted("two")
    id1 = re.search(r"<untrusted-data-([0-9a-f-]+)>", w1).group(1)
    id2 = re.search(r"<untrusted-data-([0-9a-f-]+)>", w2).group(1)
    assert id1 != id2
