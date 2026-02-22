"""Manual mode: Table of Contents generation and scroll spy."""

import re


def generate_toc(html_body: str) -> str:
    """Extract headers from HTML and generate sidebar ToC for manual mode.

    Finds all h1, h2, h3 headers with id attributes and builds a nested
    sidebar navigation list.
    """
    header_pattern = r'<h([123])[^>]*id="([^"]+)"[^>]*>(.*?)</h[123]>'
    headers = re.findall(header_pattern, html_body, re.DOTALL)

    if not headers:
        return ""

    toc_items = []
    for level, id_attr, inner_html in headers:
        # Strip HTML tags to get plain text
        text = re.sub(r"<[^>]+>", "", inner_html).strip()
        if not text:
            continue

        css_class = f"toc-h{level}"
        toc_items.append(
            f'<li class="{css_class}"><a href="#{id_attr}">{text}</a></li>'
        )

    if not toc_items:
        return ""

    return f"""<nav class="sidebar">
        <ul class="sidebar-nav">
{chr(10).join("            " + item for item in toc_items)}
        </ul>
    </nav>"""


def scrollspy_script() -> str:
    """JavaScript for scroll spy and mobile sidebar toggle."""
    return """<script>
    // Scroll spy: highlight current section in sidebar
    function updateActiveLink() {
        const headers = document.querySelectorAll('h1[id], h2[id], h3[id]');
        const links = document.querySelectorAll('.sidebar-nav a');
        const sidebar = document.querySelector('.sidebar');
        const offset = 100;

        let current = '';
        headers.forEach(header => {
            const top = header.getBoundingClientRect().top;
            if (top < offset) {
                current = header.id;
            }
        });

        links.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === '#' + current) {
                link.classList.add('active');
                // Auto-scroll sidebar to keep active item in view
                if (sidebar) {
                    const linkRect = link.getBoundingClientRect();
                    const sidebarRect = sidebar.getBoundingClientRect();
                    const linkTop = linkRect.top - sidebarRect.top;
                    const linkBottom = linkRect.bottom - sidebarRect.top;
                    const visibleHeight = sidebar.clientHeight;
                    if (linkTop < 50 || linkBottom > visibleHeight - 50) {
                        link.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            }
        });
    }

    // Mobile sidebar toggle
    function toggleSidebar() {
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.querySelector('.sidebar-overlay');
        if (sidebar) {
            sidebar.classList.toggle('mobile-open');
            if (overlay) overlay.classList.toggle('active');
        }
    }

    window.addEventListener('scroll', updateActiveLink);
    document.addEventListener('DOMContentLoaded', updateActiveLink);
    </script>"""
