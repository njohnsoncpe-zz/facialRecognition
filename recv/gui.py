#!/usr/bin/python
import time
import datetime
import shutil
import os
from tkinter import *
from PIL import ImageTk, Image
recordFlag = 0


def recordCall():
    global recordFlag
    if (recordFlag):
        recordFlag = 0
        button.configure(text="RECORD")

    else:
        recordFlag = 1
        button.configure(text="STOP RECORDING")


def refresh_image(canvas, img, image_path, image_id):
    global recordFlag
    timeVal = time.time()
    timeTitle = datetime.datetime.fromtimestamp(timeVal).strftime(
        '%Y-%m-%d--%H:%M:%S')
    canvas.itemconfigure(clock_id, text=timeTitle)
    try:
        pil_img = Image.open(image_path)
        img = ImageTk.PhotoImage(pil_img)
        canvas.itemconfigure(image_id, image=img)
        if recordFlag:
            dateFolder = datetime.datetime.fromtimestamp(timeVal).strftime(
                '%Y-%m-%d')
            timeName = datetime.datetime.fromtimestamp(timeVal).strftime(
                '%H:%M:%S')
            if not os.path.exists('recorded/' + dateFolder + '/'):
                os.mkdir('recorded/' + dateFolder + '/')
            shutil.copy(image_path,
                        'recorded/' + dateFolder + '/' + timeName + '.jpg')

    except IOError:  # missing or corrupt image file
        pass
    # repeat every half sec
    canvas.after(1, refresh_image, canvas, img, image_path, image_id)


root = Tk()
root.title("Face Detector Stream")

image_path = 'img.jpg'

canvas = Canvas(root, height=580, width=640)
canvas.grid()
img = None  # initially only need a canvas image place-holder

button = Button(canvas, text="RECORD", command=recordCall)
button.configure(
    width=15, activebackground="#33B5E5", background='#C6C6C6', relief=FLAT)
button_window = canvas.create_window(320, 20, anchor=N, window=button)

clock_id = canvas.create_text(
    320,
    10,
    fill="darkblue",
    font="Helvetica 20",
    text="Click the bubbles that are multiples of two.")

image_id = canvas.create_image(320, 340, image=img)

canvas.pack()

refresh_image(canvas, img, image_path, image_id)
root.mainloop()