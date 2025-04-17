import unittest
from core.reviewers.copyright_reviewer import CopyrightReviewer
from core.reviewers.security_reviewer import SecurityReviewer
from core.models import PRDetails


class TestReviewers(unittest.TestCase):
    def test_copyright_reviewer(self):
        reviewer = CopyrightReviewer(config={})
        comments = reviewer.review_file(
            "test.py",
            [{"lines": ["print('Hello, world!')"]}],
            PRDetails("owner", "repo", 1, "Test PR")
        )
        self.assertEqual(len(comments), 1)
        self.assertIn("copyright", comments[0]["body"].lower())

    def test_security_reviewer(self):
        reviewer = SecurityReviewer(config={})
        comments = reviewer.review_file(
            "test.py",
            [{"lines": ["eval('print(1)')"]}],
            PRDetails("owner", "repo", 1, "Test PR")
        )
        self.assertEqual(len(comments), 1)
        self.assertIn("security issue", comments[0]["body"].lower())

    def test_security_reviewer_hardcoded_secrets(self):
        """
        Test case for detecting hardcoded secrets in the code.
        """
        reviewer = SecurityReviewer(config={})
        comments = reviewer.review_file(
            "test.py",
            [{"lines": ["API_KEY = '12345'", "password = 'secret'"]}],
            PRDetails("owner", "repo", 1, "Test PR")
        )
        self.assertEqual(len(comments), 2)
        self.assertIn("hardcoded secret", comments[0]["body"].lower())
        self.assertIn("hardcoded secret", comments[1]["body"].lower())

    def test_partial_copyright_header(self):
        """
        Test case for detecting partial or incorrect copyright headers.
        """
        reviewer = CopyrightReviewer(config={})
        comments = reviewer.review_file(
            "test.py",
            [{"lines": ["# Copyright 2025"]}],
            PRDetails("owner", "repo", 1, "Test PR")
        )
        self.assertEqual(len(comments), 0)  # Should not flag this as an issue

        comments = reviewer.review_file(
            "test.py",
            [{"lines": ["# Coprigt 2025"]}],  # Intentional typo
            PRDetails("owner", "repo", 1, "Test PR")
        )
        self.assertEqual(len(comments), 1)
        self.assertIn("copyright", comments[0]["body"].lower())

    def test_code_uniqueness(self):
        """
        Test case for detecting non-unique code snippets.
        """
        reviewer = CopyrightReviewer(config={"github_token": "fake_token"})
        comments = reviewer.review_file(
            "test.py",
            [{"lines": ["print('Hello, world!')", "eval('print(1)')"]}],
            PRDetails("owner", "repo", 1, "Test PR")
        )
        # Assuming the API mock returns the code as non-unique
        self.assertGreaterEqual(len(comments), 1)
        self.assertIn("non-unique", comments[0]["body"].lower())


if __name__ == "__main__":
    unittest.main()