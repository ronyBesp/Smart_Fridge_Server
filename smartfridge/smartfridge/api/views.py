# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from smartfridge.api.serializers import FridgeContentsSerializer
from smartfridge.api.models import FridgeContents
from rest_framework import permissions, mixins
from django.shortcuts import get_object_or_404
from os.path import abspath, dirname
import os
from google.cloud import vision
from google.cloud.vision import types
import logging
import subprocess
from PIL import Image
import json

import sys
import math
import collections
from collections import OrderedDict
import cv2
import numpy as np


# Instansiate logger
logger = logging.getLogger(__name__)


def calculate_capacity(previousCapacityList, origImgPath):
    mincurmaxlist=previousCapacityList
    image_variable=origImgPath
    logger.debug("IN CAPACITY LIST")
    logger.debug(mincurmaxlist)
    logger.debug(image_variable)
    img_edge = cv2.imread(image_variable,0)
    #canny edge detection
    edges = cv2.Canny(img_edge,101,200)
    totalPixels=edges.shape[1]*edges.shape[0]
    countOfPixels=0
    if not mincurmaxlist:
        for (x,y), value in np.ndenumerate(edges):
            if value >0:
                countOfPixels+=1
        mincurmaxlist.append(float(countOfPixels)/float(totalPixels)-0.001)
        mincurmaxlist.append(float(countOfPixels)/float(totalPixels))
        mincurmaxlist.append(float(countOfPixels)/float(totalPixels)+0.001)

    else:
        for (x,y), value in np.ndenumerate(edges):
            if value >0:
                countOfPixels+=1
        mincurmaxlist[1]=float(countOfPixels)/float(totalPixels)
        if mincurmaxlist[1]>mincurmaxlist[2]:
            mincurmaxlist[2]=mincurmaxlist[1]
        elif mincurmaxlist[1]<mincurmaxlist[0]:
            mincurmaxlist[0]=mincurmaxlist[1]
       
        #print (mincurmaxlist)
        #print ((mincurmaxlist[1]-mincurmaxlist[0])/(mincurmaxlist[2]-mincurmaxlist[0])*100.0) #CRUCIAL LINE 

    return mincurmaxlist


def shelf_split(imgPath):
    imgVal = Image.open(imgPath)
    img2 = imgVal.crop((79,0, 559, 479))
    img2.save(imgPath)

    image_variable=imgPath
    img = cv2.imread(image_variable,0)

    # Perform Canny edge detenction
    edges = cv2.Canny(img,101,200)

    # Get width and height
    width=edges.shape[1]
    height=edges.shape[0]


    # Get HoughLines
    minLineLength = 100
    maxLineGap = 20
    lines = cv2.HoughLinesP(edges,1,np.pi/180,150,minLineLength,maxLineGap)


    xl=0
    yl=0
    count=0

    # make Hough lines 2D array from 3D
    allLines=lines[:,0,:]

    nonHLines=[]

    # Check for non Horizontal lines
    for x1,y1,x2,y2 in allLines:
        xl=x2-x1
        yl=abs(y2-y1)
        angle = math.degrees(math.atan2(yl,xl))
        if angle>15:
            nonHLines.append(count)
        count +=1

    # Delete non horizontal lines
    cleanLines = np.delete(allLines,nonHLines,axis=0)

    # Create dictionary to store line heights
    lineHeights={}
    for x1,y1,x2,y2 in cleanLines:
        if y1 in lineHeights.keys():
            lineHeights[y1]+=1
        else:
            lineHeights[y1] = 1
        if y2 in lineHeights.keys():
            lineHeights[y2]+=1
        else:
            lineHeights[y2] = 1

    lineHeights=OrderedDict(sorted(lineHeights.items(), key=lambda(k,v):(v,k)))


    shelvePossibilities={}
    newHeight=0
    newWeight=0
    flagVar=0
    heightThreshold=height/50

    for key in lineHeights:
        if not shelvePossibilities:
            shelvePossibilities[key]=lineHeights[key]
        flagVar=0
        for shelf in shelvePossibilities:
            if key<(shelf + heightThreshold) and key>(shelf - heightThreshold):
                newWeight=lineHeights[key]+shelvePossibilities[shelf]

                newHeight=int(key*(float(lineHeights[key])/float(newWeight))+(shelf*(float(shelvePossibilities[shelf])/float(newWeight))))
			
                shelvePossibilities[shelf]+=lineHeights[key]
                shelvePossibilities[newHeight]=shelvePossibilities.pop(shelf)
                flagVar=1
                break

        if flagVar is 0:
            shelvePossibilities[key]=lineHeights[key]

    shelvePossibilities = sorted(shelvePossibilities.items())

    splits=[]
    lastSplit=0
    shelfMin=height/6

    for poss in shelvePossibilities:
        if poss[1] >2 and poss[0]-lastSplit > shelfMin and height-shelfMin > poss[0]:
            splits.append(poss[0])
            lastSplit=poss[0]

    splits.append(height-1)
    print splits
    crop_num=0
    last_split=0
    img_crop = Image.open(image_variable)

    # Split at the split points
    imgPathParts = imgPath.split(".")
    imgPathNoExtension = imgPathParts[0]
    imgExt = imgPathParts[1]
    savedShelfList = []
    for i in range(0, len(splits)):
        savedShelfList.append(imgPathNoExtension + "_shelf_" + str(i) + "." + imgExt)

    for spl in splits:
        cropimg=img_crop.crop((0,last_split,width,spl))
        cropimg.save(savedShelfList[crop_num])
        last_split=spl
        crop_num+=1

    return savedShelfList



def item_split(imgPath):
    image_variable=imgPath
    img_edge = cv2.imread(image_variable,0)

    #canny edge detection
    edges = cv2.Canny(img_edge,101,200)

    width=edges.shape[1]
    height=edges.shape[0]


    col_edges= [0] * width

    # Convert to 1D array
    for (x,y), value in np.ndenumerate(edges):
        if value >0:
            col_edges[y]+=1


    # Set variables that are used to find split distances
    cur_split=0
    cur_min_place=0
    cur_min_num=height
    i=0
    weighted_val=0
    max_split_distance=int(width/2)
    min_split_distance=int(width/4)
    count_threshold=int(height/20)
    split_points=[]

    # While current pixel has not reached the buffer on right side of the image
    while i<width- min_split_distance:
        # Check that i is in the range to split
        if (i - cur_split) < max_split_distance and (i-cur_split) > min_split_distance:
            # Create weighted value 
            weighted_val=col_edges[i-2]*.05+ col_edges[i-1]*.15+ col_edges[i]*.6+ col_edges[i+1]*.15+ col_edges[i+2]*.05
            # If its less then the current value se this as the new minimum
            if weighted_val<cur_min_num:
                cur_min_place=i
                cur_min_num=weighted_val
        # Else if it hits max split distance make a split
        elif (i - cur_split) > max_split_distance:
            # If current minimum is under threshold split at that point
            if cur_min_num<count_threshold:
                split_points.append(cur_min_place)
                # Else split at the max point
            else:
                split_points.append(i)
		
            cur_split=split_points[-1]
            i=split_points[-1]
            cur_min_num=height

        i+=1

    # Once its reached the end check if the current minimum is below threshold and if it is split at that point
    if cur_min_num<count_threshold:
        split_points.append(cur_min_place)
 
    elif width-cur_min_place<100:
        split_points.append(split_points[-1](width-cur_min/2))

    # Append last pixel for the last split
    split_points.append(width-1)
    print split_points

    crop_num=0
    last_split=0
    img_crop = Image.open(image_variable)

    # Return the cropped image paths
    imgPathParts = imgPath.split(".")
    imgPathNoExtension = imgPathParts[0]
    imgExt = imgPathParts[1]
    savedItemList = []
    for i in range(0, len(split_points)):
        savedItemList.append(imgPathNoExtension + "_crop_" + str(i) + "." + imgExt)


    # Split at the split points
    for spl in split_points:
        cropimg=img_crop.crop((last_split,0,spl,int(height)))
        cropimg.save(savedItemList[crop_num])
        last_split=spl
        crop_num+=1

    return savedItemList


def split_img(imgPath, imgName):
    # First call shelves.py -> function
    
    img = Image.open(imgPath)
    # Get the full path to the image but not including the extension
    imgPathParts = imgPath.split(".")
    imgPathNoExtension = imgPathParts[0]
    imgExt = imgPathParts[1]
    logging.debug(imgPathNoExtension)
    savedImgList = []
    for i in range(0,4):
        savedImgList.append(imgPathNoExtension + "_crop" + str(i) + "." + imgExt)
    width = img.size[0]
    height = img.size[1]

    cropimg = img.crop((0,0,int(width/2),int(height/2)))
    cropimg.save(savedImgList[0])

    cropimg=img.crop((int(width/2),0,width-1,int(height/2)))
    cropimg.save(savedImgList[1])

    cropimg=img.crop((0,int(height/2),int(width/2),height-1))
    cropimg.save(savedImgList[2])

    cropimg=img.crop((int(width/2),int(height/2),width-1,height-1))
    cropimg.save(savedImgList[3])

    return savedImgList


def new_img_recog(imgPaths):
    logger.debug("Converting list to string")
    imgArgPassStr = ""
    for img in imgPaths:
        imgArgPassStr += img + ","
    logger.debug(imgArgPassStr)
    logger.debug("Send entire cropped list")
    proc = subprocess.Popen(['python', '/home/rony/SmartFridge_Server/smartfridge/smartfridge/api/img_recog.py', imgArgPassStr], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    imgResult = proc.communicate()[0]
    
    
    resultPts = imgResult.strip("\n").split("#")
    logger.debug("Results determined were")
    logger.debug(imgResult)
    logger.debug("Components are " + str(resultPts))
    logger.debug(resultPts[0])
    logger.debug("Done")

    # Build up the dictionary
    resultDict = {}
    for comp in resultPts:
        # Split by ":" to get the key and value
        splitPt = comp.split(":")
        logger.debug(splitPt)
        if len(splitPt) >= 2:
            # ind 0 - key
            # ind 1 - value still needs extra parsing
            val = splitPt[1].strip(" ")
            logger.debug(val[:-1])
            resultDict[int(splitPt[0])] = val[:-1]
    logger.debug("Result Dict is")
    logger.debug(resultDict)
    return resultDict


class FridgeContentsViewSet(viewsets.ModelViewSet):
    serializer_class = FridgeContentsSerializer

    def perform_create(self, serializer_class):
        logger.debug("HELLO YO YO")
        # We can go ahead and get the img value
        dataDict = serializer_class.validated_data

        # Save everything at first
        serializer_class.save()

        # Now we get the original saved image and start the split
        # This is coming from serializer so its not actually the file path ie. has 127.0.0.1/ in it
        imgFullPath = serializer_class['img'].value
        imgPathDict = imgFullPath.split('/')
        imgFullPath = abspath('') + "/uploads/" + imgPathDict[len(imgPathDict) - 2] + "/" + imgPathDict[len(imgPathDict) - 1]


        # Split image by shelf        
        logger.debug("About to call shelf script")
        savedShelfList = shelf_split(imgFullPath)
        logger.debug(savedShelfList)
        

        # Take each shelf and split within
        savedItemList = []
        for shelfPath in savedShelfList:
            savedItemList += item_split(shelfPath)

        logger.debug("Item Split complete")
        logger.debug(savedItemList)

        
        # Get the shelf dict
        i = 0
        shelfDict = {}
        for shelfPath in savedShelfList:
            serverStr = "http://138.197.175.107"
            indUpload = shelfPath.find("/uploads")
            serverStr += shelfPath[indUpload:]
            shelfDict[i] = serverStr
            i += 1
        
        logger.debug("Shelf Dict is:")
        logger.debug(shelfDict)

        # Get the imgs within shelf
        strShelf = ""
        withinShelfStr = ""
        withinShelfDict = {}
        i = 0
        logger.debug("\n\n\n\n")
        logger.debug("Within Shelf Item Dictionary")
        for pic in savedItemList:
            logger.debug(pic)
            strShelf = "shelf_" + str(i)
            logger.debug("i is " + str(i))
            logger.debug("shelf str: " + strShelf)
            #if strShelf in pic:
            logger.debug("in here")
            serverStr = "http://138.197.175.107"
            indUpload = pic.find("/uploads")
            serverStr += pic[indUpload:]
            if strShelf in pic:
                withinShelfStr += str(serverStr) + ","
            else:
                logger.debug(withinShelfStr)
                withinShelfDict[i] = withinShelfStr
                # First of new shelf
                withinShelfStr = str(serverStr) + ","
                i += 1
         
        # Always get the last shelf items
        withinShelfDict[i] = withinShelfStr
        
        logger.debug("Within Shelf Dict")
        logger.debug(withinShelfDict)
        # Perform google cloud vision Image Processing and filtering on the cropped images and return the dictionary results
        resultDict = new_img_recog(savedItemList)
        logger.debug(resultDict)

        # Get the current object and save additional fields
        curObj = FridgeContents.objects.get(id=serializer_class['id'].value)
        curObj.resultDict = resultDict
        curObj.shelfImgPaths = shelfDict
        curObj.withinShelfImgPaths = withinShelfDict
        #curObj.save()
        

       
        # Try to get previous object if it exists
        queryTest = FridgeContents.objects.all()
        queryTest = queryTest.filter(user_name=serializer_class['user_name'].value)
        #logger.debug("ID 0: " + str(queryTest[0].id))
        #logger.debug("ID 1: " + str(queryTest[1].id))

        # Go ahead and call the capacity script passing in the previous capacity list and the full image path
        jsonDecoder = json.decoder.JSONDecoder()
        if len(queryTest) > 2:
            if queryTest[1].previousCapList is not None:
                logger.debug("NOT NONE")
                prevList = jsonDecoder.decode(queryTest[1].previousCapList)
            else:
                prevList = []
        else:
            prevList = []
        logger.debug("Previous list")
        logger.debug(prevList)
        #prevList = []
        capList = calculate_capacity(prevList, imgFullPath)
        logger.debug("New capacity list")
        logger.debug(capList)
        # Cap val
        capVal = (capList[1]-capList[0])/(capList[2]-capList[0])*100.0
       
        curObj.previousCapList = json.dumps(capList)
        curObj.capacity = str(capVal)
        curObj.save()


    # GET CALLS    
    def get_queryset(self):
        queryset = FridgeContents.objects.all()
        print(self.request.query_params)
        id_val = self.request.query_params.get('id', None)
        user_val = self.request.query_params.get('user', None)
        if id_val is not None:
            queryset = queryset.filter(id=id_val)
        if user_val is not None:
            queryset = queryset.filter(user_name=user_val)
        return queryset

