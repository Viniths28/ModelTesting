#!/usr/bin/env python3
"""
Flow Engine Debug UI - One-Click Setup & Launch Script

This script sets up and launches the comprehensive debugging interface for the Flow Engine
with support for all recent enhancements including:
- Variable placeholder support ({{ variable }})
- Enhanced source node resolution
- Template substitution with JSON literals
- isPrimaryFlow parameter support
- Comprehensive debug capture
"""

import os
import sys
import subprocess
import platform
import time
import signal
import threading
from pathlib import Path

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(message, color=Colors.OKGREEN):
    """Print colored message to terminal."""
    print(f"{color}{message}{Colors.ENDC}")

def print_header(message):
    """Print header message."""
    print_colored(f"\n{'='*60}", Colors.HEADER)
    print_colored(f"  {message}", Colors.HEADER + Colors.BOLD)
    print_colored(f"{'='*60}", Colors.HEADER)

def check_python_version():
    """Check if Python version is 3.8 or higher."""
    if sys.version_info < (3, 8):
        print_colored("❌ Python 3.8 or higher is required!", Colors.FAIL)
        print_colored(f"Current version: {sys.version}", Colors.WARNING)
        return False
    print_colored(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected", Colors.OKGREEN)
    return True

def check_node_npm():
    """Check if Node.js and npm are installed."""
    try:
        # Check Node.js
        node_result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if node_result.returncode != 0:
            print_colored("❌ Node.js not found!", Colors.FAIL)
            return False
        
        node_version = node_result.stdout.strip()
        print_colored(f"✅ Node.js {node_version} detected", Colors.OKGREEN)
        
        # Check npm
        npm_result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if npm_result.returncode != 0:
            print_colored("❌ npm not found!", Colors.FAIL)
            return False
            
        npm_version = npm_result.stdout.strip()
        print_colored(f"✅ npm {npm_version} detected", Colors.OKGREEN)
        return True
        
    except FileNotFoundError:
        print_colored("❌ Node.js/npm not found in PATH!", Colors.FAIL)
        print_colored("Please install Node.js from https://nodejs.org/", Colors.WARNING)
        return False

def setup_backend():
    """Set up the backend environment and install dependencies."""
    print_header("Setting up Backend (FastAPI + SQLite + Neo4j)")
    
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    # Check if virtual environment exists
    venv_dir = backend_dir / "venv"
    if not venv_dir.exists():
        print_colored("📦 Creating Python virtual environment...", Colors.OKCYAN)
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    
    # Determine the correct pip path based on OS
    if platform.system() == "Windows":
        pip_path = venv_dir / "Scripts" / "pip"
        python_path = venv_dir / "Scripts" / "python"
    else:
        pip_path = venv_dir / "bin" / "pip"
        python_path = venv_dir / "bin" / "python"
    
    # Install dependencies
    print_colored("📦 Installing Python dependencies...", Colors.OKCYAN)
    subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
    
    print_colored("✅ Backend setup complete!", Colors.OKGREEN)
    return python_path

def setup_frontend():
    """Set up the frontend environment and install dependencies."""
    print_header("Setting up Frontend (React + Tailwind + D3)")
    
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    
    # Install npm dependencies
    print_colored("📦 Installing npm dependencies...", Colors.OKCYAN)
    subprocess.run(["npm", "install"], check=True)
    
    print_colored("✅ Frontend setup complete!", Colors.OKGREEN)

def check_neo4j_connection():
    """Check if Neo4j is accessible."""
    print_colored("🔍 Checking Neo4j connection...", Colors.OKCYAN)
    
    try:
        # Try to import neo4j and test connection
        import sys
        sys.path.append(str(Path(__file__).parent / "backend"))
        
        from neo4j import GraphDatabase, basic_auth
        
        driver = GraphDatabase.driver(
            "bolt://localhost:7689",
            auth=basic_auth("neo4j", "testpassword")
        )
        
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record and record["test"] == 1:
                print_colored("✅ Neo4j connection successful!", Colors.OKGREEN)
                return True
                
    except Exception as e:
        print_colored(f"⚠️  Neo4j connection failed: {e}", Colors.WARNING)
        print_colored("Make sure Neo4j is running on bolt://localhost:7689", Colors.WARNING)
        print_colored("Credentials: neo4j/testpassword", Colors.WARNING)
        return False
    
    return False

def launch_backend(python_path):
    """Launch the backend server."""
    print_colored("🚀 Starting Backend Server (port 8001)...", Colors.OKCYAN)
    
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    # Start the backend server
    backend_process = subprocess.Popen([
        str(python_path), "-m", "uvicorn", "app:app", 
        "--host", "0.0.0.0", "--port", "8001", "--reload"
    ])
    
    return backend_process

def launch_frontend():
    """Launch the frontend development server."""
    print_colored("🚀 Starting Frontend Server (port 3000)...", Colors.OKCYAN)
    
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    
    # Start the frontend server
    frontend_process = subprocess.Popen(["npm", "start"])
    
    return frontend_process

def wait_for_server(url, timeout=30):
    """Wait for a server to become available."""
    import urllib.request
    import urllib.error
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url, timeout=5)
            return True
        except (urllib.error.URLError, ConnectionError):
            time.sleep(1)
    return False

def main():
    """Main function to set up and launch the debug UI."""
    print_header("Flow Engine Debug UI - Enhanced Setup & Launch")
    print_colored("🔧 Enhanced with Template Support & Variable Placeholders", Colors.OKCYAN)
    print_colored("📊 Comprehensive Debug Capture & Execution History", Colors.OKCYAN)
    print_colored("🎯 isPrimaryFlow Parameter Support", Colors.OKCYAN)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check prerequisites
    print_header("Checking Prerequisites")
    if not check_python_version():
        sys.exit(1)
    
    if not check_node_npm():
        sys.exit(1)
    
    # Check Neo4j (optional)
    neo4j_available = check_neo4j_connection()
    if not neo4j_available:
        print_colored("⚠️  Continuing without Neo4j - some features may not work", Colors.WARNING)
    
    try:
        # Setup backend
        python_path = setup_backend()
        
        # Setup frontend
        setup_frontend()
        
        # Launch servers
        print_header("Launching Servers")
        
        # Start backend
        backend_process = launch_backend(python_path)
        
        # Wait a moment for backend to start
        print_colored("⏳ Waiting for backend to start...", Colors.OKCYAN)
        time.sleep(3)
        
        # Check if backend is running
        if wait_for_server("http://localhost:8001/api/health", timeout=15):
            print_colored("✅ Backend server is running!", Colors.OKGREEN)
        else:
            print_colored("⚠️  Backend server may not be ready yet", Colors.WARNING)
        
        # Start frontend
        frontend_process = launch_frontend()
        
        # Wait for frontend
        print_colored("⏳ Waiting for frontend to start...", Colors.OKCYAN)
        time.sleep(5)
        
        if wait_for_server("http://localhost:3000", timeout=30):
            print_colored("✅ Frontend server is running!", Colors.OKGREEN)
        else:
            print_colored("⚠️  Frontend server may not be ready yet", Colors.WARNING)
        
        # Success message
        print_header("🎉 Debug UI is Ready!")
        print_colored("Frontend: http://localhost:3000", Colors.OKGREEN + Colors.BOLD)
        print_colored("Backend:  http://localhost:8001", Colors.OKGREEN + Colors.BOLD)
        print_colored("API Docs: http://localhost:8001/docs", Colors.OKCYAN)
        
        print_colored("\n🚀 Enhanced Features Available:", Colors.HEADER)
        print_colored("  • Template substitution with {{ variable }} syntax", Colors.OKBLUE)
        print_colored("  • Enhanced source node resolution", Colors.OKBLUE)
        print_colored("  • isPrimaryFlow parameter support", Colors.OKBLUE)
        print_colored("  • Comprehensive debug information capture", Colors.OKBLUE)
        print_colored("  • Execution history and favorites", Colors.OKBLUE)
        print_colored("  • Real-time flow visualization", Colors.OKBLUE)
        
        print_colored("\n💡 Usage Tips:", Colors.WARNING)
        print_colored("  • Use the Track Browser to navigate flows", Colors.WARNING)
        print_colored("  • Set isPrimaryFlow=true/false in JSON payload", Colors.WARNING)
        print_colored("  • View debug info in the right panel", Colors.WARNING)
        print_colored("  • Save favorite executions for later", Colors.WARNING)
        
        print_colored(f"\nPress Ctrl+C to stop both servers", Colors.OKCYAN)
        
        # Wait for interrupt
        def signal_handler(sig, frame):
            print_colored("\n\n🛑 Shutting down servers...", Colors.WARNING)
            backend_process.terminate()
            frontend_process.terminate()
            print_colored("✅ Servers stopped. Goodbye!", Colors.OKGREEN)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Keep the script running
        backend_process.wait()
        
    except KeyboardInterrupt:
        print_colored("\n\n🛑 Interrupted by user", Colors.WARNING)
    except subprocess.CalledProcessError as e:
        print_colored(f"\n❌ Setup failed: {e}", Colors.FAIL)
        sys.exit(1)
    except Exception as e:
        print_colored(f"\n❌ Unexpected error: {e}", Colors.FAIL)
        sys.exit(1)

if __name__ == "__main__":
    main() 