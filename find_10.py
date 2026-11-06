import os

for root, _, files in os.walk('.'):
    if '.venv' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('.py') or file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    if '10' in line:
                        print(f"{path}:{i+1}:{line.strip()}")
