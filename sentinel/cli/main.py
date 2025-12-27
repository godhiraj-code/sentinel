"""
Sentinel CLI - Command-line interface for autonomous testing.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="sentinel")
def cli():
    """🛡️ The Sentinel - Autonomous Web Testing Agent
    
    Navigate, discover, and validate web applications autonomously.
    """
    pass


@cli.command()
@click.argument('url')
@click.argument('goal')
@click.option('--stealth/--no-stealth', default=True, help='Enable/disable bot evasion mode')
@click.option('--headless/--headed', default=False, help='Run browser in headless mode')
@click.option('--training', is_flag=True, help='Use heuristic mode (no LLM, free)')
@click.option('--max-steps', default=50, type=int, 
              help='Maximum exploration steps (use 5-10 for simple goals, 20-50 for complex flows)')
@click.option('--brain', default='auto', help='Intelligence Strategy: auto, heuristic, cloud, local')
@click.option('--model', default=None, help='Specific model name (e.g. gpt-4, claude-3) or path')
@click.option('--report-dir', default='./sentinel_reports', help='Report output directory')
@click.option('--stability-timeout', default=15, type=int,
              help='Waitless stability timeout in seconds (default: 15)')
@click.option('--mutation-threshold', default=200, type=int,
              help='DOM mutations/sec considered stable (default: 200, increase for animated sites)')
@click.option('--stability-mode', default='relaxed', type=click.Choice(['strict', 'normal', 'relaxed']),
              help='Stability strictness: strict/normal/relaxed (default: relaxed)')
def explore(url, goal, stealth, headless, training, max_steps, report_dir, brain, model,
            stability_timeout, mutation_threshold, stability_mode):
    """
    Explore a URL with an autonomous goal.
    
    The agent will navigate the page and attempt to achieve the goal
    using its perception and decision-making capabilities.
    
    \b
    Examples:
    
        sentinel explore "https://demo.playwright.dev/todomvc/" "Add 'Buy milk' to the list"
        
        sentinel explore "https://example.com/login" "Login" --stealth --brain cloud
        
        sentinel explore "https://example.com" "Complex goal" --brain cloud --model gpt-4
    """
    console.print(Panel.fit(
        f"[bold blue]🛡️ The Sentinel[/bold blue]\n"
        f"[dim]Autonomous Web Testing Agent[/dim]",
        border_style="blue"
    ))
    
    console.print(f"\n[bold]Target:[/bold] {url}")
    console.print(f"[bold]Goal:[/bold] {goal}")
    console.print(f"[bold]Brain:[/bold] {brain.upper() if brain else 'AUTO'}")
    console.print(f"[bold]Stealth Mode:[/bold] {'✅ Enabled' if stealth else '❌ Disabled'}")
    console.print()
    
    try:
        from sentinel import SentinelOrchestrator
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing agent...", total=None)
            
            agent = SentinelOrchestrator(
                url=url,
                goal=goal,
                stealth_mode=stealth,
                headless=headless,
                training_mode=training,
                max_steps=max_steps,
                report_dir=report_dir,
                brain_type=brain,
                model_name=model,
                stability_timeout=stability_timeout,
                mutation_threshold=mutation_threshold,
                stability_mode=stability_mode,
            )
            
            progress.update(task, description="Running exploration...")
            result = agent.run()
        
        # Display results
        if result.success:
            console.print(f"\n[bold green]✅ Goal achieved in {result.steps} steps![/bold green]")
        else:
            console.print(f"\n[bold red]❌ Goal not achieved after {result.steps} steps.[/bold red]")
            if result.error:
                console.print(f"[red]Error: {result.error}[/red]")
        
        console.print(f"\n[dim]Duration: {result.duration_seconds:.2f}s[/dim]")
        
        if result.report_path:
            console.print(f"[dim]Report: {result.report_path}[/dim]")
        
        # Show decision summary
        if result.decisions:
            console.print("\n[bold]Decision Summary:[/bold]")
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Step", style="dim", width=6)
            table.add_column("Action", style="green")
            table.add_column("Target", style="yellow", max_width=40)
            table.add_column("Confidence", justify="right")
            
            for i, decision in enumerate(result.decisions[:10]):
                confidence_color = "green" if decision.confidence > 0.7 else "yellow" if decision.confidence > 0.4 else "red"
                table.add_row(
                    str(i + 1),
                    decision.action,
                    decision.target[:40] + "..." if len(decision.target) > 40 else decision.target,
                    f"[{confidence_color}]{decision.confidence:.0%}[/{confidence_color}]"
                )
            
            if len(result.decisions) > 10:
                table.add_row("...", f"+{len(result.decisions) - 10} more", "", "")
            
            console.print(table)
        
    except ImportError as e:
        console.print(f"[red]Error: Missing dependency - {e}[/red]")
        console.print("[dim]Try: pip install the-sentinel[full][/dim]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise


@cli.command()
@click.argument('url')
@click.option('--report-dir', default='./sentinel_reports', help='Report output directory')
@click.option('--mutations', default=5, help='Number of mutations to apply')
def stress(url, report_dir, mutations):
    """
    Run UI mutation stress testing.
    
    Uses Vandal to mutate the UI and verify test resilience.
    
    Example:
    
        sentinel stress "https://example.com/checkout" --mutations 10
    """
    console.print(Panel.fit(
        f"[bold red]🔥 Mutation Stress Test[/bold red]\n"
        f"[dim]Powered by Vandal[/dim]",
        border_style="red"
    ))
    
    console.print(f"\n[bold]Target:[/bold] {url}")
    console.print(f"[bold]Mutations:[/bold] {mutations}")
    console.print()
    
    console.print("[yellow]Stress testing feature will be implemented in Phase 5[/yellow]")


@cli.command()
@click.argument('name')
@click.option('--state-dir', default='./.sentinel_states', help='State storage directory')
def save_state(name, state_dir):
    """
    Save current browser state for later use.
    
    Captures cookies, localStorage, and sessionStorage.
    
    Example:
    
        sentinel save-state "logged_in_user"
    """
    console.print(f"[yellow]State saving feature will be implemented in Phase 4[/yellow]")


@cli.command()
@click.argument('name')
@click.option('--state-dir', default='./.sentinel_states', help='State storage directory')
def load_state(name, state_dir):
    """
    Load a previously saved browser state.
    
    Example:
    
        sentinel load-state "logged_in_user"
    """
    console.print(f"[yellow]State loading feature will be implemented in Phase 4[/yellow]")


@cli.command()
def doctor():
    """
    Check system health and dependencies.
    
    Verifies that all required packages are installed
    and the system is ready for autonomous testing.
    """
    console.print(Panel.fit(
        f"[bold cyan]🩺 Sentinel Doctor[/bold cyan]\n"
        f"[dim]System Health Check[/dim]",
        border_style="cyan"
    ))
    console.print()
    
    dependencies = [
        ("selenium", "Core - WebDriver"),
        ("lumos", "Sense - Shadow DOM"),
        ("visual_guard", "Sense - Visual Regression"),
        ("waitless", "Action - UI Stability"),
        ("selenium_teleport", "Action - Session Management"),
        ("seleniumbase", "Action - Bot Evasion (SeleniumBase)"),
        ("vandal", "Validation - Mutation Testing"),
        ("beautiful_report", "Reporting - HTML Reports"),
        ("pytest_mockllm", "Intelligence - LLM Mocking"),
    ]
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Package", style="blue")
    table.add_column("Role", style="dim")
    table.add_column("Status", justify="center")
    
    all_good = True
    
    for package, role in dependencies:
        try:
            __import__(package)
            status = "[green]✅ Installed[/green]"
        except ImportError:
            status = "[yellow]⚠️ Missing[/yellow]"
            all_good = False
        
        table.add_row(package.replace("_", "-"), role, status)
    
    console.print(table)
    console.print()
    
    if all_good:
        console.print("[bold green]✅ All dependencies installed! Sentinel is ready.[/bold green]")
    else:
        console.print("[yellow]⚠️ Some optional dependencies are missing.[/yellow]")
        console.print("[dim]Install all with: pip install the-sentinel[full][/dim]")


@cli.command()
def version():
    """Show version information."""
    try:
        from sentinel import __version__
        console.print(f"The Sentinel v{__version__}")
    except ImportError:
        console.print("The Sentinel v0.2.0")


@cli.command()
@click.argument('report_dir')
@click.option('--step', is_flag=True, help='Pause after each step for inspection')
@click.option('--rerun', is_flag=True, help='Re-execute actions on a live browser')
def replay(report_dir, step, rerun):
    """
    Replay a past exploration session.
    
    View the decision timeline and optionally re-execute actions
    on a live browser.
    
    \\b
    Examples:
    
        sentinel replay ./sentinel_reports/20251227_074249
        
        sentinel replay ./sentinel_reports/20251227_074249 --rerun
        
        sentinel replay ./sentinel_reports/20251227_074249 --rerun --step
    """
    console.print(Panel.fit(
        f"[bold magenta]🎬 Session Replay[/bold magenta]\n"
        f"[dim]Replaying: {report_dir}[/dim]",
        border_style="magenta"
    ))
    console.print()
    
    try:
        from sentinel.reporters.session_replayer import SessionReplayer
        
        replayer = SessionReplayer(report_dir)
        session = replayer.load()
        
        # Print summary table
        table = Table(show_header=False, box=None)
        table.add_row("[bold]Run ID:[/bold]", session.run_id)
        table.add_row("[bold]URL:[/bold]", session.url or "N/A")
        table.add_row("[bold]Goal:[/bold]", session.goal)
        table.add_row("[bold]Duration:[/bold]", f"{session.duration_seconds:.2f}s")
        table.add_row("[bold]Steps:[/bold]", str(len(session.steps)))
        table.add_row("[bold]Decisions:[/bold]", str(session.total_decisions))
        table.add_row("[bold]Success:[/bold]", "[green]Yes[/green]" if session.success else "[red]No[/red]")
        console.print(table)
        console.print()
        
        # Print decision timeline
        console.print("[bold]📝 Decision Timeline:[/bold]")
        for i, decision in enumerate(replayer.get_decisions(), 1):
            conf = decision.confidence
            conf_bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
            target = decision.target[:35] + "..." if decision.target and len(decision.target) > 35 else (decision.target or "N/A")
            console.print(f"  {i}. [{conf_bar}] [cyan]{decision.action.upper()}[/cyan] → {target}")
            if decision.reasoning:
                console.print(f"     [dim]└─ {decision.reasoning[:50]}...[/dim]")
        
        console.print()
        
        if rerun:
            console.print("[bold yellow]🔄 Re-executing session on browser...[/bold yellow]")
            console.print()
            
            from sentinel.core.driver_factory import create_driver
            
            driver = create_driver(headless=False)
            try:
                def on_step(step_obj, success):
                    status = "[green]✅[/green]" if success else "[red]❌[/red]"
                    console.print(f"  {status} {step_obj.action} → {step_obj.target[:40] if step_obj.target else 'N/A'}")
                
                results = replayer.replay_on_browser(driver, step_mode=step, callback=on_step)
                
                successes = sum(1 for _, s in results if s)
                console.print()
                console.print(f"[bold]Replay complete: {successes}/{len(results)} actions succeeded[/bold]")
            finally:
                driver.quit()
        else:
            console.print("[dim]Use --rerun to re-execute actions on a browser[/dim]")
        
    except FileNotFoundError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
