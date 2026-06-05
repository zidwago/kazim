#!/usr/bin/env python3
"""
KAZIM — Static Site Generator
Converts Markdown content with YAML frontmatter into a static HTML site.

Usage:
    python3 build.py                           # deploys at /kazim (GitHub Pages)
    KAZIM_BASE_PATH='' python3 build.py        # local dev (localhost:8000)

Reads from:  content/, templates/, static/
Writes to:   output/
"""

import os
import re
import sys
import shutil
import yaml
import markdown
import json
from datetime import datetime
from pathlib import Path

# --- Configuration ---
SITE_TITLE = "Kazim Sherazee"
SITE_SUBTITLE = ""
SITE_URL = "https://zidwago.github.io/kazim"
BASE_PATH = os.environ.get('KAZIM_BASE_PATH', '/kazim')  # '' for local dev
BASE_DIR = Path(__file__).parent
CONTENT_DIR = BASE_DIR / "content"
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "output"

# Markdown extensions
MD_EXTENSIONS = [
    'footnotes',
    'tables',
    'toc',
    'smarty',
    'attr_list',
    'meta',
    'fenced_code',
]

MD_EXTENSION_CONFIGS = {
    'footnotes': {'BACKLINK_TEXT': '↩'},
    'smarty': {'smart_dashes': True, 'smart_quotes': True, 'smart_ellipses': True},
    'toc': {'permalink': False, 'toc_depth': '2-3'},
}

# --- Utility Functions ---

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def parse_frontmatter(text):
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return meta or {}, body
            except yaml.YAMLError:
                pass
    return {}, text

def render_markdown(text):
    md = markdown.Markdown(extensions=MD_EXTENSIONS, extension_configs=MD_EXTENSION_CONFIGS)
    html = md.convert(text)
    toc = getattr(md, 'toc', '')
    md.reset()
    html = process_blockquote_attributions(html)
    return html, toc

def process_blockquote_attributions(html):
    def replace_attribution(match):
        inner = match.group(1)
        pattern = r'<p>\s*(?:—|&mdash;|&#8212;|&mdash;)\s*'
        parts = re.split(r'(<p>\s*(?:—|&mdash;|&#8212;)\s*)', inner)
        if len(parts) >= 2:
            last_p_idx = None
            for i in range(len(parts)-1, -1, -1):
                if re.match(r'<p>\s*(?:—|&mdash;|&#8212;)\s*', parts[i]):
                    last_p_idx = i
                    break
            if last_p_idx is not None:
                before = ''.join(parts[:last_p_idx])
                attr_start = parts[last_p_idx]
                attr_rest = parts[last_p_idx+1] if last_p_idx+1 < len(parts) else ''
                attribution = attr_start.replace('<p>', '<div class="blockquote-attribution">') + attr_rest
                attribution = attribution.replace('</p>', '</div>')
                return '<blockquote>' + before + attribution + '</blockquote>'
        return match.group(0)
    html = re.sub(r'<blockquote>(.*?)</blockquote>', replace_attribution, html, flags=re.DOTALL)
    return html

def format_date(date_val):
    if isinstance(date_val, datetime):
        return date_val.strftime('%-d/%m/%Y')
    if isinstance(date_val, str):
        try:
            return datetime.strptime(date_val, '%Y-%m-%d').strftime('%-d/%m/%Y')
        except ValueError:
            return date_val
    if hasattr(date_val, 'strftime'):
        return date_val.strftime('%-d/%m/%Y')
    return str(date_val) if date_val else ''

def short_date(date_val):
    if isinstance(date_val, datetime):
        return date_val.strftime('%Y-%m-%d')
    if hasattr(date_val, 'strftime'):
        return date_val.strftime('%Y-%m-%d')
    return str(date_val) if date_val else ''

def count_words(text):
    clean = re.sub(r'[#*_\[\]\(\)\{\}`>|~]', '', text)
    clean = re.sub(r'---.*?---', '', clean, flags=re.DOTALL)
    return len(clean.split())

def sort_by_modified(items):
    def get_date(item):
        d = item.get('modified') or item.get('created') or ''
        if hasattr(d, 'isoformat'):
            return str(d)
        return str(d)
    return sorted(items, key=get_date, reverse=True)

# --- Badge/Tag Rendering ---

def render_status_badge(status):
    if not status:
        return ''
    return f'<span class="badge badge--{status}">{status}</span>'

def render_confidence_badge(confidence):
    if not confidence:
        return ''
    return f'<span class="badge badge--{confidence}">{confidence}</span>'

def render_tags(tags):
    if not tags:
        return ''
    if isinstance(tags, str):
        tags = [tags]
    return ' '.join(f'<span class="tag">{t}</span>' for t in tags)

# --- Base context (injected into every template render) ---

def base_context():
    return {
        'site_title': SITE_TITLE,
        'site_subtitle': SITE_SUBTITLE,
        'base_path': BASE_PATH,
        'year': datetime.now().year,
    }

# --- Template System ---

class TemplateEngine:
    def __init__(self, template_dir):
        self.template_dir = template_dir
        self.cache = {}

    def load(self, name):
        if name not in self.cache:
            path = self.template_dir / name
            self.cache[name] = read_file(path)
        return self.cache[name]

    def render(self, template_name, context):
        # Merge base context
        ctx = base_context()
        ctx.update(context)

        template = self.load(template_name)

        # Handle template inheritance
        extends_marker = '{% extends "'
        if extends_marker in template:
            start = template.index(extends_marker) + len(extends_marker)
            end = template.index('" %}', start)
            parent_name = template[start:end]
            parent = self.load(parent_name)

            child_blocks = self._extract_blocks(template)

            result = parent
            for block_name, block_content in child_blocks.items():
                placeholder = '{{% block ' + block_name + ' %}}{{% endblock %}}'
                result = result.replace(placeholder, block_content)
                pattern = r'\{%\s*block\s+' + re.escape(block_name) + r'\s*%\}.*?\{%\s*endblock\s*%\}'
                result = re.sub(pattern, block_content, result, flags=re.DOTALL)
        else:
            result = template

        # Replace variables
        for key, value in ctx.items():
            result = result.replace('{{ ' + key + ' }}', str(value) if value is not None else '')

        # Clean up unreplaced variables
        result = re.sub(r'\{\{.*?\}\}', '', result)

        return result

    def _extract_blocks(self, template):
        blocks = {}
        pattern = r'\{%\s*block\s+(\w+)\s*%\}(.*?)\{%\s*endblock\s*%\}'
        for match in re.finditer(pattern, template, re.DOTALL):
            blocks[match.group(1)] = match.group(2).strip()
        return blocks


# --- Content Processing ---

def process_content_dir(content_type):
    content_path = CONTENT_DIR / content_type
    if not content_path.exists():
        return []

    items = []
    for md_file in sorted(content_path.glob('*.md')):
        if md_file.name.startswith('._') or md_file.name.startswith('.'):
            continue  # skip macOS metadata files
        raw = read_file(md_file)
        meta, body = parse_frontmatter(raw)
        html_content, toc = render_markdown(body)

        meta['slug'] = md_file.stem
        meta['content'] = html_content
        meta['toc'] = toc
        meta['wordcount'] = count_words(body)
        meta['source_file'] = str(md_file)

        items.append(meta)

    return items

# --- Page Builders ---

def build_essay_page(essay, engine, show_wordcount=True):
    tags_html = render_tags(essay.get('topics'))

    meta_items = []
    if essay.get('created'):
        meta_items.append(f'<span class="article-meta__item">Written {format_date(essay["created"])}</span>')
    if essay.get('modified') and str(essay.get('modified')) != str(essay.get('created')):
        meta_items.append(f'<span class="article-meta__item">Revised {format_date(essay["modified"])}</span>')
    if show_wordcount and essay.get('wordcount'):
        meta_items.append(f'<span class="article-meta__item">{essay["wordcount"]:,} words</span>')
    if essay.get('status'):
        meta_items.append(f'<span class="article-meta__item">{render_status_badge(essay["status"])}</span>')
    if essay.get('confidence'):
        meta_items.append(f'<span class="article-meta__item">{render_confidence_badge(essay["confidence"])}</span>')

    abstract_html = ''
    if essay.get('abstract'):
        abstract_html = f'<div class="article-abstract">{essay["abstract"]}</div>'

    return engine.render('essay.html', {
        'page_title': f'{essay.get("title", "Untitled")} — {SITE_TITLE}',
        'title': essay.get('title', 'Untitled'),
        'meta': '\n'.join(meta_items),
        'abstract': abstract_html,
        'tags': tags_html,
        'content': essay.get('content', ''),
        'toc': essay.get('toc', ''),
    })

def build_reading_page(reading, engine):
    meta_pairs = []
    if reading.get('author'):
        meta_pairs.append(('author', reading['author']))
    if reading.get('publication_year'):
        meta_pairs.append(('published', str(reading['publication_year'])))
    if reading.get('type'):
        meta_pairs.append(('type', reading['type']))
    if reading.get('engagement'):
        meta_pairs.append(('engagement', reading['engagement']))
    if reading.get('status'):
        meta_pairs.append(('reading status', render_status_badge(reading['status']) if reading['status'] in ['reading','paused','completed','abandoned'] else reading['status']))
    if reading.get('started'):
        meta_pairs.append(('started', format_date(reading['started'])))
    if reading.get('finished'):
        meta_pairs.append(('finished', format_date(reading['finished'])))

    reading_meta_html = '<dl class="reading-meta">\n'
    for label, value in meta_pairs:
        reading_meta_html += f'  <dt>{label}</dt><dd>{value}</dd>\n'
    reading_meta_html += '</dl>'

    tags_html = render_tags(reading.get('topics'))

    return engine.render('reading.html', {
        'page_title': f'{reading.get("title", "Untitled")} — {SITE_TITLE}',
        'title': reading.get('title', 'Untitled'),
        'reading_meta': reading_meta_html,
        'tags': tags_html,
        'content': reading.get('content', ''),
    })

def build_research_page(research, engine, all_essays, all_reading):
    """Build a research thread page (formerly 'project' pages)."""
    slug = research.get('slug', '')

    related_essays = [e for e in all_essays if slug in (e.get('project') or [])]
    related_reading = [r for r in all_reading if slug in (r.get('project') or [])]

    essays_list = ''
    if related_essays:
        essays_list = '<h3>Essays</h3>\n<ul class="content-list">\n'
        for e in sort_by_modified(related_essays):
            essays_list += f'''<li class="content-list__item">
  <span class="content-list__title"><a href="{BASE_PATH}/essays/{e["slug"]}/">{e.get("title","Untitled")}</a></span>
  <span class="content-list__meta">{render_status_badge(e.get("status"))} {short_date(e.get("modified") or e.get("created"))}</span>
</li>\n'''
        essays_list += '</ul>\n'

    reading_list = ''
    if related_reading:
        reading_list = '<h3>Reading</h3>\n<ul class="content-list">\n'
        for r in sort_by_modified(related_reading):
            author = f' — {r["author"]}' if r.get('author') else ''
            reading_list += f'''<li class="content-list__item">
  <span class="content-list__title"><a href="{BASE_PATH}/reading/{r["slug"]}/">{r.get("title","Untitled")}</a>{author}</span>
  <span class="content-list__meta">{r.get("engagement","")} · {r.get("status","")}</span>
</li>\n'''
        reading_list += '</ul>\n'

    return engine.render('research.html', {
        'page_title': f'{research.get("title", "Untitled")} — {SITE_TITLE}',
        'title': research.get('title', 'Untitled'),
        'status': render_status_badge(research.get('status', '')),
        'description': research.get('description', ''),
        'content': research.get('content', ''),
        'related_essays': essays_list,
        'related_reading': reading_list,
        'modified': format_date(research.get('modified')) if research.get('modified') else '',
    })

def build_project_page(project, engine):
    """Build a portfolio project page (r2r, etc.)."""
    stack = project.get('stack', [])
    if isinstance(stack, str):
        stack = [stack]
    stack_html = ' '.join(f'<span class="tag">{s}</span>' for s in stack) if stack else ''

    live_url = project.get('url', '')
    live_link = f'<a href="{live_url}" class="project-live-link" target="_blank" rel="noopener">View project →</a>' if live_url else ''

    repo_url = project.get('repo', '')
    repo_link = f'<a href="{repo_url}" class="project-repo-link" target="_blank" rel="noopener">Source code →</a>' if repo_url else ''

    status = project.get('status', '')
    status_html = f'<span class="badge badge--{status}">{status}</span>' if status else ''

    return engine.render('builds.html', {
        'page_title': f'{project.get("title", "Untitled")} — {SITE_TITLE}',
        'title': project.get('title', 'Untitled'),
        'description': project.get('description', ''),
        'stack': stack_html,
        'live_link': live_link,
        'repo_link': repo_link,
        'status': status_html,
        'content': project.get('content', ''),
        'created': format_date(project.get('created')) if project.get('created') else '',
        'modified': format_date(project.get('modified')) if project.get('modified') else '',
    })

def build_about_page(engine):
    return engine.render('about.html', {
        'page_title': f'About — {SITE_TITLE}',
    })

def build_services_page(engine, projects):
    """Build the services/freelance surface page."""
    # List live projects as proof of work
    live_projects = [p for p in projects if p.get('status') == 'live']
    proof_html = ''
    for p in live_projects:
        url = p.get('url', '')
        link = f'<a href="{url}" target="_blank" rel="noopener">{p.get("title","")}</a>' if url else p.get('title','')
        proof_html += f'<div class="proof-item"><div class="proof-item__title">{link}</div><div class="proof-item__desc">{p.get("description","")}</div></div>\n'

    return engine.render('services.html', {
        'page_title': f'Services — {SITE_TITLE}',
        'proof_of_work': proof_html,
    })

def build_homepage(engine, essays, reading, research, projects, oddities):
    # Active research threads
    active_research = [r for r in research if r.get('status') == 'active']
    research_html = ''
    for r in active_research:
        research_html += f'''<div class="project-card">
  <div class="project-card__title"><a href="{BASE_PATH}/research/{r["slug"]}/">{r.get("title","Untitled")}</a></div>
  <div class="project-card__status">{render_status_badge(r.get("status"))}</div>
  <div class="project-card__description">{r.get("description","")}</div>
</div>\n'''

    # Recent essays
    recent_essays = sort_by_modified(essays)[:8]
    essays_html = '<ul class="content-list">\n'
    for e in recent_essays:
        essays_html += f'''<li class="content-list__item">
  <span class="content-list__title"><a href="{BASE_PATH}/essays/{e["slug"]}/">{e.get("title","Untitled")}</a></span>
  <span class="content-list__meta">{render_status_badge(e.get("status"))} {render_confidence_badge(e.get("confidence"))} {short_date(e.get("modified") or e.get("created"))}</span>
</li>\n'''
    essays_html += '</ul>'

    # Currently reading
    current_reading = [r for r in reading if r.get('status') in ['reading', 'in progress']]
    reading_html = '<ul class="content-list">\n'
    for r in current_reading[:5]:
        author = f' — {r["author"]}' if r.get('author') else ''
        project_names = ', '.join(r.get('project', [])) if r.get('project') else ''
        reading_html += f'''<li class="content-list__item">
  <span class="content-list__title"><a href="{BASE_PATH}/reading/{r["slug"]}/">{r.get("title","Untitled")}</a>{author}</span>
  <span class="content-list__meta">{r.get("engagement","")} {f"· {project_names}" if project_names else ""}</span>
</li>\n'''
    reading_html += '</ul>'

    # Oddities preview
    oddities_html = ''
    for o in oddities[:3]:
        source = f'<div class="oddity-entry__source">{o.get("source","")}</div>' if o.get('source') else ''
        oddities_html += f'''<div class="oddity-entry">
  {o.get("content","")}
  {source}
</div>\n'''

    # Featured projects (portfolio)
    featured_projects = projects[:2]
    projects_html = ''
    for p in featured_projects:
        url = p.get('url', '')
        link_title = f'<a href="{url}" target="_blank" rel="noopener">{p.get("title","")}</a>' if url else f'<a href="{BASE_PATH}/projects/{p["slug"]}/">{p.get("title","")}</a>'
        projects_html += f'''<div class="project-card">
  <div class="project-card__title">{link_title}</div>
  <div class="project-card__description">{p.get("description","")}</div>
</div>\n'''

    return engine.render('index.html', {
        'page_title': SITE_TITLE,
        'research': research_html,
        'recent_essays': essays_html,
        'current_reading': reading_html,
        'oddities': oddities_html,
        'projects': projects_html,
    })

def build_section_index(section_name, items, engine, url_prefix):
    section_titles = {
        'essays': 'Essays',
        'reading': 'Reading Log',
        'research': 'Research',
        'projects': 'Projects',
        'oddities': 'Oddities & Rarities',
    }

    section_descriptions = {
        'essays': 'Long-form writing at various stages — notes, drafts, and settled arguments.',
        'reading': 'A log of texts being worked through, with notes on key passages and connections.',
        'research': 'Ongoing research threads — each one a container for related essays and reading.',
        'projects': 'Things I have built.',
        'oddities': '',
    }

    items_html = '<ul class="content-list">\n'
    for item in sort_by_modified(items):
        author = f' — {item["author"]}' if item.get('author') else ''
        meta_parts = []
        if item.get('status') and item['status'] in ['seed','growing','settled','dormant','active','paused','completed','live','in-progress','archived']:
            meta_parts.append(render_status_badge(item['status']))
        if item.get('confidence'):
            meta_parts.append(render_confidence_badge(item['confidence']))
        if item.get('engagement'):
            meta_parts.append(item['engagement'])
        date = short_date(item.get('modified') or item.get('created'))
        if date:
            meta_parts.append(date)

        desc = ''
        if item.get('abstract'):
            desc = f'<div class="content-list__description">{item["abstract"]}</div>'
        elif item.get('description'):
            desc = f'<div class="content-list__description">{item["description"]}</div>'

        items_html += f'''<li class="content-list__item">
  <span class="content-list__title"><a href="{BASE_PATH}/{url_prefix}/{item["slug"]}/">{item.get("title","Untitled")}</a>{author}</span>
  <span class="content-list__meta">{" ".join(meta_parts)}</span>
  {desc}
</li>\n'''
    items_html += '</ul>'

    return engine.render('section.html', {
        'page_title': f'{section_titles.get(section_name, section_name)} — {SITE_TITLE}',
        'section_title': section_titles.get(section_name, section_name),
        'section_description': section_descriptions.get(section_name, ''),
        'items': items_html,
    })


# --- Main Build ---

def build():
    print(f"Building {SITE_TITLE} (BASE_PATH='{BASE_PATH}')...")

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, OUTPUT_DIR / "static")
    print("  Copied static files.")

    engine = TemplateEngine(TEMPLATE_DIR)

    essays   = process_content_dir('essays')
    reading  = process_content_dir('reading')
    research = process_content_dir('research')
    projects = process_content_dir('projects')   # portfolio builds
    oddities = process_content_dir('oddities')

    print(f"  Found: {len(essays)} essays, {len(reading)} reading logs, "
          f"{len(research)} research threads, {len(projects)} projects, {len(oddities)} oddities")

    # Individual essay pages
    for essay in essays:
        html = build_essay_page(essay, engine)
        write_file(OUTPUT_DIR / "essays" / essay['slug'] / "index.html", html)

    # Individual reading log pages
    for r in reading:
        html = build_reading_page(r, engine)
        write_file(OUTPUT_DIR / "reading" / r['slug'] / "index.html", html)

    # Individual research thread pages
    for r in research:
        html = build_research_page(r, engine, essays, reading)
        write_file(OUTPUT_DIR / "research" / r['slug'] / "index.html", html)

    # Individual portfolio project pages
    for p in projects:
        html = build_project_page(p, engine)
        write_file(OUTPUT_DIR / "projects" / p['slug'] / "index.html", html)

    # Oddities — single scrolling page
    oddities_entries_html = ''
    for o in sort_by_modified(oddities):
        title_html = f'<h2 class="oddity-scroll__title">{o.get("title", "")}</h2>'
        meta_parts = []
        if o.get('created'):
            meta_parts.append(format_date(o['created']))
        if o.get('source'):
            meta_parts.append(o['source'])
        meta_html = f'<div class="oddity-scroll__meta">{" · ".join(meta_parts)}</div>' if meta_parts else ''
        tags_html = render_tags(o.get('topics'))
        tags_block = f'<div class="oddity-scroll__tags">{tags_html}</div>' if tags_html else ''

        oddities_entries_html += f'''<div class="oddity-scroll__entry">
  {title_html}
  {meta_html}
  <div class="oddity-scroll__content">{o.get("content", "")}</div>
  {tags_block}
</div>\n'''

    write_file(OUTPUT_DIR / "oddities" / "index.html", engine.render('oddities.html', {
        'page_title': f'Oddities & Rarities — {SITE_TITLE}',
        'entries': oddities_entries_html,
    }))

    # Section index pages
    for section, items, prefix in [
        ('essays',   essays,   'essays'),
        ('reading',  reading,  'reading'),
        ('research', research, 'research'),
        ('projects', projects, 'projects'),
    ]:
        html = build_section_index(section, items, engine, prefix)
        write_file(OUTPUT_DIR / prefix / "index.html", html)

    # About page
    write_file(OUTPUT_DIR / "about" / "index.html", build_about_page(engine))

    # Services page
    write_file(OUTPUT_DIR / "services" / "index.html", build_services_page(engine, projects))

    # Homepage
    write_file(OUTPUT_DIR / "index.html",
               build_homepage(engine, essays, reading, research, projects, oddities))

    # Changelog
    write_file(OUTPUT_DIR / "changelog" / "index.html", engine.render('changelog.html', {
        'page_title': f'Changelog — {SITE_TITLE}',
    }))

    total = (len(essays) + len(reading) + len(research) + len(projects)
             + len(oddities) + 7)  # +7 for index pages + about + services + changelog
    print(f"  Site built successfully → {OUTPUT_DIR}/")
    print(f"  Total pages: {total}")
    print(f"  Preview: cd output && python3 -m http.server 8000")
    print(f"  Local dev build: KAZIM_BASE_PATH='' python3 build.py")


if __name__ == '__main__':
    build()
