from subtitleflow.timecode import format_ass_time, format_srt_time, parse_ass_time, parse_srt_time


def test_ass_roundtrip() -> None:
    value = parse_ass_time("1:02:03.45")
    assert value == 3_723_450
    assert format_ass_time(value) == "1:02:03.45"


def test_srt_roundtrip() -> None:
    value = parse_srt_time("01:02:03,456")
    assert value == 3_723_456
    assert format_srt_time(value) == "01:02:03,456"
