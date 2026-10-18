from scripts.mineducyt import fetch_mineducyt_source
from scripts.santillana import find_cached_santillana_sources, record_santillana_photo


def ground_topic(workspace, subject, topic, grade, is_curricular, santillana_photo_path=None, download=None):
    if not is_curricular:
        return {"sources": [], "gap": None}

    sources = []

    mineducyt_kwargs = {"download": download} if download else {}
    mineducyt_source = fetch_mineducyt_source(subject, grade, workspace / "sources" / "mineducyt", **mineducyt_kwargs)
    if mineducyt_source is not None:
        sources.append(mineducyt_source)

    just_recorded_path = None
    if santillana_photo_path is not None:
        recorded = record_santillana_photo(workspace, subject, topic, santillana_photo_path)
        sources.append(recorded)
        just_recorded_path = recorded["cached_path"]

    for cached in find_cached_santillana_sources(workspace, subject, topic):
        if cached["cached_path"] != just_recorded_path:
            sources.append(cached)

    gap = None
    if not sources:
        gap = f"no MINEDUCYT coverage and no Santillana photo supplied for {subject}/{topic} grade {grade}"

    return {"sources": sources, "gap": gap}
