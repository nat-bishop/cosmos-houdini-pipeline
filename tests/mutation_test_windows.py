"""
Simple mutation testing script for Windows.
Since mutmut doesn't work on Windows (requires Unix 'resource' module),
this provides a basic alternative for testing our test effectiveness.
"""

import ast
import copy
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

class SimpleMutator(ast.NodeTransformer):
    """Simple AST-based code mutator."""
    
    def __init__(self, mutation_index: int = 0):
        self.mutation_index = mutation_index
        self.current_index = 0
        self.mutations_applied = []
    
    def visit_Compare(self, node):
        """Mutate comparison operators."""
        self.generic_visit(node)
        
        if self.current_index == self.mutation_index:
            # Mutate comparison operators
            mutations = {
                ast.Eq: ast.NotEq,
                ast.NotEq: ast.Eq,
                ast.Lt: ast.GtE,
                ast.Gt: ast.LtE,
                ast.LtE: ast.Gt,
                ast.GtE: ast.Lt,
            }
            
            if node.ops:
                old_op = node.ops[0]
                new_op_class = mutations.get(type(old_op))
                if new_op_class:
                    node.ops[0] = new_op_class()
                    self.mutations_applied.append(f"Mutated {old_op.__class__.__name__} to {new_op_class.__name__}")
        
        self.current_index += 1
        return node
    
    def visit_BoolOp(self, node):
        """Mutate boolean operators."""
        self.generic_visit(node)
        
        if self.current_index == self.mutation_index:
            # Swap And/Or
            if isinstance(node.op, ast.And):
                node.op = ast.Or()
                self.mutations_applied.append("Mutated And to Or")
            elif isinstance(node.op, ast.Or):
                node.op = ast.And()
                self.mutations_applied.append("Mutated Or to And")
        
        self.current_index += 1
        return node
    
    def visit_Constant(self, node):
        """Mutate constants."""
        if self.current_index == self.mutation_index:
            if isinstance(node.value, bool):
                node.value = not node.value
                self.mutations_applied.append(f"Mutated {not node.value} to {node.value}")
            elif isinstance(node.value, (int, float)) and node.value != 0:
                node.value = node.value + 1
                self.mutations_applied.append(f"Mutated {node.value-1} to {node.value}")
        
        self.current_index += 1
        return node


def run_tests(test_path: str) -> bool:
    """Run tests and return True if all pass."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-x", "-q"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def mutate_file(file_path: Path, mutation_index: int) -> Tuple[str, List[str]]:
    """Apply a single mutation to a file."""
    with open(file_path, 'r') as f:
        source = f.read()
    
    tree = ast.parse(source)
    mutator = SimpleMutator(mutation_index)
    mutated_tree = mutator.visit(tree)
    
    if not mutator.mutations_applied:
        return None, []
    
    return ast.unparse(mutated_tree), mutator.mutations_applied


def run_mutation_testing(source_file: Path, test_file: str):
    """Run mutation testing on a source file."""
    print(f"\n{'='*60}")
    print(f"Mutation Testing: {source_file.name}")
    print(f"Test File: {test_file}")
    print(f"{'='*60}\n")
    
    # First verify tests pass with original code
    print("Running baseline tests...")
    if not run_tests(test_file):
        print("X Baseline tests failed! Fix tests before running mutation testing.")
        return
    print("OK Baseline tests pass\n")
    
    # Read original source
    with open(source_file, 'r') as f:
        original_source = f.read()
    
    mutations_killed = 0
    mutations_survived = 0
    survived_mutations = []
    
    # Try multiple mutations
    for i in range(50):  # Try up to 50 mutations
        mutated_source, mutations = mutate_file(source_file, i)
        
        if not mutated_source:
            continue
        
        # Write mutated code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(mutated_source)
            tmp_path = tmp.name
        
        # Replace original with mutated
        source_file.write_text(mutated_source)
        
        # Run tests
        tests_pass = run_tests(test_file)
        
        # Restore original
        source_file.write_text(original_source)
        
        # Clean up temp file
        Path(tmp_path).unlink()
        
        if tests_pass:
            mutations_survived += 1
            survived_mutations.append(mutations[0] if mutations else "Unknown")
            print(f"!  Mutation {i+1} SURVIVED: {mutations[0] if mutations else 'Unknown'}")
        else:
            mutations_killed += 1
            print(f"OK Mutation {i+1} KILLED: {mutations[0] if mutations else 'Unknown'}")
    
    # Report results
    total = mutations_killed + mutations_survived
    if total > 0:
        kill_rate = (mutations_killed / total) * 100
        print(f"\n{'='*60}")
        print(f"RESULTS:")
        print(f"  Mutations tested: {total}")
        print(f"  Killed: {mutations_killed}")
        print(f"  Survived: {mutations_survived}")
        print(f"  Kill rate: {kill_rate:.1f}%")
        
        if survived_mutations:
            print(f"\nSurvived mutations (tests didn't catch these):")
            for mutation in survived_mutations:
                print(f"  - {mutation}")
        
        if kill_rate >= 80:
            print(f"\n[GOOD] Tests are effective (>80% kill rate)")
        elif kill_rate >= 60:
            print(f"\n[OK] Tests are moderately effective (60-80% kill rate)")
        else:
            print(f"\n[POOR] Tests need improvement (<60% kill rate)")
    else:
        print("No mutations could be applied")


if __name__ == "__main__":
    # Test our refactored tests
    tests_to_check = [
        (
            Path("../cosmos_workflow/workflows/workflow_orchestrator.py"),
            "integration/test_workflow_orchestration.py::TestWorkflowOrchestrationBehavior"
        ),
        (
            Path("../cosmos_workflow/execution/docker_executor.py"),
            "integration/test_docker_executor.py::TestDockerExecutorBehavior"
        ),
    ]
    
    for source_file, test_file in tests_to_check:
        if source_file.exists():
            run_mutation_testing(source_file, test_file)
        else:
            print(f"Skipping {source_file} (not found)")