import base64
import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

class InlineContent(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.policies = []
        self.blocks = {'script': [], 'style': []}
        self.active = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'content-security-policy':
            self.policies.append(attrs['content'])
        if tag in self.blocks:
            assert 'src' not in attrs, 'Pages game scripts must remain inline'
            self.active = tag
            self.blocks[tag].append('')

    def handle_data(self, text):
        if self.active:
            self.blocks[self.active][-1] += text

    def handle_endtag(self, tag):
        if tag == self.active:
            self.active = None

def validate_csp(html, headers):
    html = html.replace('\r\n', '\n').replace('\r', '\n')
    page = InlineContent()
    page.feed(html)
    header_policies = re.findall(r'^\s*Content-Security-Policy:\s*(.+)$', headers, re.M)
    assert len(header_policies) == 1, 'Expected exactly one CSP response header'
    assert len(page.policies) == 1, 'Expected exactly one CSP meta tag'
    assert len(page.blocks['script']) == 4, 'Expected four inline game scripts'
    assert len(page.blocks['style']) == 1, 'Expected one inline style'
    policies = [page.policies[0], header_policies[0].strip()]
    for policy in policies:
        directives = dict(part.strip().split(None, 1) for part in policy.split(';') if part.strip())
        for tag, directive in [('script', 'script-src'), ('style', 'style-src')]:
            allowed = directives[directive].split()
            for index, content in enumerate(page.blocks[tag]):
                digest = base64.b64encode(hashlib.sha256(content.encode('utf-8')).digest()).decode()
                expected = "'sha256-" + digest + "'"
                assert expected in allowed, f'{directive} blocks inline {tag} {index + 1}: missing {expected}'
    return {'scripts_checked': 4, 'styles_checked': 1, 'policies_checked': 2}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    result = validate_csp((root / 'pages/index.html').read_text(encoding='utf-8'),
                          (root / 'pages/_headers').read_text(encoding='utf-8'))
    print('Final Pages HTML and header CSP hashes passed:', result)
