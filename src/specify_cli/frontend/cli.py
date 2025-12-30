import sys
import shutil
import typer
import httpx
import os
import shlex
import ssl
from pathlib import Path
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.align import Align
from typer.core import TyperGroup
from datetime import datetime

from specify_cli.data.constants import AGENT_CONFIG, SCRIPT_TYPE_CHOICES, ALL_AGENTS_KEY
from specify_cli.frontend.ui import show_banner, console, select_with_arrows, StepTracker
from specify_cli.backend.system import check_tool, ensure_executable_scripts, detect_installed_agents
from specify_cli.backend.git import is_git_repo, init_git_repo
from specify_cli.backend.project import download_and_extract_template
from specify_cli.backend.github import _github_auth_headers
from specify_cli.backend.validation import validate_agent_standards

class BannerGroup(TyperGroup):
    """Custom group that shows banner before help."""

    def format_help(self, ctx, formatter):
        # Show banner before help
        show_banner()
        super().format_help(ctx, formatter)

app = typer.Typer(
    name="specify",
    help="Setup tool for Specify spec-driven development projects",
    add_completion=False,
    invoke_without_command=True,
    cls=BannerGroup,
)

@app.callback()
def callback(ctx: typer.Context):
    """Show banner when no subcommand is provided."""
    if ctx.invoked_subcommand is None and "--help" not in sys.argv and "-h" not in sys.argv:
        show_banner()
        console.print(Align.center("[dim]Run 'specify --help' for usage information[/dim]"))
        console.print()

@app.command()
def init(
    project_name: str = typer.Argument(None, help="Name for your new project directory (optional if using --here, or use '.' for current directory)"),
    ai_assistant: str = typer.Option(None, "--ai", help="AI assistant: all (ALL agents), claude, gemini, copilot, cursor-agent, qwen, opencode, codex, windsurf, kilocode, auggie, codebuddy, amp, shai, q, bob, or qoder"),
    script_type: str = typer.Option(None, "--script", help="Script type to use: sh or ps"),
    ignore_agent_tools: bool = typer.Option(False, "--ignore-agent-tools", help="Skip checks for AI agent tools like Claude Code"),
    no_git: bool = typer.Option(False, "--no-git", help="Skip git repository initialization"),
    here: bool = typer.Option(False, "--here", help="Initialize project in the current directory instead of creating a new one"),
    force: bool = typer.Option(False, "--force", help="Force merge/overwrite when using --here (skip confirmation)"),
    skip_tls: bool = typer.Option(False, "--skip-tls", help="Skip SSL/TLS verification (not recommended)"),
    debug: bool = typer.Option(False, "--debug", help="Show verbose diagnostic output for network and extraction failures"),
    github_token: str = typer.Option(None, "--github-token", help="GitHub token to use for API requests (or set GH_TOKEN or GITHUB_TOKEN environment variable)"),
):
    """
    Initialize a new Specify project from the latest template.

    This command will:
    1. Check that required tools are installed (git is optional)
    2. Let you choose your AI assistant (or 'all' for ALL agents)
    3. Download the appropriate template from GitHub
    4. Extract the template to a new project directory or current directory
    5. Initialize a fresh git repository (if not --no-git and no existing repo)
    6. Optionally set up AI assistant commands

    Examples:
        specify init my-project
        specify init my-project --ai all           # Initialize with ALL AI agents
        specify init my-project --ai claude
        specify init my-project --ai copilot --no-git
        specify init --ignore-agent-tools my-project
        specify init . --ai all            # Initialize in current directory with ALL agents
        specify init . --ai claude         # Initialize in current directory
        specify init .                     # Initialize in current directory (interactive AI selection)
        specify init --here --ai all       # Alternative syntax for current directory with ALL agents
        specify init --here --ai claude    # Alternative syntax for current directory
        specify init --here --ai codex
        specify init --here --ai codebuddy
        specify init --here
        specify init --here --force  # Skip confirmation when current directory not empty
    """

    show_banner()

    if project_name == ".":
        here = True
        project_name = None  # Clear project_name to use existing validation logic

    if here and project_name:
        console.print("[red]Error:[/red] Cannot specify both project name and --here flag")
        raise typer.Exit(1)

    if not here and not project_name:
        console.print("[red]Error:[/red] Must specify either a project name, use '.' for current directory, or use --here flag")
        raise typer.Exit(1)

    if here:
        project_name = Path.cwd().name
        project_path = Path.cwd()

        existing_items = list(project_path.iterdir())
        if existing_items:
            console.print(f"[yellow]Warning:[/yellow] Current directory is not empty ({len(existing_items)} items)")
            console.print("[yellow]Template files will be merged with existing content and may overwrite existing files[/yellow]")
            if force:
                console.print("[cyan]--force supplied: skipping confirmation and proceeding with merge[/cyan]")
            else:
                response = typer.confirm("Do you want to continue?")
                if not response:
                    console.print("[yellow]Operation cancelled[/yellow]")
                    raise typer.Exit(0)
    else:
        project_path = Path(project_name).resolve()
        if project_path.exists():
            error_panel = Panel(
                f"Directory '[cyan]{project_name}[/cyan]' already exists\n"
                "Please choose a different project name or remove the existing directory.",
                title="[red]Directory Conflict[/red]",
                border_style="red",
                padding=(1, 2)
            )
            console.print()
            console.print(error_panel)
            raise typer.Exit(1)

    current_dir = Path.cwd()

    setup_lines = [
        "[cyan]Specify Project Setup[/cyan]",
        "",
        f"{'Project':<15} [green]{project_path.name}[/green]",
        f"{'Working Path':<15} [dim]{current_dir}[/dim]",
    ]

    if not here:
        setup_lines.append(f"{'Target Path':<15} [dim]{project_path}[/dim]")

    console.print(Panel("\n".join(setup_lines), border_style="cyan", padding=(1, 2)))

    should_init_git = False
    if not no_git:
        should_init_git = check_tool("git")
        if not should_init_git:
            console.print("[yellow]Git not found - will skip repository initialization[/yellow]")

    if ai_assistant:
        if ai_assistant not in AGENT_CONFIG:
            console.print(f"[red]Error:[/red] Invalid AI assistant '{ai_assistant}'. Choose from: {', '.join(AGENT_CONFIG.keys())}")
            raise typer.Exit(1)
        selected_ai = ai_assistant
    else:
        # Create options dict for selection (agent_key: display_name)
        ai_choices = {key: config["name"] for key, config in AGENT_CONFIG.items()}
        selected_ai = select_with_arrows(
            ai_choices,
            "Choose your AI assistant (or 'all' for all detected agents):",
            "all"  # Default to "all" - installs templates for all detected agents
        )

    # Skip agent tool checks when initializing all agents (no single tool to check)
    if not ignore_agent_tools and selected_ai != ALL_AGENTS_KEY:
        agent_config = AGENT_CONFIG.get(selected_ai)
        if agent_config and agent_config["requires_cli"]:
            install_url = agent_config["install_url"]
            if not check_tool(selected_ai):
                error_panel = Panel(
                    f"[cyan]{selected_ai}[/cyan] not found\n"
                    f"Install from: [cyan]{install_url}[/cyan]\n"
                    f"{agent_config['name']} is required to continue with this project type.\n\n"
                    "Tip: Use [cyan]--ignore-agent-tools[/cyan] to skip this check",
                    title="[red]Agent Detection Error[/red]",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print()
                console.print(error_panel)
                raise typer.Exit(1)

    if script_type:
        if script_type not in SCRIPT_TYPE_CHOICES:
            console.print(f"[red]Error:[/red] Invalid script type '{script_type}'. Choose from: {', '.join(SCRIPT_TYPE_CHOICES.keys())}")
            raise typer.Exit(1)
        selected_script = script_type
    else:
        default_script = "ps" if os.name == "nt" else "sh"

        if sys.stdin.isatty():
            selected_script = select_with_arrows(SCRIPT_TYPE_CHOICES, "Choose script type (or press Enter)", default_script)
        else:
            selected_script = default_script

    # Determine which agents to install
    agents_to_install = []
    if selected_ai == ALL_AGENTS_KEY:
        # Detect installed agents
        agents_to_install = detect_installed_agents(AGENT_CONFIG)
        if not agents_to_install:
            console.print("[yellow]No AI agents detected. Installing copilot as default.[/yellow]")
            agents_to_install = ["copilot"]
        console.print(f"[cyan]Detected agents:[/cyan] {', '.join(agents_to_install)}")
    else:
        agents_to_install = [selected_ai]
    
    console.print(f"[cyan]Selected AI assistant:[/cyan] {selected_ai}")
    console.print(f"[cyan]Selected script type:[/cyan] {selected_script}")
    if selected_ai == ALL_AGENTS_KEY:
        console.print(f"[cyan]Installing templates for:[/cyan] {len(agents_to_install)} agent(s)")

    tracker = StepTracker("Initialize Specify Project")

    sys._specify_tracker_active = True

    tracker.add("precheck", "Check required tools")
    tracker.complete("precheck", "ok")
    tracker.add("ai-select", "Select AI assistant")
    tracker.complete("ai-select", f"{selected_ai}" if selected_ai != ALL_AGENTS_KEY else f"all ({len(agents_to_install)} detected)")
    tracker.add("script-select", "Select script type")
    tracker.complete("script-select", selected_script)
    
    # Add tracker steps for each agent if "all" is selected
    if selected_ai == ALL_AGENTS_KEY:
        for agent in agents_to_install:
            tracker.add(f"agent-{agent}", f"Install {AGENT_CONFIG[agent]['name']}")
    else:
        for key, label in [
            ("fetch", "Fetch latest release"),
            ("download", "Download template"),
            ("extract", "Extract template"),
            ("zip-list", "Archive contents"),
            ("extracted-summary", "Extraction summary"),
        ]:
            tracker.add(key, label)
    
    for key, label in [
        ("chmod", "Ensure scripts executable"),
        ("cleanup", "Cleanup"),
        ("git", "Initialize git repository"),
        ("final", "Finalize")
    ]:
        tracker.add(key, label)

    # Track git error message outside Live context so it persists
    git_error_message = None

    with Live(tracker.render(), console=console, refresh_per_second=8, transient=True) as live:
        tracker.attach_refresh(lambda: live.update(tracker.render()))
        try:
            # Need to get ssl_context for client. Replicating the logic from old main.
            import truststore
            ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

            verify = not skip_tls
            local_ssl_context = ssl_context if verify else False
            local_client = httpx.Client(verify=local_ssl_context)

            if selected_ai == ALL_AGENTS_KEY:
                # Download and extract templates for each detected agent
                for i, agent in enumerate(agents_to_install):
                    tracker.start(f"agent-{agent}")
                    try:
                        # For first agent, create the project structure; for subsequent ones, merge
                        is_merge = (i > 0) or here
                        download_and_extract_template(
                            project_path, agent, selected_script, is_merge, 
                            verbose=False, tracker=None, client=local_client, 
                            debug=debug, github_token=github_token
                        )
                        tracker.complete(f"agent-{agent}", "installed")
                    except Exception as e:
                        tracker.error(f"agent-{agent}", str(e)[:30])
                        if debug:
                            console.print(f"[yellow]Warning: Failed to install {agent}: {e}[/yellow]")
            else:
                download_and_extract_template(project_path, selected_ai, selected_script, here, verbose=False, tracker=tracker, client=local_client, debug=debug, github_token=github_token)

            ensure_executable_scripts(project_path, tracker=tracker)

            if not no_git:
                tracker.start("git")
                if is_git_repo(project_path):
                    tracker.complete("git", "existing repo detected")
                elif should_init_git:
                    success, error_msg = init_git_repo(project_path, quiet=True)
                    if success:
                        tracker.complete("git", "initialized")
                    else:
                        tracker.error("git", "init failed")
                        git_error_message = error_msg
                else:
                    tracker.skip("git", "git not available")
            else:
                tracker.skip("git", "--no-git flag")

            tracker.complete("final", "project ready")
        except Exception as e:
            tracker.error("final", str(e))
            console.print(Panel(f"Initialization failed: {e}", title="Failure", border_style="red"))
            if debug:
                _env_pairs = [
                    ("Python", sys.version.split()[0]),
                    ("Platform", sys.platform),
                    ("CWD", str(Path.cwd())),
                ]
                _label_width = max(len(k) for k, _ in _env_pairs)
                env_lines = [f"{k.ljust(_label_width)} → [bright_black]{v}[/bright_black]" for k, v in _env_pairs]
                console.print(Panel("\n".join(env_lines), title="Debug Environment", border_style="magenta"))
            if not here and project_path.exists():
                shutil.rmtree(project_path)
            raise typer.Exit(1)
        finally:
            pass

    console.print(tracker.render())
    console.print("\n[bold green]Project ready.[/bold green]")

    # Show git error details if initialization failed
    if git_error_message:
        console.print()
        git_error_panel = Panel(
            f"[yellow]Warning:[/yellow] Git repository initialization failed\n\n"
            f"{git_error_message}\n\n"
            f"[dim]You can initialize git manually later with:[/dim]\n"
            f"[cyan]cd {project_path if not here else '.'}[/cyan]\n"
            f"[cyan]git init[/cyan]\n"
            f"[cyan]git add .[/cyan]\n"
            f"[cyan]git commit -m \"Initial commit\"[/cyan]",
            title="[red]Git Initialization Failed[/red]",
            border_style="red",
            padding=(1, 2)
        )
        console.print(git_error_panel)

    # Agent folder security notice
    if selected_ai == ALL_AGENTS_KEY:
        # List all agent folders when "all" is selected
        agent_folders = [config["folder"] for key, config in AGENT_CONFIG.items() 
                        if key != ALL_AGENTS_KEY and config["folder"]]
        unique_folders = sorted(set(agent_folders))
        folder_list = ", ".join([f"[cyan]{f}[/cyan]" for f in unique_folders[:5]])
        if len(unique_folders) > 5:
            folder_list += f", and {len(unique_folders) - 5} more"
        
        security_notice = Panel(
            f"[bold green]All AI agents initialized![/bold green]\n\n"
            f"Some agents may store credentials, auth tokens, or other identifying and private artifacts.\n"
            f"Agent folders include: {folder_list}\n\n"
            f"Consider reviewing these folders and adding sensitive paths to [cyan].gitignore[/cyan].",
            title="[yellow]Agent Folder Security[/yellow]",
            border_style="yellow",
            padding=(1, 2)
        )
        console.print()
        console.print(security_notice)
    else:
        agent_config = AGENT_CONFIG.get(selected_ai)
        if agent_config and agent_config["folder"]:
            agent_folder = agent_config["folder"]
            security_notice = Panel(
                f"Some agents may store credentials, auth tokens, or other identifying and private artifacts in the agent folder within your project.\n"
                f"Consider adding [cyan]{agent_folder}[/cyan] (or parts of it) to [cyan].gitignore[/cyan] to prevent accidental credential leakage.",
                title="[yellow]Agent Folder Security[/yellow]",
                border_style="yellow",
                padding=(1, 2)
            )
            console.print()
            console.print(security_notice)

    steps_lines = []
    if not here:
        steps_lines.append(f"1. Go to the project folder: [cyan]cd {project_name}[/cyan]")
        step_num = 2
    else:
        steps_lines.append("1. You're already in the project directory!")
        step_num = 2

    # Add Codex-specific setup step if needed (for individual codex or all agents)
    if selected_ai == "codex" or selected_ai == ALL_AGENTS_KEY:
        codex_path = project_path / ".codex"
        quoted_path = shlex.quote(str(codex_path))
        if os.name == "nt":  # Windows
            cmd = f"setx CODEX_HOME {quoted_path}"
        else:  # Unix-like systems
            cmd = f"export CODEX_HOME={quoted_path}"

        if selected_ai == ALL_AGENTS_KEY:
            steps_lines.append(f"{step_num}. [dim](For Codex users)[/dim] Set [cyan]CODEX_HOME[/cyan]: [cyan]{cmd}[/cyan]")
        else:
            steps_lines.append(f"{step_num}. Set [cyan]CODEX_HOME[/cyan] environment variable before running Codex: [cyan]{cmd}[/cyan]")
        step_num += 1

    if selected_ai == ALL_AGENTS_KEY:
        steps_lines.append(f"{step_num}. Use slash commands with [bold]any[/bold] of your preferred AI agents:")
    else:
        steps_lines.append(f"{step_num}. Start using slash commands with your AI agent:")

    steps_lines.append("   2.1 [cyan]/speckit.constitution[/] - Establish project principles")
    steps_lines.append("   2.2 [cyan]/speckit.specify[/] - Create baseline specification")
    steps_lines.append("   2.3 [cyan]/speckit.plan[/] - Create implementation plan")
    steps_lines.append("   2.4 [cyan]/speckit.tasks[/] - Generate actionable tasks")
    steps_lines.append("   2.5 [cyan]/speckit.implement[/] - Execute implementation")

    steps_panel = Panel("\n".join(steps_lines), title="Next Steps", border_style="cyan", padding=(1,2))
    console.print()
    console.print(steps_panel)

    enhancement_lines = [
        "Optional commands that you can use for your specs [bright_black](improve quality & confidence)[/bright_black]",
        "",
        f"○ [cyan]/speckit.clarify[/] [bright_black](optional)[/bright_black] - Ask structured questions to de-risk ambiguous areas before planning (run before [cyan]/speckit.plan[/] if used)",
        f"○ [cyan]/speckit.analyze[/] [bright_black](optional)[/bright_black] - Cross-artifact consistency & alignment report (after [cyan]/speckit.tasks[/], before [cyan]/speckit.implement[/])",
        f"○ [cyan]/speckit.checklist[/] [bright_black](optional)[/bright_black] - Generate quality checklists to validate requirements completeness, clarity, and consistency (after [cyan]/speckit.plan[/])"
    ]
    enhancements_panel = Panel("\n".join(enhancement_lines), title="Enhancement Commands", border_style="cyan", padding=(1,2))
    console.print()
    console.print(enhancements_panel)

@app.command()
def check():
    """Check that all required tools are installed."""
    show_banner()
    console.print("[bold]Checking for installed tools...[/bold]\n")

    tracker = StepTracker("Check Available Tools")

    tracker.add("git", "Git version control")
    git_ok = check_tool("git", tracker=tracker)

    agent_results = {}
    for agent_key, agent_config in AGENT_CONFIG.items():
        agent_name = agent_config["name"]
        requires_cli = agent_config["requires_cli"]

        tracker.add(agent_key, agent_name)

        if requires_cli:
            agent_results[agent_key] = check_tool(agent_key, tracker=tracker)
        else:
            # IDE-based agent - skip CLI check and mark as optional
            tracker.skip(agent_key, "IDE-based, no CLI check")
            agent_results[agent_key] = False  # Don't count IDE agents as "found"

    # Check VS Code variants (not in agent config)
    tracker.add("code", "Visual Studio Code")
    code_ok = check_tool("code", tracker=tracker)

    tracker.add("code-insiders", "Visual Studio Code Insiders")
    code_insiders_ok = check_tool("code-insiders", tracker=tracker)

    console.print(tracker.render())

    console.print("\n[bold green]Specify CLI is ready to use![/bold green]")

    if not git_ok:
        console.print("[dim]Tip: Install git for repository management[/dim]")

    if not any(agent_results.values()):
        console.print("[dim]Tip: Install an AI assistant for the best experience[/dim]")

@app.command()
def version():
    """Display version and system information."""
    import platform
    import importlib.metadata

    show_banner()

    # Get CLI version from package metadata
    cli_version = "unknown"
    try:
        cli_version = importlib.metadata.version("specify-cli")
    except Exception:
        # Fallback: try reading from pyproject.toml if running from source
        try:
            import tomllib
            pyproject_path = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    cli_version = data.get("project", {}).get("version", "unknown")
        except Exception:
            pass

    # Fetch latest template release version
    repo_owner = "github"
    repo_name = "spec-kit"
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    template_version = "unknown"
    release_date = "unknown"

    try:
        import truststore
        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        client = httpx.Client(verify=ssl_context)

        response = client.get(
            api_url,
            timeout=10,
            follow_redirects=True,
            headers=_github_auth_headers(),
        )
        if response.status_code == 200:
            release_data = response.json()
            template_version = release_data.get("tag_name", "unknown")
            # Remove 'v' prefix if present
            if template_version.startswith("v"):
                template_version = template_version[1:]
            release_date = release_data.get("published_at", "unknown")
            if release_date != "unknown":
                # Format the date nicely
                try:
                    dt = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                    release_date = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass
    except Exception:
        pass

    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Key", style="cyan", justify="right")
    info_table.add_column("Value", style="white")

    info_table.add_row("CLI Version", cli_version)
    info_table.add_row("Template Version", template_version)
    info_table.add_row("Released", release_date)
    info_table.add_row("", "")
    info_table.add_row("Python", platform.python_version())
    info_table.add_row("Platform", platform.system())
    info_table.add_row("Architecture", platform.machine())
    info_table.add_row("OS Version", platform.version())

    panel = Panel(
        info_table,
        title="[bold cyan]Specify CLI Information[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    )

    console.print(panel)
    console.print()

@app.command()
def validate(
    project_dir: str = typer.Argument(".", help="Project directory to validate (defaults to current directory)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed validation results"),
):
    """
    Validate all AI agent configurations in a project.
    
    This command checks all detected AI agent configurations to ensure they
    follow proper standards and best practices:
    
    - Directory structure follows agent-specific conventions
    - Command files use correct format (Markdown vs TOML)
    - Required spec-kit commands are present
    - Context files are properly configured
    - File formats match agent requirements
    
    Examples:
        specify validate                    # Validate current directory
        specify validate ./my-project       # Validate specific project
        specify validate --verbose          # Show detailed results
    """
    show_banner()
    
    project_path = Path(project_dir).resolve()
    
    if not project_path.exists():
        console.print(f"[red]Error:[/red] Project directory not found: {project_path}")
        raise typer.Exit(1)
    
    if not project_path.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {project_path}")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Validating AI agent configurations in:[/cyan] {project_path}")
    console.print()
    
    # Run validation
    success, issues, warnings = validate_agent_standards(project_path, AGENT_CONFIG)
    
    # Display results
    if not issues and not warnings:
        console.print("[bold green]✓ All agent configurations are valid![/bold green]")
        console.print()
        console.print("[dim]No issues or warnings found.[/dim]")
        return
    
    # Create summary table
    summary_table = Table(title="Validation Summary", show_header=True, header_style="bold cyan")
    summary_table.add_column("Category", style="cyan")
    summary_table.add_column("Count", justify="right")
    
    summary_table.add_row("Errors", f"[red]{len(issues)}[/red]" if issues else "[green]0[/green]")
    summary_table.add_row("Warnings", f"[yellow]{len(warnings)}[/yellow]" if warnings else "[green]0[/green]")
    
    console.print(summary_table)
    console.print()
    
    # Display issues
    if issues:
        console.print("[bold red]Errors Found:[/bold red]")
        console.print()
        
        # Group by agent
        issues_by_agent = {}
        for issue in issues:
            agent = issue.get("agent", "unknown")
            if agent not in issues_by_agent:
                issues_by_agent[agent] = []
            issues_by_agent[agent].append(issue)
        
        for agent, agent_issues in issues_by_agent.items():
            agent_name = AGENT_CONFIG.get(agent, {}).get("name", agent)
            console.print(f"[bold]{agent_name}[/bold] ({agent}):")
            
            for issue in agent_issues:
                category = issue.get("category", "unknown")
                message = issue.get("message", "No message")
                file_path = issue.get("file", "")
                
                if file_path:
                    console.print(f"  [red]✗[/red] [{category}] {message}")
                    console.print(f"    File: [cyan]{file_path}[/cyan]")
                else:
                    console.print(f"  [red]✗[/red] [{category}] {message}")
            
            console.print()
    
    # Display warnings
    if warnings:
        console.print("[bold yellow]Warnings:[/bold yellow]")
        console.print()
        
        # Group by agent
        warnings_by_agent = {}
        for warning in warnings:
            agent = warning.get("agent", "unknown")
            if agent not in warnings_by_agent:
                warnings_by_agent[agent] = []
            warnings_by_agent[agent].append(warning)
        
        for agent, agent_warnings in warnings_by_agent.items():
            agent_name = AGENT_CONFIG.get(agent, {}).get("name", agent) if agent != "none" else "General"
            console.print(f"[bold]{agent_name}[/bold] ({agent}):")
            
            for warning in agent_warnings:
                category = warning.get("category", "unknown")
                message = warning.get("message", "No message")
                file_path = warning.get("file", "")
                
                if file_path:
                    console.print(f"  [yellow]⚠[/yellow] [{category}] {message}")
                    console.print(f"    File: [cyan]{file_path}[/cyan]")
                else:
                    console.print(f"  [yellow]⚠[/yellow] [{category}] {message}")
            
            console.print()
    
    # Final status
    if issues:
        console.print("[bold red]Validation failed with errors.[/bold red]")
        console.print("[dim]Fix the errors above and run validation again.[/dim]")
        raise typer.Exit(1)
    else:
        console.print("[bold green]Validation passed with warnings.[/bold green]")
        console.print("[dim]Consider addressing the warnings above.[/dim]")

def main():
    app()
