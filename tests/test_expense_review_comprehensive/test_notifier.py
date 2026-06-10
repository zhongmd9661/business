import pytest
from unittest.mock import patch, MagicMock

from src.expense_review_comprehensive.notifier import WebhookNotifier
from src.expense_review_comprehensive.models import Finding, RuleCategory


def _make_finding(level="高"):
    return Finding(
        category=RuleCategory.DOCUMENT_INTEGRITY,
        rule="测试规则",
        clause="第1条",
        level=level,
        message="测试消息",
        detail="测试详情",
    )


@patch("src.expense_review_comprehensive.notifier.requests.post")
def test_notify_sends_high_risk(mock_post):
    mock_post.return_value = MagicMock()
    notifier = WebhookNotifier("http://localhost:9999/hook")

    findings = [_make_finding("高"), _make_finding("中")]
    result = notifier.notify(findings, "test.md")

    assert result is True
    call_json = mock_post.call_args.kwargs["json"]
    assert call_json["count"] == 1
    assert call_json["filename"] == "test.md"


@patch("src.expense_review_comprehensive.notifier.requests.post")
def test_notify_no_high_risk(mock_post):
    notifier = WebhookNotifier("http://localhost:9999/hook")

    findings = [_make_finding("中"), _make_finding("低")]
    result = notifier.notify(findings, "test.md")

    assert result is False
    mock_post.assert_not_called()


def test_notify_empty_findings():
    notifier = WebhookNotifier("http://localhost:9999/hook")
    result = notifier.notify([], "test.md")
    assert result is False


@patch("src.expense_review_comprehensive.notifier.requests.post")
def test_notify_failure_does_not_crash(mock_post):
    mock_post.side_effect = Exception("connection refused")
    notifier = WebhookNotifier("http://localhost:9999/hook")

    findings = [_make_finding("高")]
    result = notifier.notify(findings, "test.md")

    assert result is False


@patch("src.expense_review_comprehensive.notifier.requests.post")
def test_notify_payload_includes_category_and_clause(mock_post):
    mock_post.return_value = MagicMock()
    notifier = WebhookNotifier("http://localhost:9999/hook")

    findings = [_make_finding("高")]
    notifier.notify(findings, "test.md")

    call_json = mock_post.call_args.kwargs["json"]
    finding_payload = call_json["findings"][0]
    assert finding_payload["category"] == "单据完整性"
    assert finding_payload["clause"] == "第1条"
    assert finding_payload["rule"] == "测试规则"
