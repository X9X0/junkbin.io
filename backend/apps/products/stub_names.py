"""
Machine names that come from parts listings ('Dell Inspirion 15-3567', 'Lenovo Flex 5-14ARE05. LC55-14A') carry
the listings' noise: typo'd family words, dropped family words, a repeated brand, an ODM's name, screen sizes,
trailing project codes. This module gives such a name one canonical form and finds the product the site already
has for it, so a stub machine is created once and the next spelling of the same machine links to the same page.

    r = Resolver()
    r.clean('Dell', 'Inspirion 15-3567')   -> Cleaned('Inspiron 15-3567', key='3567')
    r.find('Dell', 'Inspirion 15-3567')    -> the site's 'Dell 15-3567' (same brand and model key, compatible family)

Two names denote the same machine when the brand and the model key agree (model tokens with dashes, spaces and
junk removed) and their family words are compatible: equal, or one set contains the other, or one is empty
('Dell 15-3567' and 'Dell Inspiron 15-3567'). 'Vostro 5590' and 'Latitude 5590' share a number but not a family:
different machines. A screen size in front of the model ('15-3567', '15 3567') is ignored for the key, but two
names that carry different sizes are different machines ('Inspiron 13-5000' / 'Inspiron 15-5000'), and a name
with family words only meets a name without any ('HP 2000') when the sizes agree too ('Spectre XT 13-2000' is
not the HP 2000). A family word is corrected only to a word the site's own products use for that brand, so
'Inspirion' becomes 'Inspiron' while 'Legion', which the site may not have yet, is kept as written.
"""
import difflib
import re
from collections import Counter, defaultdict, namedtuple

from .models import Product

# words a listing adds around a machine name that are not part of it (form factors included: 'laptop', 'aio')
JUNK = {'inc', 'inc.', 'modelo', 'model', 'logo', 'only', 'fullpack', 'bezel', 'gaming', 'laptop', 'notebook', 'netbook',
        'desktop', 'tablet', 'new', 'washer', 'special', 'edition', 'home', 'emmc', 'cardpop', 'pc', 'computer', 'series',
        'no.', 'for', 'with', 'and', '&', 'oem', 'genuine', 'original', 'replacement', 'parts', 'motherboard', 'mainboard',
        'mb', 'board', 'system', 'the', 'a', '-', 'brand', 'ultrabook', 'all-in-one', 'aio', 'convertible', '2-in-1',
        'touch', 'touchscreen', 'non-touch', 'intel', 'amd', 'nvidia', 'ati', 'core', 'ryzen', 'celeron', 'pentium'}
# another maker's name inside a machine name: what follows it is that maker's board, not a machine model
ODM_WORDS = {'asus', 'msi', 'microstar', 'micro-star', 'wistron', 'quanta', 'compal', 'inventec', 'foxconn', 'pegatron', 'ecs',
             'gigabyte', 'asrock', 'wstron', 'clevo', 'tongfang', 'uniwill', 'mitac', 'arima'}
# family words brands use whether or not the site has products with them yet (never "corrected" to another word)
KNOWN_FAMILIES = {'thinkpad', 'ideapad', 'legion', 'yoga', 'thinkbook', 'thinkcentre', 'ideacentre', 'miix', 'loq', 'flex', 'xiaoxin',
                  'inspiron', 'latitude', 'vostro', 'precision', 'xps', 'alienware', 'optiplex', 'venue', 'wyse', 'studio',
                  'pavilion', 'envy', 'elitebook', 'probook', 'zbook', 'omen', 'spectre', 'compaq', 'presario', 'elitedesk',
                  'prodesk', 'stream', 'victus', 'folio', 'slatebook', 'omnibook', 'touchsmart', 'sleekbook', 'split',
                  'aspire', 'travelmate', 'extensa', 'nitro', 'predator', 'swift', 'spin', 'switch', 'iconia', 'veriton', 'helios',
                  'triton', 'conceptd', 'emachines', 'gateway', 'satellite', 'tecra', 'portege', 'qosmio', 'vaio', 'vivobook',
                  'zenbook', 'rog', 'tuf', 'transformer', 'eee', 'lifebook', 'amilo', 'esprimo', 'celsius', 'ativ', 'galaxy',
                  'iphone', 'ipad', 'imac', 'macbook', 'mac', 'air', 'pro', 'mini', 'max', 'plus', 'slim', 'carbon', 'tab', 'one',
                  'edge', 'essential', 'book', 'ultra', 'lite', 'se', 'xs', 'neo', 'prime', 'duo', 'nano', 'note', 'fe', 'surface',
                  'pixel', 'chromebook', 'erazer', 'akoya', 'magicbook', 'matebook'}
SUFFIX_WORDS = {'PLUS', 'PRO', 'MAX', 'MINI', 'AIR', 'ULTRA', 'LITE', 'SE', 'XL', 'DUO', 'SLIM', 'TOUCH', 'EDGE', 'NOTE', 'FE',
                'NEO', 'PRIME', 'ACTIVE'}
# tokens with a digit that are not a model: GPUs, chipsets, CPUs, memory, screen sizes, generations, ODM board codes
NOT_MODEL = re.compile(r'^(?:GT\d{3}M?X?|GTX\d{3,4}|MX\d{3}|RTX\d{4}|HM\d{2,3}|QM\d{2,3}|PM\d{2,3}|UM\d{2,3}|HD\d{4}|\d+GB|\d+TB|'
                       r'I[3579]|\d{1,2}(?:\.\d)?"?|GEN\s?\d|G\d{1,2}|[A-Z]{2}\d{2}[A-Z]?\d{2,3}[A-Z]{0,2}|N\d{2}[A-Z]-[A-Z]{2}|'
                       r'DA0?[0-9A-Z]{2,4}(?:MB|LB|DB)[0-9A-Z]{2,4}|L[AS]-?[A-Z0-9]{4,5}P?|N[MS]-?[A-Z]\d{3,4}|6050A\d{7}(?:-[A-Z0-9]+)*|'
                       r'BA41-\d{5}[A-Z]?|820-\d{4,5}(?:-[A-Z0-9]+)?|\d{5}-[A-Z0-9]{1,3})$', re.I)
# a family word that marks a different machine when only one of two names has it (ThinkPad L390 / L390 Yoga)
DISTINCT = {'yoga', 'carbon', 'nano', 'chromebook', 'flip', 'x360', 'duo', 'twist', 'helix', 'fold'}
PHONE_FAMILIES = {'iphone', 'ipad', 'galaxy', 'pixel', 'surface'}
MACHINE_CATEGORIES = {'desktop', 'laptop', 'tablet', 'phone'}
SIZE = re.compile(r'1[0-7](?:\.\d)?"?')                     # a laptop screen size in inches, as listings write it

Row = namedtuple('Row', 'pk family stub category model source strict size gen canonical')


class Cleaned:
    __slots__ = ('family', 'models', 'key', 'strict', 'size', 'gen', 'name')

    def __init__(self, family, models, tokens, size=None, gen=None):
        self.family = tuple(family)
        self.models = tuple(models)
        self.key, _, found = model_keys(models)
        self.size = found or size
        self.strict = (re.sub(r'\D', '', self.size) if self.size else '') + self.key   # '15 3567' and '15-3567' agree
        self.gen = gen                                   # 'G3': HP's generation, a different machine from the one without
        self.name = ' '.join(tokens)[:100]

    @property
    def family_set(self):
        return {w.lower() for w in self.family}

    def __repr__(self):
        return f'Cleaned({self.name!r}, key={self.key!r})'


def model_keys(models):
    """(key, strict key, screen size): '15-3567', '15 3567' and '3567' share the key '3567'; the strict key keeps the
    size ('153567'); size is the inches a name carries in front of its model ('15'), or None."""
    toks = [t.upper() for t in models]
    strict = re.sub(r'[^A-Z0-9]', '', ''.join(toks))
    size = None
    if len(toks) > 1:
        sizes = [t for t in toks if SIZE.fullmatch(t)]
        if sizes and len(sizes) < len(toks):
            size = sizes[0]
            toks = [t for t in toks if not SIZE.fullmatch(t)]                                  # '15 3567' -> '3567'
    out = []
    for t in toks:
        m = re.fullmatch(r'(1[0-7])-([A-Z0-9-]{3,})', t)
        if m and sum(c.isdigit() for c in m.group(2)) >= 2:
            size = size or m.group(1)
            t = m.group(2)                                                                        # '15-3567' -> '3567'
        out.append(t)
    size = re.sub(r'[^0-9.]', '', size) if size else None
    return re.sub(r'[^A-Z0-9]', '', ''.join(out)), strict, size


def families_compatible(a, b):
    """Family word sets that can name one machine: equal, nested, or one empty - unless the words one has and the
    other lacks mark a different machine ('ThinkPad L390' / 'ThinkPad L390 Yoga')."""
    if a == b or not a or not b:
        return True
    if a <= b or b <= a:
        return not ((a ^ b) & DISTINCT)
    return False


def junk(word):
    """A listing's filler word, or a near miss of one ('Gamming')."""
    return word in JUNK or (len(word) >= 5 and bool(difflib.get_close_matches(word, [j for j in JUNK if len(j) >= 5], n=1, cutoff=0.85)))


class Resolver:
    """Cleans names and finds the site's product for them; caches the brand's words and model keys for one run."""

    def __init__(self):
        self._vocab = {}
        self._index = {}

    # --- words -------------------------------------------------------------------------
    def vocab(self, brand):
        """Family words the brand's own (non-stub) products use, each with the casing they use most (an all-caps
        spelling only when no other is in use): {'inspiron': 'Inspiron'}."""
        b = brand.lower()
        if b not in self._vocab:
            seen = defaultdict(Counter)
            for model in Product.objects.filter(manufacturer__iexact=brand).exclude(
                    import_source__startswith='norway-machine').values_list('model_number', flat=True):
                for w in model.split():
                    if re.search(r'\d', w):
                        break
                    seen[w.lower()][w] += 1
            vocab = {}
            for w, c in seen.items():
                if sum(c.values()) < 2:
                    continue
                mixed = [(n, s) for s, n in c.items() if not s.isupper()]
                vocab[w] = max(mixed)[1] if mixed else c.most_common(1)[0][0]
            self._vocab[b] = vocab
        return self._vocab[b]

    def fix_word(self, brand, word):
        """A family word corrected to the brand's spelling when it is a near miss of one the brand's products use
        ('Inspirion' -> 'Inspiron'); a word the site knows, a known family, or one with no close match is kept."""
        w = word.lower()
        vocab = self.vocab(brand)
        if w in vocab:
            return vocab[w]
        if w in KNOWN_FAMILIES or len(w) < 4:
            return word
        close = difflib.get_close_matches(w, [v for v in vocab if len(v) >= 4], n=1, cutoff=0.8)
        return vocab[close[0]] if close else word

    def clean(self, brand, model):
        """The canonical form of a machine name's model part, or None when nothing a machine could be called is
        left (no model token, or the model tokens belong to another maker's board)."""
        family, models, tokens, size, gen = [], [], [], None, None
        brand_l = brand.lower()
        words = [t for w in model.replace(',', ' ').split() for t in w.split('/') if t]
        for w in words:
            w = w.strip('.;:()[]')
            if not w:
                continue
            lw = w.lower()
            if re.search(r'\d', w):
                if NOT_MODEL.match(w) and not (re.fullmatch(r'\d{1,2}(?:\.\d)?[A-Z]?', w, re.I)
                                               and any(f.lower() in PHONE_FAMILIES for f in family)):
                    if SIZE.fullmatch(w.upper()):
                        if models:
                            break                                                 # a screen size after the model ends it
                        size = re.sub(r'[^0-9.]', '', w)                          # 'Inspiron 15 3567': the 15 is inches
                    elif models and re.fullmatch(r'G\d{1,2}|GEN\s?\d', w, re.I):
                        gen = w.upper()                                           # 'HP 650 G1' is not the HP 650
                        tokens.append(w)
                    continue
                shape = re.sub(r'\d', '9', w.upper())
                if any(re.sub(r'\d', '9', m.upper()) == shape for m in models):
                    break                                                         # a sibling model: another machine
                if models and (re.fullmatch(r'[A-Z0-9]{4,5}', w) and sum(c.isalpha() for c in w) >= 2
                               or re.fullmatch(r'[A-Z]{2}\d{2}-\d{2}[A-Z]?', w, re.I)):
                    break                                                         # a project code after the model (LZ2B, LC55-14A)
                models.append(w)
                tokens.append(w)
            elif lw in ODM_WORDS:
                if not models:
                    return None                                                   # 'HP Asus M2NC51-AR': a board, not a machine
                break
            elif not models:
                if lw == brand_l or junk(lw):
                    continue
                w = self.fix_word(brand, w)
                family.append(w)
                tokens.append(w)
            elif w.upper() in SUFFIX_WORDS:
                w = w.capitalize() if len(w) > 2 else w.upper()
                models.append(w)                                                  # 'iPhone 7 Plus', 'Galaxy S7 Edge'
                tokens.append(w)
            elif lw in KNOWN_FAMILIES:
                w = self.fix_word(brand, w)
                family.append(w)                                                  # 'ThinkPad X1 Carbon', 'X380 Yoga'
                tokens.append(w)
            else:
                break
        if not models:
            return None
        if not family and len(re.sub(r'[^A-Za-z0-9]', '', ''.join(models))) < 3:
            return None
        return Cleaned(family, models, tokens, size, gen)

    # --- products ----------------------------------------------------------------------
    def row(self, pk, model, category, source, brand):
        c = self.clean(brand, model)
        if not c:
            return None
        return Row(pk, c.family_set, source.startswith('norway-machine'), category, model, source, c.strict, c.size,
                   c.gen, model == c.name)

    def index(self, brand):
        """The brand's products by model key: {key: [Row]}."""
        b = brand.lower()
        if b not in self._index:
            idx = defaultdict(list)
            for pk, model, cat, src in Product.objects.filter(manufacturer__iexact=brand).values_list(
                    'pk', 'model_number', 'category', 'import_source'):
                r = self.row(pk, model, cat, src, brand)
                if r:
                    idx[model_keys(self.clean(brand, model).models)[0]].append(r)
            self._index[b] = idx
        return self._index[b]

    def remember(self, product):
        """A product created or renamed during the run joins the index."""
        c = self.clean(product.manufacturer, product.model_number)
        if c:
            self.index(product.manufacturer)[c.key].append(
                self.row(product.pk, product.model_number, product.category, product.import_source, product.manufacturer))

    def forget(self, product):
        idx = self.index(product.manufacturer)
        for key in list(idx):
            idx[key] = [r for r in idx[key] if r.pk != product.pk]

    def candidates(self, brand, cleaned, exclude_pk=None, exclude_tag_prefix=None, category=None):
        fam = cleaned.family_set
        rows = []
        for r in self.index(brand).get(cleaned.key, []):
            if r.pk == exclude_pk or (exclude_tag_prefix and r.source.startswith(exclude_tag_prefix)):
                continue
            if not families_compatible(r.family, fam):
                continue
            if r.size and cleaned.size and r.size != cleaned.size:
                continue                                                          # Inspiron 13-5000 is not the 15-5000
            if bool(fam) != bool(r.family) and r.strict != cleaned.strict:
                continue                                                          # Spectre XT 13-2000 is not the HP 2000
            if r.gen != cleaned.gen:
                continue                                                          # HP 650 G1 is not the HP 650
            if re.fullmatch(r'\d+000', cleaned.key) and (r.family != fam or r.size != cleaned.size):
                continue                                                          # 'Inspiron 5000' is a series: only its own spelling
            if cleaned.key.isdigit() and (fam | r.family) & PHONE_FAMILIES and r.family != fam:
                continue                                                          # iPad 2 is not the iPad Air 2
            if category and r.category and category in MACHINE_CATEGORIES and r.category in MACHINE_CATEGORIES \
                    and r.category != category:
                continue
            rows.append(r)
        return rows

    def find(self, brand, model, exclude_pk=None, exclude_tag_prefix=None, category=None, stubs_only_if_wider=False,
             self_name=None):
        """The product this name denotes, or None. A real (non-stub) product wins over a stub; among several real
        ones the family words must match exactly, else the name is ambiguous and nothing is returned. A name
        without family words is left alone when the site has that number under families that exclude each other
        ('Dell 5510' with a Vostro 5510 and a Precision 5510). A stub is returned only when its family words
        contain the name's; with `stubs_only_if_wider` (deduplication) a stub of equal words is returned only when
        it is the better survivor: spelled canonically, then shorter, then the earlier id."""
        cleaned = model if isinstance(model, Cleaned) else self.clean(brand, model)
        if not cleaned:
            return None
        rows = self.candidates(brand, cleaned, exclude_pk, exclude_tag_prefix, category)
        fam = cleaned.family_set
        if not fam:                                     # 'Dell 5510' with a Vostro 5510 and a Precision 5510 on the site
            others = [r for r in self.index(brand).get(cleaned.key, []) if r.pk != exclude_pk]
            if any(not families_compatible(a.family, b.family) for a in others for b in others):
                return None
        real = [r for r in rows if not r.stub]
        if real:
            if len(real) > 1:
                exact = [r for r in real if r.family == fam]
                if len(exact) != 1:
                    return None
                real = exact
            return Product.objects.get(pk=real[0].pk)
        stubs = [r for r in rows if r.stub and fam <= r.family]
        if stubs_only_if_wider:
            me = (0, len(self_name or cleaned.name), str(exclude_pk)) if self_name == cleaned.name \
                else (1, len(self_name or cleaned.name), str(exclude_pk))
            stubs = [r for r in stubs if r.family > fam or (r.family == fam and (0 if r.canonical else 1, len(r.model), str(r.pk)) < me)]
        if not stubs:
            return None
        stubs.sort(key=lambda r: (-len(r.family), 0 if r.canonical else 1, len(r.model), str(r.pk)))
        return Product.objects.get(pk=stubs[0].pk)
