# Cube Class
# Spaxel Class

import sys
import numpy as np
import math
import logging
from .. import datamodels
from . import coord

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)



class CubeInfo(object):
# Array of classes, CubeType[i]  defines type of Cube being created and the list
# of files are are used in making the cube.

    def __init__(self, instrument,detector, parameter1, parameter2, output_name):

        self.channel = list()
        self.subchannel = list()

        self.file = list()
        self.a_wave = list()
        self.c_wave = list()

        self.ra_ref = list()
        self.dec_ref = list()
        self.roll_ref = list()
        self.v2_ref = list()
        self.v3_ref = list()
        self.a_weight = list()
        self.c_weight = list()
        self.transform = list()

        self.filter = list()
        self.grating = list()

        self.output_name = ''
        self.detector = detector
        self.instrument = instrument
        self.output_name = output_name
        if(instrument == 'MIRI'):
            self.channel = parameter1
            self.subchannel = parameter2
            
        elif(instrument == 'NIRSPEC'):
            self.filter = parameter1
            self.grating = parameter2

            self.output_name = output_name

#_______________________________________________________________________
    def SetScale(self, a_scale, b_scale, wscale):
        self.Cdelt1 = a_scale
        self.Cdelt2 = b_scale
        self.Cdelt3 = wscale
#_______________________________________________________________________
# cube in alpha-beta space (single exposure cube - small FOV assume rectangular coord system
    def SetGeometryAB(self, footprint):
        self.a_min, self.a_max, self.b_min, self.b_max, self.lambda_min, self.lambda_max = footprint

        #set up the a (x) coordinates of the cube
        range_a = self.a_max - self.a_min
        self.naxis1 = int(math.ceil(range_a / self.Cdelt1))

        # adjust min and max based on integer value of naxis1
        a_center = (self.a_max + self.a_min) / 2.0
        self.a_min = a_center - (self.naxis1 / 2.0) * self.Cdelt1
        self.a_max = a_center + (self.naxis1 / 2.0) * self.Cdelt1

        self.xcoord = np.zeros(self.naxis1)
        self.Crval1 = self.a_min
        self.Crpix1 = 0.5
        xstart = self.a_min + self.Cdelt1 / 2.0
        for i in range(self.naxis1):
            self.xcoord[i] = xstart
            xstart = xstart + self.Cdelt1

#_______________________________________________________________________
        #set up the lambda (z) coordinate of the cube

        range_lambda = self.lambda_max - self.lambda_min
        self.naxis3 = int(math.ceil(range_lambda / self.Cdelt3))

         # adjust max based on integer value of naxis3
        lambda_center = (self.lambda_max + self.lambda_min) / 2.0

        self.lambda_min = lambda_center - (self.naxis3 / 2.0) * self.Cdelt3
        self.lambda_max = lambda_center + (self.naxis3 / 2.0) * self.Cdelt3

        self.lambda_max = self.lambda_min + (self.naxis3) * self.Cdelt3

        self.zcoord = np.zeros(self.naxis3)
        self.Crval3 = self.lambda_min
        self.Crpix3 = 0.5
        zstart = self.lambda_min + self.Cdelt3 / 2.0

        for i in range(self.naxis3):
            self.zcoord[i] = zstart
            zstart = zstart + self.Cdelt3
#_______________________________________________________________________

        range_b = self.b_max - self.b_min

        self.naxis2 = int(math.ceil(range_b / self.Cdelt2))
        b_center = (self.b_max + self.b_min) / 2.0

        # adjust min and max based on integer value of naxis2
        self.b_max = b_center + (self.naxis2 / 2.0) * self.Cdelt2
        self.b_min = b_center - (self.naxis2 / 2.0) * self.Cdelt2


        self.ycoord = np.zeros(self.naxis2)
        self.Crval2 = self.b_min
        self.Crpix2 = 0.5
        ystart = self.b_min + self.Cdelt2 / 2.0
        for i in range(self.naxis2):
            self.ycoord[i] = ystart
            ystart = ystart + self.Cdelt2


#        ycube,xcube = np.mgrid[:self.naxis2,:self.naxis1]
#        print(ycube)
#        print(xcube)
#        sys.exit('STOP')
#_______________________________________________________________________
# Footprint values are RA,DEC values on the sky
# Values are given in degrees 

    def SetGeometry(self, footprint):
        padfactor = 1.1 # a padding on the size of cube to make sure the spatial dimensions are large eniugh
        deg2rad = math.pi/180.0
        
        ra_min, ra_max, dec_min, dec_max,lambda_min, lambda_max = footprint # in degrees

        print('in SetGeometry',ra_min,ra_max,dec_min,dec_max)
        dec_ave = (dec_min + dec_max)/2.0
        ra_ave = ((ra_min + ra_max)/2.0 )* math.cos(dec_ave*deg2rad) # actually this is hard due to converenge of hour angle
        # improve determining ra_ave in the future

        range_ra = (ra_max - ra_min) * 3600.0 #* math.cos(dec_ave*deg2rad)

        self.naxis1 = int(math.ceil(range_ra / self.Cdelt1)) 
        print('ra range',range_ra,self.naxis1)

        range_dec = (dec_max - dec_min) * 3600.0
        self.naxis2 = int(math.ceil(range_dec / self.Cdelt2)) 
        print('dec range', range_dec,self.naxis2)

        self.Crval1 = ra_ave 
        self.Crval2 = dec_ave
        xi,eta = coord.radec2std(self.Crval1, self.Crval2,ra_ave,dec_ave)
        print('xi eta',xi,eta)

        
        xi_min,eta_min = coord.radec2std(self.Crval1, self.Crval2,ra_min,dec_min)
        xi_max,eta_max = coord.radec2std(self.Crval1, self.Crval2,ra_max,dec_max)
        
        xi_min = xi_min - self.Cdelt1/2.0
        xi_max = xi_max + self.Cdelt1/2.0

        eta_min = eta_min - self.Cdelt2/2.0
        eta_max = eta_max + self.Cdelt2/2.0

        print('xi eta min ',xi_min,eta_min)
        print('xi eta max ',xi_max,eta_max)

        
        n1a = int(math.ceil(math.fabs(xi_min) / self.Cdelt1)) 
        n1b = int(math.ceil(math.fabs(xi_max) / self.Cdelt1)) 

        n2a = int(math.ceil(math.fabs(eta_min) / self.Cdelt2)) 
        n2b = int(math.ceil(math.fabs(eta_max) / self.Cdelt2)) 

        self.naxis1 = n1a + n1b
        self.naxis2 = n2a + n2b 
#        range_xi = (xi_max - xi_min)
#        range_eta = (eta_max - eta_min)
#        self.naxis1 = int(math.ceil(range_xi / self.Cdelt1)) 
#        self.naxis2 = int(math.ceil(range_eta / self.Cdelt2)) 

        self.a_min  = xi_min
        self.a_max = xi_max
        self.b_min = eta_min
        self.b_max = eta_max


        self.xcoord = np.zeros(self.naxis1)

        self.Crpix1 = n1a
        xstart = self.a_min + self.Cdelt1 / 2.0
        for i in range(self.naxis1):
            self.xcoord[i] = xstart
            xstart = xstart + self.Cdelt1

        self.ycoord = np.zeros(self.naxis2)

        self.Crpix2 = n2a
        ystart = self.b_min + self.Cdelt2 / 2.0
        for i in range(self.naxis2):
            self.ycoord[i] = ystart
            ystart = ystart + self.Cdelt2
#_______________________________________________________________________
        #set up the lambda (z) coordinate of the cube

        self.lambda_min = lambda_min
        self.lambda_max = lambda_max

        range_lambda = self.lambda_max - self.lambda_min
        self.naxis3 = int(math.ceil(range_lambda / self.Cdelt3))

         # adjust max based on integer value of naxis3
        lambda_center = (self.lambda_max + self.lambda_min) / 2.0

        self.lambda_min = lambda_center - (self.naxis3 / 2.0) * self.Cdelt3
        self.lambda_max = lambda_center + (self.naxis3 / 2.0) * self.Cdelt3

        self.lambda_max = self.lambda_min + (self.naxis3) * self.Cdelt3

        self.zcoord = np.zeros(self.naxis3)
        self.Crval3 = self.lambda_min
        self.Crpix3 = 0.5
        zstart = self.lambda_min + self.Cdelt3 / 2.0

        for i in range(self.naxis3):
            self.zcoord[i] = zstart
            zstart = zstart + self.Cdelt3
#_______________________________________________________________________

#        ycube,xcube = np.mgrid[:self.naxis2,:self.naxis1]
#        print(ycube)
#        print(xcube)
#        sys.exit('STOP')
#_______________________________________________________________________


    def PrintCubeGeometry(self, instrument):
        log.info('Cube Geometry')
        blank = '  '
        log.info('axis# Naxis  CRPIX    CRVAL        CDELT           MIN           MAX')
        log.info('Axis 1 %5d  %5.2f %12.8f %12.8f %12.8f %12.8f', self.naxis1, self.Crpix1, self.Crval1, self.Cdelt1, self.a_min, self.a_max)
        log.info('Axis 2 %5d  %5.2f %12.8f %12.8f %12.8f %12.8f', self.naxis2, self.Crpix2, self.Crval2, self.Cdelt2, self.b_min, self.b_max)
        log.info('Axis 3 %5d  %5.2f %12.8f %12.8f %12.8f %12.8f', self.naxis3, self.Crpix3, self.Crval3, self.Cdelt3, self.lambda_min, self.lambda_max)

        if(instrument == 'MIRI'):
            number_channels = len(self.channel)
            number_subchannels = len(self.subchannel)
            for i in range(number_channels):
                this_channel = self.channel[i]
                log.info('Cube covers channel: %s', this_channel)
            for j in range(number_subchannels):
                this_subchannel = self.subchannel[j]
                log.info('Cube covers subchannel: %s', this_subchannel)
        elif(instrument == 'NIRSPEC'):
            number_fwa = len(self.filter)
            number_gwa = len(self.grating)
            for i in range(number_fwa):
                this_fwa = self.filter[i]
                log.info('Cube covers filter: %s', this_fwa)
            for j in range(number_gwa):
                this_gwa = self.grating[j]
                log.info('Cube covers grating: %s', this_gwa)
#_______________________________________________________________________



##################################################################################
class Spaxel(object):

    __slots__ = ['xcenter', 'ycenter', 'zcenter', 'v2center','v3center',
                 'flux', 'error', 'pixel_flux', 'pixel_error', 'pixel_overlap',
                 'pixel_beta', 'ipointcloud', 'pointcloud_weight']

    def __init__(self, xcenter, ycenter, zcenter):
        self.xcenter = xcenter    # set in cube_build_step, default xi
        self.ycenter = ycenter    # set in cube_build_step, default eta
        self.zcenter = zcenter    # set in cube build step, defailt lambda
        self.v2center  = 0
        self.v3center = 0
        self.flux = 0
        self.error = 0

        self.ipointcloud = list()         # appended to in CubeCloud.MakePointCloud
        self.pointcloud_weight = list()   # appended to in CubeCloud.MakePointCloud

        self.pixel_flux = list()
        self.pixel_error = list()
        self.pixel_overlap = list()
        self.pixel_beta = list()



##################################################################################
class FileTable(object):
        # FileMap right now it is designed with MIRI in mind
        # For the 4 channels and 3 subchannels it holds the name of the
        # input file that covers 'channel','subchannel' region
    def __init__(self):

        self.FileMap = {}
        self.FileMap['MIRI'] = {}

        self.FileMap['MIRI']['1'] = {}
        self.FileMap['MIRI']['1']['SHORT'] = list()
        self.FileMap['MIRI']['1']['MEDIUM'] = list()
        self.FileMap['MIRI']['1']['LONG'] = list()

        self.FileMap['MIRI']['2'] = {}
        self.FileMap['MIRI']['2']['SHORT'] = list()
        self.FileMap['MIRI']['2']['MEDIUM'] = list()
        self.FileMap['MIRI']['2']['LONG'] = list()

        self.FileMap['MIRI']['3'] = {}
        self.FileMap['MIRI']['3']['SHORT'] = list()
        self.FileMap['MIRI']['3']['MEDIUM'] = list()
        self.FileMap['MIRI']['3']['LONG'] = list()

        self.FileMap['MIRI']['4'] = {}
        self.FileMap['MIRI']['4']['SHORT'] = list()
        self.FileMap['MIRI']['4']['MEDIUM'] = list()
        self.FileMap['MIRI']['4']['LONG'] = list()

        self.FileMap['NIRSPEC'] = {}
        self.FileMap['NIRSPEC']['CLEAR'] = {}
        self.FileMap['NIRSPEC']['CLEAR']['PRISM'] = list()

        self.FileMap['NIRSPEC']['F070LP'] = {}
        self.FileMap['NIRSPEC']['F070LP']['G140M'] = list()
        self.FileMap['NIRSPEC']['F070LP']['G140H'] = list()

        self.FileMap['NIRSPEC']['F100LP'] = {}
        self.FileMap['NIRSPEC']['F100LP']['G140M'] = list()
        self.FileMap['NIRSPEC']['F100LP']['G140H'] = list()

        self.FileMap['NIRSPEC']['F170LP'] = {}
        self.FileMap['NIRSPEC']['F170LP']['G235M'] = list()
        self.FileMap['NIRSPEC']['F170LP']['G235H'] = list()

        self.FileMap['NIRSPEC']['F290LP'] = {}
        self.FileMap['NIRSPEC']['F290LP']['G395M'] = list()
        self.FileMap['NIRSPEC']['F290LP']['G395H'] = list()

        self.FileOffset = {}
        self.FileOffset['1'] = {}
        self.FileOffset['1']['SHORT'] = {}
        self.FileOffset['1']['SHORT']['C1'] = list()
        self.FileOffset['1']['SHORT']['C2'] = list()
        self.FileOffset['1']['MEDIUM'] = {}
        self.FileOffset['1']['MEDIUM']['C1'] = list()
        self.FileOffset['1']['MEDIUM']['C2'] = list()
        self.FileOffset['1']['LONG'] = {}
        self.FileOffset['1']['LONG']['C1'] = list()
        self.FileOffset['1']['LONG']['C2'] = list()

        self.FileOffset['2'] = {}
        self.FileOffset['2']['SHORT'] = {}
        self.FileOffset['2']['SHORT']['C1'] = list()
        self.FileOffset['2']['SHORT']['C2'] = list()

        self.FileOffset['2']['MEDIUM'] = {}
        self.FileOffset['2']['MEDIUM']['C1'] = list()
        self.FileOffset['2']['MEDIUM']['C2'] = list()

        self.FileOffset['2']['LONG'] = {}
        self.FileOffset['2']['LONG']['C1'] = list()
        self.FileOffset['2']['LONG']['C2'] = list()


        self.FileOffset['3'] = {}
        self.FileOffset['3']['SHORT'] = {}
        self.FileOffset['3']['SHORT']['C1'] = list()
        self.FileOffset['3']['SHORT']['C2'] = list()

        self.FileOffset['3']['MEDIUM'] = {}
        self.FileOffset['3']['MEDIUM']['C1'] = list()
        self.FileOffset['3']['MEDIUM']['C2'] = list()

        self.FileOffset['3']['LONG'] = {}
        self.FileOffset['3']['LONG']['C1'] = list()
        self.FileOffset['3']['LONG']['C2'] = list()


        self.FileOffset['4'] = {}
        self.FileOffset['4']['SHORT'] = {}
        self.FileOffset['4']['SHORT']['C1'] = list()
        self.FileOffset['4']['SHORT']['C2'] = list()

        self.FileOffset['4']['MEDIUM'] = {}
        self.FileOffset['4']['MEDIUM']['C1'] = list()
        self.FileOffset['4']['MEDIUM']['C2'] = list()

        self.FileOffset['4']['LONG'] = {}
        self.FileOffset['4']['LONG']['C1'] = list()
        self.FileOffset['4']['LONG']['C2'] = list()

        self.FileOffset['CLEAR'] = {}
        self.FileOffset['CLEAR']['PRISM'] = {}
        self.FileOffset['CLEAR']['PRISM']['C1'] = list()
        self.FileOffset['CLEAR']['PRISM']['C2'] = list()

        self.FileOffset['F070LP'] = {}
        self.FileOffset['F070LP']['G140M'] = {}
        self.FileOffset['F070LP']['G140M']['C1'] = list()
        self.FileOffset['F070LP']['G140M']['C2'] = list()

        self.FileOffset['F070LP']['G140H'] = {}
        self.FileOffset['F070LP']['G140H']['C1'] = list()
        self.FileOffset['F070LP']['G140H']['C2'] = list()

        self.FileOffset['F100LP'] = {}
        self.FileOffset['F100LP']['G140M'] = {}
        self.FileOffset['F100LP']['G140M']['C1'] = list()
        self.FileOffset['F100LP']['G140M']['C2'] = list()
        self.FileOffset['F100LP']['G140H'] = {}
        self.FileOffset['F100LP']['G140H']['C1'] = list()
        self.FileOffset['F100LP']['G140H']['C2'] = list()

        self.FileOffset['F170LP'] = {}
        self.FileOffset['F170LP']['G235M'] = {}
        self.FileOffset['F170LP']['G235M']['C1'] = list()
        self.FileOffset['F170LP']['G235M']['C2'] = list()
        self.FileOffset['F170LP']['G235H'] = {}
        self.FileOffset['F170LP']['G235H']['C1'] = list()
        self.FileOffset['F170LP']['G235H']['C2'] = list()

        self.FileOffset['F290LP'] = {}
        self.FileOffset['F290LP']['G395M'] = {}
        self.FileOffset['F290LP']['G395M']['C1'] = list()
        self.FileOffset['F290LP']['G395M']['C2'] = list()
        self.FileOffset['F290LP']['G395H'] = {}
        self.FileOffset['F290LP']['G395H']['C1'] = list()
        self.FileOffset['F290LP']['G395H']['C2'] = list()
