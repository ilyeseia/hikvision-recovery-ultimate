"""
CLI entry point for Hikvision Recovery.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich import print as rprint

from ..core import ISAPIClient, ISAPIConfig, SearchCriteria, RecordingType, StreamType
from ..core.models import DeviceInfo, RecordingInfo


console = Console()


def load_config(config_path: Optional[str] = None) -> ISAPIConfig:
    """Load configuration from file or environment"""
    import yaml
    
    # Default config paths
    config_files = [
        config_path,
        os.environ.get("HIKVISION_CONFIG"),
        "./config.yaml",
        "./config.yml",
        os.path.expanduser("~/.hikvision/config.yaml"),
        "/etc/hikvision-recovery/config.yaml",
    ]
    
    for cf in config_files:
        if cf and Path(cf).exists():
            with open(cf, "r") as f:
                data = yaml.safe_load(f)
                return ISAPIConfig(**data)
    
    # Fallback to environment variables
    return ISAPIConfig(
        host=os.environ.get("HIKVISION_HOST", ""),
        username=os.environ.get("HIKVISION_USER", "admin"),
        password=os.environ.get("HIKVISION_PASS", ""),
        port=int(os.environ.get("HIKVISION_PORT", "80")),
        use_https=os.environ.get("HIKVISION_HTTPS", "false").lower() == "true",
    )


@click.group()
@click.option("--host", "-h", help="Device IP/hostname", envvar="HIKVISION_HOST")
@click.option("--user", "-u", default="admin", help="Username", envvar="HIKVISION_USER")
@click.option("--pass", "-p", "password", help="Password", envvar="HIKVISION_PASS")
@click.option("--port", default=80, help="Port", envvar="HIKVISION_PORT")
@click.option("--https/--no-https", default=False, help="Use HTTPS", envvar="HIKVISION_HTTPS")
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.option("--verbose", "-v", count=True, help="Verbosity level")
@click.pass_context
def main(ctx, host, user, password, port, https, config, verbose):
    """
    Hikvision Recovery - Professional ISAPI client for Hikvision DVR/NVR.
    
    Manage recordings, download footage, and recover deleted videos.
    """
    # Setup logging
    import logging
    log_level = logging.WARNING
    if verbose == 1:
        log_level = logging.INFO
    elif verbose >= 2:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")
    
    ctx.ensure_object(dict)
    ctx.obj["config"] = ISAPIConfig(
        host=host or "",
        username=user,
        password=password or "",
        port=port,
        use_https=https,
    )
    ctx.obj["config_file"] = config
    ctx.obj["client"] = None


def get_client(ctx) -> ISAPIClient:
    """Get or create ISAPI client"""
    if ctx.obj["client"] is None:
        if not ctx.obj["config"].host:
            console.print("[red]Error:[/red] Host not specified. Use --host or set HIKVISION_HOST")
            sys.exit(1)
        if not ctx.obj["config"].password:
            console.print("[red]Error:[/red] Password not specified. Use --pass or set HIKVISION_PASS")
            sys.exit(1)
        ctx.obj["client"] = ISAPIClient(ctx.obj["config"])
    return ctx.obj["client"]


@main.command()
@click.pass_context
def info(ctx):
    """Show device information"""
    client = get_client(ctx)
    
    with console.status("[bold green]Fetching device info..."):
        try:
            device = client.get_device_info()
        except Exception as e:
            console.print(f"[red]Failed to get device info: {e}[/red]")
            sys.exit(1)
    
    table = Table(title=f"Device Information: {device.device_name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    fields = [
        ("Device Name", device.device_name),
        ("Model", device.model),
        ("Serial Number", device.serial_number),
        ("MAC Address", device.mac_address),
        ("Firmware Version", device.firmware_version),
        ("Firmware Date", device.firmware_date),
        ("Encoding Version", device.encoding_version),
        ("Build Date", device.build_date),
        ("Language", device.language),
        ("Timezone", device.timezone),
        ("IPv6 Support", "Yes" if device.is_support_ipv6 else "No"),
        ("DDNS Support", "Yes" if device.is_support_ddns else "No"),
        ("RTSP Support", "Yes" if device.is_support_rtsp else "No"),
        ("HTTPS Support", "Yes" if device.is_support_https else "No"),
        ("Cloud Support", "Yes" if device.is_support_cloud else "No"),
        ("P2P Support", "Yes" if device.is_support_p2p else "No"),
    ]
    
    for prop, val in fields:
        table.add_row(prop, str(val))
    
    console.print(table)


@main.command()
@click.option("--channels", "-ch", help="Camera IDs (comma-separated)", default="")
@click.option("--days", "-d", default=7, help="Days back to search")
@click.option("--hours", default=0, help="Additional hours back")
@click.option("--type", "-t", "rec_types", multiple=True, 
              type=click.Choice([t.value for t in RecordingType]),
              help="Recording types to search")
@click.option("--stream", "-s", type=click.Choice([s.value for s in StreamType]), default="main")
@click.option("--max", "-m", default=100, help="Max results")
@click.option("--all-pages", "-a", is_flag=True, help="Fetch all pages")
@click.pass_context
def search(ctx, channels, days, hours, rec_types, stream, max, all_pages):
    """Search for recordings"""
    client = get_client(ctx)
    
    channel_list = [int(c.strip()) for c in channels.split(",") if c.strip()] if channels else None
    type_list = [RecordingType(t) for t in rec_types] if rec_types else [RecordingType.ALL]
    stream_type = StreamType(stream)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days, hours=hours)
    
    criteria = SearchCriteria(
        start_time=start_time,
        end_time=end_time,
        camera_ids=channel_list,
        recording_types=type_list,
        stream_type=stream_type,
        max_results=max,
        page_size=min(50, max),
    )
    
    with console.status("[bold green]Searching recordings..."):
        try:
            if all_pages:
                recordings = list(client.search_all_recordings(criteria))
            else:
                result = client.search_recordings(criteria)
                recordings = result.recordings
        except Exception as e:
            console.print(f"[red]Search failed: {e}[/red]")
            sys.exit(1)
    
    if not recordings:
        console.print("[yellow]No recordings found[/yellow]")
        return
    
    table = Table(title=f"Found {len(recordings)} recording(s)")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Name", style="white")
    table.add_column("Channel", justify="center")
    table.add_column("Start Time", style="green")
    table.add_column("End Time", style="green")
    table.add_column("Duration", justify="right")
    table.add_column("Type", style="yellow")
    table.add_column("Size", justify="right")
    table.add_column("Locked", justify="center")
    
    for rec in recordings:
        table.add_row(
            rec.id[:12] + "..." if len(rec.id) > 12 else rec.id,
            rec.name[:40] + "..." if len(rec.name) > 40 else rec.name,
            str(rec.channel),
            rec.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            rec.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            rec.duration_human,
            rec.recording_type.value,
            f"{rec.file_size / (1024*1024):.1f} MB" if rec.file_size else "N/A",
            "🔒" if rec.locked else "",
        )
    
    console.print(table)


@main.command()
@click.argument("recording_ids", nargs=-1, required=True)
@click.option("--output", "-o", default="./downloads", help="Output directory")
@click.option("--no-resume", is_flag=True, help="Disable resume")
@click.pass_context
def download(ctx, recording_ids, output, no_resume):
    """Download recordings by ID"""
    client = get_client(ctx)
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Fetch full recording info for each ID
    recordings = []
    with console.status("[bold green]Fetching recording details..."):
        for rec_id in recording_ids:
            try:
                # Search for this specific recording
                criteria = SearchCriteria(
                    start_time=datetime.now() - timedelta(days=365),
                    end_time=datetime.now(),
                    max_results=1,
                )
                result = client.search_recordings(criteria)
                for rec in result.recordings:
                    if rec.id == rec_id:
                        recordings.append(rec)
                        break
            except Exception as e:
                console.print(f"[red]Failed to get info for {rec_id}: {e}[/red]")
    
    if not recordings:
        console.print("[red]No valid recordings found[/red]")
        return
    
    console.print(f"[green]Downloading {len(recordings)} recording(s) to {output_path}[/green]")
    
    # Progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        
        def update_progress(prog):
            task_id = progress.task_ids[0] if progress.task_ids else None
            if task_id is not None:
                progress.update(task_id, completed=prog.downloaded_bytes, total=prog.total_bytes, description=f"[cyan]{prog.file_name}[/cyan]")
        
        for i, rec in enumerate(recordings):
            file_name = f"{rec.start_time.strftime('%Y%m%d_%H%M%S')}_{rec.name}.mp4"
            task = progress.add_task(f"[cyan]{file_name}[/cyan]", total=rec.file_size or 100)
            
            try:
                prog = client.download_recording(
                    rec,
                    str(output_path / file_name),
                    progress_callback=update_progress,
                    resume=not no_resume,
                )
                progress.update(task, completed=prog.total_bytes, description=f"[green]✓ {file_name}[/green]")
            except Exception as e:
                progress.update(task, description=f"[red]✗ {file_name}: {e}[/red]")
                console.print(f"[red]Failed: {e}[/red]")
        
        progress.remove_task(task)
    
    console.print(f"\n[green]Done! Files saved to {output_path}[/green]")


@main.command()
@click.option("--output", "-o", default="./config.yaml", help="Output config file")
@click.pass_context
def init_config(ctx, output):
    """Generate a sample configuration file"""
    import yaml
    
    config = {
        "host": "192.168.1.100",
        "username": "admin",
        "password": "your_password",
        "port": 80,
        "use_https": False,
        "verify_ssl": False,
        "timeout": 30,
        "max_retries": 3,
        "backoff_factor": 0.5,
        "digest_auth": True,
    }
    
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    console.print(f"[green]Sample config written to {output_path}[/green]")
    console.print("[yellow]Edit the file and set your device credentials[/yellow]")


@main.command()
@click.option("--channel", "-ch", default=1, help="Channel number")
@click.option("--stream", "-s", type=click.Choice([s.value for s in StreamType]), default="main")
@click.pass_context
def rtsp(ctx, channel, stream):
    """Generate RTSP URL for live streaming"""
    client = get_client(ctx)
    url = client.get_rtsp_url(channel, stream)
    console.print(Panel.fit(f"RTSP URL for channel {channel} ({stream} stream):"))
    console.print(f"[cyan]{url}[/cyan]")


@main.command()
@click.option("--channel", "-ch", default=1, help="Channel number")
@click.option("--start", required=True, help="Start time (YYYY-MM-DD HH:MM:SS)")
@click.option("--end", required=True, help="End time (YYYY-MM-DD HH:MM:SS)")
@click.option("--stream", "-s", type=click.Choice([s.value for s in StreamType]), default="main")
@click.pass_context
def playback(ctx, channel, start, end, stream):
    """Generate RTSP URL for playback"""
    client = get_client(ctx)
    
    # Parse and format times
    start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
    
    start_str = start_dt.strftime("%Y%m%dT%H%M%SZ")
    end_str = end_dt.strftime("%Y%m%dT%H%M%SZ")
    
    url = client.get_playback_rtsp_url(channel, start_str, end_str, stream)
    console.print(Panel.fit(f"Playback RTSP URL for channel {channel}:"))
    console.print(f"[cyan]{url}[/cyan]")


@main.command()
@click.option("--channel", "-ch", default=1, help="Channel number")
@click.option("--command", "-cmd", type=click.Choice(["up", "down", "left", "right", "zoom_in", "zoom_out", "stop"]), required=True)
@click.option("--speed", default=5, help="Speed (1-10)")
@click.pass_context
def ptz(ctx, channel, command, speed):
    """Control PTZ"""
    client = get_client(ctx)
    
    with console.status(f"[bold green]Sending PTZ command: {command}..."):
        try:
            result = client.ptz_control(channel, command, speed)
            if result:
                console.print(f"[green]PTZ command '{command}' sent successfully[/green]")
            else:
                console.print("[red]PTZ command failed[/red]")
        except Exception as e:
            console.print(f"[red]PTZ error: {e}[/red]")


@main.command()
@click.pass_context
def capabilities(ctx):
    """Show device capabilities"""
    client = get_client(ctx)
    
    with console.status("[bold green]Fetching capabilities..."):
        try:
            caps = client.get_capabilities()
        except Exception as e:
            console.print(f"[red]Failed to get capabilities: {e}[/red]")
            sys.exit(1)
    
    table = Table(title="Device Capabilities")
    table.add_column("Capability", style="cyan")
    table.add_column("Value", style="white")
    
    for field_name, value in caps:
        display_name = field_name.replace("_", " ").title()
        table.add_row(display_name, str(value))
    
    console.print(table)


if __name__ == "__main__":
    main()