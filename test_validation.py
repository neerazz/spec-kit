#!/usr/bin/env python3
"""
Quick test script for the validation module.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import only what we need, bypassing __init__.py
from specify_cli.backend.validation import AgentValidator

# Manually define AGENT_CONFIG for testing
AGENT_CONFIG = {
    "copilot": {"name": "GitHub Copilot", "folder": ".github/", "install_url": None, "requires_cli": False},
    "claude": {"name": "Claude Code", "folder": ".claude/", "install_url": "https://docs.anthropic.com/en/docs/claude-code/setup", "requires_cli": True},
    "gemini": {"name": "Gemini CLI", "folder": ".gemini/", "install_url": "https://github.com/google-gemini/gemini-cli", "requires_cli": True},
    "cursor-agent": {"name": "Cursor", "folder": ".cursor/", "install_url": None, "requires_cli": False},
    "qwen": {"name": "Qwen Code", "folder": ".qwen/", "install_url": "https://github.com/QwenLM/qwen-code", "requires_cli": True},
    "opencode": {"name": "opencode", "folder": ".opencode/", "install_url": "https://opencode.ai", "requires_cli": True},
    "codex": {"name": "Codex CLI", "folder": ".codex/", "install_url": "https://github.com/openai/codex", "requires_cli": True},
    "windsurf": {"name": "Windsurf", "folder": ".windsurf/", "install_url": None, "requires_cli": False},
    "kilocode": {"name": "Kilo Code", "folder": ".kilocode/", "install_url": None, "requires_cli": False},
    "auggie": {"name": "Auggie CLI", "folder": ".augment/", "install_url": "https://docs.augmentcode.com/cli/setup-auggie/install-auggie-cli", "requires_cli": True},
    "codebuddy": {"name": "CodeBuddy", "folder": ".codebuddy/", "install_url": "https://www.codebuddy.ai/cli", "requires_cli": True},
    "qoder": {"name": "Qoder CLI", "folder": ".qoder/", "install_url": "https://qoder.com/cli", "requires_cli": True},
    "roo": {"name": "Roo Code", "folder": ".roo/", "install_url": None, "requires_cli": False},
    "q": {"name": "Amazon Q Developer CLI", "folder": ".amazonq/", "install_url": "https://aws.amazon.com/developer/learning/q-developer-cli/", "requires_cli": True},
    "amp": {"name": "Amp", "folder": ".agents/", "install_url": "https://ampcode.com/manual#install", "requires_cli": True},
    "shai": {"name": "SHAI", "folder": ".shai/", "install_url": "https://github.com/ovh/shai", "requires_cli": True},
    "bob": {"name": "IBM Bob", "folder": ".bob/", "install_url": None, "requires_cli": False},
}

def test_validation():
    """Test the validation module."""
    # Get project path from command line or use current directory
    project_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    project_path = project_path.resolve()
    
    print("=" * 70)
    print("Testing Validation Module")
    print("=" * 70)
    print(f"Project root: {project_path}")
    print()
    
    # Create validator
    validator = AgentValidator(project_path, AGENT_CONFIG)
    
    # Run validation
    success, issues, warnings = validator.validate_all()
    
    print("Validation Results:")
    print("-" * 70)
    print(f"Success: {success}")
    print(f"Issues: {len(issues)}")
    print(f"Warnings: {len(warnings)}")
    print()
    
    if issues:
        print("ISSUES FOUND:")
        print("-" * 70)
        for i, issue in enumerate(issues, 1):
            agent = issue.get('agent', 'unknown')
            category = issue.get('category', 'unknown')
            message = issue.get('message', 'No message')
            file_path = issue.get('file', '')
            
            print(f"{i}. [{agent}] ({category})")
            print(f"   {message}")
            if file_path:
                print(f"   File: {file_path}")
            print()
    
    if warnings:
        print("WARNINGS FOUND:")
        print("-" * 70)
        for i, warning in enumerate(warnings, 1):
            agent = warning.get('agent', 'unknown')
            category = warning.get('category', 'unknown')
            message = warning.get('message', 'No message')
            file_path = warning.get('file', '')
            
            print(f"{i}. [{agent}] ({category})")
            print(f"   {message}")
            if file_path:
                print(f"   File: {file_path}")
            print()
    
    if not issues and not warnings:
        print("✓ No issues or warnings found!")
        print()
    
    # Print summary
    summary = validator.get_summary()
    print("Summary by Agent:")
    print("-" * 70)
    if summary['errors_by_agent']:
        print("Errors:")
        for agent, count in summary['errors_by_agent'].items():
            print(f"  {agent}: {count}")
    if summary['warnings_by_agent']:
        print("Warnings:")
        for agent, count in summary['warnings_by_agent'].items():
            print(f"  {agent}: {count}")
    print()
    
    print("=" * 70)
    print(f"Test {'PASSED' if success else 'FAILED'}")
    print("=" * 70)
    
    return success

if __name__ == "__main__":
    try:
        success = test_validation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
