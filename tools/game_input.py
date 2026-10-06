import hashlib
import os
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
GAME_EXE = Path(os.environ.get('FNAF_EXE', str(REPOSITORY / 'FiveNightsatFreddys.exe'))).expanduser().resolve()
EXPECTED_SHA256 = '862cd7ab7c81b20a4e848888bc2493dda0181759c39958a42cc5c3d02dfb195a'

def load_game():
    data = GAME_EXE.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != EXPECTED_SHA256:
        raise ValueError(f'Unsupported executable SHA256: {actual}. Expected {EXPECTED_SHA256}.')
    return data
