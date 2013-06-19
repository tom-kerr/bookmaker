import os
from environment import Environment
from component import Component

class Optics(Component):
    """
    Optics
    ------

    Clustering algorithm

    """

    args = []
    executable = ''

    
    def __init__(self, book):
        super(Optics, self).__init__(Optics.args)
        self.book = book

    """
    def run_optics(self, leaf, log='clusterAnalysis'):
        leafnum = "%04d" % leaf
        in_file = (self.book.dirs['corner'] + '/' +
                   self.book.identifier + '_corners_' +
                   leafnum + '.txt')
        cluster_file = (self.book.dirs['cluster'] + '/' +
                        self.book.identifier + '_cluster_' +
                        leafnum + '.txt')
        out_file = (self.book.dirs['cluster'] + '/' +
                    self.book.identifier + '_out_' +
                    leafnum + '.txt')
        center_file = (self.book.dirs['cluster'] + '/' +
                       self.book.identifier + '_center_' +
                       leafnum + '.txt')
        unique_file = (self.book.dirs['cluster'] + '/' +
                       self.book.identifier + '_unique_' +
                       leafnum + '.txt')

        eps = self.eps
        minpts = self.minpts
        args = {'input_file': in_file,
                'output_file': out_file,
                'cluster_file': cluster_file,
                'center_file': center_file,
                'unique_file': unique_file,
                'eps': eps,
                'minpts': minpts}
        try:
            self.ImageOps.execute(leaf, 'optics', args, self.book.logger, log)
        except Exception as e:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_featuredetection',
                                                 str(e), self.book.logger))
            self.ProcessHandler.ThreadQueue.join()
        self.parse_optics_data(leaf, in_file, cluster_file,
                               out_file, center_file, unique_file)


    def parse_optics_data(self, leaf, in_file, cluster_file,
                          out_file, center_file, unique_file):
        leafnum = "%04d" % leaf
        try:
            fcluster = open(cluster_file, 'r')
        except:
            return
        fcluster_lines = fcluster.readlines()

        clusters = {}
        clusters['segments'] = {}
        clusters['corners'] = {}
        clusters['clusters'] = {}
        for num, line in enumerate(fcluster_lines):
            if num == 0:
                continue
            entry = re.split(' +', line)
            id = entry[1]
            parent = entry[2]
            start = int(float(entry[3]))
            end = int(float(entry[4]))
            size = entry[5]
            if parent not in clusters['segments']:
                clusters['segments'][parent] = []
            clusters['segments'][parent].append( (start, end) )

        fcorners = open(in_file, 'r')
        fcorners_lines = fcorners.readlines()
        for parent, segments in clusters['segments'].items():
            if parent not in clusters['corners']:
                clusters['corners'][parent] = []
            for segment in segments:
                clusters['corners'][parent].append( tuple(fcorners_lines[segment[0]:segment[1]]) )

        for parent, lcorners in clusters['corners'].items():
            if parent not in clusters['clusters']:
                clusters['clusters'][parent] = []
            for corners in lcorners:
                box = Box()
                for corner in corners:
                    x, y = corner.rstrip('\n').split(' ')
                    x = int(float(x))
                    y = int(float(y))
                    if x < box.l or box.l is None:
                        box.set_dimension('l', x)
                    if x > box.r or box.r is None:
                        box.set_dimension('r', x)
                    if y < box.t or box.t is None:
                        box.set_dimension('t', y)
                    if y > box.b or box.b is None:
                        box.set_dimension('b', y)
                clusters['clusters'][parent].append(box)

        canvas = self.book.dirs['thumb'] + '/' + self.book.identifier + '_thumb_' + leafnum + '.jpg'
        img = Image.open(canvas)
        draw = ImageDraw.Draw(img)
        for parent, clusters in clusters['clusters'].items():
            if parent != '-1':
                continue

            if int(float(parent))%2 == 0:
                color = 'green'
            else:
                color = 'red'
            for cluster in clusters:
                if cluster.is_valid():
                    draw.rectangle([cluster.l, cluster.t,
                                    cluster.r, cluster.b],
                                   outline=color)
        img.save(canvas)
        del draw

        """