#!/usr/bin/env python3

import requests
from typing import List, Dict, Any
from core.models import PRDetails
from core.reviewers.base_reviewer import BaseReviewer


class CopyrightReviewer(BaseReviewer):
    """
    Reviewer to check for missing or incorrect copyright headers in files
    and verify the uniqueness of the code.
    """

    def review_file(self, file_path: str, hunks: List[Dict[str, Any]], pr_details: PRDetails) -> List[Dict[str, Any]]:
        """
        Check for copyright headers and uniqueness of the code.

        Args:
            file_path: Path to the file in the repository
            hunks: List of hunks from the diff
            pr_details: Pull request details

        Returns:
            List of comments, each with body, path, and position fields
        """
        comments = []

        # Check if the file has a copyright header
        with open(file_path, 'r') as file:
            lines = file.readlines()

        if not any("Copyright" in line for line in lines[:10]):
            comments.append({
                "body": "⚠️ Missing copyright header. Please add a copyright notice at the top of the file.",
                "path": file_path,
                "position": 1
            })

        # Check for code uniqueness
        for hunk in hunks:
            for line_number, line in enumerate(hunk.get('lines', []), start=1):
                if self._is_code_non_unique(line):
                    comments.append({
                        "body": f"⚠️ This line of code may not be unique. Please ensure it is not copied from another source: `{line.strip()}`",
                        "path": file_path,
                        "position": line_number
                    })

        return comments

    def _is_code_non_unique(self, code_snippet: str) -> bool:
        """
        Check if the given code snippet exists in other repositories or online.

        Args:
            code_snippet: A line or snippet of code to check

        Returns:
            True if the code is found elsewhere, False otherwise
        """
        # Use GitHub Code Search API or a search engine API to check for the code
        search_url = "https://api.github.com/search/code"
        headers = {
            "Authorization": f"Bearer {self.config.get('github_token')}",
            "Accept": "application/vnd.github.v3+json"
        }
        params = {
            "q": f'"{code_snippet.strip()}" in:file',
            "per_page": 1
        }

        try:
            response = requests.get(search_url, headers=headers, params=params)
            if response.status_code == 200:
                results = response.json()
                return results.get("total_count", 0) > 0
            else:
                print(f"GitHub API error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error checking code uniqueness: {e}")
            return False