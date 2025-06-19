# main.py - Enhanced FastAPI Online Judge
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import subprocess
import os
import uuid
import tempfile
import psutil
import threading
import time
import sqlite3
from typing import List, Optional
import json

# Initialize FastAPI app
app = FastAPI(
    title="Online Judge Platform",
    description="Competitive Programming Platform with Problems and Submissions",
)

# Templates for HTML pages
templates = Jinja2Templates(directory="templates")

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect("data/online_judge.db")
    conn.row_factory = sqlite3.Row
    return conn

# Pydantic models
class CodeRequest(BaseModel):
    language: str
    code: str
    input_data: str = ""

class SubmissionRequest(BaseModel):
    problem_id: int
    language: str
    code: str

class ResourceMonitor:
    """Monitor resource usage during code execution"""
    
    def __init__(self, time_limit_ms: int, memory_limit_mb: int):
        self.time_limit = time_limit_ms / 1000.0  # Convert to seconds
        self.memory_limit = memory_limit_mb * 1024 * 1024  # Convert to bytes
        self.start_time = None
        self.max_memory = 0
        self.timed_out = False
        self.memory_exceeded = False
        self.monitoring = False
        
    def start_monitoring(self, process):
        """Start monitoring a subprocess"""
        self.start_time = time.time()
        self.monitoring = True
        
        def monitor():
            try:
                proc = psutil.Process(process.pid)
                while self.monitoring and proc.is_running():
                    # Check time limit
                    elapsed = time.time() - self.start_time
                    if elapsed > self.time_limit:
                        self.timed_out = True
                        process.terminate()
                        break
                    
                    # Check memory limit
                    try:
                        memory_info = proc.memory_info()
                        current_memory = memory_info.rss
                        self.max_memory = max(self.max_memory, current_memory)
                        
                        if current_memory > self.memory_limit:
                            self.memory_exceeded = True
                            process.terminate()
                            break
                    except psutil.NoSuchProcess:
                        break
                    
                    time.sleep(0.01)  # Check every 10ms
            except Exception as e:
                print(f"Monitoring error: {e}")
        
        monitor_thread = threading.Thread(target=monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        
    def get_verdict(self, return_code, stderr):
        """Determine verdict based on execution results"""
        if self.timed_out:
            return "TLE", f"Time Limit Exceeded"
        
        if self.memory_exceeded:
            return "MLE", f"Memory Limit Exceeded"
        
        if return_code != 0:
            return "RE", f"Runtime Error: {stderr[:200]}"
        
        return "OK", "Execution completed successfully"

def execute_code_with_limits(code: str, input_data: str, language: str, 
                           time_limit_ms: int = 1000, memory_limit_mb: int = 128):
    """Execute code with resource limits"""
    
    # Create temporary file
    extension = ".py" if language == "python" else ".js"
    with tempfile.NamedTemporaryFile(mode='w', suffix=extension, delete=False) as f:
        f.write(code)
        file_path = f.name
    
    try:
        # Prepare command
        if language == "python":
            command = ["python", file_path]
        elif language == "javascript":
            command = ["node", file_path]
        else:
            return {
                "verdict": "CE",
                "message": "Unsupported language",
                "output": "",
                "execution_time": 0,
                "memory_used": 0
            }
        
        # Start subprocess
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Start monitoring
        monitor = ResourceMonitor(time_limit_ms, memory_limit_mb)
        monitor.start_monitoring(process)
        
        # Execute with input
        start_time = time.time()
        try:
            stdout, stderr = process.communicate(input=input_data, timeout=time_limit_ms/1000.0 + 1)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            
        execution_time = int((time.time() - start_time) * 1000)
        
        # Stop monitoring
        monitor.stop_monitoring()
        
        # Get verdict
        verdict, message = monitor.get_verdict(process.returncode, stderr)
        
        return {
            "verdict": verdict,
            "message": message,
            "output": stdout,
            "stderr": stderr,
            "execution_time": execution_time,
            "memory_used": monitor.max_memory // 1024,  # Convert to KB
            "return_code": process.returncode
        }
        
    finally:
        # Clean up
        if os.path.exists(file_path):
            os.unlink(file_path)

def judge_submission(problem_id: int, language: str, code: str):
    """Judge a submission against all test cases"""
    
    # Get problem details
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
    problem = cursor.fetchone()
    if not problem:
        return {"verdict": "CE", "message": "Problem not found"}
    
    # Get all test cases (including hidden ones)
    cursor.execute("SELECT * FROM test_cases WHERE problem_id = ?", (problem_id,))
    test_cases = cursor.fetchall()
    conn.close()
    
    if not test_cases:
        return {"verdict": "CE", "message": "No test cases found"}
    
    # Run against each test case
    total_cases = len(test_cases)
    passed_cases = 0
    max_time = 0
    max_memory = 0
    
    for i, test_case in enumerate(test_cases):
        result = execute_code_with_limits(
            code, 
            test_case["input_data"], 
            language,
            problem["time_limit"],
            problem["memory_limit"]
        )
        
        max_time = max(max_time, result["execution_time"])
        max_memory = max(max_memory, result["memory_used"])
        
        # Check for resource limit violations
        if result["verdict"] == "TLE":
            return {
                "verdict": "TLE",
                "message": f"Time Limit Exceeded on test case {i+1}",
                "test_cases_passed": passed_cases,
                "total_test_cases": total_cases,
                "execution_time": max_time,
                "memory_used": max_memory
            }
        
        if result["verdict"] == "MLE":
            return {
                "verdict": "MLE", 
                "message": f"Memory Limit Exceeded on test case {i+1}",
                "test_cases_passed": passed_cases,
                "total_test_cases": total_cases,
                "execution_time": max_time,
                "memory_used": max_memory
            }
        
        if result["verdict"] == "RE":
            return {
                "verdict": "RE",
                "message": f"Runtime Error on test case {i+1}: {result['message']}",
                "test_cases_passed": passed_cases,
                "total_test_cases": total_cases,
                "execution_time": max_time,
                "memory_used": max_memory
            }
        
        # Check output correctness
        expected_output = test_case["expected_output"].strip()
        actual_output = result["output"].strip()
        
        if actual_output != expected_output:
            return {
                "verdict": "WA",
                "message": f"Wrong Answer on test case {i+1}",
                "test_cases_passed": passed_cases,
                "total_test_cases": total_cases,
                "execution_time": max_time,
                "memory_used": max_memory,
                "expected": expected_output,
                "actual": actual_output
            }
        
        passed_cases += 1
    
    # All test cases passed!
    return {
        "verdict": "AC",
        "message": f"Accepted - All {total_cases} test cases passed",
        "test_cases_passed": passed_cases,
        "total_test_cases": total_cases,
        "execution_time": max_time,
        "memory_used": max_memory
    }

# === ROUTES ===

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with problem list"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, difficulty, time_limit, memory_limit FROM problems ORDER BY created_at DESC")
    problems = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return templates.TemplateResponse("home.html", {
        "request": request,
        "problems": problems
    })

@app.get("/problem/{problem_id}", response_class=HTMLResponse)
async def problem_page(request: Request, problem_id: int):
    """Individual problem page"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get problem details
    cursor.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
    problem = cursor.fetchone()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Get sample test cases only
    cursor.execute("SELECT * FROM test_cases WHERE problem_id = ? AND is_sample = 1", (problem_id,))
    sample_cases = [dict(row) for row in cursor.fetchall()]
    
    # Get recent submissions for this problem
    cursor.execute("""
        SELECT verdict, execution_time, memory_used, submitted_at 
        FROM submissions 
        WHERE problem_id = ? 
        ORDER BY submitted_at DESC 
        LIMIT 10
    """, (problem_id,))
    recent_submissions = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return templates.TemplateResponse("problem.html", {
        "request": request,
        "problem": dict(problem),
        "sample_cases": sample_cases,
        "recent_submissions": recent_submissions
    })

# API endpoints
@app.post("/api/execute")
async def execute_code(request: CodeRequest):
    """Execute code (for testing/debugging)"""
    result = execute_code_with_limits(
        request.code, 
        request.input_data, 
        request.language
    )
    return {
        "output": result["output"] if result["verdict"] == "OK" else result["stderr"],
        "error": result["verdict"] != "OK",
        "execution_time": result["execution_time"],
        "memory_used": result["memory_used"]
    }

@app.post("/api/submit")
async def submit_solution(request: SubmissionRequest):
    """Submit solution for judging"""
    
    # Judge the submission
    result = judge_submission(request.problem_id, request.language, request.code)
    
    # Save to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO submissions (problem_id, language, code, verdict, execution_time, 
                               memory_used, test_cases_passed, total_test_cases, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        request.problem_id,
        request.language, 
        request.code,
        result["verdict"],
        result.get("execution_time", 0),
        result.get("memory_used", 0),
        result.get("test_cases_passed", 0),
        result.get("total_test_cases", 0),
        result.get("message", "")
    ))
    
    submission_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "submission_id": submission_id,
        "verdict": result["verdict"],
        "message": result["message"],
        "test_cases_passed": result.get("test_cases_passed", 0),
        "total_test_cases": result.get("total_test_cases", 0),
        "execution_time": result.get("execution_time", 0),
        "memory_used": result.get("memory_used", 0)
    }

@app.get("/api/problems")
async def get_problems():
    """Get all problems"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM problems ORDER BY created_at DESC")
    problems = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"problems": problems}

@app.get("/api/problem/{problem_id}")
async def get_problem(problem_id: int):
    """Get specific problem with sample test cases"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
    problem = cursor.fetchone()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    cursor.execute("SELECT * FROM test_cases WHERE problem_id = ? AND is_sample = 1", (problem_id,))
    sample_cases = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "problem": dict(problem),
        "sample_cases": sample_cases
    }

@app.get("/submissions", response_class=HTMLResponse)
async def submissions_page(request: Request):
    """Submissions page"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.*, p.title as problem_title 
        FROM submissions s 
        JOIN problems p ON s.problem_id = p.id 
        ORDER BY s.submitted_at DESC 
        LIMIT 50
    """)
    submissions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return templates.TemplateResponse("submissions.html", {
        "request": request,
        "submissions": submissions
    })

# Mount static files (must be last)
app.mount("/static", StaticFiles(directory="templates"), name="static")
app.mount("/public", StaticFiles(directory="public", html=True), name="static")
