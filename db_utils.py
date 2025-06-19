import sqlite3
from typing import List, Dict, Optional

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect("data/online_judge.db")
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def get_all_problems() -> List[Dict]:
    """Get all problems"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM problems ORDER BY created_at DESC")
    problems = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return problems

def get_problem_by_id(problem_id: int) -> Optional[Dict]:
    """Get a specific problem by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
    problem = cursor.fetchone()
    conn.close()
    return dict(problem) if problem else None

def get_test_cases(problem_id: int, include_hidden: bool = False) -> List[Dict]:
    """Get test cases for a problem"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if include_hidden:
        cursor.execute("SELECT * FROM test_cases WHERE problem_id = ?", (problem_id,))
    else:
        cursor.execute("SELECT * FROM test_cases WHERE problem_id = ? AND is_sample = 1", (problem_id,))
    
    test_cases = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return test_cases

def save_submission(problem_id: int, language: str, code: str, verdict: str, 
                   execution_time: int, memory_used: int, test_cases_passed: int, 
                   total_test_cases: int, error_message: str = None) -> int:
    """Save a submission to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO submissions (problem_id, language, code, verdict, execution_time, 
                               memory_used, test_cases_passed, total_test_cases, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (problem_id, language, code, verdict, execution_time, memory_used, 
          test_cases_passed, total_test_cases, error_message))
    
    submission_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return submission_id

def get_submissions(problem_id: int = None, limit: int = 50) -> List[Dict]:
    """Get recent submissions"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if problem_id:
        cursor.execute("""
            SELECT s.*, p.title as problem_title 
            FROM submissions s 
            JOIN problems p ON s.problem_id = p.id 
            WHERE s.problem_id = ? 
            ORDER BY s.submitted_at DESC 
            LIMIT ?
        """, (problem_id, limit))
    else:
        cursor.execute("""
            SELECT s.*, p.title as problem_title 
            FROM submissions s 
            JOIN problems p ON s.problem_id = p.id 
            ORDER BY s.submitted_at DESC 
            LIMIT ?
        """, (limit,))
    
    submissions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return submissions
