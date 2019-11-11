import os.path
import math

import PartSegData
import numpy as np
import pytest
import tifffile

from PartSegImage import TiffImageReader, Image, CziImageReader, OifImagReader, GenericImageReader
from help_fun import get_test_dir


class TestImageClass:
    def test_tiff_image_read(self):
        image = TiffImageReader.read_image(PartSegData.segmentation_mask_default_image)
        assert isinstance(image, Image)

    def test_czi_file_read(self):
        test_dir = get_test_dir()
        image = CziImageReader.read_image(os.path.join(test_dir, "test_czi.czi"))
        assert image.channels == 4
        assert image.layers == 1

        assert np.all(np.isclose(image.spacing, (7.752248561753867e-08, )*2))

    def test_oib_file_read(self):
        test_dir = get_test_dir()
        image = OifImagReader.read_image(os.path.join(test_dir, "N2A_H2BGFP_dapi_falloidin_cycling1.oib"))
        assert image.channels == 3
        assert image.layers == 6
        assert np.all(np.isclose(image.spacing, (2.1e-07,) + (7.752248561753867e-08, )*2))

    def test_oif_file_read(self):
        test_dir = get_test_dir()
        image = OifImagReader.read_image(os.path.join(test_dir, "Image0003_01.oif"))
        assert image.channels == 1
        assert image.layers == 49
        assert np.all(np.isclose(image.spacing, (3.2e-07,) + (5.1e-08, )*2))

    def test_read_with_mask(self):
        test_dir = get_test_dir()
        image = TiffImageReader.read_image(os.path.join(test_dir, "stack1_components", "stack1_component1.tif"),
                                           os.path.join(test_dir, "stack1_components", "stack1_component1_mask.tif"))
        assert isinstance(image, Image)
        with pytest.raises(ValueError):
            TiffImageReader.read_image(os.path.join(test_dir, "stack1_components", "stack1_component1.tif"),
                                       os.path.join(test_dir, "stack1_components", "stack1_component2_mask.tif"))

    def test_lsm_read(self):
        test_dir = get_test_dir()
        image1 = TiffImageReader.read_image(os.path.join(test_dir, "test_lsm.lsm"))
        image2 = TiffImageReader.read_image(os.path.join(test_dir, "test_lsm.tif"))
        data = np.load(os.path.join(test_dir, "test_lsm.npy"))
        assert np.all(image1.get_data() == data)
        assert np.all(image2.get_data() == data)
        assert np.all(image1.get_data() == image2.get_data())

    def test_ome_read(self):  # error in tifffile
        test_dir = get_test_dir()
        image1 = TiffImageReader.read_image(os.path.join(test_dir, "test_lsm2.tif"))
        image2 = TiffImageReader.read_image(os.path.join(test_dir, "test_lsm.tif"))
        data = np.load(os.path.join(test_dir, "test_lsm.npy"))
        assert np.all(image1.get_data() == data)
        assert np.all(image2.get_data() == data)
        assert np.all(image1.get_data() == image2.get_data())

    def test_generic_reader(self):
        test_dir = get_test_dir()
        GenericImageReader.read_image(os.path.join(test_dir, "stack1_components", "stack1_component1.tif"),
                                os.path.join(test_dir, "stack1_components", "stack1_component1_mask.tif"))
        GenericImageReader.read_image(os.path.join(test_dir, "test_czi.czi"))
        GenericImageReader.read_image(os.path.join(test_dir, "test_lsm2.tif"))
        GenericImageReader.read_image(os.path.join(test_dir, "test_lsm.tif"))
        GenericImageReader.read_image(os.path.join(test_dir, "Image0003_01.oif"))
        GenericImageReader.read_image(os.path.join(test_dir, "N2A_H2BGFP_dapi_falloidin_cycling1.oib"))


def test_xml2dict():
    sample_text = """
    <level1>
        <level2>3.5322</level2>
    </level1>
    """
    data = tifffile.xml2dict(sample_text)
    assert math.isclose(data["level1"]["level2"], 3.5322)