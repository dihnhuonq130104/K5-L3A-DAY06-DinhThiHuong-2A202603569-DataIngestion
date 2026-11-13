"""Project paths and serialization."""
from pathlib import Path
from datetime import datetime, timezone
import json
import hashlib

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT/'results'

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def config():
    return read_json(ROOT/'configs/experiment.json')
