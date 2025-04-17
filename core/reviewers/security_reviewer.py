#!/usr/bin/env python3

from typing import List, Dict, Any
from core.models import PRDetails
from core.reviewers.base_reviewer import BaseReviewer


class SecurityReviewer(BaseReviewer):
    """
    Reviewer to identify potential security issues in the code.
    """

    def review_file(self, file_path: str, hunks: List[Dict[str, Any]], pr_details: PRDetails) -> List[Dict[str, Any]]:
        """
        Check for potential security issues in the file.

        Args:
            file_path: Path to the file in the repository
            hunks: List of hunks from the diff
            pr_details: Pull request details

        Returns:
            List of comments, each with body, path, and position fields
        """
        comments = []

        for hunk in hunks:
            for line_number, line in enumerate(hunk.get('lines', []), start=1):
                if "eval(" in line or "exec(" in line:
                    comments.append({
                        "body": "⚠️ Potential security issue: Avoid using `eval` or `exec` as they can execute arbitrary code.",
                        "path": file_path,
                        "position": line_number
                    })

        return comments