#!/usr/bin/env python3
"""
Unit tests for social analytics comments tracking, sync, and dashboard generation.
"""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import json
import etoro_client
import analytics_tracker


class TestAnalyticsCommentsSync(unittest.TestCase):

    def test_get_post_metrics_fetch_comments_false_returns_none_when_absent_in_summary(self):
        """When comments are not in summary and fetch_comments is False, comments should be None."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "test-post-1",
            "summary": {
                "likeCount": 5,
                "sharedCount": 1
            },
            "emotionsData": {
                "like": {
                    "emotions": [],
                    "paging": {"totalCount": 5}
                }
            },
            "post": {"owner": {"username": "AndreaRavalli", "id": "8029424"}},
            "requesterContext": {"hasLiked": False}
        }

        with patch("etoro_client.get_headers", return_value={"mock": "header"}), \
             patch("requests.get", return_value=mock_resp):
            metrics = etoro_client.get_post_metrics("test-post-1", fetch_comments=False)
            self.assertIsNotNone(metrics)
            self.assertEqual(metrics["likes"], 5)
            self.assertEqual(metrics["shares"], 1)
            self.assertIsNone(metrics["comments"], "Comments should be None when not requested and not in summary")

    def test_get_post_metrics_fetch_comments_true_calls_comments_endpoint(self):
        """When fetch_comments is True, comments should be queried and author comments filtered."""
        post_resp = MagicMock()
        post_resp.status_code = 200
        post_resp.json.return_value = {
            "id": "test-post-2",
            "summary": {"likeCount": 3},
            "emotionsData": {"like": {"emotions": [], "paging": {"totalCount": 3}}},
            "post": {"owner": {"username": "AndreaRavalli", "id": "8029424"}},
            "requesterContext": {"hasLiked": False}
        }

        comments_resp = MagicMock()
        comments_resp.status_code = 200
        comments_resp.json.return_value = {
            "comments": [
                {"entity": {"owner": {"username": "user1", "id": "111"}}, "requesterContext": {"isOwner": False}},
                {"entity": {"owner": {"username": "AndreaRavalli", "id": "8029424"}}, "requesterContext": {"isOwner": True}},
                {"entity": {"owner": {"username": "user2", "id": "222"}}, "requesterContext": {"isOwner": False}},
            ],
            "paging": {"totalCount": 3}
        }

        def mock_get(url, **kwargs):
            if "/comments" in url:
                return comments_resp
            return post_resp

        with patch("etoro_client.get_headers", return_value={"mock": "header"}), \
             patch("requests.get", side_effect=mock_get):
            metrics = etoro_client.get_post_metrics("test-post-2", fetch_comments=True)
            self.assertIsNotNone(metrics)
            self.assertEqual(metrics["likes"], 3)
            # 3 total comments minus 1 author comment = 2 external comments
            self.assertEqual(metrics["comments"], 2)

    def test_sync_preserves_older_comments_and_applies_answered_floor(self):
        """sync_etoro_metrics must preserve existing comments on older posts and enforce answered floor."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analytics_path = os.path.join(tmpdir, "post_analytics.json")
            answered_path = os.path.join(tmpdir, "answered_comments.json")

            initial_data = {
                "posts": [
                    {
                        "id": "recent-post",
                        "platform": "etoro",
                        "published_at": "2026-09-22T07:00:00Z",
                        "likes": 0,
                        "comments": 0,
                        "shares": 0
                    },
                    {
                        "id": "old-post-with-comments",
                        "platform": "etoro",
                        "published_at": "2026-08-01T10:00:00Z",
                        "likes": 2,
                        "comments": 4,  # Existing recorded comments
                        "shares": 0
                    }
                ]
            }
            with open(analytics_path, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            answered_db = {
                "c1": {"post_id": "recent-post", "author": "copier1"},
                "c2": {"post_id": "recent-post", "author": "copier2"},
                "c3": {"post_id": "old-post-with-comments", "author": "copier3"}
            }
            with open(answered_path, "w", encoding="utf-8") as f:
                json.dump(answered_db, f)

            def mock_get_metrics(pid, fetch_comments=False):
                if pid == "recent-post":
                    # comments endpoint returned 1 live external comment
                    return {"id": pid, "likes": 5, "comments": 1, "shares": 0}
                else:
                    # comments endpoint not fetched for old post
                    return {"id": pid, "likes": 3, "comments": None, "shares": 0}

            with patch("analytics_tracker.ANALYTICS_FILE", analytics_path), \
                 patch("analytics_tracker.ANSWERED_COMMENTS_FILE", answered_path), \
                 patch("etoro_client.get_post_metrics", side_effect=mock_get_metrics):
                updated_data = analytics_tracker.sync_etoro_metrics(max_comment_sync_days=14)

                posts_by_id = {p["id"]: p for p in updated_data["posts"]}
                # recent-post: metrics returned 1, but answered_comments has 2 -> floor applied to 2
                self.assertEqual(posts_by_id["recent-post"]["comments"], 2)
                self.assertEqual(posts_by_id["recent-post"]["likes"], 5)

                # old-post: metrics returned comments=None, existing was 4, answered floor is 1 -> preserved 4!
                self.assertEqual(posts_by_id["old-post-with-comments"]["comments"], 4)
                self.assertEqual(posts_by_id["old-post-with-comments"]["likes"], 3)


if __name__ == "__main__":
    unittest.main()

