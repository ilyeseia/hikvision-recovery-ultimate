name: Pull Request Template
description: Standard PR template for Hikvision Recovery
title: "[PR]: "
labels: ["needs-review"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for contributing! Please fill out the form below.

  - type: checkboxes
    id: checklist
    attributes:
      label: Checklist
      options:
        - label: I have read the CONTRIBUTING.md guide
        - label: My code follows the project's style guidelines (ruff, black)
        - label: I have added tests for my changes
        - label: All tests pass locally
        - label: I have updated documentation if needed
        - label: My changes don't break existing functionality

  - type: dropdown
    id: type
    attributes:
      label: Type of Change
      options:
        - Bug fix
        - New feature
        - Breaking change
        - Documentation update
        - Code refactoring
        - Performance improvement
        - Test addition/improvement
        - CI/CD improvement
        - Dependency update
        - Other
    validations:
      required: true

  - type: textarea
    id: description
    attributes:
      label: Description
      description: What does this PR do? Why is it needed?
      placeholder: Describe the changes...
    validations:
      required: true

  - type: textarea
    id: related
    attributes:
      label: Related Issues/PRs
      description: Link any related issues or PRs
      placeholder: |
        Fixes #123
        Related to #456

  - type: textarea
    id: testing
    attributes:
      label: Testing
      description: How did you test your changes?
      placeholder: |
        - Ran `pytest tests/ -v`
        - Tested against Hikvision DS-7608NI-K2
        - Verified CLI commands work

  - type: checkboxes
    id: breaking
    attributes:
      label: Breaking Changes
      options:
        - label: This PR introduces breaking changes
        - label: Migration guide needed
        - label: Documentation updated

  - type: textarea
    id: screenshots
    attributes:
      label: Screenshots/Logs (if applicable)
      description: Add screenshots or logs for UI/CLI changes
      placeholder: Paste screenshots or relevant logs here...

  - type: checkboxes
    id: docs
    attributes:
      label: Documentation
      options:
        - label: README updated
        - label: Docstrings updated
        - label: CLI help text updated
        - label: Changelog entry added
        - label: No documentation needed