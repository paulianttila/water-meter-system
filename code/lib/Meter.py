import configparser
from lib.CutImage import CutImage
from lib.DigitalCounterCNN import DigitalCounterCNN
from lib.AnalogCounterCNN import AnalogCounterCNN
from lib.ImageLoader import DownloadFailure, ImageLoader
from lib.Config import Config
import math
import os
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Meter:
    def __init__(
        self,
        configFile: str = "/config/config.ini",
        prevValueFile: str = "/config/prevalue.ini",
        imageTmpFolder: str = "/tmp_images",
    ):
        logger.debug("Start Init Meter Reader")
        self.prevValueFile = prevValueFile
        self.imageTmpFolder = imageTmpFolder
        self.config = Config()
        self.config.parseConfig(configFile)

        if self.config.readPreValueFromFileAtStartup:
            self._loadPrevalueFromFile(
                self.prevValueFile, self.config.readPreValueFromFileMaxAge
            )
        else:
            self.lastIntegerValue = ""
            self.lastDecimalValue = ""

        self._initAnalog()
        self._initDigital()

        self.cutImageHandler = CutImage(self.config, imageTmpFolder=imageTmpFolder)
        self.imageLoader = ImageLoader(
            url=self.config.httpImageUrl,
            timeout=self.config.httpTimeoutLoadImage,
            minImageSize=10000,
            imageLogFolder=self.config.httpImageLogFolder,
            logOnlyFalsePictures=self.config.httpLogOnlyFalsePictures,
        )

        self.akt_vorkomma = ""
        self.akt_nachkomma = ""

    def _initAnalog(self):
        if self.config.analogReadOutEnabled:
            self.readAnalogNeedle = AnalogCounterCNN(
                modelfile=self.config.analogModelFile,
                dx=32,
                dy=32,
                imageTmpFolder=self.imageTmpFolder,
                imageLogFolder=self.config.analogImageLogFolder,
                imageLogNames=self.config.analogLogImageNames,
            )
            logger.debug("Analog model init done")
        else:
            logger.debug("Analog model disabled")

    def _initDigital(self):
        if self.config.digitalReadOutEnabled:
            self.readDigitalDigit = DigitalCounterCNN(
                modelfile=self.config.digitModelFile,
                dx=20,
                dy=32,
                imageTmpFolder=self.imageTmpFolder,
                imageLogFolder=self.config.digitImageLogFolder,
                imageLogNames=self.config.digitLogImageNames,
            )
            logger.debug("Digital model init done")
        else:
            logger.debug("Digital model disabled")

    def setPreviousValue(self, setValue):
        zerlegt = setValue.split(".")
        vorkomma = zerlegt[0][: len(self.cutImageHandler.Digital_Digit)]
        self.lastIntegerValue = vorkomma.zfill(len(self.cutImageHandler.Digital_Digit))

        result = "N"
        if self.config.analogReadOutEnabled:
            nachkomma = zerlegt[1][: len(self.cutImageHandler.Analog_Counter)]
            while len(nachkomma) < len(self.cutImageHandler.Analog_Counter):
                nachkomma = f"{nachkomma}0"
            self.lastDecimalValue = nachkomma
            result = f"{self.lastIntegerValue}.{self.lastDecimalValue}"
        else:
            result = self.lastIntegerValue

        self._storePrevalueToFile(self.prevValueFile)

        result = f"Last value set to: {result}"
        return result

    def _storePrevalueToFile(self, file: str):
        logtime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        config = configparser.ConfigParser()
        config.read(file)
        config["PreValue"]["LastVorkomma"] = self.lastDecimalValue
        if self.config.analogReadOutEnabled:
            config["PreValue"]["LastNachkomma"] = self.lastIntegerValue
        else:
            config["PreValue"]["LastNachkomma"] = "0"
        config["PreValue"]["Time"] = logtime
        with open(file, "w") as cfg:
            config.write(cfg)

    def _loadPrevalueFromFile(self, file: str, readPreValueFromFileMaxAge):
        config = configparser.ConfigParser()
        config.read(file)
        logtime = config["PreValue"]["Time"]

        fmt = "%Y-%m-%d_%H-%M-%S"
        #        d1 = datetime.strptime(nowtime, fmt)
        d1 = datetime.now()
        d2 = datetime.strptime(logtime, fmt)
        diff = (d1 - d2).days * 24 * 60

        if diff <= readPreValueFromFileMaxAge:
            self.lastDecimalValue = config["PreValue"]["LastVorkomma"]
            self.lastIntegerValue = config["PreValue"]["LastNachkomma"]
            zw = (
                f"Previous value loaded from file: "
                f"{self.lastIntegerValue}.{self.lastDecimalValue}"
            )

        else:
            self.lastDecimalValue = ""
            self.lastIntegerValue = ""
            zw = (
                f"Previous value not loaded from file as value is too old: "
                f"({str(diff)} minutes)."
            )

        logger.info(zw)

    def getROI(self, url: str, timeout: int = 0):
        self._removeFile(f"{self.imageTmpFolder}/original.jpg")

        self.imageLoader.loadImageFromUrl(
            url, f"{self.imageTmpFolder}/original.jpg", timeout
        )

        logger.debug("Start ROI")
        self.cutImageHandler.drawRoi(
            f"{self.imageTmpFolder}/aligned.jpg", f"{self.imageTmpFolder}/roi.jpg"
        )
        logger.debug("Get ROI done")

    def getMeterValueHtml(
        self,
        url: str,
        simple: bool = True,
        usePreValue: bool = False,
        single: bool = False,
        ignoreConsistencyCheck: bool = False,
        timeout: int = 0,
    ) -> str:
        if self.config.analogReadOutEnabled:
            prevValue = self.lastIntegerValue.lstrip("0") + "." + self.lastDecimalValue
        else:
            prevValue = self.lastIntegerValue.lstrip("0")

        preval = {
            "Value": None if prevValue == "." else prevValue,
            "DigitalDigits": (
                None if self.lastIntegerValue == "" else self.lastIntegerValue
            ),
            "AnalogCounter": (
                None if self.lastDecimalValue == "" else self.lastDecimalValue
            ),
        }

        try:
            self.imageLoader.loadImageFromUrl(
                url, f"{self.imageTmpFolder}/original.jpg", timeout
            )
        except DownloadFailure as e:
            return self._makeReturnValue(True, f"{e}", preval)

        if self.config.analogReadOutEnabled:
            logger.debug("Start CutImage, AnalogReadout, DigitalReadout")
        else:
            logger.debug("Start CutImage, DigitalReadout")
        cutIimages = self.cutImageHandler.cut(f"{self.imageTmpFolder}/original.jpg")
        self.cutImageHandler.drawRoi(f"{self.imageTmpFolder}/roi.jpg")

        if self.config.analogReadOutEnabled:
            resultAnalog = self.readAnalogNeedle.readout(cutIimages.analogImages)
        resultDigital = self.readDigitalDigit.readout(cutIimages.digitalImages)

        self.akt_nachkomma = 0
        if self.config.analogReadOutEnabled:
            self.akt_nachkomma = self._analogReadoutToValue(resultAnalog)
        self.akt_vorkomma = self._digitalReadoutToValue(
            resultDigital, usePreValue, self.lastDecimalValue, self.akt_nachkomma
        )
        self.imageLoader.postProcessLogImageProcedure(True)

        logger.debug("Start making meter value")
        (consistencyError, errortxt) = self._checkConsistency(ignoreConsistencyCheck)
        self._updateLastValues(consistencyError)

        txt = self._makeReturnValue(consistencyError, errortxt, single)

        if not simple:
            txt = f"{txt}<p>Aligned Image: <p><img src=/image_tmp/aligned.jpg></img><p>"
            txt = f"{txt}Digital Counter: <p>"
            for i in range(len(resultDigital)):
                zw = "NaN" if resultDigital[i] == "NaN" else str(int(resultDigital[i]))
                imageName = str(cutIimages.digitalImages[i][0])
                txt += f"<img src=/image_tmp/{imageName}.jpg></img>{zw}"
            txt = f"{txt}<p>"
            if self.config.analogReadOutEnabled:
                txt = f"{txt}Analog Meter: <p>"
                for i in range(len(resultAnalog)):
                    imageName = str(cutIimages.analogImages[i][0])
                    txt += (
                        f"<img src=/image_tmp/{imageName}.jpg></img>"
                        + "{:.1f}".format(resultAnalog[i])
                    )
                txt = f"{txt}<p>"
        logger.debug("Get meter value done")
        return txt

    def getMeterValueJson(
        self,
        url: str,
        simple: bool = True,
        usePreValue: bool = False,
        single: bool = False,
        ignoreConsistencyCheck: bool = False,
        timeout: int = 0,
    ) -> str:

        if self.config.analogReadOutEnabled:
            prevValue = self.lastIntegerValue.lstrip("0") + "." + self.lastDecimalValue
        else:
            prevValue = self.lastIntegerValue.lstrip("0")

        preval = {
            "Value": None if prevValue == "." else prevValue,
            "DigitalDigits": (
                None if self.lastIntegerValue == "" else self.lastIntegerValue
            ),
            "AnalogCounter": (
                None if self.lastDecimalValue == "" else self.lastDecimalValue
            ),
        }

        try:
            self.imageLoader.loadImageFromUrl(
                url, f"{self.imageTmpFolder}/original.jpg", timeout
            )
        except DownloadFailure as e:
            return {
                "Value": None,
                "DigitalDigits": None,
                "AnalogCounter": None,
                "Error": f"{e}",
                "Prevalue": preval,
            }

        if self.config.analogReadOutEnabled:
            logger.debug("Start CutImage, AnalogReadout, DigitalReadout")
        else:
            logger.debug("Start CutImage, DigitalReadout")
        cutIimages = self.cutImageHandler.cut(f"{self.imageTmpFolder}/original.jpg")
        self.cutImageHandler.drawRoi(f"{self.imageTmpFolder}/roi.jpg")

        if self.config.analogReadOutEnabled:
            resultAnalog = self.readAnalogNeedle.readout(cutIimages.analogImages)
        resultDigital = self.readDigitalDigit.readout(cutIimages.digitalImages)

        self.akt_nachkomma = 0
        if self.config.analogReadOutEnabled:
            self.akt_nachkomma = self._analogReadoutToValue(resultAnalog)
        self.akt_vorkomma = self._digitalReadoutToValue(
            resultDigital, usePreValue, self.lastDecimalValue, self.akt_nachkomma
        )
        self.imageLoader.postProcessLogImageProcedure(True)

        logger.debug("Start making meter value")
        (consistencyError, errortxt) = self._checkConsistency(ignoreConsistencyCheck)
        self._updateLastValues(consistencyError)

        (Value, AnalogCounter, Digit, Error) = self._makeReturnValueJSON(
            consistencyError, errortxt, single
        )

        logger.debug("Get meter value done")
        return {
            "Value": Value,
            "DigitalDigits": Digit,
            "AnalogCounter": AnalogCounter,
            "Error": Error,
            "Prevalue": preval,
        }

    def _makeReturnValueJSON(self, error, errortxt, single):
        Value = ""
        AnalogCounter = ""
        Digit = ""
        Errortxt = errortxt
        if error:
            if self.config.errorReturn.find("Value") > -1:
                Digit = str(self.akt_vorkomma)
                Value = str(self.akt_vorkomma.lstrip("0"))
                if self.config.analogReadOutEnabled:
                    Value = f"{Value}.{str(self.akt_nachkomma)}"
                    AnalogCounter = str(self.akt_nachkomma)
        else:
            Digit = str(self.akt_vorkomma.lstrip("0"))
            Value = str(self.akt_vorkomma.lstrip("0"))
            if self.config.analogReadOutEnabled:
                Value = f"{Value}.{str(self.akt_nachkomma)}"
                AnalogCounter = str(self.akt_nachkomma)
        return (Value, AnalogCounter, Digit, Errortxt)

    def _makeReturnValue(self, error, errortxt, single):
        output = ""
        if error:
            if self.config.errorReturn.find("Value") > -1:
                output = str(self.akt_vorkomma.lstrip("0"))
                if self.config.analogReadOutEnabled:
                    output = f"{output}.{str(self.akt_nachkomma)}"
                if not single:
                    output = output + "\t" + self.akt_vorkomma
                    if self.config.analogReadOutEnabled:
                        output = output + "\t" + self.akt_nachkomma
            output = output + "\t" + errortxt if len(output) > 0 else errortxt
        else:
            output = str(self.akt_vorkomma.lstrip("0")) or "0"
            if self.config.analogReadOutEnabled:
                output = f"{output}.{str(self.akt_nachkomma)}"
            if not single:
                output = output + "\t" + self.akt_vorkomma
                if self.config.analogReadOutEnabled:
                    output = output + "\t" + self.akt_nachkomma
        return output

    def _updateLastValues(self, error):
        if "N" in self.akt_vorkomma:
            return
        if error:
            if self.config.errorReturn.find("NewValue") > -1:
                self.lastDecimalValue = self.akt_nachkomma
                self.lastIntegerValue = self.akt_vorkomma
            else:
                self.akt_nachkomma = self.lastDecimalValue
                self.akt_vorkomma = self.lastIntegerValue
        else:
            self.lastDecimalValue = self.akt_nachkomma
            self.lastIntegerValue = self.akt_vorkomma

        self._storePrevalueToFile(self.prevValueFile)

    def _checkConsistency(self, ignoreConsistencyCheck):
        error = False
        errortxt = ""
        if (
            (len(self.lastIntegerValue) > 0)
            and "N" not in self.akt_vorkomma
            and self.config.consistencyEnabled
        ):
            akt_zaehlerstand = float(
                str(self.akt_vorkomma.lstrip("0")) + "." + str(self.akt_nachkomma)
            )
            old_zaehlerstand = float(
                str(self.lastIntegerValue.lstrip("0"))
                + "."
                + str(self.lastDecimalValue)
            )
            delta = akt_zaehlerstand - old_zaehlerstand
            if not (self.config.allowNegativeRates) and (delta < 0):
                error = True
                errortxt = "Error - NegativeRate"
            if abs(delta) > self.config.maxRateValue:
                if error:
                    errortxt = "Error - RateTooHigh ({:.4f})" + errortxt.format(delta)
                else:
                    errortxt = "Error - RateTooHigh ({:.4f})".format(delta)
                error = True
            if self.config.errorReturn.find("ErrorMessage") == -1:
                errortxt = ""
            if error and (self.config.errorReturn.find("Readout") > -1):
                if len(errortxt):
                    errortxt = errortxt + "\t" + str(akt_zaehlerstand)
                else:
                    errortxt = str(akt_zaehlerstand)
        return (error, errortxt)

    def _analogReadoutToValue(self, res_analog):
        prev = -1
        erg = ""
        for item in res_analog[::-1]:
            prev = self._evaluateValue(item, prev)
            erg = str(int(prev)) + erg
        return erg

    def _evaluateValue(self, newValue, prevValue):
        result_decimal = math.floor((newValue * 10) % 10)
        result_integer = math.floor(newValue % 10)

        if prevValue == -1:
            result = result_integer
        else:
            result_rating = result_decimal - prevValue
            if result_decimal >= 5:
                result_rating -= 5
            else:
                result_rating += 5
            result = round(newValue)
            if result_rating < 0:
                result -= 1
            if result == -1:
                result += 10

        result = result % 10
        return result

    def _digitalReadoutToValue(
        self, res_digital, usePreValue, lastnachkomma, aktnachkomma
    ):
        erg = ""
        if (
            usePreValue
            and str(self.lastIntegerValue) != ""
            and str(self.lastDecimalValue) != ""
        ):
            last = int(str(lastnachkomma)[:1])
            aktu = int(str(aktnachkomma)[:1])
            overZero = 1 if aktu < last else 0
        else:
            usePreValue = False

        for i in range(len(res_digital) - 1, -1, -1):
            item = res_digital[i]
            if item == "NaN":
                if usePreValue:
                    item = int(self.lastIntegerValue[i])
                    if overZero:
                        item += 1
                        if item == 10:
                            item = 0
                            overZero = 1
                        else:
                            overZero = 0
                else:
                    item = "N"
            erg = str(item) + erg

        return erg

    def _removeFile(self, filename):
        if os.path.exists(filename):
            os.remove(filename)
