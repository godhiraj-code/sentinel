from datetime import datetime
from html.parser import HTMLParser

from sentinel.reporters.flight_recorder import FlightRecorder, LogEntry


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_report_treats_page_content_and_screenshot_names_as_text(tmp_path):
    recorder = FlightRecorder(str(tmp_path), "safe-run")
    payload = '<script>alert("external page")</script>'
    recorder.run_name = payload
    recorder.metadata["url"] = payload
    recorder.entries.append(LogEntry(
        datetime.now(), 0, "info", payload,
        data={"page_text": payload},
        screenshot_path=str(tmp_path / 'image" onerror="alert(1).png'),
    ))
    html = recorder._build_html_report()
    tags = Tags()
    tags.feed(html)
    assert not any(tag == "script" for tag, _ in tags.tags)
    assert not any("onerror" in attrs for _, attrs in tags.tags)
    assert html.count("&lt;script&gt;") == 5
    assert any(tag == "img" for tag, _ in tags.tags)
