import os
import logging

from util import Util
from environment import Environment
from .component import Component
from datastructures import Clusters

class SWClustering(Component):
    """
    Sliding Window Clustering
    -------------------------

    Takes a set of points in ascending x/y order and outputs a list of
    clusters. The algorithm works by recursively sliding a 'window' across
    the set of points, gathering them into clusters. The window starts
    centered around the first point and ...


    in_file: the file containing the set of points. Each vertice is to be
             separated by a space and each point by a newline, ie, "X Y\n"

    out_file: the file where the cluster dimensions will be written. the
              dimensions will be of the format "L T R B\n", where L is the
              left edge, T the top, R the right, and B the bottom.

    window_width: the width of the window used in clustering.

    window_height: the height of the window used in clustering.

    skew_angle: the angle at which to rotate the points by before clustering.

    center_x: the x value of the point of rotation

    center_y: the y value of the point of rotation

    """

    args = ['in_file','out_file',
            'window_width','window_height',
            'skew_angle','center_x','center_y']

    executable = Environment.current_path + '/bin/clusterAnalysis/slidingWindow/./slidingWindow'

    def __init__(self, book):
        super(SWClustering, self).__init__()
        self.book = book
        dirs = {'clusters': self.book.root_dir + '/' + \
                    self.book.identifier + '_clusters',
                'windows':  self.book.root_dir + '/' + \
                    self.book.identifier + '_windows',
                'noise':    self.book.root_dir + '/' + \
                    self.book.identifier + '_noise',}
        self.book.add_dirs(dirs)
        self.book.clusters = {}
        self.filtered_clusters = {}
        
    def run(self, leaf, in_file=None, out_file=None, window_width=None, 
            window_height=None, skew_angle=None, center_x=None, center_y=None,
            callback=None, **kwargs):        
        if not self.book.corner_data[leaf]:
            self.book.contentCropScaled.classification[leaf] = 'Blank'
            return
        leafnum = '%04d' % leaf
        if not in_file:
            in_file = (self.book.dirs['corners'] + '/' +
                       self.book.identifier + '_corners_' +
                       leafnum + '.txt')        
        if not os.path.exists(in_file):
            raise OSError(in_file + ' does not exist.')

        if not out_file:
            out_file = (self.book.dirs['clusters'] + '/' +
                        self.book.identifier + '_clusters_' +
                        leafnum + '.txt')
        
        if not window_width:
            window_width = self.book.corner_data[leaf]['window_width']
        if not window_height:
            window_height = self.book.corner_data[leaf]['window_height']
        if not skew_angle:
            skew_angle = self.book.pageCropScaled.skew_angle[leaf]
        if not center_x:
            center_x = self.book.scaled_center_point[leaf]['x']
        if not center_y:
            center_y = self.book.scaled_center_point[leaf]['y']

        kwargs.update({'in_file': in_file,
                       'out_file': out_file,
                       'window_width': window_width,
                       'window_height': window_height,
                       'center_x': center_x,
                       'center_y': center_y,
                       'skew_angle': skew_angle})
        
        if self.book.settings['respawn']:
            output = self.execute(kwargs, return_output=True)
        else:
            output = None
        if callback:
            self.execute_callback(callback, leaf, output, **kwargs)
        else:
            return output

    def post_process(self, *args, **kwargs):
        leaf = args[0]
        out_file = kwargs['out_file']
        self.parse_cluster_data(leaf, out_file)
        self.filter_clusters(leaf)
        self.get_content_dimensions(leaf)
        
    @staticmethod
    def get_cluster_data(cluster_file):
        if not os.path.exists(cluster_file):
            return False
        data = Clusters(0)
        f = open(cluster_file, "r")
        contents = f.readlines()
        for num, line in enumerate(contents):
            components = line.split(" ")
            data.new_cluster()
            data.cluster[num].set_dimension('l', int(components[0]))
            data.cluster[num].set_dimension('t', int(components[1]))
            data.cluster[num].set_dimension('r', int(components[2]))
            data.cluster[num].set_dimension('b', int(components[3]))
            data.cluster[num].s =                int(components[4])
        return data

    def parse_cluster_data(self, leaf, cluster_file):
        self.book.clusters[leaf] = Clusters(leaf)
        contents = SWClustering.get_cluster_data(cluster_file)
        if not contents:
            self.book.contentCropScaled.classification[leaf] is 'Blank'
            return
        leafnum = '%04d' % leaf
        cluster_count = 0
        for num, tmp_cluster in contents.cluster.items():
            if (tmp_cluster.is_valid() and
                self.book.pageCropScaled.box[leaf].is_valid() and
                tmp_cluster.is_contained_by(self.book.pageCropScaled.box[leaf])):

                self.book.clusters[leaf].new_cluster()
                self.book.clusters[leaf].cluster[cluster_count].set_dimension('l', tmp_cluster.l)
                self.book.clusters[leaf].cluster[cluster_count].set_dimension('t', tmp_cluster.t)
                self.book.clusters[leaf].cluster[cluster_count].set_dimension('r', tmp_cluster.r)
                self.book.clusters[leaf].cluster[cluster_count].set_dimension('b', tmp_cluster.b)
                self.book.clusters[leaf].cluster[cluster_count].size =             tmp_cluster.s
                self.book.clusters[leaf].thumb = (self.book.dirs['cornered_scaled'] + '/' +
                                                  self.book.identifier + '_cornered_scaled_' +
                                                  str(leafnum) + '.jpg')

                if self.book.settings['draw_clusters'] and self.book.settings['respawn']:
                    try:
                        self.book.clusters[leaf].cluster[cluster_count].draw(self.book.clusters[leaf].thumb)
                    except Exception as e:
                        self.book.logger.debug(str(e))

                cluster_count += 1
            else:
                self.book.logger.debug('cluster ' + str(num) + ' dimensions are invalid on leaf ' +
                                  str(leaf) + '-- ignoring...')

                if self.book.settings['draw_invalid_clusters'] and self.book.settings['respawn']:
                    tmp_cluster.thumb = (self.book.dirs['cornered_scaled'] + '/' +
                                         self.book.identifier + '_cornered_scaled_' + str(leafnum) + '.jpg')
                    tmp_cluster.draw(tmp_cluster.thumb, outline="purple")

        if cluster_count == 0:
            #self.book.logger.message('No content detected on leaf ' + str(leaf) + ' -- marking page as blank', log)
            self.book.contentCropScaled.classification[leaf] = 'Blank'
        else:
            self.book.contentCropScaled.classification[leaf] = 'normal'


    def filter_clusters(self, leaf, noise_lim=25):
        self.filtered_clusters[leaf] = Clusters(leaf)
        cluster_count = len(self.book.clusters[leaf].cluster)
        for num, cluster in self.book.clusters[leaf].cluster.items():
            if cluster.size <= noise_lim:
                self.filtered_clusters[leaf].new_cluster(num)
                self.filtered_clusters[leaf].cluster[num].set_dimension('l', cluster.l)
                self.filtered_clusters[leaf].cluster[num].set_dimension('t', cluster.t)
                self.filtered_clusters[leaf].cluster[num].set_dimension('r', cluster.r)
                self.filtered_clusters[leaf].cluster[num].set_dimension('b', cluster.b)
                self.filtered_clusters[leaf].cluster[num].size = cluster.size
                self.filtered_clusters[leaf].thumb = self.book.clusters[leaf].thumb
                self.book.clusters[leaf].cluster[num] = None
                cluster_count -= 1

                if self.book.settings['draw_removed_clusters'] and self.book.settings['respawn']:
                    self.filtered_clusters[leaf].cluster[num].draw(self.book.clusters[leaf].thumb,
                                                                   outline="orange")
                    self.book.logger.debug('noise filter removed cluster ' +
                                           str(num) + ' ('+ str(cluster.size) +
                                           ' corners) on leaf ' + str(leaf))
                                          

        if cluster_count is 0:
            #self.book.logger.message('all clusters filtered on leaf ' + str(leaf) + ' -- marking page as blank', log)
            self.book.contentCropScaled.classification[leaf] = 'Blank'


    def get_content_dimensions(self, leaf):
        self.book.logger.debug('getting content dimensions for leaf ' + str(leaf))

        if self.book.contentCropScaled.classification[leaf] is not 'Blank':
            l = t = r = b = None

            for num, cluster in self.book.clusters[leaf].cluster.items():
                if hasattr(cluster, 'dimensions'):
                    if l is None or cluster.l < l:
                        l = cluster.l
                    if t is None or cluster.t < t:
                        t = cluster.t
                    if r is None or cluster.r > r:
                        r = cluster.r
                    if b is None or cluster.b > b:
                        b = cluster.b

            self.book.contentCropScaled.box[leaf].set_dimension('l', l)
            self.book.contentCropScaled.box[leaf].set_dimension('t', t)
            self.book.contentCropScaled.box[leaf].set_dimension('r', r)
            self.book.contentCropScaled.box[leaf].set_dimension('b', b)
            self.book.contentCropScaled.skew_angle[leaf] = self.book.pageCropScaled.skew_angle[leaf]
            self.book.contentCropScaled.box[leaf].thumb = self.book.clusters[leaf].thumb

            if self.book.settings['respawn']:
                self.book.contentCropScaled.skew(self.book.scaled_center_point[leaf]['x'],
                                                 self.book.scaled_center_point[leaf]['y'],
                                                 leaf,
                                                 mode='expand')

            self.book.contentCrop.box[leaf] = self.book.contentCropScaled.scale_box(leaf,
                                                                                    scale_factor=0.25)

            if self.book.settings['draw_content_dimensions']:
                try:
                    self.book.contentCropScaled.box[leaf].draw(self.book.clusters[leaf].thumb, outline='green')
                except Exception as e:
                    self.book.logger.debug(str(e))

    def analyse_noise(self, log='noiseAnalysis'):
        self.book.logger.debug('analysing noise...')
        if not self.get_reference_leafs():
            return

        if self.book.settings['draw_noise']:
            Box.new_image(self.book.dirs['noise'] + '/left_noise.jpg',
                          self.book.raw_image_dimensions[0]['height']/4,
                          self.book.raw_image_dimensions[0]['width']/4,
                          'black')
            Box.new_image(self.book.dirs['noise'] + '/right_noise.jpg',
                          self.book.raw_image_dimensions[0]['height']/4,
                          self.book.raw_image_dimensions[0]['width']/4,
                          'black')

        if not self.generate_noise_files():
            return

        in_file = self.book.dirs['noise'] + '/left_noise.txt'
        out_file = out_file = self.book.dirs['noise'] + '/left_noise_clusters.txt'
        thumb_file = self.book.dirs['noise'] + '/left_noise.jpg'
        self.cluster_noise_and_resurrect('left', in_file, out_file, thumb_file)

        in_file = self.book.dirs['noise'] + '/right_noise.txt'
        out_file = out_file = self.book.dirs['noise'] + '/right_noise_clusters.txt'
        thumb_file = self.book.dirs['noise'] + '/right_noise.jpg'
        self.cluster_noise_and_resurrect('right', in_file, out_file, thumb_file)


    def get_reference_leafs(self, log='noiseAnalysis'):
        self.left_reference_leaf = None
        self.right_reference_leaf = None
        self.book.pageCropScaled.get_box_metadata()
        for leaf, box in self.book.pageCropScaled.box.items():
            if ((box.w in self.book.pageCropScaled.meta['w']['stats_hist']['above_mean'] or
                 box.w in self.book.pageCropScaled.meta['w']['stats_hist']['below_mean']) and
                (box.h in self.book.pageCropScaled.meta['h']['stats_hist']['above_mean'] or
                 box.h in self.book.pageCropScaled.meta['h']['stats_hist']['below_mean'])):
                if leaf%2==0 and self.left_reference_leaf is None:
                    self.book.logger.debug('left reference leaf is ' + str(leaf))
                    self.left_reference_leaf = self.book.pageCropScaled.box[leaf]
                elif leaf%2==0 and self.right_reference_leaf is None:
                    self.book.logger.debug('right reference leaf is ' + str(leaf))
                    self.right_reference_leaf = self.book.pageCropScaled.box[leaf]
        if self.left_reference_leaf is None and self.right_reference_leaf is None:
            self.book.logger.debug('could not find suitable reference leafs...aborting noise analysis')
            return False
        return True


    def generate_noise_files(self, log='noiseAnalysis'):

        self.t_deltas = {}

        self.left_noise = {}
        left = {'l':[], 't':[]}

        self.right_noise = {}
        right = {'l':[], 't':[]}

        for leaf in range(1, self.book.page_count-1):
            if self.book.contentCropScaled.classification[leaf] is not 'Blank':
                self.left_noise[leaf] = {}
                self.right_noise[leaf] = {}
                for num, cluster in self.filtered_clusters[leaf].cluster.items():
                    if leaf%2==0:
                        self.left_noise[leaf][num] = cluster
                        left['l'].append(cluster.l)
                        left['t'].append(cluster.t)
                        self.t_deltas[leaf] = self.left_reference_leaf.t - self.book.pageCropScaled.box[leaf].t
                        if self.book.settings['draw_noise']:
                            try:
                                cluster.draw(self.book.dirs['noise'] + '/left_noise.jpg', outline='gray')
                            except Exception as e:
                                self.book.logger.debug(str(e))
                    else:
                        self.right_noise[leaf][num] = cluster
                        right['l'].append(cluster.l)
                        right['t'].append(cluster.t)
                        self.t_deltas[leaf] = self.right_reference_leaf.t - self.book.pageCropScaled.box[leaf].t
                        if self.book.settings['draw_noise']:
                            try:
                                cluster.draw(self.book.dirs['noise'] + '/right_noise.jpg', outline='gray')
                            except Exception as e:
                                self.book.logger.debug(str(e))

        left_corners = zip(left['t'], left['l'])
        left_corners = sorted(left_corners)
        left_noise_file = self.book.dirs['noise'] + '/left_noise.txt'

        right_corners = zip(right['t'], right['l'])
        right_corners = sorted(right_corners)
        right_noise_file = self.book.dirs['noise'] + '/right_noise.txt'

        if self.book.settings['respawn']:
            try:
                lnf = open(left_noise_file,"w")
                rnf = open(right_noise_file,"w")
                for corner in left_corners:
                    lnf.write(str(corner[1]) + ' ' + str(corner[0]) + "\n")
                for corner in right_corners:
                    rnf.write(str(corner[1]) + ' ' + str(corner[0]) + "\n")
            except (OSError, IOError) as e:
                self.book.logger.debug('failed to generate noise files... aborting\n'+str(e))
                return False
        return True


    def cluster_noise_and_resurrect(self, side,
                                    in_file, out_file, thumb_file,
                                    log='noiseAnalysis'):
        if not os.path.exists(in_file):
            return False
        kwargs = {}
        kwargs['in_file'] = in_file
        kwargs['out_file'] = out_file
        kwargs['window_width'] = 10
        kwargs['window_height'] = 10
        kwargs['skew_angle'] = 0.0

        kwargs['center_x'] = self.book.scaled_center_point[0]['x']
        kwargs['center_y'] = self.book.scaled_center_point[0]['y']

        if self.book.settings['respawn']:
            self.execute(kwargs)

        resurrect = {}
        contents = SWClustering.get_cluster_data(out_file)
        if contents:
            noise_clusters = Clusters(0)
            for num, noise_cluster in contents.cluster.items():
                if noise_cluster.is_valid:
                    noise_clusters.new_cluster
                    noise_clusters.cluster[num] = noise_cluster
                    if self.book.settings['draw_noise']:
                        noise_clusters.cluster[num].draw(thumb_file, outline='white')
            for leaf in range(1, self.book.page_count-1):
                if self.book.contentCropScaled.classification[leaf] is not 'Blank':
                    if side is 'left':
                        if leaf%2==0:
                            leaf_noise = self.left_noise[leaf]
                        else:
                            continue
                    elif side is 'right':
                        if leaf%2!=0:
                            leaf_noise = self.right_noise[leaf]
                        else:
                            continue
                    resurrect[leaf] = []
                    for n, noise in leaf_noise.items():
                        for num, noise_cluster in noise_clusters.cluster.items():
                            if noise.size > 10 and (noise.touches(noise_cluster) or
                                                    noise.is_contained_by(noise_cluster, padding=0)):
                                resurrect[leaf].append(n)
                                #self.book.logger.message('will resurrect cluster ' +str(n) + ' on leaf ' + str(leaf), log)

        for leaf, clusters in resurrect.items():
            if self.book.contentCropScaled.classification[leaf] is not 'Blank':
                if side is 'left' and leaf%2!=0:
                    continue
                elif side is 'right' and leaf%2==0:
                    continue
                for num in clusters:
                    #print str(leaf) + ' ' + str(num)
                    if self.filtered_clusters[leaf].cluster[num] is None:
                        continue
                    self.book.clusters[leaf].new_cluster(num)
                    self.book.clusters[leaf].cluster[num].set_dimension('l',
                                                                   self.filtered_clusters[leaf].cluster[num].l)
                    self.book.clusters[leaf].cluster[num].set_dimension('t',
                                                                   self.filtered_clusters[leaf].cluster[num].t)
                    self.book.clusters[leaf].cluster[num].set_dimension('r',
                                                                   self.filtered_clusters[leaf].cluster[num].r)
                    self.book.clusters[leaf].cluster[num].set_dimension('b',
                                                                   self.filtered_clusters[leaf].cluster[num].b)
                    self.book.clusters[leaf].cluster[num].size = self.filtered_clusters[leaf].cluster[num].size
                    self.filtered_clusters[leaf].cluster[num] = None
            self.get_content_dimensions(leaf)
            self.book.contentCrop.box[leaf] = self.book.contentCropScaled.scale_box(leaf,
                                                                                    scale_factor=0.25)
            #print (self.book.contentCrop.box[leaf])
