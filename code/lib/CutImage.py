import numpy as np
import cv2
from PIL import Image
from pathlib import Path
import threading
import logging
from lib.Config import Config

logger = logging.getLogger(__name__)

debug = True


class CutImage:
    def __init__(self, config: Config, imageTmpFolder="/image_tmp/"):
        self.imageTmpFolder = imageTmpFolder
        self.config = config
        self.reference_images = []
        self.M = None
        for i in range(3):
            file = self.config.cutReferenceName[i]
            self.reference_images.append(cv2.imread(file))

    def Cut(self, image):
        source = cv2.imread(image)
        cv2.imwrite(f"{self.imageTmpFolder}/org.jpg", source)
        target = self.RotateImage(source)
        cv2.imwrite(f"{self.imageTmpFolder}/rot.jpg", target)
        target = self.Alignment(target)
        cv2.imwrite(f"{self.imageTmpFolder}/alg.jpg", target)

        zeiger = self.cutZeiger(target)
        ziffern = self.cutZiffern(target)

        zeiger = ziffern
        if self.config.analogReadOutEnabled:
            zeiger = self.cutZeiger(target)

        return [zeiger, ziffern]

    def cutZeiger(self, source):
        result = []
        for zeiger in self.config.cutAnalogCounter:
            #            img[y:y+h, x:x+w]
            x, y, dx, dy = zeiger[1]
            crop_img = source[y : y + dy, x : x + dx]
            name = f"{self.imageTmpFolder}/{zeiger[0]}.jpg"
            cv2.imwrite(name, crop_img)
            crop_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
            im_pil = Image.fromarray(crop_img)
            singleresult = [zeiger[0], im_pil]
            result.append(singleresult)
        return result

    def cutZiffern(self, source):
        result = []
        for zeiger in self.config.cutDigitalDigit:
            x, y, dx, dy = zeiger[1]
            crop_img = source[y : y + dy, x : x + dx]
            name = f"{self.imageTmpFolder}/{zeiger[0]}.jpg"
            cv2.imwrite(name, crop_img)
            crop_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
            im_pil = Image.fromarray(crop_img)
            singleresult = [zeiger[0], im_pil]
            result.append(singleresult)
        return result

    def Alignment(self, source):
        h, w, ch = source.shape
        if (self.M is None) or (self.config.cutFastMode is False):
            self.CalculateAffineTransform(source)
        else:
            CalcAffTransOffline = self.CalcAffTransOfflineClass(self)
            CalcAffTransOffline.start()
        return cv2.warpAffine(source, self.M, (w, h))

    def CalculateAffineTransform(self, source):
        logger.debug("Cut CalcAffineTransformation")
        h, w, ch = source.shape
        if debug:
            logger.debug("Align 01a")
        p0 = self.getRefCoordinate(source, self.reference_images[0])
        if debug:
            logger.debug("Align 01b")
        p1 = self.getRefCoordinate(source, self.reference_images[1])
        if debug:
            logger.debug("Align 01c")
        p2 = self.getRefCoordinate(source, self.reference_images[2])
        if debug:
            logger.debug("Align 02")

        pts1 = np.float32([p0, p1, p2])
        pts2 = np.float32(
            [
                self.config.cutReferencePos[0],
                self.config.cutReferencePos[1],
                self.config.cutReferencePos[2],
            ]
        )
        self.M = cv2.getAffineTransform(pts1, pts2)

    class CalcAffTransOfflineClass(threading.Thread):
        def __init__(self, _master):
            threading.Thread.__init__(self)
            self.master = _master

        def run(self):
            self.master.CalculateAffineTransform(self.master.targetrot)

    def CutAfter(self):
        logger.debug("Cut After")
        if self.config.cutFastMode:
            CalcAffTransOffline = self.CalcAffTransOfflineClass(self)
            CalcAffTransOffline.start()

    def getRefCoordinate(self, image, template):
        #        method = cv2.TM_SQDIFF                     #2
        method = cv2.TM_SQDIFF_NORMED  # 1
        #        method = cv2.TM_CCORR_NORMED                #3
        method = cv2.TM_CCOEFF_NORMED  # 4
        res = cv2.matchTemplate(image, template, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return min_loc if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED] else max_loc

    def RotateImage(self, image):
        h, w, ch = image.shape
        center = (w / 2, h / 2)
        M = cv2.getRotationMatrix2D(center, self.config.cutRotateAngle, 1.0)
        image = cv2.warpAffine(image, M, (w, h))
        return image

    def DrawROIOLDOLDOLD(self, url):
        im = cv2.imread(url)

        d = 2
        x = self.reference_p0[0]
        y = self.reference_p0[1]
        h, w = self.ref0.shape[:2]
        cv2.rectangle(
            im, (x - d, y - d), (x + w + 2 * d, y + h + 2 * d), (0, 0, 255), d
        )
        cv2.putText(im, "ref0", (x, y - 5), 0, 0.4, (0, 0, 255))

        x = self.reference_p1[0]
        y = self.reference_p1[1]
        h, w = self.ref1.shape[:2]
        cv2.rectangle(
            im, (x - d, y - d), (x + w + 2 * d, y + h + 2 * d), (0, 0, 255), d
        )
        cv2.putText(im, "ref1", (x, y - 5), 0, 0.4, (0, 0, 255))

        x = self.reference_p2[0]
        y = self.reference_p2[1]
        h, w = self.ref2.shape[:2]
        cv2.rectangle(
            im, (x - d, y - d), (x + w + 2 * d, y + h + 2 * d), (0, 0, 255), d
        )
        cv2.putText(im, "ref2", (x, y - 5), 0, 0.4, (0, 0, 255))

        if self.config.analogReadOutEnabled:
            d_eclipse = 1

            for zeiger in self.config.cutAnalogCounter:
                x, y, w, h = zeiger[1]
                cv2.rectangle(
                    im, (x - d, y - d), (x + w + 2 * d, y + h + 2 * d), (0, 255, 0), d
                )
                xct = int(x + w / 2) + 1
                yct = int(y + h / 2) + 1
                cv2.line(im, (xct - 5, yct), (xct + 5, yct), (0, 255, 0), 1)
                cv2.line(im, (xct, yct - 5), (xct, yct + 5), (0, 255, 0), 1)
                cv2.ellipse(
                    im,
                    (xct, yct),
                    (int(w / 2) + 2 * d_eclipse, int(h / 2) + 2 * d_eclipse),
                    0,
                    0,
                    360,
                    (0, 255, 0),
                    d_eclipse,
                )
                cv2.putText(im, zeiger[0], (x, y - 5), 0, 0.4, (0, 255, 0))
        for zeiger in self.config.cutDigitalDigit:
            x, y, w, h = zeiger[1]
            cv2.rectangle(
                im, (x - d, y - d), (x + w + 2 * d, y + h + 2 * d), (0, 255, 0), d
            )
            cv2.putText(im, zeiger[0], (x, y - 5), 0, 0.4, (0, 255, 0))
        cv2.imwrite(f"{self.imageTmpFolder}/roi.jpg", im)

    def DrawROI(
        self,
        image_in,
        image_out="/image_tmp/roi.jpg",
        draw_ref=False,
        draw_dig=True,
        draw_cou=True,
        ign_ref=-1,
        ign_dig=-1,
        ign_cou=-1,
    ):
        zwimage = str(image_in)
        im = cv2.imread(zwimage)

        d = 3
        _colour = (255, 0, 0)

        if draw_ref:
            for i in range(3):
                if i != ign_ref:
                    x, y = self.config.cutReferencePos[i]
                    h, w = self.reference_images[i].shape[:2]
                    cv2.rectangle(
                        im, (x - d, y - d), (x + w + 2 * d, y + h + 2 * d), _colour, d
                    )
                    cv2.putText(
                        im,
                        self.config.cutReferenceName[i].replace("/config/", ""),
                        (x, y - 5),
                        0,
                        0.4,
                        _colour,
                    )

        if self.config.analogReadOutEnabled and draw_cou:
            d_eclipse = 1
            for i in range(len(self.config.cutAnalogCounter)):
                if i != ign_cou:
                    x, y, w, h = self.config.cutAnalogCounter[i][1]
                    cv2.rectangle(
                        im,
                        (x - d, y - d),
                        (x + w + 2 * d, y + h + 2 * d),
                        (0, 255, 0),
                        d,
                    )
                    xct = int(x + w / 2) + 1
                    yct = int(y + h / 2) + 1
                    cv2.line(im, (x, yct), (x + w + 5, yct), (0, 255, 0), 1)
                    cv2.line(im, (xct, y), (xct, y + h), (0, 255, 0), 1)
                    cv2.ellipse(
                        im,
                        (xct, yct),
                        (int(w / 2) + 2 * d_eclipse, int(h / 2) + 2 * d_eclipse),
                        0,
                        0,
                        360,
                        (0, 255, 0),
                        d_eclipse,
                    )
                    cv2.putText(
                        im,
                        self.config.cutAnalogCounter[i][0],
                        (x, y - 5),
                        0,
                        0.5,
                        (0, 255, 0),
                    )

        if draw_dig:
            for i in range(len(self.config.cutDigitalDigit)):
                if i != ign_dig:
                    x, y, w, h = self.config.cutDigitalDigit[i][1]
                    cv2.rectangle(
                        im,
                        (x - d, y - d),
                        (x + w + 2 * d, y + h + 2 * d),
                        (0, 255, 0),
                        d,
                    )
                    cv2.putText(
                        im,
                        self.config.cutDigitalDigit[i][0],
                        (x, y - 5),
                        0,
                        0.5,
                        (0, 255, 0),
                    )

        zwname = str(image_out)
        cv2.imwrite(zwname, im)
