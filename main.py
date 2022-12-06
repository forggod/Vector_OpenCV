"""
    Thanks alot:
    https://github.com/tprlab/pitanq-dev/tree/master/selfdrive/follow_line
"""

import cv2
import numpy as np
import conf
import roi
import time
import geom_util as geom


def find_main_countour(cnts):
        C = None
        if cnts is not None and len(cnts) > 0:
            C = max(cnts, key = cv2.contourArea)
        if C is None:
            return None, None

        rect = cv2.minAreaRect(C)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        box = geom.order_box(box)
        return C, box

def handle_pic(img, contours, wh):
    cont, box = find_main_countour(contours)
    if cont is None:
        return None, None
    
    p1, p2 = geom.calc_box_vector(box)
    cv2.imshow("Result",img)

    if p1 is None:
        return None, None
    cv2.line(img, (int(p1[0]),int(p1[1])), (int(p2[0]),int(p2[1])), (0, 255, 0), 5)
    cv2.imshow("Result",img)
    angle = geom.get_vert_angle(p1, p2, wh[0], wh[1])
    shift = geom.get_horz_shift(p1[0], wh[0])
    return angle, shift

def find_line(side, img, contours, wh):
    print(("Finding line", side))
    if side == 0:
        return None, None
        
    for i in range(0, conf.find_turn_attempts):
        turn(side, conf.find_turn_step)
        angle, shift = handle_pic(img, contours, wh)
        if angle is not None:
            return angle, shift

    return None, None

def turn(r, t):
    turn_cmd = "s0" if r > 0 else "0s"
    ret_cmd = "f0" if r > 0 else "0f"
    turn = "Right" if r > 0 else "Left"
    print(("Turn", turn, t))
    print(turn_cmd)
    time.sleep(t)
    print(ret_cmd)

def check_shift_turn(angle, shift):
    turn_state = 0
    if angle < conf.turn_angle or angle > 180 - conf.turn_angle:
        turn_state = np.sign(90 - angle)

    shift_state = 0
    if abs(shift) > conf.shift_max:
        shift_state = np.sign(shift)
    return turn_state, shift_state

def get_turn(turn_state, shift_state):
    turn_dir = 0
    turn_val = 0
    if shift_state != 0:
        turn_dir = shift_state
        turn_val = conf.shift_step if shift_state != turn_state else conf.turn_step
    elif turn_state != 0:
        turn_dir = turn_state
        turn_val = conf.turn_step
    return turn_dir, turn_val   

def follow(iterations, img, contours, wh):
    print("Stay")   

    try:
        last_turn = 0
        last_angle = 0 

        for i in range(0, iterations):
            a, shift = handle_pic(img, contours, wh)
            if a is None:
                if last_turn != 0:
                    a, shift = find_line(last_turn, img, contours, wh)
                    if a is None:
                        break
                elif last_angle != 0:
                    print(("Looking for line by angle", last_angle))
                    turn(np.sign(90 - last_angle), conf.turn_step)
                    continue
                else:
                    break

            print((i, "Angle", a, "Shift", shift))

            turn_state, shift_state = check_shift_turn(a, shift)

            turn_dir, turn_val = get_turn(turn_state, shift_state)

            if turn_dir != 0:
                turn(turn_dir, turn_val)
                last_turn = turn_dir
            else:
                time.sleep(conf.straight_run)
                last_turn = 0
            last_angle = a
        
    finally:
        print("ss")




cv2.namedWindow( 'Origin' )
cv2.namedWindow( 'Result' )
for i in range(1, 13):
    path = 'img/' + str(i) + '.jpg'
    img = cv2.imread(path)
    img = cv2.resize(img, (480, 640))

    #
    # scale_percent = 40 # percent of original size
    # width = int(img.shape[1] * scale_percent / 100)
    # height = int(img.shape[0] * scale_percent / 100)
    # dim = (width, height)
    # img_r = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)

    # Применяем фильтр
    img_median = cv2.medianBlur(img, 7)

    # Оставляем контуры
    thresh = 60
    img_gray = cv2.cvtColor(img_median, cv2.COLOR_BGR2GRAY)
    ret, img_thresh = cv2.threshold(img_gray, thresh, 255, cv2.THRESH_BINARY)
    for x in range(img_gray.shape[0]):
        for y in range(img_gray.shape[1]):
            if img_thresh[x, y] == 255:
                img_thresh[x, y] = 0
            else:
                img_thresh[x, y] = 255
            
    contours, heirarchy = cv2.findContours(img_thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    img_contours = np.zeros(img.shape)
    cv2.drawContours(img_contours, contours, -1, (255, 255, 255), -1)

    #
    # Поиск вектора
    axis = handle_pic(img_contours, contours, img_contours.shape[:2])
    print(axis)
    
    cont, box = find_main_countour(contours)
    p1, p2 = geom.calc_box_vector(box)
    print(p1, p2) 
    print('WH', img_contours.shape[:2])
    # 480-w  640-h  side- m, l, r
    side = 'm'
    if p2[0] <= 220 and axis[0] > 90:
        side = 'l'
    elif 260 <= p2[0] and axis[0] < 90:
        side = 'r'
    print(side)

    # follow(1, img_contours, contours, img_contours.shape[:2])
    #


    
    try:
        cv2.imshow('Origin', img)
        cv2.imshow('Result', img_contours)
    except:
        print('Cant show origin')
    ch = cv2.waitKey(0)

    if ch == 27:
        break

cv2.destroyAllWindows()