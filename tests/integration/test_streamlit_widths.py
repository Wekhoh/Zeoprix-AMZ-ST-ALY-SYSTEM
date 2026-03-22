from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_hot_path_pages_stop_using_deprecated_use_container_width():
    hot_path_pages = [
        ROOT / 'src/ui/pages/analysis.py',
        ROOT / 'src/ui/pages/asin_analysis.py',
        ROOT / 'src/ui/pages/analysis_asin.py',
        ROOT / 'src/ui/pages/analysis_campaign.py',
        ROOT / 'src/ui/pages/upload.py',
    ]

    remaining = {}
    for page in hot_path_pages:
        lines = [
            line.strip()
            for line in page.read_text(encoding='utf-8').splitlines()
            if 'use_container_width' in line
        ]
        if lines:
            remaining[str(page.relative_to(ROOT))] = lines

    assert remaining == {}, f'Deprecated use_container_width remains: {remaining}'
