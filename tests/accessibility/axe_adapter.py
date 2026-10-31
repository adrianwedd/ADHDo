"""Keep the suite's dictionary result format while using axe's supported API."""
from axe_playwright_python.sync_playwright import Axe as _Axe


class Axe(_Axe):
    def analyze(self, page, options=None):
        options = dict(options or {})
        context = options.pop('context', None)
        tags = options.pop('tags', None)
        if tags:
            options['runOnly'] = {'type': 'tag', 'values': tags}
        return self.run(page, context=context, options=options).response
