
import os

from OpenImageIO import ImageBufAlgo, ImageBuf, CompareResults


report_msg = """
Failures:       {failures}
Warnings:       {warn}
Average error:  {meanerror}
RMS error:      {rmserror}
PSNR:           {psnr}
"""


class ImageDifferenceError(Exception):
    """Raised if image difference exceeds threshold"""
    pass


class ImageCompare(object):
    """Image comparison using OpenImageIO. It creates a difference image.

    Args:
        image_a (str): File path to image
        image_b (str): File path to image to compare against. The baseline

    Attributes:
        fail_threshold (float): Threshold value for failures
        warn_threshold (float): Threshold value for warnings
        image_a_buffer (ImageBuf): Image buffer
        image_b_buffer (ImageBuf): Image buffer
    """

    def __init__(self, image_a, image_b):
        self.fail_threshold = 0.1
        self.warn_threshold = 0.01

        self.image_a_buffer = ImageBuf()
        self.image_b_buffer = ImageBuf()

        # remove alpha channel from input images
        ImageBufAlgo.channels(
            self.image_a_buffer,
            ImageBuf(image_a),
            ('R', 'G', 'B')
        )
        ImageBufAlgo.channels(
            self.image_b_buffer,
            ImageBuf(image_b),
            ('R', 'G', 'B'),
        )

        # protected
        self._image_a_location = image_a
        self._image_b_location = image_b
        self._file_ext = os.path.splitext(image_a)[-1]
        self._compare_results = CompareResults()

    def compare(self, diff_image_location=None, blur=10, raise_exception=True):
        """Compare the two given images

        Args:
            diff_image_location (str): file path for difference image.
                Written only if there are failures
            blur (float): image blur to apply before comparing
        """
        self.blur_images(blur)
        ImageBufAlgo.compare(
            self.image_a_buffer,
            self.image_b_buffer,
            self.fail_threshold,
            self.warn_threshold,
            self._compare_results,
        )
        diff_buffer = self.create_diff_buffer()
        if self._compare_results.nfail > 0:
            ImageBufAlgo.color_map(diff_buffer, diff_buffer, -1, 'inferno')
            remap_buffer = ImageBuf()
            multiplier = 5
            ImageBufAlgo.mul(
                remap_buffer,
                diff_buffer,
                (multiplier, multiplier, multiplier, 1.0),
            )
            ImageBufAlgo.add(remap_buffer, self.image_a_buffer, remap_buffer)
            msg = report_msg.format(
                failures=self._compare_results.nfail,
                warn=self._compare_results.nwarn,
                meanerror=self._compare_results.meanerror,
                rmserror=self._compare_results.rms_error,
                psnr=self._compare_results.PSNR
            )
            if not diff_image_location:
                diff_image_location = os.path.dirname(self._image_a_location)
            remap_buffer.write(
                '{}/{}-{}_diff{}'.format(
                    diff_image_location,
                    os.path.basename(self._image_a_location),
                    os.path.basename(self._image_b_location),
                    self._file_ext,
                )
            )
            self.image_a_buffer.write(
                '{}/{}_debug{}'.format(
                    diff_image_location,
                    '1_a',
                    self._file_ext,
                )
            )
            self.image_b_buffer.write(
                '{}/{}_debug{}'.format(
                    diff_image_location,
                    '1_b',
                    self._file_ext,
                )
            )
            if raise_exception:
                raise ImageDifferenceError(msg)
            else:
                print(msg)

    def create_diff_buffer(self):
        """Create a difference image buffer from image_a and image_b

        Returns:
            ImageBuf: new difference image buffer
        """
        diff_buffer = ImageBuf(self.image_a_buffer.spec())
        ImageBufAlgo.sub(diff_buffer, self.image_a_buffer, self.image_b_buffer)
        ImageBufAlgo.abs(diff_buffer, diff_buffer)

        return diff_buffer

    def _blur(self, source, size=1.0):
        """Apply gaussian blur to given image

        Args:
            source (ImageBuf): Image buffer which to blur
            size (float): Blur size

        Return:
            ImageBuf: Blurred image
        """
        source = self._open(source)
        kernel = ImageBuf(source.spec())
        ImageBufAlgo.make_kernel(
            kernel,
            "gaussian",
            size, size
        )
        blurred = ImageBuf(source.spec())
        ImageBufAlgo.convolve(blurred, source, kernel)

        return blurred

    def _dilate(self, source):
        dilate = ImageBuf(source.spec())
        ImageBufAlgo.dilate(
            dilate,
            source,
            4,
            4,
        )
        return dilate

    def _open(self, source, size=3):
        erode = ImageBuf(source.spec())
        ImageBufAlgo.erode(erode, source, size, size)
        dilate = ImageBuf(source.spec())
        ImageBufAlgo.dilate(dilate, erode, size, size)

        return dilate

    def _median(self, source, size=5):
        size = int(size)
        median = ImageBuf(source.spec())
        ImageBufAlgo.median_filter(
            median,
            source,
            size,
            size
        )
        return median

    def blur_images(self, size):
        """Blur test images with given size

        Args:
            size (float): Blur size
        """
        self.image_a_buffer = self._blur(self.image_a_buffer, size)
        self.image_b_buffer = self._blur(self.image_b_buffer, size)


if __name__ == '__main__':

    # ic = ImageCompare(
    #     image_a='../tests/image_a.png',
    #     image_b='../tests/image_c.png',
    # )
    ic = ImageCompare(
        image_a='../tests/test_low_samples.png',
        image_b='../tests/test_high_samples.png',
    )
    try:
        ic.compare(blur=10)
    except ImageDifferenceError as ide:
        print(ide)
    # image = ImageBuf('../tests/image_c.png')
    # median = ImageBuf()
    # ImageBufAlgo.median_filter(median, image, 5)
    # median.write('../tests/median.png')
    # dilated = ImageBuf()
    # ImageBufAlgo.dilate(dilated, image, 4, 4)
    # dilated.write('../tests/dilated.png')
    # erode = ImageBuf()
    # ImageBufAlgo.erode(erode, dilated, 2, 2)
    # erode.write('../tests/erode.png')

