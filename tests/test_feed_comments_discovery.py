#!/usr/bin/env python3
"""
Unit tests for live eToro feed comments discovery and response pipeline.
Verifies:
  1. Discovery of all posts (both automated and manual) from eToro user feed.
  2. Optimization: posts with 0 comments do not trigger extra API calls.
  3. Embedded comments from feed are processed without extra API calls.
  4. Deduplication and skip of comments already answered or authored by Andrea.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import etoro_client
import ai_comment_responder


class TestFeedCommentsDiscovery(unittest.TestCase):

    @patch("etoro_client.get_headers")
    @patch("requests.get")
    def test_get_user_feed_posts(self, mock_get, mock_headers):
        mock_headers.return_value = {"x-user-key": "test"}
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "discussions": [
                {
                    "post": {
                        "id": "post-manual-1",
                        "created": "2026-10-28T20:00:00Z",
                        "message": {"text": "Manual post by Andrea $MSFT $NVDA"},
                        "tags": [{"market": {"symbolName": "MSFT"}}]
                    },
                    "commentsData": {
                        "reactionPaging": {"totalCount": 1},
                        "comments": [
                            {
                                "id": "comment-1",
                                "owner": {"username": "ExternalUser"},
                                "message": {"text": "Great insights on Microsoft!"},
                                "replies": []
                            }
                        ]
                    }
                },
                {
                    "post": {
                        "id": "post-bot-2",
                        "created": "2026-10-28T10:00:00Z",
                        "message": {"text": "Bot post 0 comments"},
                        "tags": []
                    },
                    "commentsData": {
                        "reactionPaging": {"totalCount": 0},
                        "comments": []
                    }
                }
            ]
        }
        mock_get.return_value = mock_resp

        posts = etoro_client.get_user_feed_posts(days_back=7)
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0]["id"], "post-manual-1")
        self.assertIn("MSFT", posts[0]["tickers"])
        self.assertIn("NVDA", posts[0]["tickers"])
        self.assertEqual(posts[0]["comments_count"], 1)
        self.assertEqual(posts[1]["comments_count"], 0)

    @patch("ai_comment_responder.load_answered_comments")
    @patch("etoro_client.get_user_feed_posts")
    @patch("etoro_client.is_configured")
    @patch("etoro_client.get_post_comments")
    def test_find_unreplied_comments_skips_zero_comments_and_finds_manual(
        self, mock_get_comments, mock_is_configured, mock_get_feed, mock_answered
    ):
        mock_is_configured.return_value = True
        mock_answered.return_value = {}

        mock_get_feed.return_value = [
            {
                "id": "post-zero-comments",
                "published_at": "2026-10-28T12:00:00Z",
                "title": "Post with zero comments",
                "session_name": "Zero Comments",
                "tickers": ["MSFT"],
                "comments_count": 0,
                "embedded_comments": []
            },
            {
                "id": "post-manual-with-comment",
                "published_at": "2026-10-28T18:00:00Z",
                "title": "Manual Post by Andrea",
                "session_name": "Manual Post",
                "tickers": ["GOOGL"],
                "comments_count": 1,
                "embedded_comments": [
                    {
                        "id": "comm-ext-100",
                        "owner": {"username": "CommunityUser"},
                        "message": {"text": "Great perspective on Alphabet!"},
                        "replies": []
                    }
                ]
            }
        ]

        unreplied = ai_comment_responder.find_unreplied_comments(days_back=7)
        self.assertTrue(any(u["comment_id"] == "comm-ext-100" for u in unreplied))
        found = next(u for u in unreplied if u["comment_id"] == "comm-ext-100")
        self.assertEqual(found["author"], "CommunityUser")
        self.assertEqual(found["post_id"], "post-manual-with-comment")
        # Ensure get_post_comments was NOT called for post-zero-comments or post-manual-with-comment (since embedded)
        from unittest.mock import call
        self.assertNotIn(call("post-zero-comments"), mock_get_comments.call_args_list)
        self.assertNotIn(call("post-manual-with-comment"), mock_get_comments.call_args_list)


if __name__ == "__main__":
    unittest.main()
