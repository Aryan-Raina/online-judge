import sqlite3
import os
from datetime import datetime

def init_database():
    """Initialize the online judge database with required tables"""
    
    # Create database directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Connect to SQLite database
    conn = sqlite3.connect("data/online_judge.db")
    cursor = conn.cursor()
    
    # Create problems table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            input_format TEXT,
            output_format TEXT,
            constraints TEXT,
            time_limit INTEGER DEFAULT 2000,  -- in milliseconds
            memory_limit INTEGER DEFAULT 256,  -- in MB
            difficulty TEXT DEFAULT 'Easy',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create test_cases table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER,
            input_data TEXT NOT NULL,
            expected_output TEXT NOT NULL,
            is_sample BOOLEAN DEFAULT 0,  -- 1 for sample cases, 0 for hidden
            FOREIGN KEY (problem_id) REFERENCES problems (id)
        )
    """)
    
    # Create submissions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER,
            language TEXT NOT NULL,
            code TEXT NOT NULL,
            verdict TEXT DEFAULT 'Pending',  -- AC, WA, TLE, MLE, RE, CE
            execution_time INTEGER,  -- in milliseconds
            memory_used INTEGER,  -- in KB
            test_cases_passed INTEGER DEFAULT 0,
            total_test_cases INTEGER DEFAULT 0,
            error_message TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (problem_id) REFERENCES problems (id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def add_sample_problem():
    """Add a sample problem for testing"""
    
    conn = sqlite3.connect("data/online_judge.db")
    cursor = conn.cursor()
    
    # Check if sample problem already exists
    cursor.execute("SELECT COUNT(*) FROM problems WHERE title = ?", ("Two Sum",))
    if cursor.fetchone()[0] > 0:
        print("Sample problem already exists!")
        conn.close()
        return
    
    # Insert sample problem
    cursor.execute("""
        INSERT INTO problems (title, description, input_format, output_format, constraints, time_limit, memory_limit, difficulty)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Two Sum",
        """Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.

You may assume that each input would have exactly one solution, and you may not use the same element twice.

You can return the answer in any order.

Example 1:
Input: nums = [2,7,11,15], target = 9
Output: [0,1]
Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].

Example 2:
Input: nums = [3,2,4], target = 6
Output: [1,2]""",
        "First line contains n (array size) and target separated by space.\nSecond line contains n integers separated by spaces.",
        "Two integers representing the indices, separated by space.",
        "2 ≤ n ≤ 10^4\n-10^9 ≤ nums[i] ≤ 10^9\n-10^9 ≤ target ≤ 10^9",
        1000,  # 1 second
        128,   # 128 MB
        "Easy"
    ))
    
    problem_id = cursor.lastrowid
    
    # Add sample test cases
    test_cases = [
        ("4 9\n2 7 11 15", "0 1", True),   # Sample case
        ("3 6\n3 2 4", "1 2", False),      # Hidden case
        ("2 6\n3 3", "0 1", False),        # Hidden case
        ("5 8\n1 2 3 4 5", "2 4", False),  # Hidden case
    ]
    
    for input_data, expected_output, is_sample in test_cases:
        cursor.execute("""
            INSERT INTO test_cases (problem_id, input_data, expected_output, is_sample)
            VALUES (?, ?, ?, ?)
        """, (problem_id, input_data, expected_output, is_sample))
    
    conn.commit()
    conn.close()
    print(f"Sample problem 'Two Sum' added with ID {problem_id}")

if __name__ == "__main__":
    init_database()
    add_sample_problem()
