from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_process_page_present():
    app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    assert '📖 Alur Program' in app
    assert 'show_process_page()' in app
    assert 'Created by Mohamad Idris, S.Si., M.Sc.' in app


def test_flowcharts_are_bundled():
    for filename in ('alur_enkripsi.png', 'alur_dekripsi.png'):
        assert (ROOT / 'assets' / filename).stat().st_size > 10_000
