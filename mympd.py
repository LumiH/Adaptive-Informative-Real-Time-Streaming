import xml.etree.ElementTree

ns = {'mpd' : 'urn:mpeg:dash:schema:mpd:2011'}

class MPDRepresentation:
    def __init__(self, representation_xml):
        # Extract representation details
        self._id = representation_xml.attrib['id']
        self._bandwidth = int(representation_xml.attrib['bandwidth'])
        self._width = int(representation_xml.attrib['width'])
        self._height = int(representation_xml.attrib['height'])

        # Extract base URL
        base_url = representation_xml.find('mpd:BaseURL', namespaces=ns)
        self._base_url = base_url.text

        # Extract timescale
        segment_list = representation_xml.find('mpd:SegmentList', namespaces=ns)
        self._segment_duration = int(segment_list.attrib['duration'])

        # Extract ranges
        segment_urls = segment_list.findall('mpd:SegmentURL', namespaces=ns)
        self._segment_ranges = []
        for segment in segment_urls:
            self._segment_ranges.append(tuple(
                    [int(x) for x in segment.attrib['mediaRange'].split('-')]))

    @property
    def id(self):
        return self._id

    @property
    def base_url(self):
        return self._base_url

    @property 
    def segment_ranges(self):
        return self._segment_ranges

    def segment_range(self, index):
        return self._segment_ranges[index]

    def __str__(self):
        return ('Representation:\n\t' + '\n\t'.join([
            'Id: %s' % self._id,
            'Width: %d' % self._width, 
            'Height: %d' % self._height,
            'Bandwidth: %d' % self._bandwidth,
            'BaseURL: %s' % self._base_url,
            'Segment duration: %d' % self._segment_duration,
            'Segment ranges: %s' % self._segment_ranges]))

class MPDFile:
    def __init__(self, xml_string):
        # Parse XML
        root = xml.etree.ElementTree.fromstring(xml_string)

        # Extract Initialization
        period = root.find('mpd:Period', namespaces=ns)
        adaptation_set = period.find('mpd:AdaptationSet', namespaces=ns)
        segment_list = adaptation_set.find('mpd:SegmentList', namespaces=ns)
        initialization = segment_list.find('mpd:Initialization', namespaces=ns)
        self._initialization_url = initialization.attrib['sourceURL']

        # Extract representations
        representations = adaptation_set.findall('mpd:Representation', 
                namespaces=ns)
        self._representations = []
        for representation in representations:
            self._representations.append(MPDRepresentation(representation))

    @property
    def initialization_url(self):
        return self._initialization_url

    @property
    def representations(self):
        return self._representations

    def __str__(self):
        return ('\n'.join(['MPD:', 
            'InitializationtURL: %s' % self._initialization_url,
            '\n'.join([str(r) for r in self._representations])]))


