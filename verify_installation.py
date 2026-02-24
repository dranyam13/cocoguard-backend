#!/usr/bin/env python3
"""
CocoGuard Installation Verification Script
Checks if all components are properly installed and configured
"""

import os
import sys
import json
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def check_file_exists(path, name):
    """Check if a file exists"""
    if os.path.exists(path):
        print_success(f"Found: {name}")
        return True
    else:
        print_error(f"Missing: {name}")
        return False

def check_directory_exists(path, name):
    """Check if a directory exists"""
    if os.path.isdir(path):
        print_success(f"Found directory: {name}")
        return True
    else:
        print_error(f"Missing directory: {name}")
        return False

def main():
    print(f"\n{Colors.BLUE}{'='*60}")
    print("   CocoGuard Installation Verification")
    print(f"{'='*60}{Colors.END}\n")
    
    checks = {
        'backend': [],
        'web': [],
        'mobile': [],
        'docs': []
    }
    
    # Backend checks
    print(f"\n{Colors.BLUE}[BACKEND]{Colors.END}")
    backend_path = "cocoguard-backend"
    checks['backend'].append(check_directory_exists(backend_path, "Backend directory"))
    checks['backend'].append(check_file_exists(f"{backend_path}/requirements.txt", "requirements.txt"))
    checks['backend'].append(check_file_exists(f"{backend_path}/.env.example", ".env.example"))
    checks['backend'].append(check_file_exists(f"{backend_path}/run.bat", "run.bat"))
    checks['backend'].append(check_file_exists(f"{backend_path}/run.sh", "run.sh"))
    checks['backend'].append(check_file_exists(f"{backend_path}/SETUP.md", "SETUP.md"))
    checks['backend'].append(check_file_exists(f"{backend_path}/API_REQUESTS.rest", "API_REQUESTS.rest"))
    checks['backend'].append(check_file_exists(f"{backend_path}/app/main.py", "main.py"))
    checks['backend'].append(check_file_exists(f"{backend_path}/app/config.py", "config.py"))
    checks['backend'].append(check_file_exists(f"{backend_path}/app/routers/analytics.py", "analytics.py"))
    checks['backend'].append(check_file_exists(f"{backend_path}/app/routers/feedback.py", "feedback.py"))
    checks['backend'].append(check_file_exists(f"{backend_path}/app/routers/knowledge.py", "knowledge.py"))
    checks['backend'].append(check_file_exists(f"{backend_path}/app/routers/uploads.py", "uploads.py"))
    
    # Web frontend checks
    print(f"\n{Colors.BLUE}[WEB FRONTEND]{Colors.END}")
    web_path = "cocoguard_web"
    checks['web'].append(check_directory_exists(web_path, "Web frontend directory"))
    checks['web'].append(check_file_exists(f"{web_path}/api-client.js", "api-client.js"))
    checks['web'].append(check_file_exists(f"{web_path}/index.html", "index.html"))
    checks['web'].append(check_file_exists(f"{web_path}/script.js", "script.js"))
    checks['web'].append(check_file_exists(f"{web_path}/pages/dashboard.js", "dashboard.js"))
    
    # Mobile checks
    print(f"\n{Colors.BLUE}[MOBILE APP]{Colors.END}")
    mobile_path = "cocoguard"
    checks['mobile'].append(check_directory_exists(mobile_path, "Flutter project directory"))
    checks['mobile'].append(check_file_exists(f"{mobile_path}/BACKEND_INTEGRATION.md", "BACKEND_INTEGRATION.md"))
    checks['mobile'].append(check_file_exists(f"{mobile_path}/pubspec.yaml", "pubspec.yaml"))
    
    # Documentation checks
    print(f"\n{Colors.BLUE}[DOCUMENTATION]{Colors.END}")
    checks['docs'].append(check_file_exists("README.md", "README.md"))
    checks['docs'].append(check_file_exists("START_HERE.md", "START_HERE.md"))
    checks['docs'].append(check_file_exists("QUICKSTART.md", "QUICKSTART.md"))
    checks['docs'].append(check_file_exists("IMPLEMENTATION_COMPLETE.md", "IMPLEMENTATION_COMPLETE.md"))
    checks['docs'].append(check_file_exists("COMPLETE_SUMMARY.md", "COMPLETE_SUMMARY.md"))
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}")
    print("   VERIFICATION SUMMARY")
    print(f"{'='*60}{Colors.END}\n")
    
    total_checks = 0
    total_passed = 0
    
    for category, results in checks.items():
        passed = sum(results)
        total = len(results)
        total_checks += total
        total_passed += passed
        
        status = Colors.GREEN if passed == total else Colors.YELLOW
        print(f"{status}{category.upper():.<20} {passed}/{total}{Colors.END}")
    
    print()
    
    # Overall status
    if total_passed == total_checks:
        print_success(f"All {total_checks} checks passed! ✨")
        print_info("Your CocoGuard system is ready!")
        return 0
    else:
        print_warning(f"Some checks failed: {total_passed}/{total_checks} passed")
        print_info("Missing files may indicate incomplete setup")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nVerification cancelled.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Verification failed: {e}")
        sys.exit(1)
