#!/usr/bin/env python3
import requests
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing import Dict, Any

# Initialize Rich console for pretty printing
console = Console()

def pretty_print_request(method: str, url: str, headers: Dict[str, str], data: Dict[str, Any]) -> None:
    """Pretty print the request details"""
    table = Table(title="Request Details", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Method", method)
    table.add_row("URL", url)
    table.add_row("Headers", json.dumps(headers, indent=2))
    table.add_row("Data", json.dumps(data, indent=2))
    
    console.print(table)

def pretty_print_response(response: requests.Response) -> None:
    """Pretty print the response details"""
    table = Table(title="Response Details", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Status Code", str(response.status_code))
    table.add_row("Headers", json.dumps(dict(response.headers), indent=2))
    
    try:
        response_body = response.json()
        table.add_row("Response Body", json.dumps(response_body, indent=2))
        
        # Extract trace_id from response if available
        trace_id = response_body.get("trace_id")
        if trace_id:
            console.print(f"\n[bold blue]Trace ID from server:[/bold blue] {trace_id}")
    except json.JSONDecodeError:
        table.add_row("Response Body", response.text)
    
    console.print(table)

def main():
    # API configuration
    base_url = "http://localhost:8000/api/v1"
    signup_url = f"{base_url}/auth/signup"
    
    # Test user data
    user_data = {
        "phone_number": "+9876543210",
        "password": "SecurePass123!",
        "user_type": "human",
        "language": "en"
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Print request details
    console.print(Panel.fit("Creating Test User", style="bold blue"))
    pretty_print_request("POST", signup_url, headers, user_data)
    
    try:
        # Make the request
        response = requests.post(signup_url, json=user_data, headers=headers)
        
        # Print response details
        console.print(Panel.fit("Received Response", style="bold blue"))
        pretty_print_response(response)
        
        if response.status_code == 200:
            console.print("[green]Test user created successfully![/green]")
            console.print("[yellow]You can now use these credentials in auth_debug.py:[/yellow]")
            console.print(f"Phone: {user_data['phone_number']}")
            console.print(f"Password: {user_data['password']}")
        else:
            console.print(f"[red]Failed to create test user with status code: {response.status_code}[/red]")
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error making request: {str(e)}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")

if __name__ == "__main__":
    main() 