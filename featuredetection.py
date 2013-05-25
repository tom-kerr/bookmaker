import os
import sys
import re
import math
import Image, ImageDraw

from environment import Environment
from util import Util
#from imageops import ImageOps
from datastructures import Crop, Box, Clusters

class FeatureDetection:

    exec_time = 0
    fms = False

    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book

        self.book.pageCropScaled = Crop('pageCrop', 0, self.book.page_count,
                                        self.book.raw_image_dimensions[0]['height']/4,
                                        self.book.raw_image_dimensions[0]['width']/4)

        self.book.contentCropScaled = Crop('contentCrop', 0, self.book.page_count,
                                           self.book.raw_image_dimensions[0]['height']/4,
                                           self.book.raw_image_dimensions[0]['width']/4)
        self.clusters = {}
        self.filtered_clusters = {}
        #self.ImageOps = ImageOps()
        try:
            self.__import_components()
        except Exception as e:
            print str(e)
            raise e


    def __import_components(self):
        from components.pagedetector import PageDetector
        from components.fastcornerdetection import FastCornerDetection
        from components.swclustering import SWClustering

        self.PageDetector = PageDetector(self.book)
        self.FastCornerDetection = FastCornerDetection(self.book)
        #self.CornerFilter = CornerFilter()
        #self.SWClustering = SWClustering()
        self.components = [self.PageDetector,
                           self.FastCornerDetection]


    def pipeline(self):
        self.book.logger.message('Entering FeatureDetection pipeline...','global')
        for leaf in range(0, self.book.page_count):
            self.book.logger.message('...leaf ' + str(leaf) + ' of ' +
                                     str(self.book.page_count) + '...',
                                     ('global','featureDetection'))
            for component in self.components:
                try:
                    component.run(leaf)
                    #print self.book.pageCropScaled.box[leaf].dimensions
                except Exception as e:
                    print str(e)
                    self.ProcessHandler.ThreadQueue.put((self.book.identifier +
                                                         '_featuredetection',
                                                         str(e), self.book.logger))
                    self.ProcessHandler.ThreadQueue.join()


    """
    def pipeline(self):
        self.book.logger.message('Entering FeatureDetection pipeline...','global')
        for leaf in range(0, self.book.page_count):
            self.book.logger.message('...leaf ' + str(leaf) + ' of ' +
                                     str(self.book.page_count) + '...',
                                     ('global','featureDetection'))

            rot_dir = -1 if leaf%2==0 else 1
            self.find_page(leaf, rot_dir)
            corner_data = self.get_corners(leaf)

            #print 'leaf {}  eps {}  minpts {}'.format(leaf, self.eps, self.minpts)
            #self.run_optics(leaf)
            #self.eps += 5
            #self.minpts += 5


            self.get_clusters(leaf, corner_data)
            self.get_content_dimensions(leaf)
            self.book.contentCrop.box[leaf] = self.book.contentCropScaled.scale_box(leaf, scale_factor=0.25)
            leaf_exec_time = self.ImageOps.return_total_leaf_exec_time(leaf)
            #FeatureDetection.exec_time += leaf_exec_time
            self.book.logger.message('Finished FeatureDetection for leaf ' + str(leaf)+ ' in: ' + str(leaf_exec_time) + ' seconds\n')
            self.check_exec_times(leaf)
            self.ImageOps.complete(leaf, 'Finished FeatureDetection ' + str(leaf_exec_time))
        self.analyse_noise()
        self.find_page_number_candidates()
        #self.book.logger.message('total executable time: ' +
        #                         str(FeatureDetection.exec_time/60) +' minutes')
        if self.book.settings['respawn']:
            self.book.pageCrop.xml_io('export')
        self.book.contentCrop.xml_io('export')
        """

    def check_exec_times(self, leaf):
        self.book.logger.message(" current average exec times:\n "+
                                 "\n\t\t\t  pageDetection: " +str(self.ImageOps.exec_times['pageDetection']['avg_exec_time'])+
                                 "\n\t\t    fastCornerDetection: " +str(self.ImageOps.exec_times['fastCornerDetection']['avg_exec_time'])+
                                 "\n\t\t\t   cornerFilter: " +str(self.ImageOps.exec_times['cornerFilter']['avg_exec_time'])+
                                 "\n\t\t\t  slidingWindow: " +str(self.ImageOps.exec_times['slidingWindow']['avg_exec_time'])+
                                 "\n", 'featureDetection')
        #if leaf > self.book.page_count*0.05:
        #    if self.ImageOps.ops['slidingWindow']['avg_exec_time'] > 5:
        #        print "turned on suppression for " + self.book.identifier
        #        self.book.logger.message("turned on fast maximal suppression")
        #        FeatureDetection.fms = True;



    def get_clusters(self, leaf, corner_data):
        self.book.logger.message('getting clusters...', 'featureDetection')
        leafnum = '%04d' % leaf
        if not corner_data:
            self.book.contentCropScaled.classification[leaf] = 'Blank'
        else:
            in_file = (self.book.dirs['corner'] + '/' +
                       self.book.identifier + '_corners_' +
                       leafnum + '.txt')

            out_file = (self.book.dirs['cluster'] + '/' +
                        self.book.identifier + '_clusters_' +
                        leafnum + '.txt')

            skew_angle = self.book.pageCropScaled.skew_angle[leaf]

            if self.book.settings['respawn']:
                self.cluster_analysis('slidingWindow',
                                      leaf, in_file, out_file,
                                      corner_data, skew_angle,
                                      self.book.thumb_rotation_point['x'],
                                      self.book.thumb_rotation_point['y'])
            self.parse_cluster_data(leaf, out_file)
            self.filter_clusters(leaf)


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



    def cluster_analysis(self, cmd,
                         leaf, in_file, out_file, corner_data,
                         skew_angle, center_x, center_y,
                         log='clusterAnalysis'):
        if not os.path.exists(in_file):
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_featuredetection',
                                                 str(in_file) + ' does not exist',
                                                 self.book.logger))
            self.ProcessHandler.ThreadQueue.join()
        if cmd is 'slidingWindow':
            args = {'in_file': in_file,
                    'out_file': out_file,
                    'window_width': corner_data['window_width'],
                    'window_height': corner_data['window_height'],
                    'skew_angle': skew_angle,
                    'center_x': center_x,
                    'center_y': center_y}
        elif cmd is 'optics':
            pass
        try:
            self.ImageOps.execute(leaf, cmd, args, self.book.logger, log)
        except Exception as e:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_featuredetection',
                                                 str(e), self.book.logger))
            self.ProcessHandler.ThreadQueue.join()



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


    def parse_cluster_data(self, leaf, cluster_file, log='clusterAnalysis'):
        self.clusters[leaf] = Clusters(leaf)
        contents = FeatureDetection.get_cluster_data(cluster_file)
        if contents is False:
            self.book.contentCropScaled.classification[leaf] is 'Blank'
            return
        leafnum = '%04d' % leaf
        cluster_count = 0
        for num, tmp_cluster in contents.cluster.items():
            if (tmp_cluster.is_valid() and
                self.book.pageCropScaled.box[leaf].is_valid() and
                tmp_cluster.is_contained_by(self.book.pageCropScaled.box[leaf])):
                #self.book.logger.message('cluster ' + str(num) + ' dimensions are valid...', log)
                self.clusters[leaf].new_cluster()
                self.clusters[leaf].cluster[cluster_count].set_dimension('l', tmp_cluster.l)
                self.clusters[leaf].cluster[cluster_count].set_dimension('t', tmp_cluster.t)
                self.clusters[leaf].cluster[cluster_count].set_dimension('r', tmp_cluster.r)
                self.clusters[leaf].cluster[cluster_count].set_dimension('b', tmp_cluster.b)
                self.clusters[leaf].cluster[cluster_count].size =             tmp_cluster.s
                self.clusters[leaf].thumb = (self.book.dirs['corner_thumb'] + '/' +
                                             self.book.identifier + '_thumb_' + str(leafnum) + '.jpg')

                if self.book.settings['draw_clusters'] and self.book.settings['respawn']:
                    self.clusters[leaf].cluster[cluster_count].draw(self.clusters[leaf].thumb)

                cluster_count += 1
            else:
                self.book.logger.message('cluster ' + str(num) + ' dimensions are invalid on leaf ' +
                               str(leaf) + '-- ignoring...', log)

                if self.book.settings['draw_invalid_clusters'] and self.book.settings['respawn']:
                    tmp_cluster.thumb = (self.book.dirs['corner_thumb'] + '/' +
                                         self.book.identifier + '_thumb_' + str(leafnum) + '.jpg')
                    tmp_cluster.draw(tmp_cluster.thumb, outline="purple")

        if cluster_count == 0:
            self.book.logger.message('No content detected on leaf ' + str(leaf) + ' -- marking page as blank', log)
            self.book.contentCropScaled.classification[leaf] = 'Blank'
        else:
            self.book.contentCropScaled.classification[leaf] = 'normal'


    def filter_clusters(self, leaf, noise_lim=25, log='clusterAnalysis'):
        self.filtered_clusters[leaf] = Clusters(leaf)
        cluster_count = len(self.clusters[leaf].cluster)
        for num, cluster in self.clusters[leaf].cluster.items():
            if cluster.size <= noise_lim:
                self.filtered_clusters[leaf].new_cluster(num)
                self.filtered_clusters[leaf].cluster[num].set_dimension('l', cluster.l)
                self.filtered_clusters[leaf].cluster[num].set_dimension('t', cluster.t)
                self.filtered_clusters[leaf].cluster[num].set_dimension('r', cluster.r)
                self.filtered_clusters[leaf].cluster[num].set_dimension('b', cluster.b)
                self.filtered_clusters[leaf].cluster[num].size = cluster.size
                self.filtered_clusters[leaf].thumb = self.clusters[leaf].thumb
                self.clusters[leaf].cluster[num] = None
                cluster_count -= 1

                if self.book.settings['draw_removed_clusters'] and self.book.settings['respawn']:
                    self.filtered_clusters[leaf].cluster[num].draw(self.clusters[leaf].thumb,
                                                                   outline="orange")
                self.book.logger.message('noise filter removed cluster ' +
                               str(num) + ' ('+ str(cluster.size) +' corners) on leaf ' + str(leaf), log)

        if cluster_count is 0:
            self.book.logger.message('all clusters filtered on leaf ' + str(leaf) + ' -- marking page as blank', log)
            self.book.contentCropScaled.classification[leaf] = 'Blank'


    def get_content_dimensions(self, leaf):
        self.book.logger.message('getting content dimensions...', 'featureDetection')
        if self.book.contentCropScaled.classification[leaf] is not 'Blank':
            l = t = r = b = None
            for num, cluster in self.clusters[leaf].cluster.items():
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
            self.book.contentCropScaled.box[leaf].thumb = self.clusters[leaf].thumb

            if self.book.settings['respawn']:
                self.book.contentCropScaled.skew(self.book.thumb_rotation_point['x'],
                                                 self.book.thumb_rotation_point['y'],
                                                 leaf,
                                                 mode='expand')

            if self.book.settings['draw_content_dimensions']:
                self.book.contentCropScaled.box[leaf].draw(self.clusters[leaf].thumb, outline='green')


    def analyse_noise(self, log='noiseAnalysis'):
        self.book.logger.message('analysing noise...', 'featureDetection')
        if not self.get_reference_leafs():
            return

        if self.book.settings['draw_noise']:
            Box.new_image(self.book.dirs['noise'] + '/left_noise.jpg',
                                self.book.raw_image_dimensions[0][1]/4,
                                self.book.raw_image_dimensions[0][0]/4,
                                'black')
            Box.new_image(self.book.dirs['noise'] + '/right_noise.jpg',
                                self.book.raw_image_dimensions[0][1]/4,
                                self.book.raw_image_dimensions[0][0]/4,
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
        for leaf, box in self.book.pageCropScaled.box.iteritems():
            if ((box.w in self.book.pageCropScaled.meta['w']['stats_hist']['above_mean'] or
                 box.w in self.book.pageCropScaled.meta['w']['stats_hist']['below_mean']) and
                (box.h in self.book.pageCropScaled.meta['h']['stats_hist']['above_mean'] or
                 box.h in self.book.pageCropScaled.meta['h']['stats_hist']['below_mean'])):
                if leaf%2==0 and self.left_reference_leaf is None:
                    self.book.logger.message('left reference leaf is ' + str(leaf), log)
                    self.left_reference_leaf = self.book.pageCropScaled.box[leaf]
                elif leaf%2==0 and self.right_reference_leaf is None:
                    self.book.logger.message('right reference leaf is ' + str(leaf), log)
                    self.right_reference_leaf = self.book.pageCropScaled.box[leaf]
        if self.left_reference_leaf is None and self.right_reference_leaf is None:
            self.book.logger.message('could not find suitable reference leafs...aborting noise analysis', log)
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
                            cluster.draw(self.book.dirs['noise'] + '/left_noise.jpg', outline='gray')
                    else:
                        self.right_noise[leaf][num] = cluster
                        right['l'].append(cluster.l)
                        right['t'].append(cluster.t)
                        self.t_deltas[leaf] = self.right_reference_leaf.t - self.book.pageCropScaled.box[leaf].t
                        if self.book.settings['draw_noise']:
                            cluster.draw(self.book.dirs['noise'] + '/right_noise.jpg', outline='gray')

        left_corners = zip(left['t'], left['l'])
        left_corners.sort()
        left_noise_file = self.book.dirs['noise'] + '/left_noise.txt'

        right_corners = zip(right['t'], right['l'])
        right_corners.sort()
        right_noise_file = self.book.dirs['noise'] + '/right_noise.txt'

        if self.book.settings['respawn']:
            try:
                lnf = open(left_noise_file,"w")
                rnf = open(right_noise_file,"w")
                for corner in left_corners:
                    lnf.write(str(corner[1]) + ' ' + str(corner[0]) + "\n")
                for corner in right_corners:
                    rnf.write(str(corner[1]) + ' ' + str(corner[0]) + "\n")
            except IOError:
                self.book.logger.message('failed to generate noise files... aborting', log)
                return False
        return True


    def cluster_noise_and_resurrect(self, side,
                                    in_file, out_file, thumb_file,
                                    log='noiseAnalysis'):

        if not os.path.exists(in_file):
            return False

        if self.book.settings['respawn']:
            self.cluster_analysis('slidingWindow',
                                  'noise', in_file, out_file,
                                  {'window_width':10,'window_height':10}, 0.0,
                                  self.book.thumb_rotation_point['x'],
                                  self.book.thumb_rotation_point['y'])
        resurrect = {}
        contents = self.get_cluster_data(out_file)
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
                                self.book.logger.message('will resurrect cluster ' +str(n) + ' on leaf ' + str(leaf), log)

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
                    self.clusters[leaf].new_cluster(num)
                    self.clusters[leaf].cluster[num].set_dimension('l',
                                                                   self.filtered_clusters[leaf].cluster[num].l)
                    self.clusters[leaf].cluster[num].set_dimension('t',
                                                                   self.filtered_clusters[leaf].cluster[num].t)
                    self.clusters[leaf].cluster[num].set_dimension('r',
                                                                   self.filtered_clusters[leaf].cluster[num].r)
                    self.clusters[leaf].cluster[num].set_dimension('b',
                                                                   self.filtered_clusters[leaf].cluster[num].b)
                    self.clusters[leaf].cluster[num].size = self.filtered_clusters[leaf].cluster[num].size
                    self.filtered_clusters[leaf].cluster[num] = None
            self.get_content_dimensions(leaf)
            self.book.contentCrop.box[leaf] = self.book.contentCropScaled.scale_box(leaf,
                                                                                        scale_factor=0.25)


    def find_page_number_candidates(self):
        self.book.page_number_candidates = {}
        for leaf in range(1, self.book.page_count-1):
            self.book.page_number_candidates[leaf] = []
            if self.book.contentCropScaled.classification[leaf] is not 'Blank':
                top_container = Box()
                top_container.l = self.book.contentCropScaled.box[leaf].l
                top_container.t = self.book.contentCropScaled.box[leaf].t
                top_container.r = self.book.contentCropScaled.box[leaf].r
                top_container.b = self.book.contentCropScaled.box[leaf].t +(0.1*self.book.contentCropScaled.box[leaf].h)

                top_candidates = self.clusters[leaf].search(top_container,
                                                            size_limit=100)
                if top_candidates:
                    self.book.page_number_candidates[leaf].append(top_candidates)

                bottom_container = Box()
                bottom_container.l = self.book.contentCropScaled.box[leaf].l
                bottom_container.t = self.book.contentCropScaled.box[leaf].b - (0.1*self.book.contentCropScaled.box[leaf].h)
                bottom_container.r = self.book.contentCropScaled.box[leaf].r
                bottom_container.b = self.book.contentCropScaled.box[leaf].b

                bottom_candidates = self.clusters[leaf].search(bottom_container,
                                                               size_limit=100)
                if bottom_candidates:
                    self.book.page_number_candidates[leaf].append(bottom_candidates)

                if self.book.settings['respawn'] and self.book.settings['draw_page_number_candidates']:
                    for zone in self.book.page_number_candidates[leaf]:
                        for num, cluster in zone.items():
                            cluster.draw(self.clusters[leaf].thumb, outline='cyan')
