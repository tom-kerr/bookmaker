import os
import sys
import re
import math

from environment import Environment
from util import Util
from imageops import ImageOps
from datastructures import Crop, Box, Clusters


class FeatureDetection:

    exec_time = 0
    fms = False

    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book

        self.book.pageCropScaled = Crop('pageCrop', 0, self.book.page_count,
                                        self.book.raw_image_dimensions[0][1]/4,
                                        self.book.raw_image_dimensions[0][0]/4)

        self.book.contentCropScaled = Crop('contentCrop', 0, self.book.page_count,
                                           self.book.raw_image_dimensions[0][1]/4,
                                           self.book.raw_image_dimensions[0][0]/4)
        self.clusters = {}
        self.filtered_clusters = {}
        self.ImageOps = ImageOps()

                         
    def pipeline(self):
        self.book.logger.message('Entering FeatureDetection pipeline...','global')
        for leaf in range(0, self.book.page_count):
            self.book.logger.message('...leaf ' + str(leaf) + ' of ' + 
                                     str(self.book.page_count) + '...', 
                                     ('global','featureDetection'))
            rot_dir = -1 if leaf%2==0 else 1
            self.find_page(leaf, rot_dir)                        
            corner_data = self.get_corners(leaf)
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

        
    def find_page(self, leaf, rot_dir):
        self.book.logger.message('finding page...', 'featureDetection')
        leafnum = '%04d' % leaf
        if self.book.settings['respawn']:
            in_file = self.book.raw_images[leaf]
            out_file = (self.book.dirs['thumb'] + '/' + 
                        self.book.identifier + '_thumb_' + 
                        leafnum + '.jpg')
            output = self.page_detection(leaf, in_file, out_file, rot_dir)
            self.parse_page_detection_output(leaf, output)
        self.book.pageCropScaled.box[leaf] = self.book.pageCrop.scale_box(leaf, scale_factor = 4)


    def page_detection(self, leaf, in_file, out_file, rot_dir, 
                       debug_out = '/home/reklak/development/debug/debug.jpg', log = 'pageDetection'):
        if not os.path.exists(in_file):
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_page_detection',
                                                 str(in_file) +  'does not exist',
                                                 self.book.logger))
            self.ProcessHandler.ThreadQueue.join()
        cmd = 'pageDetection'
        args = {'in_file': in_file, 
                'out_file': out_file,
                'rotation_direction': rot_dir,
                'debug_out': debug_out}
        try:
            output = self.ImageOps.execute(leaf, cmd, args, self.book.logger, log, return_output = True)
        except Exception as e:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_featuredetection',
                                                 str(e), self.book.logger))
            self.ProcessHandler.ThreadQueue.join()
        else:
            return output


    def parse_page_detection_output(self, leaf, output):
        fields = {'PAGE_L:': {'regex': '([0-9]+)' },
                  'PAGE_T:': {'regex': '([0-9]+)' },
                  'PAGE_R:': {'regex': '([0-9]+)' },
                  'PAGE_B:': {'regex': '([0-9]+)' },
                  'SKEW_ANGLE:': {'regex': '([0-9\.\-]+)' },
                  'SKEW_CONF:': {'regex': '([0-9\.\-]+)' }  
                  }
        for field, attr in fields.iteritems():
            pattern = str(field) + str(attr['regex'])
            m = re.search(pattern, output)
            if m is not None:
                if field is 'PAGE_L:':
                    self.book.pageCrop.box[leaf].set_dimension('l', int(m.group(1)))
                if field is 'PAGE_T:':
                    self.book.pageCrop.box[leaf].set_dimension('t', int(m.group(1)))
                if field is 'PAGE_R:':
                    self.book.pageCrop.box[leaf].set_dimension('r', int(m.group(1)))
                if field is 'PAGE_B:':
                    self.book.pageCrop.box[leaf].set_dimension('b', int(m.group(1)))
                if field is 'SKEW_ANGLE:':
                    self.book.pageCrop.skew_angle[leaf] = float(m.group(1))
                    self.book.pageCrop.skew_active[leaf] = True
                    self.book.pageCropScaled.skew_angle[leaf] = float(m.group(1))
                    self.book.pageCropScaled.skew_active[leaf] = True
                    self.book.contentCrop.skew_angle[leaf] = float(m.group(1))
                    self.book.contentCrop.skew_active[leaf] = True
                    self.book.contentCropScaled.skew_angle[leaf] = float(m.group(1))
                    self.book.contentCropScaled.skew_active[leaf] = True
                if field is 'SKEW_CONF:':
                    self.book.pageCrop.skew_conf[leaf] = float(m.group(1))
                    self.book.pageCropScaled.skew_conf[leaf] = float(m.group(1))
                    self.book.contentCrop.skew_conf[leaf] = float(m.group(1))                    
                    self.book.contentCrop.skew_angle[leaf] = float(m.group(1))
                    self.book.contentCropScaled.skew_active[leaf] = True
            else:
                if field is 'PAGE_L:':
                    self.book.pageCrop.box[leaf].set_dimension('l', 0)
                if field is 'PAGE_T:':
                    self.book.pageCrop.box[leaf].set_dimension('t', 0)
                if field is 'PAGE_R:':
                    self.book.pageCrop.box[leaf].set_dimension('r', self.book.pageCrop.image_width-1)
                if field is 'PAGE_B:':
                    self.book.pageCrop.box[leaf].set_dimension('b', self.book.pageCrop.image_height-1)
                if field is 'SKEW_ANGLE:':
                    self.book.pageCrop.skew_angle[leaf] = 0.0
                    self.book.pageCrop.skew_active[leaf] = False
                    self.book.pageCropScaled.skew_angle[leaf] = 0.0
                    self.book.pageCropScaled.skew_active[leaf] = False
                    self.book.contentCrop.skew_angle[leaf] = 0.0
                    self.book.contentCrop.skew_active[leaf] = False
                    self.book.contentCropScaled.skew_angle[leaf] = 0.0
                    self.book.contentCropScaled.skew_active[leaf] = False
                if field is 'SKEW_CONF:':
                    self.book.pageCrop.skew_conf[leaf] = 0.0
                    self.book.pageCropScaled.skew_conf[leaf] = 0.0
                    self.book.contentCrop.skew_conf[leaf] = 0.0
                    self.book.contentCropScaled.skew_conf[leaf] = 0.0


    def get_corners(self, leaf):
        self.book.logger.message('getting corners...', 'featureDetection')
        leafnum = '%04d' % leaf
        in_file = (self.book.dirs['thumb'] + '/' + 
                   self.book.identifier + '_thumb_' + 
                   leafnum + '.jpg')
        out_file = (self.book.dirs['corner'] + '/' +
                    self.book.identifier + '_corners_' +
                    leafnum + '.txt')

        if self.book.settings['respawn']:
            self.fast_corner_detection(leaf, in_file, out_file)
            
            if self.book.settings['make_cornered_thumbs']:
                out_file = (self.book.dirs['corner_thumb'] + '/' +
                            self.book.identifier + '_thumb_' +
                            leafnum + '.jpg')
                self.fast_corner_detection(leaf, in_file, out_file, l='')

        in_file = (self.book.dirs['corner'] + '/' +
                   self.book.identifier + '_corners_' +
                   leafnum + '.txt')
        out_file = (self.book.dirs['window'] + '/' + 
                    self.book.identifier + '_window_' + 
                    leafnum + '.txt')
            
        if self.book.settings['respawn']:                
            self.book.pageCrop.skew(self.book.thumb_rotation_point['x'],
                                        self.book.thumb_rotation_point['y'],
                                        leaf)
            self.book.pageCropScaled.box[leaf] = self.book.pageCrop.scale_box(leaf, scale_factor = 4)
            self.filter_corners(leaf, in_file, out_file, self.book.pageCropScaled.box[leaf] )
        return FeatureDetection.parse_corner_data(out_file)            


    def fast_corner_detection(self, leaf, in_file, out_file,
                              t=44, s='', n=9, l = '-l', 
                              log = 'fastCornerDetection'):        
        if not os.path.exists(in_file):
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_featuredetection',
                                            str(in_file) + ' does not exist',
                                            self.book.logger))
            self.ProcessHandler.ThreadQueue.join()
        if FeatureDetection.fms:
            s = '-s'
        cmd = 'fastCornerDetection'
        args = {'in_file': in_file,
                'out_file': out_file,
                't':t, 's':s, 'n':n, 'l':l }
        try:
            self.ImageOps.execute(leaf, cmd, args, self.book.logger, log, return_output=False)
        except Exception as e:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_featuredetection',
                                                 str(e), self.book.logger))
            self.ProcessHandler.ThreadQueue.join()


    def filter_corners(self, leaf, in_file, out_file, 
                       crop, log='fastCornerDetection'):
        if not os.path.exists(in_file):
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_featuredetection',
                                            str(in_file) + ' does not exist',
                                            self.book.logger))
            self.ProcessHandler.ThreadQueue.join()
        if not crop.is_valid():
            return
        crop.resize(-10)
        cmd = 'cornerFilter'
        args = {'in_file': in_file, 
                'out_file': out_file,
                'l':crop.l,
                't':crop.t,
                'r':crop.r,
                'b':crop.b,
                'thumb_width':self.book.raw_image_dimensions[0][1]/4,
                'thumb_height':self.book.raw_image_dimensions[0][0]/4 }
        try:
            self.ImageOps.execute(leaf, cmd, args, self.book.logger, log, return_output = False)
        except Exception as e:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_featuredetection',
                                                 str(e), self.book.logger))
            self.ProcessHandler.ThreadQueue.join()
        crop.resize(10)


    @staticmethod
    def parse_corner_data(window_file):
        if os.path.exists(window_file):
            D = open(window_file, "r")
            contents = D.readline()
            contents = contents.split(" ")
            if len(contents) is not 5:
                return False
            window_width = contents[0]
            window_height = contents[1]
            corner_count = contents[2]
            x_variance = contents[3]
            y_variance = contents[4]
            return {'window_width': window_width,
                    'window_height': window_height,
                    'corner_count': corner_count,
                    'x_variance': x_variance,
                    'y_variance': x_variance }
        else:
            return False


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
            self.ImageOps.execute(leaf, cmd, args, self.book.logger, log, return_output = False)
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
