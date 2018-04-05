import os
from google.cloud import vision
from google.cloud.vision import types
import sys

#IMG_PATH = '/home/rony/SmartFridge_Server/fridge.jpg'
# Only do this once - more efficient
fruitList = []
with open('/home/rony/SmartFridge_Server/acceptedObjects.txt', 'rb') as fruitFile:
  for val in fruitFile:
    curLine = val.strip("\n").lower()
    curLine = curLine.encode('ascii', 'ignore')
    fruitList.append(curLine)

vegList = []
with open('/home/rony/SmartFridge_Server/vegetables.txt', 'rb') as vegFile:
  for val in vegFile:
    curLine = val.strip("\n").lower()
    vegList.append(curLine)

    clientVal = vision.ImageAnnotatorClient()

# Do this for all the cropped images
imgPaths = sys.argv[1]
#print(imgPaths)

# Need to make the paths into a list - rn a string
imgPaths = imgPaths.strip("\n").split(",")
#print(imgPaths)
# Loop through all paths but last cuz last path is just ','
tempResult = ""
count = 0
for imgVal in imgPaths[:-1]:
  img = open(imgVal, 'rb')
  img_read = img.read()

  imgVal = types.Image(content=img_read)
  # Send results to Google Cloud Vision platform for analysis
  resp = clientVal.label_detection(image=imgVal)
  lblVals = resp.label_annotations


  tempResult += str(count) + ": "  
  for val in lblVals:
    pluralStr = val.description + "s"
    if val.description in fruitList or pluralStr in fruitList:
      tempResult += val.description + ','
  # Add special termination character used for splitting in main script and increment count for next image
  tempResult += "#"
  count += 1
  

'''
for val in lblVals:
  pluralStr = val.description + "s"
  if val.description in fruitList or pluralStr in fruitList:
    tempResult += val.description + ", "
'''

print(tempResult)
