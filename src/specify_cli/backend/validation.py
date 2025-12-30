"""
Agent configuration validation module for Specify CLI.

This module provides comprehensive validation for AI agent configurations
to ensure they follow proper standards and best practices.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


class AgentValidator:
    """Validates AI agent configurations against standards."""
    
    def __init__(self, project_root: Path, agent_config: Dict):
        """
        Initialize the validator.
        
        Args:
            project_root: Root directory of the project
            agent_config: Agent configuration dictionary from constants
        """
        self.project_root = project_root
        self.agent_config = agent_config
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []
    
    def validate_all(self) -> Tuple[bool, List[Dict], List[Dict]]:
        """
        Run all validation checks for all detected agents.
        
        Returns:
            Tuple of (success, issues, warnings)
        """
        detected_agents = self._detect_agents()
        
        if not detected_agents:
            self.warnings.append({
                "agent": "none",
                "category": "detection",
                "message": "No AI agent configurations detected in project"
            })
            return True, [], self.warnings
        
        for agent_key, agent_paths in detected_agents.items():
            self._validate_agent(agent_key, agent_paths)
        
        return len(self.issues) == 0, self.issues, self.warnings
    
    def _detect_agents(self) -> Dict[str, Dict]:
        """
        Detect which agents are configured in the project.
        
        Returns:
            Dictionary mapping agent_key to paths dict
        """
        detected = {}
        
        for agent_key, config in self.agent_config.items():
            folder = config["folder"]
            
            # Skip agents with no folder (like "all" which is a meta-option)
            if folder is None:
                continue
            
            agent_dir = self.project_root / folder
            
            # Check if agent directory exists
            if agent_dir.exists():
                paths = {"dir": agent_dir}
                
                # Detect specific files based on agent
                if agent_key == "claude":
                    claude_file = self.project_root / "CLAUDE.md"
                    if claude_file.exists():
                        paths["context_file"] = claude_file
                    commands_dir = agent_dir / "commands"
                    if commands_dir.exists():
                        paths["commands"] = commands_dir
                
                elif agent_key == "gemini":
                    gemini_file = self.project_root / "GEMINI.md"
                    if gemini_file.exists():
                        paths["context_file"] = gemini_file
                    commands_dir = agent_dir / "commands"
                    if commands_dir.exists():
                        paths["commands"] = commands_dir
                
                elif agent_key == "copilot":
                    agents_dir = agent_dir / "agents"
                    prompts_dir = agent_dir / "prompts"
                    if agents_dir.exists():
                        paths["agents"] = agents_dir
                    if prompts_dir.exists():
                        paths["prompts"] = prompts_dir
                    instructions = agents_dir / "copilot-instructions.md" if agents_dir.exists() else None
                    if instructions and instructions.exists():
                        paths["context_file"] = instructions
                
                elif agent_key == "cursor-agent":
                    rules_dir = agent_dir / "rules"
                    commands_dir = agent_dir / "commands"
                    if rules_dir.exists():
                        paths["rules"] = rules_dir
                        rules_file = rules_dir / "specify-rules.mdc"
                        if rules_file.exists():
                            paths["context_file"] = rules_file
                    if commands_dir.exists():
                        paths["commands"] = commands_dir
                
                elif agent_key == "qwen":
                    qwen_file = self.project_root / "QWEN.md"
                    if qwen_file.exists():
                        paths["context_file"] = qwen_file
                    commands_dir = agent_dir / "commands"
                    if commands_dir.exists():
                        paths["commands"] = commands_dir
                
                elif agent_key == "opencode":
                    command_dir = agent_dir / "command"
                    if command_dir.exists():
                        paths["commands"] = command_dir
                
                elif agent_key == "codex":
                    prompts_dir = agent_dir / "prompts"
                    if prompts_dir.exists():
                        paths["prompts"] = prompts_dir
                
                elif agent_key == "windsurf":
                    rules_dir = agent_dir / "rules"
                    workflows_dir = agent_dir / "workflows"
                    if rules_dir.exists():
                        paths["rules"] = rules_dir
                        rules_file = rules_dir / "specify-rules.md"
                        if rules_file.exists():
                            paths["context_file"] = rules_file
                    if workflows_dir.exists():
                        paths["workflows"] = workflows_dir
                
                elif agent_key == "kilocode":
                    rules_dir = agent_dir / "rules"
                    workflows_dir = agent_dir / "workflows"
                    if rules_dir.exists():
                        paths["rules"] = rules_dir
                        rules_file = rules_dir / "specify-rules.md"
                        if rules_file.exists():
                            paths["context_file"] = rules_file
                    if workflows_dir.exists():
                        paths["workflows"] = workflows_dir
                
                elif agent_key == "auggie":
                    rules_dir = agent_dir / "rules"
                    commands_dir = agent_dir / "commands"
                    if rules_dir.exists():
                        paths["rules"] = rules_dir
                        rules_file = rules_dir / "specify-rules.md"
                        if rules_file.exists():
                            paths["context_file"] = rules_file
                    if commands_dir.exists():
                        paths["commands"] = commands_dir
                
                elif agent_key == "roo":
                    rules_dir = agent_dir / "rules"
                    if rules_dir.exists():
                        paths["rules"] = rules_dir
                        rules_file = rules_dir / "specify-rules.md"
                        if rules_file.exists():
                            paths["context_file"] = rules_file
                
                elif agent_key == "codebuddy":
                    codebuddy_file = self.project_root / "CODEBUDDY.md"
                    if codebuddy_file.exists():
                        paths["context_file"] = codebuddy_file
                    commands_dir = agent_dir / "commands"
                    if commands_dir.exists():
                        paths["commands"] = commands_dir
                
                elif agent_key == "qoder":
                    qoder_file = self.project_root / "QODER.md"
                    if qoder_file.exists():
                        paths["context_file"] = qoder_file
                    commands_dir = agent_dir / "commands"
                    if commands_dir.exists():
                        paths["commands"] = commands_dir
                
                elif agent_key in ["q", "amp", "bob"]:
                    # These agents may share AGENTS.md
                    agents_file = self.project_root / "AGENTS.md"
                    if agents_file.exists():
                        paths["context_file"] = agents_file
                    
                    if agent_key == "q":
                        prompts_dir = agent_dir / "prompts"
                        if prompts_dir.exists():
                            paths["prompts"] = prompts_dir
                    elif agent_key == "amp":
                        commands_dir = agent_dir / "commands"
                        if commands_dir.exists():
                            paths["commands"] = commands_dir
                    elif agent_key == "bob":
                        commands_dir = agent_dir / "commands"
                        if commands_dir.exists():
                            paths["commands"] = commands_dir
                
                elif agent_key == "shai":
                    shai_file = self.project_root / "SHAI.md"
                    if shai_file.exists():
                        paths["context_file"] = shai_file
                    commands_dir = agent_dir / "commands"
                    if commands_dir.exists():
                        paths["commands"] = commands_dir
                
                if paths.keys() != {"dir"}:  # Has more than just the directory
                    detected[agent_key] = paths
        
        return detected
    
    def _validate_agent(self, agent_key: str, paths: Dict):
        """
        Validate a specific agent configuration.
        
        Args:
            agent_key: Agent identifier
            paths: Dictionary of detected paths for this agent
        """
        config = self.agent_config[agent_key]
        agent_name = config["name"]
        
        # Check directory structure
        self._check_directory_structure(agent_key, agent_name, paths)
        
        # Check command files
        if "commands" in paths:
            self._check_command_files(agent_key, agent_name, paths["commands"])
        elif "workflows" in paths:
            self._check_command_files(agent_key, agent_name, paths["workflows"], "workflow")
        elif "prompts" in paths:
            self._check_command_files(agent_key, agent_name, paths["prompts"], "prompt")
        
        # Check context files
        if "context_file" in paths:
            self._check_context_file(agent_key, agent_name, paths["context_file"])
        
        # Check for expected spec-kit commands
        self._check_required_commands(agent_key, agent_name, paths)
    
    def _check_directory_structure(self, agent_key: str, agent_name: str, paths: Dict):
        """Check if directory structure follows standards."""
        config = self.agent_config[agent_key]
        expected_folder = config["folder"]
        
        if "dir" not in paths:
            self.issues.append({
                "agent": agent_key,
                "category": "structure",
                "severity": "error",
                "message": f"Agent directory not found: {expected_folder}"
            })
            return
        
        # Check for required subdirectories based on agent type
        agent_dir = paths["dir"]
        
        # Markdown-based agents should have commands/workflows/prompts
        if agent_key in ["claude", "gemini", "cursor-agent", "qwen", "opencode", "codebuddy", "qoder", "shai"]:
            commands_dir = agent_dir / "commands"
            if not commands_dir.exists():
                self.warnings.append({
                    "agent": agent_key,
                    "category": "structure",
                    "message": f"Expected commands directory not found: {commands_dir.relative_to(self.project_root)}"
                })
        
        elif agent_key == "copilot":
            agents_dir = agent_dir / "agents"
            prompts_dir = agent_dir / "prompts"
            if not agents_dir.exists():
                self.issues.append({
                    "agent": agent_key,
                    "category": "structure",
                    "severity": "error",
                    "message": f"Expected agents directory not found: {agents_dir.relative_to(self.project_root)}"
                })
            if not prompts_dir.exists():
                self.warnings.append({
                    "agent": agent_key,
                    "category": "structure",
                    "message": f"Expected prompts directory not found: {prompts_dir.relative_to(self.project_root)}"
                })
        
        elif agent_key in ["windsurf", "kilocode"]:
            workflows_dir = agent_dir / "workflows"
            rules_dir = agent_dir / "rules"
            if not workflows_dir.exists():
                self.warnings.append({
                    "agent": agent_key,
                    "category": "structure",
                    "message": f"Expected workflows directory not found: {workflows_dir.relative_to(self.project_root)}"
                })
            if not rules_dir.exists():
                self.warnings.append({
                    "agent": agent_key,
                    "category": "structure",
                    "message": f"Expected rules directory not found: {rules_dir.relative_to(self.project_root)}"
                })
    
    def _check_command_files(self, agent_key: str, agent_name: str, commands_dir: Path, file_type: str = "command"):
        """Check command/workflow/prompt files for standards compliance."""
        if not commands_dir.exists():
            return
        
        # Get expected file extension
        extension = self._get_expected_extension(agent_key)
        
        # List all command files
        command_files = list(commands_dir.glob(f"*.{extension}"))
        
        if not command_files:
            self.warnings.append({
                "agent": agent_key,
                "category": "commands",
                "message": f"No {file_type} files found in {commands_dir.relative_to(self.project_root)}"
            })
            return
        
        # Check each command file
        for cmd_file in command_files:
            self._validate_command_file(agent_key, agent_name, cmd_file, file_type)
    
    def _validate_command_file(self, agent_key: str, agent_name: str, cmd_file: Path, file_type: str):
        """Validate individual command file structure and content."""
        try:
            content = cmd_file.read_text(encoding="utf-8")
        except Exception as e:
            self.issues.append({
                "agent": agent_key,
                "category": "commands",
                "severity": "error",
                "file": str(cmd_file.relative_to(self.project_root)),
                "message": f"Failed to read {file_type} file: {e}"
            })
            return
        
        # Check format-specific requirements
        if agent_key in ["gemini", "qwen"]:
            # TOML format
            self._validate_toml_format(agent_key, cmd_file, content)
        elif agent_key == "copilot":
            # Copilot agent.md format
            self._validate_copilot_format(agent_key, cmd_file, content)
        else:
            # Standard markdown format
            self._validate_markdown_format(agent_key, cmd_file, content)
    
    def _validate_markdown_format(self, agent_key: str, cmd_file: Path, content: str):
        """Validate markdown command file format."""
        relative_path = cmd_file.relative_to(self.project_root)
        
        # Check for YAML frontmatter
        if not content.startswith("---"):
            self.issues.append({
                "agent": agent_key,
                "category": "format",
                "severity": "error",
                "file": str(relative_path),
                "message": "Missing YAML frontmatter (should start with ---)"
            })
            return
        
        # Extract frontmatter
        parts = content.split("---", 2)
        if len(parts) < 3:
            self.issues.append({
                "agent": agent_key,
                "category": "format",
                "severity": "error",
                "file": str(relative_path),
                "message": "Invalid YAML frontmatter format"
            })
            return
        
        frontmatter = parts[1]
        body = parts[2]
        
        # Check for required description field
        if not re.search(r'^\s*description:', frontmatter, re.MULTILINE):
            self.issues.append({
                "agent": agent_key,
                "category": "format",
                "severity": "error",
                "file": str(relative_path),
                "message": "Missing 'description:' field in YAML frontmatter"
            })
        
        # Check for script placeholders in body
        if "{SCRIPT}" not in body and "scripts/" not in body.lower():
            self.warnings.append({
                "agent": agent_key,
                "category": "content",
                "file": str(relative_path),
                "message": "No {SCRIPT} placeholder or script reference found in command body"
            })
        
        # Check for argument placeholder
        if "$ARGUMENTS" not in body and "{ARGS}" not in body and "{{args}}" not in body:
            self.warnings.append({
                "agent": agent_key,
                "category": "content",
                "file": str(relative_path),
                "message": "No argument placeholder ($ARGUMENTS, {ARGS}, {{args}}) found in command body"
            })
    
    def _validate_toml_format(self, agent_key: str, cmd_file: Path, content: str):
        """Validate TOML command file format."""
        relative_path = cmd_file.relative_to(self.project_root)
        
        # Check for required fields
        if not re.search(r'^\s*description\s*=', content, re.MULTILINE):
            self.issues.append({
                "agent": agent_key,
                "category": "format",
                "severity": "error",
                "file": str(relative_path),
                "message": "Missing 'description =' field in TOML file"
            })
        
        if not re.search(r'^\s*prompt\s*=', content, re.MULTILINE):
            self.issues.append({
                "agent": agent_key,
                "category": "format",
                "severity": "error",
                "file": str(relative_path),
                "message": "Missing 'prompt =' field in TOML file"
            })
        
        # Check for proper argument format in TOML ({{args}})
        if "{{args}}" not in content and "$ARGUMENTS" in content:
            self.warnings.append({
                "agent": agent_key,
                "category": "format",
                "file": str(relative_path),
                "message": "TOML format should use {{args}} instead of $ARGUMENTS"
            })
    
    def _validate_copilot_format(self, agent_key: str, cmd_file: Path, content: str):
        """Validate GitHub Copilot agent.md format."""
        relative_path = cmd_file.relative_to(self.project_root)
        
        # Copilot format should have YAML frontmatter with mode field
        if not content.startswith("---"):
            self.issues.append({
                "agent": agent_key,
                "category": "format",
                "severity": "error",
                "file": str(relative_path),
                "message": "Missing YAML frontmatter (should start with ---)"
            })
            return
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            self.issues.append({
                "agent": agent_key,
                "category": "format",
                "severity": "error",
                "file": str(relative_path),
                "message": "Invalid YAML frontmatter format"
            })
            return
        
        frontmatter = parts[1]
        
        # Check for mode field (Copilot-specific)
        if not re.search(r'^\s*mode:', frontmatter, re.MULTILINE):
            self.warnings.append({
                "agent": agent_key,
                "category": "format",
                "file": str(relative_path),
                "message": "Missing 'mode:' field in YAML frontmatter (recommended for Copilot)"
            })
        
        # Check for description
        if not re.search(r'^\s*description:', frontmatter, re.MULTILINE):
            self.issues.append({
                "agent": agent_key,
                "category": "format",
                "severity": "error",
                "file": str(relative_path),
                "message": "Missing 'description:' field in YAML frontmatter"
            })
    
    def _check_context_file(self, agent_key: str, agent_name: str, context_file: Path):
        """Check agent context file for standards compliance."""
        relative_path = context_file.relative_to(self.project_root)
        
        try:
            content = context_file.read_text(encoding="utf-8")
        except Exception as e:
            self.issues.append({
                "agent": agent_key,
                "category": "context",
                "severity": "error",
                "file": str(relative_path),
                "message": f"Failed to read context file: {e}"
            })
            return
        
        # Check for manual additions markers (if applicable)
        if "<!-- MANUAL ADDITIONS START -->" in content:
            if "<!-- MANUAL ADDITIONS END -->" not in content:
                self.warnings.append({
                    "agent": agent_key,
                    "category": "context",
                    "file": str(relative_path),
                    "message": "Found MANUAL ADDITIONS START marker but missing END marker"
                })
        
        # Check for project name placeholder
        if "[PROJECT NAME]" in content:
            self.warnings.append({
                "agent": agent_key,
                "category": "context",
                "file": str(relative_path),
                "message": "Context file contains unreplaced [PROJECT NAME] placeholder"
            })
        
        # Check for date placeholder
        if "[DATE]" in content:
            self.warnings.append({
                "agent": agent_key,
                "category": "context",
                "file": str(relative_path),
                "message": "Context file contains unreplaced [DATE] placeholder"
            })
        
        # Check for active technologies section
        if "Active Technologies" not in content and "Technologies" not in content:
            self.warnings.append({
                "agent": agent_key,
                "category": "context",
                "file": str(relative_path),
                "message": "Context file may be missing 'Active Technologies' section"
            })
    
    def _check_required_commands(self, agent_key: str, agent_name: str, paths: Dict):
        """Check for expected spec-kit commands."""
        required_commands = [
            "specify", "plan", "tasks", "implement",
            "constitution", "clarify", "analyze", "checklist"
        ]
        
        # Determine which directory to check
        commands_dir = None
        if "commands" in paths:
            commands_dir = paths["commands"]
        elif "workflows" in paths:
            commands_dir = paths["workflows"]
        elif "prompts" in paths:
            commands_dir = paths["prompts"]
        elif "agents" in paths:
            commands_dir = paths["agents"]
        
        if not commands_dir or not commands_dir.exists():
            return
        
        # Get expected extension
        extension = self._get_expected_extension(agent_key)
        
        # Check for each required command
        missing_commands = []
        for cmd in required_commands:
            # Special handling for Copilot (uses different naming)
            if agent_key == "copilot":
                cmd_file = commands_dir / f"speckit-{cmd}.agent.md"
            else:
                cmd_file = commands_dir / f"{cmd}.{extension}"
            
            if not cmd_file.exists():
                missing_commands.append(cmd)
        
        if missing_commands:
            self.warnings.append({
                "agent": agent_key,
                "category": "commands",
                "message": f"Missing expected spec-kit commands: {', '.join(missing_commands)}"
            })
    
    def _get_expected_extension(self, agent_key: str) -> str:
        """Get the expected file extension for an agent's command files."""
        if agent_key in ["gemini", "qwen"]:
            return "toml"
        elif agent_key == "copilot":
            return "agent.md"
        else:
            return "md"
    
    def get_summary(self) -> Dict:
        """Get a summary of validation results."""
        return {
            "total_issues": len(self.issues),
            "total_warnings": len(self.warnings),
            "errors_by_agent": self._group_by_agent(self.issues),
            "warnings_by_agent": self._group_by_agent(self.warnings),
        }
    
    def _group_by_agent(self, items: List[Dict]) -> Dict[str, int]:
        """Group items by agent."""
        grouped = {}
        for item in items:
            agent = item.get("agent", "unknown")
            grouped[agent] = grouped.get(agent, 0) + 1
        return grouped


def validate_agent_standards(project_root: Path, agent_config: Dict) -> Tuple[bool, List[Dict], List[Dict]]:
    """
    Validate all agent configurations in a project.
    
    Args:
        project_root: Root directory of the project
        agent_config: Agent configuration dictionary from constants
    
    Returns:
        Tuple of (success, issues, warnings)
    """
    validator = AgentValidator(project_root, agent_config)
    return validator.validate_all()

