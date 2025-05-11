#!/usr/bin/env python3
import requests
import json
from datetime import datetime
import jwt
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
from typing import Dict, Any
import uuid

# Initialize Rich console for pretty printing
console = Console()

# API configuration
API_URL = "http://localhost:8000/api/v1"

def get_auth_token(phone: str = "+9876543210", password: str = "SecurePass123!") -> str:
    """Get authentication token for testing."""
    signin_data = {
        "identifier": phone,
        "password": password
    }
    signin_response = requests.post(f"{API_URL}/auth/signin", json=signin_data)
    if signin_response.status_code == 200:
        return signin_response.json().get("access_token")
    return None

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

def decode_jwt(token: str) -> Dict[str, Any]:
    """Decode JWT token without verification"""
    return jwt.decode(token, options={"verify_signature": False})

def pretty_print_jwt(token: str) -> None:
    """Print JWT token in a readable format."""
    try:
        # Decode the token without verification
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Format the output
        console.print("\nJWT Token Contents:")
        console.print("-" * 50)
        
        # Handle user_id (sub)
        user_id = decoded.get('sub')
        console.print(f"user_id (sub): {user_id}")
        
        # Handle expiration time
        exp = decoded.get('exp')
        if exp:
            try:
                exp_time = datetime.fromtimestamp(exp).strftime('%Y-%m-%d %H:%M:%S')
                console.print(f"exp: {exp_time}")
            except (TypeError, ValueError) as e:
                console.print(f"exp: {exp} (raw value)")
        
        # Handle issued at time
        iat = decoded.get('iat')
        if iat:
            try:
                iat_time = datetime.fromtimestamp(iat).strftime('%Y-%m-%d %H:%M:%S')
                console.print(f"iat: {iat_time}")
            except (TypeError, ValueError) as e:
                console.print(f"iat: {iat} (raw value)")
        
        console.print("-" * 50)
    except Exception as e:
        console.print(f"Error decoding token: {e}")
        # Print raw token for debugging
        console.print("\nRaw token:")
        console.print(token)

def test_auth_flow():
    """Test the authentication flow."""
    base_url = "http://localhost:8000/api/v1"
    
    # Test user credentials
    phone = "+9876543210"
    password = "SecurePass123!"
    
    # Step 1: Create a new user
    console.print("\n1. Creating new user...")
    signup_data = {
        "phone_number": phone,
        "password": password
    }
    signup_response = requests.post(f"{base_url}/auth/signup", json=signup_data)
    console.print(f"Signup Response: {signup_response.status_code}")
    if signup_response.status_code == 200:
        console.print(json.dumps(signup_response.json(), indent=2))
    
    # Step 2: Sign in
    console.print("\n2. Signing in...")
    signin_data = {
        "identifier": phone,
        "password": password
    }
    signin_response = requests.post(f"{base_url}/auth/signin", json=signin_data)
    console.print(f"Signin Response: {signin_response.status_code}")
    if signin_response.status_code == 200:
        console.print(json.dumps(signin_response.json(), indent=2))
        token = signin_response.json().get("access_token")
        if token:
            pretty_print_jwt(token)
    
    # Step 3: Test protected route
    if signin_response.status_code == 200:
        console.print("\n3. Testing protected route...")
        token = signin_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        protected_response = requests.get(f"{base_url}/auth/protected", headers=headers)
        console.print(f"Protected Route Response: {protected_response.status_code}")
        if protected_response.status_code == 200:
            console.print(json.dumps(protected_response.json(), indent=2))

if __name__ == "__main__":
    test_auth_flow() 