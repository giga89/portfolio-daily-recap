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
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import etoro_client
import ai_comment_responder


class TestFeedCommentsDiscovery(unittest.TestCase):

    @patch("etoro_client.get_headers")
    @patch("requests.get")
    def test_get_user_feed_posts(self, mock_get, mock_headers):
        mock_headers.return_value = {"x-user-key": "test"}
        now = datetime.now(timezone.utc)
        t1 = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        t2 = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "discussions": [
                {
                    "post": {
                        "id": "post-manual-1",
                        "created": t1,
                        "message": {"text": "Manual post by Andrea $MSFT $NVDA $1919.HK $NSDQ100. at $440 and $0.3085 with $115.23M cap"},
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
                        "created": t2,
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
        self.assertIn("1919.HK", posts[0]["tickers"])
        self.assertIn("NSDQ100", posts[0]["tickers"])
        self.assertNotIn("440", posts[0]["tickers"])
        self.assertNotIn("0.3085", posts[0]["tickers"])
        self.assertNotIn("115.23M", posts[0]["tickers"])
        self.assertIn("Manual post by Andrea", posts[0]["content"])
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
        now = datetime.now(timezone.utc)
        t1 = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        t2 = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

        mock_get_feed.return_value = [
            {
                "id": "post-zero-comments",
                "published_at": t1,
                "title": "Post with zero comments",
                "session_name": "Zero Comments",
                "tickers": ["MSFT"],
                "comments_count": 0,
                "embedded_comments": []
            },
            {
                "id": "post-manual-with-comment",
                "published_at": t2,
                "title": "Manual Post by Andrea",
                "content": "Manual Post by Andrea\nFull body detailing $GOOG (5.1% weight) and Cloud AI growth.",
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
        self.assertIn("5.1% weight", found["post_content"])
        # Ensure get_post_comments was NOT called for post-zero-comments or post-manual-with-comment (since embedded)
        from unittest.mock import call
        self.assertNotIn(call("post-zero-comments"), mock_get_comments.call_args_list)
        self.assertNotIn(call("post-manual-with-comment"), mock_get_comments.call_args_list)

    @patch("etoro_client.get_headers")
    @patch("requests.get")
    def test_get_comment_replies_requests_take_50(self, mock_get, mock_headers):
        mock_headers.return_value = {"x-user-key": "test"}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"comments": [{"entity": {"id": "rep-1"}}]}
        mock_get.return_value = mock_resp

        replies = etoro_client.get_comment_replies("post-1", "comm-1")
        self.assertEqual(len(replies), 1)
        sent_params = mock_get.call_args.kwargs.get("params", {})
        self.assertEqual(sent_params.get("take"), 50)
        self.assertEqual(sent_params.get("offset"), 0)

    @patch("ai_comment_responder.gist_storage.load_data", return_value={})
    @patch("ai_comment_responder.record_answered_comment")
    @patch("ai_comment_responder.load_answered_comments")
    @patch("etoro_client.get_comment_replies")
    @patch("etoro_client.get_user_feed_posts")
    @patch("etoro_client.is_configured")
    @patch("etoro_client.get_post_comments")
    def test_find_unreplied_sub_reply_under_andrea_focus_comment(
        self, mock_get_comments, mock_is_configured, mock_get_feed, mock_get_replies, mock_answered, mock_record, _mock_gist
    ):
        mock_is_configured.return_value = True
        mock_answered.return_value = {}
        now = datetime.now(timezone.utc)
        t1 = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Simulate live feed where totalCount=4 > embedded=3 (due to 1 sub-reply under Andrea's 3/3 Focus comment)
        mock_get_feed.return_value = [
            {
                "id": "post-us-open-1",
                "published_at": t1,
                "title": "APERTURA WALL STREET",
                "content": "APERTURA WALL STREET\nFocus su mercati USA e portafoglio.",
                "session_name": "APERTURA WALL STREET",
                "tickers": ["NVDA", "WDEF.L"],
                "comments_count": 4,
                "embedded_comments": [],
            }
        ]
        focus_comment = [
            {
                "entity": {
                    "id": "focus-3-id",
                    "owner": {"username": "AndreaRavalli"},
                    "message": {"text": "3/3 FOCUS STRATEGIA ETF & RENDIMENTO: $WDEF.L (WisdomTree Europe Defence ETF)"},
                    "repliesCount": 1,
                },
                "repliesCount": 1,
                "replies": [],
            }
        ]
        mock_get_comments.side_effect = lambda pid: focus_comment if pid == "post-us-open-1" else []
        mock_get_replies.return_value = [
            {
                "entity": {
                    "id": "sub-reply-stefano",
                    "owner": {"username": "StefanoCasulli"},
                    "message": {"text": "@AndreaRavalli mai la difesa, mai."},
                    "created": t1,
                }
            }
        ]

        unreplied = ai_comment_responder.find_unreplied_comments(days_back=7)
        self.assertEqual(len(unreplied), 1)
        item = unreplied[0]
        self.assertEqual(item["comment_id"], "sub-reply-stefano")
        self.assertEqual(item["reply_target_comment_id"], "focus-3-id")
        self.assertEqual(item["author"], "StefanoCasulli")
        self.assertIn("3/3 FOCUS STRATEGIA", item["post_content"])
        self.assertIn("WDEF.L", item["tickers"])

        # Once Andrea replies after StefanoCasulli in that thread, it must be skipped and recorded
        mock_get_replies.return_value.append(
            {
                "entity": {
                    "id": "andrea-reply-1",
                    "owner": {"username": "AndreaRavalli"},
                    "message": {"text": "Ciao @StefanoCasulli, rispetto la tua scelta etica."},
                    "created": t1,
                }
            }
        )
        unreplied_after = ai_comment_responder.find_unreplied_comments(days_back=7)
        self.assertEqual(unreplied_after, [])
        mock_record.assert_called_with("sub-reply-stefano", "post-us-open-1", "StefanoCasulli")

    @patch("ai_comment_responder.send_telegram_comment_notification")
    @patch("ai_comment_responder.record_answered_comment")
    @patch("ai_comment_responder.etoro_client.reply_to_comment")
    @patch("ai_comment_responder.generate_ai_comment_reply")
    @patch("ai_comment_responder.find_unreplied_comments")
    def test_process_community_replies_targets_parent_thread_but_records_sub_reply_id(
        self, mock_find, mock_gen, mock_reply, mock_record, mock_tg
    ):
        mock_find.return_value = [
            {
                "post_id": "post-us-open-1",
                "comment_id": "sub-reply-stefano",
                "reply_target_comment_id": "focus-3-id",
                "author": "StefanoCasulli",
                "message": "@AndreaRavalli mai la difesa, mai.",
                "post_title": "APERTURA WALL STREET",
                "post_content": "Contesto $WDEF.L",
                "tickers": ["WDEF.L"],
                "created_at": "2026-11-27T15:00:23Z",
            }
        ]
        mock_gen.return_value = "Ciao @StefanoCasulli, grazie per aver condiviso il tuo punto di vista su $WDEF.L. Un saluto! 🤝"
        mock_reply.return_value = {"success": True, "id": "new-reply-id"}

        results = ai_comment_responder.process_community_replies(dry_run=False)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "published")
        mock_reply.assert_called_once()
        self.assertEqual(mock_reply.call_args.kwargs["comment_id"], "focus-3-id")
        mock_record.assert_called_once_with(
            comment_id="sub-reply-stefano",
            post_id="post-us-open-1",
            author="StefanoCasulli",
            reply_id="new-reply-id",
        )


if __name__ == "__main__":
    unittest.main()
