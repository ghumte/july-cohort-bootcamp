"""Explicit skill discovery and loading for this small host application."""
import hashlib
import re
from .config import ROOT

SKILLS = ROOT / 'skills'

def discover_skills():
    """Read only YAML metadata for discovery. The body loads on selection."""
    found = []
    for path in sorted(SKILLS.glob('*/SKILL.md')):
        text = path.read_text()
        head = text.split('---', 2)[1]
        meta = dict(re.findall(r'^(name|description):\s*(.+)$', head, re.M))
        if meta.get('name') != path.parent.name or not meta.get('description'):
            raise ValueError(f'Invalid skill metadata: {path.name}')
        found.append(meta)
    return found

def load_skill(name):
    allowed = {s['name'] for s in discover_skills()}
    if name not in allowed:
        raise ValueError('Choose a skill from the local registry.')
    path = SKILLS / name / 'SKILL.md'
    raw = path.read_text()
    body = raw.split('---', 2)[2].strip()
    references = []
    for relative in re.findall(r'\]\((references/[^)]+)\)', body):
        ref = (path.parent / relative).resolve()
        if not ref.is_relative_to(path.parent.resolve()):
            raise ValueError('Reference must stay in the skill folder.')
        references.append({'path': relative, 'text': ref.read_text()})
    prompt = body + ''.join(f'\n\nReference: {r["path"]}\n{r["text"]}' for r in references)
    return {'name': name, 'body': body, 'references': references, 'prompt': prompt,
            'sha256': hashlib.sha256(prompt.encode()).hexdigest()[:12]}
