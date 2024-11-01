from configuration import Config, ConfigurationMissing
from data_classes import ImagePosition, MeterConfig, RefImage


def test_config():
    config = Config().load_from_file("config/config.ini")

    assert config.log_level == "INFO"
    assert config.image_tmp_dir == "/image_tmp"
    assert config.config_dir == "/config"
    assert config.digital_models_dir == "/config/neuralnets/digital"
    assert config.analog_models_dir == "/config/neuralnets/analog"
    assert config.prevoius_value_file == "/config/prevalue.ini"

    assert config.image_source.url == "file:///config/original.jpg"
    assert config.image_source.timeout == 10
    assert config.image_source.min_size == 20000

    assert config.alignment.rotate_angle == 180
    assert config.alignment.post_rotate_angle == 0
    assert config.alignment.ref_images == [
        RefImage(
            name="ref0",
            x=99,
            y=219,
            w=0,
            h=0,
            file_name="/config/Ref_ZR_x99_y219.jpg",
        ),
        RefImage(
            name="ref1",
            x=512,
            y=117,
            w=0,
            h=0,
            file_name="/config/Ref_m3_x512_y117.jpg",
        ),
        RefImage(
            name="ref2",
            x=301,
            y=386,
            w=0,
            h=0,
            file_name="/config/Ref_x0_x301_y386.jpg",
        ),
    ]

    assert config.crop.enabled is False
    assert config.crop.x == 100
    assert config.crop.y == 200
    assert config.crop.w == 300
    assert config.crop.h == 400

    assert config.resize.enabled is False
    assert config.resize.w == 640
    assert config.resize.h == 480

    assert config.image_processing.enabled is False
    assert config.image_processing.contrast == 1.0
    assert config.image_processing.brightness == 1.0
    assert config.image_processing.sharpness == 1.0
    assert config.image_processing.color == 1.0
    assert config.image_processing.grayscale is False
    assert config.image_processing.autocontrast.enabled is False
    assert config.image_processing.autocontrast.cutoff_low == 2.0
    assert config.image_processing.autocontrast.cutoff_high == 45
    assert config.image_processing.autocontrast.ignore is None
    assert config.image_processing.autocontrast_cut_images.enabled is False
    assert config.image_processing.autocontrast_cut_images.cutoff_low == 2.0
    assert config.image_processing.autocontrast_cut_images.cutoff_high == 45
    assert config.image_processing.autocontrast_cut_images.ignore is None

    assert config.digital_readout.enabled is True
    assert (
        config.digital_readout.model_file
        == "/config/neuralnets/digital/dig-class100_0168_s2_q.tflite"
    )
    assert config.digital_readout.model == "auto"
    assert config.digital_readout.cut_images == [
        ImagePosition(name="digit1", x=215, y=97, w=42, h=75),
        ImagePosition(name="digit2", x=273, y=97, w=42, h=75),
        ImagePosition(name="digit3", x=332, y=97, w=42, h=75),
        ImagePosition(name="digit4", x=390, y=97, w=42, h=75),
        ImagePosition(name="digit5", x=446, y=97, w=42, h=75),
    ]

    assert config.analog_readout.enabled is True
    assert (
        config.analog_readout.model_file
        == "/config/neuralnets/analog/ana-cont_1209_s2.tflite"
    )
    assert config.analog_readout.model == "auto"
    assert config.analog_readout.cut_images == [
        ImagePosition(name="analog1", x=491, y=307, w=115, h=115),
        ImagePosition(name="analog2", x=417, y=395, w=115, h=115),
        ImagePosition(name="analog3", x=303, y=424, w=115, h=115),
        ImagePosition(name="analog4", x=163, y=358, w=115, h=115),
    ]

    assert config.meter_configs == [
        MeterConfig(
            name="digital",
            format="{digit1}{digit2}{digit3}{digit4}{digit5}",
            consistency_enabled=False,
            allow_negative_rates=False,
            max_rate_value=0,
            use_previuos_value=False,
            pre_value_from_file_max_age=0,
            use_extended_resolution=False,
        ),
        MeterConfig(
            name="analog",
            format="{analog1}{analog2}{analog3}{analog4}",
            consistency_enabled=False,
            allow_negative_rates=False,
            max_rate_value=0,
            use_previuos_value=False,
            pre_value_from_file_max_age=0,
            use_extended_resolution=False,
        ),
        MeterConfig(
            name="total",
            format="{digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}"
            "{analog3}{analog4}",
            consistency_enabled=True,
            allow_negative_rates=False,
            max_rate_value=0.2,
            use_previuos_value=True,
            pre_value_from_file_max_age=0,
            use_extended_resolution=True,
        ),
    ]


def test_config_file_missing():
    config = Config()
    try:
        config.load_from_file("config/missing.ini")
    except ConfigurationMissing as e:
        assert str(e) == "Configuration file 'config/missing.ini' not found"
    else:
        assert False


def test_save():
    TEMPFILENAME = "temp-file-for-unit-test.ini"
    try:
        config = Config().load_from_file("tests/unit/resource/config-for-save-test.ini")
        config.save_to_file(TEMPFILENAME)
        config2 = Config().load_from_file(TEMPFILENAME)
        assert config == config2
    finally:
        import os

        os.remove(TEMPFILENAME)
