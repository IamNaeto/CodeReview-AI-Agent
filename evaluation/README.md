# Evaluation Scenarios

This directory contains 5 intentionally flawed code snippets designed to test the agentic review system.

| Scenario | File | Expected Issues | Expected Agents |
|----------|------|-----------------|-----------------|
| 1 | scenario1_sql_injection.py | SQL Injection (Critical), Input Validation | Security, Correctness |
| 2 | scenario2_performance.py | N+1 Query, Inefficient Algorithm | Performance |
| 3 | scenario3_logic_error.py | Race Condition, Missing Exception Handling | Correctness, Security |
| 4 | scenario4_missing_tests.py | Missing unit/edge-case tests | Testing |
| 5 | scenario5_architecture.py | Tight coupling, God class | Architecture, Quality |

## Running Evaluation

1. Start the backend
2. Paste the content of any scenario file as a raw diff into the UI
3. Verify the expected findings appear in the report
