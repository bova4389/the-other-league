"""Find first unclosed bracket in JS extracted from index.html."""
html = open('c:/Users/bovac/OneDrive/Desktop/Claude Code/index.html', encoding='utf-8').read()

# Find the single inline <script> block (not <script src=...>)
import re
m = re.search(r'<script>(.+?)</script>', html, re.DOTALL)
if not m:
    print('No <script> block found')
    exit(1)

js = m.group(1)
lines = js.split('\n')
print(f'JS lines: {len(lines)}')

stacks = {'(': [], '[': [], '{': []}
close_map = {')': '(', ']': '[', '}': '{'}
in_str = None
in_block_comment = False

for lnum, line in enumerate(lines, 1):
    in_line_comment = False
    i = 0
    while i < len(line):
        ch = line[i]

        if in_block_comment:
            if i > 0 and line[i-1] == '*' and ch == '/':
                in_block_comment = False
            i += 1
            continue

        if in_line_comment:
            break

        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue

        if i+1 < len(line) and ch == '/' and line[i+1] == '/':
            in_line_comment = True
            break
        if i+1 < len(line) and ch == '/' and line[i+1] == '*':
            in_block_comment = True
            i += 2
            continue

        if ch in ('"', "'", '`'):
            in_str = ch
            i += 1
            continue

        if ch in stacks:
            stacks[ch].append((lnum, line.strip()[:60]))
        elif ch in close_map:
            k = close_map[ch]
            if stacks[k]:
                stacks[k].pop()
            else:
                print(f'UNMATCHED CLOSE {ch!r} at line {lnum}: {line.strip()[:60]}')
        i += 1

for ch, stack in stacks.items():
    if stack:
        print(f'UNCLOSED {ch!r}: {len(stack)} open — last opened at line {stack[-1][0]}: {stack[-1][1]}')

if all(len(s)==0 for s in stacks.values()):
    print('All brackets balanced.')
