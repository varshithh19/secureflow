"""Unit tests verifying HTML escaping and XSS payload neutralization (THR-09 / SR-09)."""
import html


def esc(s: str) -> str:
    """Python reference implementation of the frontend esc() utility function."""
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def test_xss_payload_escaping():
    xss_payloads = [
        '<img onerror=alert(1) src="invalid">',
        "<script>alert('XSS')</script>",
        '" onfocus="alert(1)" autofocus="',
        "javascript:alert(document.domain)",
        "<b>Bold</b> & 'SingleQuotes' \"DoubleQuotes\""
    ]

    for payload in xss_payloads:
        escaped = esc(payload)
        # Verify dangerous HTML tag characters are neutralized
        assert "<" not in escaped
        assert ">" not in escaped
        assert '"' not in escaped
        assert "'" not in escaped


def test_view_template_escaping_simulation():
    malicious_title = 'Stalled Car <img onerror=alert(1) src=x>'
    malicious_user = 'Hacker <script>alert(1)</script>'

    escaped_title = esc(malicious_title)
    escaped_user = esc(malicious_user)

    rendered_html = f"<tr><td><b>{escaped_title}</b></td><td>{escaped_user}</td></tr>"

    assert "<img" not in rendered_html
    assert "<script" not in rendered_html
    assert "&lt;img onerror=alert(1)" in rendered_html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered_html
