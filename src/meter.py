import dataclasses
import json
import signal
from lib.Utils.ImageLoader import DownloadFailure
from lib.MeterProcessor import MeterProcessor
import os
import gc
import logging
import sys
from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

VERSION = "8.0.0"
meter = None

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI(title="meter")
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")


@app.get("/", response_class=HTMLResponse)
def get_index(request: Request):
    return templates.TemplateResponse(
        "index.html", context={"request": request, "version": VERSION}
    )


@app.get("/healthcheck", response_class=HTMLResponse)
def healthcheck():
    return "Health - OK"


@app.get("/image_tmp/{image}")
def get_image(image: str):
    logger.info(f"Getting image: {image}")
    return FileResponse(
        f"{image_tmp_dir}/{image}", media_type="image/jpg", filename=image
    )


@app.get("/version", response_class=HTMLResponse)
def get_version():
    return VERSION


@app.get("/exit", response_class=HTMLResponse)
def do_exit():
    os.kill(os.getpid(), signal.SIGTERM)
    return "App will exit in immidiately"


@app.get("/reload", response_class=HTMLResponse)
def reload_config():
    global meter
    del meter
    gc.collect()
    meter = MeterProcessor(  # noqa: F841
        config_file=f"{config_dir}/config.ini",
        prev_value_file=f"{config_dir}/prevalue.ini",
        image_tmp_dir=image_tmp_dir,
    )
    return "Configuration reloaded"


@app.get("/roi", response_class=HTMLResponse)
def get_roi(request: Request, url: str = None, timeout: int = 0):
    try:
        base64image = meter.get_roi_image(url, timeout)
        return templates.TemplateResponse(
            "roi.html",
            context={"request": request, "data": base64image},
        )
    except DownloadFailure as e:
        return f"Error: {e}"


@app.get("/setPreviousValue", response_class=HTMLResponse)
def set_previous_value(value: float):
    result = meter.setPreviousValue(value)
    return f"Last value set to: {result}"


@app.get("/meters")
def get_meters(
    request: Request,
    format: str = "html",
    url: str = None,
    timeout: int = 0,
):
    if format not in ["html", "json"]:
        return Response("Invalid format. Use 'html' or 'json'", media_type="text/html")

    try:
        result = meter.get_meters(
            url=url,
            timeout=timeout,
            save_images=format == "html",
        )
    except Exception as e:
        logger.warning(f"Error occured: {str(e)}")
        if format != "html":
            return Response(
                json.dumps({"error": str(e)}), media_type="application/json"
            )
        return Response(f"Error: {e}", media_type="text/html")

    if format != "html":
        return Response(
            json.dumps(dataclasses.asdict(result)),
            media_type="application/json",
        )
    return templates.TemplateResponse(
        "meters.html",
        context={
            "request": request,
            "result": result,
        },
        media_type="text/html",
    )


if __name__ == "__main__":
    log_level = os.environ.get("LOG_LEVEL")
    if log_level is not None:
        logger.setLevel(log_level)

    logging.getLogger("lib.CNN.CNNBase").setLevel(logger.level)
    logging.getLogger("lib.CNN.AnalogNeedleCNN").setLevel(logger.level)
    logging.getLogger("lib.CNN.DigitalCounterCNN").setLevel(logger.level)
    logging.getLogger("lib.Utils.ImageLoader").setLevel(logger.level)
    logging.getLogger("lib.Utils.ImageProcesor").setLevel(logger.level)
    logging.getLogger("lib.Config").setLevel(logger.level)
    logging.getLogger("lib.MeterProcessor").setLevel(logger.level)
    logging.getLogger("lib.PreviousValueFile").setLevel(logger.level)

    config_dir = os.environ.get("CONFIG_DIR", "/config")
    image_tmp_dir = os.environ.get("IMAGE_TMP", "/image_tmp")
    meter = MeterProcessor(
        config_file=f"{config_dir}/config.ini",
        prev_value_file=f"{config_dir}/prevalue.ini",
        image_tmp_dir=image_tmp_dir,
    )

    port = 3000
    logger.info(f"Meter is serving at port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)