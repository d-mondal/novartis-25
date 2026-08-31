import os
import re

def find_imports_in_file(filepath):
    imports = set()
    with open(filepath, 'r') as f:
        content = f.read()
        # Find import statements
        matches = re.findall(r'^\s*(?:from|import)\s+(\S+)', content, re.MULTILINE)
        for match in matches:
            # Get base package name
            pkg = match.split('.')[0]
            imports.add(pkg)
    return imports

all_imports = set()
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            imports = find_imports_in_file(filepath)
            all_imports.update(imports)

print("Packages your code imports:")
for pkg in sorted(all_imports):
    print(f"  {pkg}")
