"""Proper JS bracket checker with template literal and regex character class support."""
import sys, re

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
html = open('c:/Users/bovac/OneDrive/Desktop/Claude Code/index.html', encoding='utf-8').read()
m = re.search(r'<script>(.+?)</script>', html, re.DOTALL)
js = m.group(1)

STATE_NORMAL = 0
STATE_LINE_COMMENT = 1
STATE_BLOCK_COMMENT = 2
STATE_STRING_SINGLE = 3
STATE_STRING_DOUBLE = 4
STATE_TEMPLATE = 5
STATE_REGEX = 6
STATE_REGEX_CLASS = 7

state = STATE_NORMAL
template_brace_depth = []
bracket_stack = {'(': [], '[': [], '{': []}
close_map = {')': '(', ']': '[', '}': '{'}
BACKSLASH = chr(92)

lnum = 1
errors = []
i = 0

def peek(offset=1):
    return js[i+offset] if i+offset < len(js) else ''

while i < len(js):
    ch = js[i]
    if ch == '\n':
        lnum += 1

    if state == STATE_LINE_COMMENT:
        if ch == '\n':
            state = STATE_NORMAL
        i += 1
        continue

    if state == STATE_BLOCK_COMMENT:
        if ch == '*' and peek() == '/':
            state = STATE_NORMAL
            i += 2
            continue
        i += 1
        continue

    if state == STATE_STRING_SINGLE:
        if ch == BACKSLASH:
            i += 2
            continue
        if ch == "'":
            state = STATE_NORMAL
        i += 1
        continue

    if state == STATE_STRING_DOUBLE:
        if ch == BACKSLASH:
            i += 2
            continue
        if ch == '"':
            state = STATE_NORMAL
        i += 1
        continue

    if state == STATE_REGEX_CLASS:
        if ch == BACKSLASH:
            i += 2
            continue
        if ch == ']':
            state = STATE_REGEX
        i += 1
        continue

    if state == STATE_REGEX:
        if ch == BACKSLASH:
            i += 2
            continue
        if ch == '[':
            state = STATE_REGEX_CLASS
            i += 1
            continue
        if ch == '/':
            state = STATE_NORMAL
            i += 1
            while i < len(js) and js[i].isalpha():
                i += 1
            continue
        i += 1
        continue

    if state == STATE_TEMPLATE:
        if ch == BACKSLASH:
            i += 2
            continue
        if ch == '`':
            state = STATE_NORMAL
            if template_brace_depth:
                template_brace_depth.pop()
            i += 1
            continue
        if ch == '$' and peek() == '{':
            bracket_stack['{'].append((lnum, 'tmpl-expr'))
            template_brace_depth.append(0)
            state = STATE_NORMAL
            i += 2
            continue
        i += 1
        continue

    # STATE_NORMAL
    if ch == '/' and peek() == '/':
        state = STATE_LINE_COMMENT
        i += 2
        continue
    if ch == '/' and peek() == '*':
        state = STATE_BLOCK_COMMENT
        i += 2
        continue
    if ch == "'":
        state = STATE_STRING_SINGLE
        i += 1
        continue
    if ch == '"':
        state = STATE_STRING_DOUBLE
        i += 1
        continue
    if ch == '`':
        state = STATE_TEMPLATE
        template_brace_depth.append(0)
        i += 1
        continue

    if ch in bracket_stack:
        bracket_stack[ch].append((lnum, ''))
    elif ch in close_map:
        k = close_map[ch]
        if bracket_stack[k]:
            top = bracket_stack[k].pop()
            if ch == '}' and template_brace_depth and top[1] == 'tmpl-expr':
                state = STATE_TEMPLATE
                template_brace_depth.pop()
        else:
            errors.append(f'UNMATCHED CLOSE {ch!r} at line {lnum}')
    i += 1

for ch, stack in bracket_stack.items():
    if stack:
        print(f'UNCLOSED {ch!r}: {len(stack)} open — last at line {stack[-1][0]}')
for e in errors[:5]:
    print(e)
if all(len(s) == 0 for s in bracket_stack.values()) and not errors:
    print('All brackets balanced.')
print(f'Ended state: {state} (0=normal,1=line-comment,2=block-comment,3=str-single,4=str-double,5=template,6=regex,7=regex-class)')
