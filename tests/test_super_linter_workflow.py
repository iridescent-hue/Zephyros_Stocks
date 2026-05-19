"""
Tests for .github/workflows/super-linter.yml

Validates that the GitHub Actions Super Linter workflow is correctly configured,
including trigger events, job structure, steps, and environment variables.
"""

import os
import unittest

import yaml

WORKFLOW_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    ".github",
    "workflows",
    "super-linter.yml",
)


def load_workflow():
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)
    # PyYAML (YAML 1.1) parses the bare key `on` as Python boolean True.
    # Normalise it back to the string "on" so tests can use intuitive key names.
    if isinstance(workflow, dict) and True in workflow and "on" not in workflow:
        workflow["on"] = workflow.pop(True)
    return workflow


class TestWorkflowFileExists(unittest.TestCase):
    """Tests that the workflow file is present and readable."""

    def test_file_exists(self):
        self.assertTrue(
            os.path.isfile(WORKFLOW_PATH),
            f"Workflow file not found at {WORKFLOW_PATH}",
        )

    def test_file_is_valid_yaml(self):
        """YAML should parse without raising an exception."""
        try:
            workflow = load_workflow()
        except yaml.YAMLError as exc:
            self.fail(f"Workflow YAML is invalid: {exc}")
        self.assertIsInstance(workflow, dict)

    def test_file_is_not_empty(self):
        workflow = load_workflow()
        self.assertTrue(len(workflow) > 0, "Workflow YAML should not be empty")


class TestWorkflowName(unittest.TestCase):
    """Tests the top-level workflow name."""

    def setUp(self):
        self.workflow = load_workflow()

    def test_workflow_name_present(self):
        self.assertIn("name", self.workflow, "Workflow must have a 'name' field")

    def test_workflow_name_value(self):
        self.assertEqual(
            self.workflow["name"],
            "Lint Code Base",
            "Workflow name should be 'Lint Code Base'",
        )


class TestWorkflowTriggers(unittest.TestCase):
    """Tests the 'on' trigger configuration."""

    def setUp(self):
        self.workflow = load_workflow()
        self.on = self.workflow.get("on", {})

    def test_on_field_present(self):
        self.assertIn("on", self.workflow, "Workflow must have an 'on' trigger field")

    def test_push_trigger_present(self):
        self.assertIn("push", self.on, "Workflow must trigger on 'push' events")

    def test_pull_request_trigger_present(self):
        self.assertIn(
            "pull_request", self.on, "Workflow must trigger on 'pull_request' events"
        )

    def test_push_triggers_on_main_branch(self):
        push_branches = self.on["push"].get("branches", [])
        self.assertIn(
            "main",
            push_branches,
            "Push trigger must include the 'main' branch",
        )

    def test_push_triggers_only_on_main_branch(self):
        """Regression: push should only trigger on 'main', not on arbitrary branches."""
        push_branches = self.on["push"].get("branches", [])
        self.assertEqual(
            push_branches,
            ["main"],
            "Push trigger should only be scoped to the 'main' branch",
        )

    def test_pull_request_triggers_on_main_branch(self):
        pr_branches = self.on["pull_request"].get("branches", [])
        self.assertIn(
            "main",
            pr_branches,
            "Pull request trigger must include the 'main' branch",
        )

    def test_pull_request_triggers_only_on_main_branch(self):
        """Regression: PR trigger should only target 'main', not arbitrary branches."""
        pr_branches = self.on["pull_request"].get("branches", [])
        self.assertEqual(
            pr_branches,
            ["main"],
            "Pull request trigger should only be scoped to the 'main' branch",
        )

    def test_no_unexpected_trigger_types(self):
        """Boundary: workflow should not include unexpected additional triggers."""
        allowed_triggers = {"push", "pull_request"}
        actual_triggers = set(self.on.keys())
        unexpected = actual_triggers - allowed_triggers
        self.assertEqual(
            unexpected,
            set(),
            f"Unexpected trigger type(s) found: {unexpected}",
        )


class TestWorkflowJobs(unittest.TestCase):
    """Tests the jobs section structure."""

    def setUp(self):
        self.workflow = load_workflow()
        self.jobs = self.workflow.get("jobs", {})

    def test_jobs_field_present(self):
        self.assertIn("jobs", self.workflow, "Workflow must have a 'jobs' field")

    def test_run_lint_job_exists(self):
        self.assertIn(
            "run-lint", self.jobs, "A job named 'run-lint' must exist"
        )

    def test_exactly_one_job(self):
        self.assertEqual(
            len(self.jobs),
            1,
            "Workflow should define exactly one job",
        )

    def test_job_runs_on_ubuntu_latest(self):
        runs_on = self.jobs["run-lint"].get("runs-on")
        self.assertEqual(
            runs_on,
            "ubuntu-latest",
            "The run-lint job should run on ubuntu-latest",
        )

    def test_job_has_steps(self):
        steps = self.jobs["run-lint"].get("steps", [])
        self.assertTrue(len(steps) > 0, "The run-lint job must have at least one step")

    def test_job_has_exactly_two_steps(self):
        steps = self.jobs["run-lint"].get("steps", [])
        self.assertEqual(
            len(steps),
            2,
            "The run-lint job should have exactly 2 steps",
        )


class TestCheckoutStep(unittest.TestCase):
    """Tests the first step: actions/checkout."""

    def setUp(self):
        workflow = load_workflow()
        self.steps = workflow["jobs"]["run-lint"]["steps"]
        self.checkout_step = self.steps[0]

    def test_checkout_step_name(self):
        self.assertEqual(
            self.checkout_step.get("name"),
            "Checkout code",
            "First step should be named 'Checkout code'",
        )

    def test_checkout_step_uses_correct_action(self):
        self.assertEqual(
            self.checkout_step.get("uses"),
            "actions/checkout@v4",
            "Checkout step must use actions/checkout@v4",
        )

    def test_checkout_step_has_with_config(self):
        self.assertIn(
            "with",
            self.checkout_step,
            "Checkout step must have a 'with' configuration block",
        )

    def test_checkout_fetch_depth_is_zero(self):
        """Full git history (fetch-depth: 0) is required for super-linter to detect changed files."""
        fetch_depth = self.checkout_step["with"].get("fetch-depth")
        self.assertEqual(
            fetch_depth,
            0,
            "fetch-depth must be 0 to retrieve full git history for super-linter",
        )

    def test_checkout_fetch_depth_is_not_shallow(self):
        """Boundary: fetch-depth must not be 1 (shallow clone), which would break super-linter."""
        fetch_depth = self.checkout_step["with"].get("fetch-depth")
        self.assertNotEqual(
            fetch_depth,
            1,
            "fetch-depth must not be 1 (shallow clone breaks super-linter changed file detection)",
        )


class TestSuperLinterStep(unittest.TestCase):
    """Tests the second step: github/super-linter."""

    def setUp(self):
        workflow = load_workflow()
        self.steps = workflow["jobs"]["run-lint"]["steps"]
        self.linter_step = self.steps[1]

    def test_linter_step_name(self):
        self.assertEqual(
            self.linter_step.get("name"),
            "Lint Code Base",
            "Second step should be named 'Lint Code Base'",
        )

    def test_linter_step_uses_correct_action(self):
        self.assertEqual(
            self.linter_step.get("uses"),
            "github/super-linter@v4",
            "Linter step must use github/super-linter@v4",
        )

    def test_linter_step_has_env_block(self):
        self.assertIn(
            "env",
            self.linter_step,
            "Linter step must have an 'env' configuration block",
        )


class TestSuperLinterEnvVars(unittest.TestCase):
    """Tests the environment variables passed to super-linter."""

    def setUp(self):
        workflow = load_workflow()
        self.env = workflow["jobs"]["run-lint"]["steps"][1].get("env", {})

    def test_validate_all_codebase_is_present(self):
        self.assertIn(
            "VALIDATE_ALL_CODEBASE",
            self.env,
            "VALIDATE_ALL_CODEBASE env var must be set",
        )

    def test_validate_all_codebase_is_false(self):
        """Only changed files should be linted, not the entire codebase."""
        self.assertIs(
            self.env["VALIDATE_ALL_CODEBASE"],
            False,
            "VALIDATE_ALL_CODEBASE must be false to lint only changed files",
        )

    def test_default_branch_is_present(self):
        self.assertIn(
            "DEFAULT_BRANCH",
            self.env,
            "DEFAULT_BRANCH env var must be set",
        )

    def test_default_branch_is_main(self):
        self.assertEqual(
            self.env["DEFAULT_BRANCH"],
            "main",
            "DEFAULT_BRANCH must be set to 'main'",
        )

    def test_github_token_is_present(self):
        self.assertIn(
            "GITHUB_TOKEN",
            self.env,
            "GITHUB_TOKEN env var must be set for super-linter authentication",
        )

    def test_github_token_references_secret(self):
        """GITHUB_TOKEN must reference the built-in GITHUB_TOKEN secret, not a hardcoded value."""
        token_value = self.env["GITHUB_TOKEN"]
        self.assertIn(
            "secrets.GITHUB_TOKEN",
            token_value,
            "GITHUB_TOKEN must reference '${{ secrets.GITHUB_TOKEN }}'",
        )

    def test_github_token_is_not_hardcoded(self):
        """Boundary/security: token must not be a hardcoded string literal."""
        token_value = self.env["GITHUB_TOKEN"]
        self.assertTrue(
            token_value.strip().startswith("${{"),
            "GITHUB_TOKEN must use a GitHub Actions expression, not a hardcoded value",
        )

    def test_no_unexpected_env_vars(self):
        """Regression: no extra undocumented env vars should be present."""
        expected_keys = {"VALIDATE_ALL_CODEBASE", "DEFAULT_BRANCH", "GITHUB_TOKEN"}
        actual_keys = set(self.env.keys())
        unexpected = actual_keys - expected_keys
        self.assertEqual(
            unexpected,
            set(),
            f"Unexpected env var(s) found in linter step: {unexpected}",
        )

    def test_all_required_env_vars_present(self):
        """Boundary: all three required env vars must be set simultaneously."""
        required = {"VALIDATE_ALL_CODEBASE", "DEFAULT_BRANCH", "GITHUB_TOKEN"}
        missing = required - set(self.env.keys())
        self.assertEqual(
            missing,
            set(),
            f"Required env var(s) missing from linter step: {missing}",
        )


class TestWorkflowIntegrity(unittest.TestCase):
    """High-level structural integrity tests for the full workflow."""

    def setUp(self):
        self.workflow = load_workflow()

    def test_required_top_level_keys_present(self):
        """Workflow must have name, on, and jobs at the top level."""
        for key in ("name", "on", "jobs"):
            self.assertIn(key, self.workflow, f"Top-level key '{key}' is missing")

    def test_step_order_checkout_before_lint(self):
        """Checkout must come before the linter step."""
        steps = self.workflow["jobs"]["run-lint"]["steps"]
        names = [s.get("name") for s in steps]
        checkout_idx = names.index("Checkout code")
        linter_idx = names.index("Lint Code Base")
        self.assertLess(
            checkout_idx,
            linter_idx,
            "Checkout step must appear before the Lint Code Base step",
        )

    def test_super_linter_version_pinned_to_v4(self):
        """Regression: super-linter action must be pinned to v4, not an unpinned 'latest'."""
        linter_uses = self.workflow["jobs"]["run-lint"]["steps"][1]["uses"]
        self.assertNotIn(
            "latest",
            linter_uses.lower(),
            "super-linter action should be pinned to a specific version, not 'latest'",
        )
        self.assertTrue(
            linter_uses.endswith("@v4"),
            f"super-linter action should end with '@v4', got: {linter_uses}",
        )

    def test_checkout_action_version_pinned_to_v4(self):
        """Regression: checkout action must be pinned to v4, not 'latest'."""
        checkout_uses = self.workflow["jobs"]["run-lint"]["steps"][0]["uses"]
        self.assertNotIn(
            "latest",
            checkout_uses.lower(),
            "checkout action should be pinned to a specific version, not 'latest'",
        )
        self.assertTrue(
            checkout_uses.endswith("@v4"),
            f"checkout action should end with '@v4', got: {checkout_uses}",
        )


if __name__ == "__main__":
    unittest.main()
