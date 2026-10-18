def make_source(origin, title, url_or_path, cached_path=None, subject=None, topic=None, grade=None):
    return {
        "origin": origin,
        "title": title,
        "url_or_path": url_or_path,
        "cached_path": cached_path,
        "subject": subject,
        "topic": topic,
        "grade": grade,
    }


def format_citation(source):
    return f"{source['title']} -- {source['url_or_path']}"
