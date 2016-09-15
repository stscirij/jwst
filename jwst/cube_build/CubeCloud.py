# Routines used in Spectral Cube Building
from __future__ import absolute_import, print_function

import sys
import numpy as np
import math
from .. import datamodels
from ..datamodels import dqflags
from . import CubeD2C
from . import cube
from . import coord
#________________________________________________________________________________

def MakePointCloudMIRI(self, input_model,
                       x, y, file_no, 
                       Cube,
                       v2v32radec,
                       c1_offset, c2_offset):
    """

    Short Summary
    -------------
    map x,y to Point cloud  in final coordinate system

    Parameters
    ----------
    x,y list of x and y values to map
    input_model: slope image
    file_no: the index on the files that are used to construct the Cube
    Cube: holds the basic information on the Cube (including wcs of Cube)
    v2v32radec: temporary (until information is contained in assign_wcs) 
                holds the information to do the transformation from v2-v3 to ra-dec
    c1_offset, c2_offset: dither offsets for each file (default = 0)
               provided by the user




    Returns
    -------
    coordinates of x,y in point cloud


    """
#________________________________________________________________________________
    det2ab_transform = input_model.meta.wcs.get_transform('detector','alpha_beta')
    alpha, beta, wave = det2ab_transform(x, y)

    detector2v23 = input_model.meta.wcs.get_transform('detector', 'V2_V3')

    v2, v3, lam = detector2v23(x, y)
    flux_all = input_model.data[y, x]
    error_all = input_model.err[y, x]
    dq_all = input_model.dq[y,x]
    #v2,v3,lam = input_model.meta.wcs(x,y)

#________________________________________________________________________________
# in the slice gaps the v2,v3 and lam are NaN values. Select the valid slice pixels
# based on if v2,v3,lam are finite 
    valid1 = np.isfinite(v2) 
    valid2 = np.isfinite(v3)
    valid3 = np.isfinite(lam)  

    valid = dq_all.copy() * 0 
    index  = np.where(np.logical_and(np.logical_and(valid1,valid2),valid3))
    valid[index] = 1

#________________________________________________________________________________
# using the DQFlags from the input_image find pixels that should be excluded 
# from the cube mapping    
    all_flags = (dqflags.pixel['DO_NOT_USE'] + dqflags.pixel['DROPOUT'] + 
                 dqflags.pixel['NON_SCIENCE'] +
                 dqflags.pixel['DEAD'] + dqflags.pixel['HOT'] + 
                 dqflags.pixel['RC'] + dqflags.pixel['NONLINEAR'])

    # find the location of all the values to reject in cube building    
    good_data = np.where((np.bitwise_and(dq_all, all_flags)==0) & (valid == 1))

    # good data holds the location of pixels we want to map to cube 
    flux = flux_all[good_data]
    error = error_all[good_data]
    alpha = alpha[good_data]
    beta = beta[good_data]
    xpix = x[good_data]
    ypix = y[good_data]

    if(self.coord_system == 'alpha-beta'):
        coord1 = alpha
        coord2 = beta

#    elif (self.coord_system == 'v2-v3'):
#        coord1 = v2[good_data] * 60.0
#        coord2 = v3[good_data] * 60.0
#        coord1 = coord1 - c1_offset 
#        coord2 = coord2 - c2_offset
    else:
        v2_use = v2[good_data] #arc mins
        v3_use = v3[good_data] #arc mins

        ra_ref,dec_ref,roll_ref,v2_ref,v3_ref = v2v32radec
        print('ref values',ra_ref,dec_ref,roll_ref,v2_ref,v3_ref)
        ra,dec = coord.V2V32RADEC(ra_ref,dec_ref,roll_ref,
                                  v2_ref, v3_ref,
                                  v2_use,v3_use) # return ra and dec in degrees
        ra = ra - c1_offset/3600.0
        dec = dec - c2_offset/3600.0
        xi,eta = coord.radec2std(Cube.Crval1, Cube.Crval2,ra,dec) # xi,eta in arc seconds
        coord1 = xi
        coord2 = eta

        ra_test,dec_test=coord.std2radec(Cube.Crval1,Cube.Crval2,xi,eta)
        print('testing', ra,dec,ra_test,dec_test)
        print('ref values',ra_ref,dec_ref,roll_ref,v2_ref,v3_ref)
        v2_test,v3_test = coord.RADEC2V2V3(ra_ref,dec_raf,roll_ref,
                                           v2_ref,v3_ref,
                                           ra_test,dec_test)
        print('testing', v2_use,v3_use,v2_test,v3_test)
        #sys.exit('STOP')


    wave = lam[good_data]
    ifile = np.zeros(flux.shape, dtype='int') + int(file_no)

    # get in form of 8 columns of data - shove the information in an array.

    print('xi results', coord1[0:10])
    print('eta results',coord2[0:10])
    print('wave',wave[0:10])
    # stuff the point cloud arrays for this configuration into cloud 
    # Point cloud will eventually contain all the cloud values

    cloud = np.asarray([coord1, coord2, wave, alpha, beta, flux, error, ifile, xpix, ypix])

    return cloud
#______________________________________________________________________
def MakePointCloudMIRI_DistortionFile(self, x, y, file_no, c1_offset, c2_offset, channel, subchannel, sliceno, start_sliceno, input_model):


    """
    Short Summary
    -------------
    map x,y to Point cloud
    x,y detector values for sliceno

    Parameters
    ----------
    x,y list of x and y values to map
    channel: channel number working with
    subchannel: subchannel working with
    sliceno
    input_model: slope image
    transform: wsc transform to go from x,y to point cloud

    Returns
    -------
    location of x,y in Point Cloud as well as mapping of spaxel to each overlapping PointCloud member


    """
#________________________________________________________________________________
# if using distortion polynomials

    nn = len(x)
    sliceno_use = sliceno - start_sliceno + 1
    coord1 = list()
    coord2 = list()
    wave = list()
    alpha = list()
    beta = list()
    ifile = list()
    flux = list()
    error = list()
    x_pixel = list()
    y_pixel = list()
#________________________________________________________________________________
# loop over pixels in slice
#________________________________________________________________________________

    for ipixel in range(0, nn - 1):
        valid_pixel = True
        if(y[ipixel] >= 1024):
            valid_pixel = False
            #print(' Error ypixel = ',y[ipixel])

        if(valid_pixel):
            alpha_pixel, beta_pixel, wave_pixel = CubeD2C.xy2abl(self, sliceno_use - 1, x[ipixel], y[ipixel])

            flux_pixel = input_model.data[y[ipixel], x[ipixel]]
            error_pixel = input_model.err[y[ipixel], x[ipixel]]
            xan, yan = CubeD2C.ab2xyan(self, alpha_pixel, beta_pixel)
            v2, v3 = CubeD2C.xyan2v23(self, xan, yan)

            coord1_pixel = v2 * 60.0
            coord2_pixel = v3 * 60.0

            coord1_pixel = coord1_pixel + c1_offset / 60.0
            coord2_pixel = coord2_pixel + c2_offset / 60.0

            coord1.append(coord1_pixel)
            coord2.append(coord2_pixel)
            alpha.append(alpha_pixel)
            beta.append(beta_pixel)
            flux.append(flux_pixel)
            error.append(error_pixel)
            ifile.append(file_no)

            x_pixel.append(x[ipixel])
            y_pixel.append(y[ipixel])
    # get in form of 8 columns of data - shove the information in an array.
    #print('size',len(coord1),len(coord2))

    cloud = np.asarray([coord1, coord2, wave, alpha, beta, flux, error, ifile, x_pixel, y_pixel])
    return cloud

#_______________________________________________________________________



def FindROI(self, Cube, spaxel, PointCloud):

    """
    Short Summary
    -------------
    using the point cloud loop over the Spaxel and find the point cloud members that
    fall withing the ROI of the spaxel center. 


    For MIRI the weighting of the Cloud points is based on the distance in the local
    MRS alpha-beta plane. Each cloud point as an associated alpha-beta coordinate
    The spaxel centers have xi,eta & V2,V3 so we need to know the channel and band information
    and transform the V2,V3 coordinates back to alpha-beta

    Parameters
    ----------
    Cube: holds basic Cube information
    spaxel: a class that holds information on each spaxel in the cube. 
    PointCloud: array of point cloud members

    Returns
    -------
    location of x,y in Point Cloud as well as mapping of spaxel to each overlapping PointCloud member


    """
#________________________________________________________________________________
    nxc = len(Cube.xcoord)
    nzc = len(Cube.zcoord)
    nyc = len(Cube.ycoord)

    nplane = Cube.naxis1 * Cube.naxis2
    lower_limit = 0.0001

    iprint = 0
    nn = len(PointCloud[0])
    
    print('number of elements in PT',nn)
# loop over each point cloud member - might want to change this to looping
# over spaxels but for now just keep it point cloud elements because it
# is easy to find ROI members because the cube spaxel values are regularily spaced

    for ipt in range(0, nn - 1):

        ifile = int(PointCloud[7, ipt])
        a = Cube.a_wave[ifile]
        c = Cube.c_wave[ifile]
        wa = Cube.a_weight[ifile]
        wc = Cube.c_weight[ifile]
        wave = PointCloud[2,ipt]
        weights = FindNormalizationWeights(wave, a, c, wa, wc)

        weight_alpha = weights[0]
        weight_beta = weights[1]
        weight_wave = weights[2]

        ra_ref = Cube.ra_ref[ifile]
        dec_ref = Cube.dec_ref[ifile]
        roll_ref = Cube.roll_ref[ifile]
        v2_ref = Cube.v2_ref[ifile]
        v3_ref = Cube.v3_ref[ifile]

        coord1 = PointCloud[0, ipt]  # default coords xi
        coord2 = PointCloud[1, ipt]  # default coords eta
        alpha = PointCloud[3, ipt]
        beta = PointCloud[4, ipt]
        x = PointCloud[8, ipt]
        y = PointCloud[9, ipt]

        if(self.coord_system == 'alpha-beta'):
            coord1 = alpha
            coord2 = beta

        
        # Coord1 and Coord2 are in the coordinate system of the cube.
        # using the Cube regularily spaced arrays - Cube.zcoord, xcoord,ycoord
        # find the spaxels that fall withing ROI of point cloud

        # find values within the ROI
        indexz = np.asarray(np.where(abs(Cube.zcoord - wave) <= self.roiw))
        indexx = np.asarray(np.where(abs(Cube.xcoord - coord1) <= self.roi1))
        indexy = np.asarray(np.where(abs(Cube.ycoord - coord2) <= self.roi2))


        # transform Cube Spaxel to alpha,beta system of Point Cloud
        # for MIRI weighting parameters are based on distance in alpha-beta coord system
        # transform the cube coordinate values to alpha and beta values 
        # xi,eta -> ra,dec
        # ra-dec -> v2,v3 
        # v2,v3 -> local alph,beta


        zloc = Cube.zcoord[indexz[0]]
        xloc = Cube.xcoord[indexx[0]]  # default coordinates are xi
        yloc = Cube.ycoord[indexy[0]]  # default coordinates are eta

        ra_spaxel,dec_spaxel=coord.std2radec(Cube.Crval1,Cube.Crval2,
                                             Cube.xcoord[x],Cube.ycoord[x])
        v2_spaxel,v3_spaxel = coord.RADEC2V2V3(ra_ref,dec_ref,roll_ref,
                                                v2_ref,v3_ref,
                                                ra_spaxel, dec_spaxel)
        
        v2ab_transform = Cube.transform[ifile]


        alpha_spaxel,beta_spaxel,wave_spaxel = v2ab_transform(v2_spaxel/0.0,v3_spaxel/60.0,zloc[iz])
        alpha_distance = abs(alpha-alpha_spaxel)
        beta_distance = abs(beta-beta_spaxel)
        wave_distance  = abs(wave-wave_spaxel)

        xn = alpha_distance/weight_alpha
        yn = beta_distance/weight_beta
        wn = wave_distance/weight_wave
        weight_distance = xn*xn + yn*yn + wn*wn


        distance1 = abs(xloc - coord1)
        distance2 = abs(yloc - coord2)

        if(self.coord_system == 'alpha-beta'):
            distance1 = abs(xloc - alpha)
            distance2 = abs(yloc - beta)

        # Determine the distances in alpha-beta system
        distance3 = abs(zloc - wave)
        distance12 = distance1 * distance1
        distance22 = distance2 * distance2
        distance32 = distance3 * distance3
        
        iz = 0
        for zz in indexz[0]:
            istart = zz * nplane
            iy = 0
            for yy in indexy[0]:
                ix = 0
                for xx in indexx[0]:

                    # in Cube_Build_step we saved the coordinate of the spaxel centers also in V2,V3
                    
#                    if(self.coord_system=='v2-v3'):



                    weight_distance = distance12[ix] + distance22[iy] + distance32[iz]

                    if(weight_distance < lower_limit): weight_distance = lower_limit
                    weight_distance = 1.0 / weight_distance


                    cube_index = istart + yy * Cube.naxis1 + xx
                    spaxel[cube_index].ipointcloud.append(ipt)
                    spaxel[cube_index].pointcloud_weight.append(weight_distance)

                    #if(zz == 100 and xx == 7 and yy == 10):
                    #    print('Match',ipt,cube_index)
                    #    print('Pt point',coord1,coord2,wave)
                    #    print('Pt a-b-l',alpha,beta)
                    #    print('x y',x+1,y+1)
                    #    print(xloc[ix],xloc[ix]-coord1)
                    #    print(yloc[iy],yloc[iy]-coord2)
                    #    print(zloc[iz],zloc[iz]-wave)

                    ix = ix + 1
                    iprint = iprint + 1
#                    if(iprint > 10000):
#                        iprint = 0
                iy = iy + 1
            iz = iz + 1

#_______________________________________________________________________

#_______________________________________________________________________
def FindWaveWeights(channel, subchannel):
    """
    Short Summary
    -------------
    Get the wavelength normalization weights that we will use to normalize wavelengths.

    Parameters
    ----------
    channel- channel for point
    subchannel- subchannel for point

    Returns
    -------
    normalized weighting for wavelength for this channel, subchannel

    """

    if(channel == '1'):
        if(subchannel == 'SHORT'):
            a = 3050.0
            c = 3340.0
            wa = 4.91
            wc = 5.79
        elif(subchannel == 'MEDIUM'):
            a = 2920.0
            c = 3400.0
            wa = 5.6
            wc = 6.62
        elif(subchannel == 'LONG'):
            a = 2800.0
            c = 3220.0
            wa = 6.46
            wc = 7.63


    if(channel == '2'):
        if(subchannel == 'SHORT'):
            a = 2700.0
            c = 2800.0
            wa = 7.55
            wc = 8.91
        elif(subchannel == 'MEDIUM'):
            a = 2600.0
            c = 2880.0
            wa = 8.71
            wc = 10.34
        elif(subchannel == 'LONG'):
            a = 2590.0
            c = 3000.0
            wa = 9.89
            wc = 11.71

    if(channel == '3'):
        if(subchannel == 'SHORT'):
            a = 2390.0
            c = 2650.0
            wa = 11.50
            wc = 13.59
        elif(subchannel == 'MEDIUM'):
            a = 1600.0
            c = 2400.0
            wa = 13.19
            wc = 15.58
        elif(subchannel == 'LONG'):
            a = 1850.0
            c = 2550.0
            wa = 15.40
            wc = 18.14

    if(channel == '4'):
        if(subchannel == 'SHORT'):
            a = 1320.0
            c = 1720.0
            wa = 17.88
            wc = 21.34
        elif(subchannel == 'MEDIUM'):
            a = 1550.0
            c = 1600.0
            wa = 20.69
            wc = 24.68
        elif(subchannel == 'LONG'):
            a = 1450.0
            c = 1200.0
            wa = 23.83
            wc = 28.43
    return a, c, wa, wc

#_______________________________________________________________________



def FindNormalizationWeights(a, c, wa, wc, wavelength):
    """
    Short Summary
    -------------
    we need to normalize how to each point cloud in the spaxel. The normalization of
gs     weighting is determined from width of PSF as well as wavelength resolution

    Parameters
    ----------
    channel- channel for point
    subchannel- subchannel for point
    wavelength of point

    Returns
    -------
    normalized weighting for 3 dimension

    """
    alpha_weight = 1.0
    beta_weight = 1.0
    lambda_weight = 1.0

    beta_weight = 0.31 * (wavelength / 8.0)


    if(wavelength < 8.0):
        alpha_weight = 0.31
    else:
        alpha_weight = beta_weight


        # linear interpolation

    if (wavelength >= wa and wavelength <= wc):
        b = a + (c - a) * (wavelength - wa) / (wc - wa)

    elif (wavelength < wa):
        b = a
    else:
        b = c


    lambda_weight = wavelength / b

    weight = [alpha_weight, beta_weight, lambda_weight]
    return weight

