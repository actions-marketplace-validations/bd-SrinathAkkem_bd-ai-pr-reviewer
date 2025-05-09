#!/usr/bin/env python3

import os
import sys
import subprocess
import tempfile
from typing import Dict, Any, List

from core.github_client import GitHubClient
from core.diff_parser import DiffParser
from core.reviewers.base_reviewer import BaseReviewer
from core.reviewers.code_reviewer import AICodeReviewer
from core.reviewers.copyright_reviewer import CopyrightReviewer
from core.reviewers.security_reviewer import SecurityReviewer
from config import load_config


def get_reviewers(config: Dict[str, Any]) -> List[BaseReviewer]:
    """
    Initialize reviewer instances based on configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of reviewer instances
    """
    enabled_reviewers = config.get("enabled_reviewers", [])
    reviewers = []

    # Map of reviewer names to classes
    reviewer_classes = {
        "ai": AICodeReviewer,
        "copyright": CopyrightReviewer,
        "security": SecurityReviewer,
    }

    # Initialize enabled reviewers
    for reviewer_name in enabled_reviewers:
        if reviewer_name in reviewer_classes:
            reviewer_class = reviewer_classes[reviewer_name]
            reviewers.append(reviewer_class(config))
            print(f"Initialized {reviewer_name} reviewer")
        else:
            print(f"Warning: Unknown reviewer type '{reviewer_name}'")

    return reviewers


def generate_and_run_tests(file_path: str, reviewer: BaseReviewer, pr_details: Any) -> None:
    """
    Generate test cases for the given file and run them.

    Args:
        file_path: Path to the file being reviewed
        reviewer: The reviewer instance generating the test cases
        pr_details: Pull request details
    """
    print(f"Generating test cases for {file_path} using {reviewer.name}...")

    # Generate test cases using the reviewer
    test_cases = reviewer.generate_test_cases(file_path, pr_details)
    if not test_cases:
        print(f"No test cases generated for {file_path}.")
        return

    # Write the test cases to a temporary file
    with tempfile.NamedTemporaryFile(suffix="_test.py", delete=False) as temp_test_file:
        temp_test_file.write(test_cases.encode("utf-8"))
        temp_test_file_path = temp_test_file.name

    print(f"Test cases written to {temp_test_file_path}")

    # Run the test cases using unittest
    try:
        print(f"Running test cases in {temp_test_file_path}...")
        result = subprocess.run(
            ["python", "-m", "unittest", temp_test_file_path],
            capture_output=True,
            text=True
        )
        print("Test case execution completed.")
        print("Test Output:\n", result.stdout)
        print("Test Errors:\n", result.stderr)

        # Report test results
        if result.returncode == 0:
            print(f"All tests passed for {file_path}.")
        else:
            print(f"Some tests failed for {file_path}. See details above.")

    except Exception as e:
        print(f"Error running test cases for {file_path}: {e}")

    finally:
        # Clean up the temporary test file
        os.remove(temp_test_file_path)
        print(f"Temporary test file {temp_test_file_path} removed.")


def main():
    """Main function to execute the code review process."""
    print("Starting PR review bot...")

    try:
        # Load configuration
        config = load_config()

        # Validate required environment variables
        required_vars = ["GITHUB_TOKEN"]
        if "ai" in config.get("enabled_reviewers", []):
            required_vars.extend([
                "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_KEY",
                "AZURE_OPENAI_DEPLOYMENT"
            ])

        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)

        # Initialize GitHub client
        github = GitHubClient(config["github_token"])

        # Get PR details
        pr_details = github.get_pr_details()
        print(f"Analyzing PR #{pr_details.pull_number} in repo {pr_details.owner}/{pr_details.repo}")

        # Get the diff
        diff = github.get_diff(pr_details.owner, pr_details.repo, pr_details.pull_number)
        if not diff:
            print("No diff found. Exiting.")
            return

        # Parse the diff
        diff_parser = DiffParser()
        parsed_files = diff_parser.parse_diff(diff)

        # Initialize reviewers
        reviewers = get_reviewers(config)
        if not reviewers:
            print("No reviewers enabled. Exiting.")
            return

        # Collect all comments from all reviewers
        all_comments = []

        # Process each file with applicable reviewers
        for file_change in parsed_files:
            file_path = file_change.path

            if not file_path or file_path == "/dev/null":
                continue

            print(f"\nProcessing file: {file_path}")

            # Find applicable reviewers for this file
            for reviewer in reviewers:
                if reviewer.can_review_file(file_path):
                    print(f"Running {reviewer.name} on {file_path}")
                    comments = reviewer.review_file(file_path, file_change.hunks, pr_details)
                    if comments:
                        print(f"Found {len(comments)} issues with {reviewer.name}")
                        all_comments.extend(comments)

                    # Generate and run test cases
                    if hasattr(reviewer, "generate_test_cases"):
                        generate_and_run_tests(file_path, reviewer, pr_details)

        # Create review comments if we have any
        if all_comments:
            print(f"Creating {len(all_comments)} review comments")
            github.create_review_comment(
                pr_details.owner, pr_details.repo, pr_details.pull_number, all_comments
            )
        else:
            print("No issues found to comment on. Great job!")

    except Exception as e:
        print(f"Error in main execution: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()