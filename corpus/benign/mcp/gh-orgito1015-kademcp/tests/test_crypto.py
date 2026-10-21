"""Tests for tools.crypto (offline: no hashcat/john/network required)."""

import asyncio

from tools.crypto import handle_crypto


def call(name, args):
    return asyncio.run(handle_crypto(name, args))


# --- hash_crack mode resolution ---------------------------------------------

def test_unknown_length_no_mode_errors_not_md5():
    r = call("hash_crack", {"hash_value": "z" * 13})
    assert r.startswith("[error]")
    assert "could not determine" in r


def test_unsupported_mode_rejected():
    r = call("hash_crack", {"hash_value": "a" * 32, "mode": "bcrypt"})
    assert r.startswith("[error]")
    assert "unsupported mode" in r


def test_32_char_ambiguous_requires_mode():
    r = call("hash_crack", {"hash_value": "a" * 32})
    assert r.startswith("[error]")
    assert "MD5 or NTLM" in r


def test_32_char_with_explicit_mode_passes_resolution():
    # No wordlist in the test env, so it should reach the wordlist check,
    # proving mode resolution succeeded rather than erroring earlier.
    r = call("hash_crack", {"hash_value": "a" * 32, "mode": "ntlm"})
    assert "wordlist not found" in r


def test_unambiguous_length_auto_detects():
    r = call("hash_crack", {"hash_value": "a" * 40})  # sha1
    assert "wordlist not found" in r


# --- morse -------------------------------------------------------------------

def test_morse_word_separator_decode():
    r = call("decode_encode", {"data": "... --- ... / -- .- -.--", "scheme": "morse", "direction": "decode"})
    assert r == "SOS MAY"


def test_morse_multiple_spaces_collapse_on_encode():
    r = call("decode_encode", {"data": "A  B", "scheme": "morse", "direction": "encode"})
    assert r == ".- / -..."


def test_morse_round_trip():
    enc = call("decode_encode", {"data": "HELLO WORLD", "scheme": "morse", "direction": "encode"})
    dec = call("decode_encode", {"data": enc, "scheme": "morse", "direction": "decode"})
    assert dec == "HELLO WORLD"


# --- base64 ------------------------------------------------------------------

def test_base64_valid_decode():
    assert call("decode_encode", {"data": "aGVsbG8=", "scheme": "base64", "direction": "decode"}) == "hello"


def test_base64_invalid_returns_controlled_error():
    r = call("decode_encode", {"data": "@@@nope@@@", "scheme": "base64", "direction": "decode"})
    assert r.startswith("[error]")


def test_base64url_no_padding():
    assert call("decode_encode", {"data": "aGVsbG8", "scheme": "base64url", "direction": "decode"}) == "hello"
