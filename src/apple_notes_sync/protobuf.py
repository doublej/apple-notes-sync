"""Minimal protobuf encoder for Apple Notes ZDATA format."""


def encode_varint(value: int) -> bytes:
    """Encode an integer as a protobuf varint."""
    parts = []
    while value > 0x7F:
        parts.append((value & 0x7F) | 0x80)
        value >>= 7
    parts.append(value & 0x7F)
    return bytes(parts)


def encode_tag(field: int, wire: int) -> bytes:
    """Encode a protobuf field tag (field number + wire type)."""
    return encode_varint((field << 3) | wire)


def field_varint(field_num: int, value: int) -> bytes:
    """Encode a varint field (wire type 0)."""
    return encode_tag(field_num, 0) + encode_varint(value)


def field_bytes(field_num: int, data: bytes) -> bytes:
    """Encode a length-delimited field (wire type 2)."""
    return encode_tag(field_num, 2) + encode_varint(len(data)) + data


def field_str(field_num: int, text: str) -> bytes:
    """Encode a string field (wire type 2, UTF-8)."""
    return field_bytes(field_num, text.encode("utf-8"))
