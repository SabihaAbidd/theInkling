"""Behavior checks for reader-feedback content personalization."""

import unittest

from app.agent.personalization import feedback_relevance_scores


class FeedbackRelevanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.articles = [
            {
                "title": "Quantum chips advance computing",
                "summary": "Researchers built a quantum processor for computing.",
            },
            {
                "title": "Coastal cities plan for rising seas",
                "summary": "Climate adaptation projects protect coastal communities.",
            },
        ]

    def test_saved_story_increases_similarity_for_related_article(self) -> None:
        feedback = [
            {
                "action": "saved",
                "title": "Quantum computing breakthrough",
                "summary": "New quantum processor advances computing research.",
            }
        ]

        scores = feedback_relevance_scores(self.articles, feedback)

        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[0], 0)

    def test_skipped_story_reduces_similarity_for_related_article(self) -> None:
        feedback = [
            {
                "action": "skipped",
                "title": "Quantum chip computing",
                "summary": "Quantum processor research.",
            }
        ]

        scores = feedback_relevance_scores(self.articles, feedback)

        self.assertLess(scores[0], scores[1])
        self.assertLess(scores[0], 0)

    def test_short_open_is_neutral_and_no_feedback_has_no_effect(self) -> None:
        feedback = [
            {
                "action": "opened",
                "dwell_seconds": 4,
                "title": "Quantum chips advance computing",
                "summary": "Quantum processor research.",
            }
        ]

        self.assertEqual(feedback_relevance_scores(self.articles, feedback), [0.0, 0.0])
        self.assertEqual(feedback_relevance_scores(self.articles, []), [0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
