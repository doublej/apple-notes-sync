"""Tests for the protobuf encoder."""

from apple_notes_sync.protobuf import (
    encode_tag,
    encode_varint,
    field_bytes,
    field_str,
    field_varint,
)


def test_varint_single_byte():
    assert encode_varint(0) == b"\x00"
    assert encode_varint(1) == b"\x01"
    assert encode_varint(127) == b"\x7f"


def test_varint_multi_byte():
    assert encode_varint(128) == b"\x80\x01"
    assert encode_varint(300) == b"\xac\x02"


def test_tag():
    # field 1, wire type 0 (varint) -> (1 << 3) | 0 = 8
    assert encode_tag(1, 0) == b"\x08"
    # field 2, wire type 2 (length-delimited) -> (2 << 3) | 2 = 18
    assert encode_tag(2, 2) == b"\x12"


def test_field_varint():
    result = field_varint(1, 0)
    assert result == b"\x08\x00"


def test_field_bytes():
    result = field_bytes(1, b"abc")
    assert result == b"\x0a\x03abc"


def test_field_str():
    result = field_str(2, "hi")
    assert result == b"\x12\x02hi"
