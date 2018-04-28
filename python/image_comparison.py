
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
        self._image_location = image_a
        self._file_ext = os.path.splitext(image_a)[-1]
        self._compare_results = CompareResults()
        self._diff_buffer = None

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

        if self._compare_results.nfail > 0:
            self._diff_buffer = ImageBuf(self.image_a_buffer.spec())
            ImageBufAlgo.sub(self._diff_buffer, self.image_a_buffer, self.image_b_buffer)
            ImageBufAlgo.abs(self._diff_buffer, self._diff_buffer)
            ImageBufAlgo.color_map(self._diff_buffer, self._diff_buffer, -1, 'inferno')
            remap_buffer = ImageBuf()
            multiplier = 50
            ImageBufAlgo.mul(
                remap_buffer,
                self._diff_buffer,
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
                diff_image_location = os.path.dirname(self._image_location)
            remap_buffer.write(
                '{}/{}_diff{}'.format(
                    diff_image_location,
                    os.path.basename(self._image_location),
                    self._file_ext,
                )
            )
            if raise_exception:
                raise ImageDifferenceError(msg)
            else:
                print(msg)

    def _blur(self, source, size=1.0):
        """Apply gaussian blur to given image

        Args:
            source (ImageBuf): Image buffer which to blur
            size (float): Blur size

        Return:
            ImageBuf: Blurred image
        """
        kernel = ImageBuf(source.spec())
        ImageBufAlgo.make_kernel(
            kernel,
            "gaussian",
            size, size
        )
        blurred = ImageBuf(source.spec())
        ImageBufAlgo.convolve(blurred, source, kernel)

        return blurred

    def blur_images(self, size):
        """Blur test images with given size

        Args:
            size (float): Blur size
        """
        self.image_a_buffer = self._blur(self.image_a_buffer, size)
        self.image_b_buffer = self._blur(self.image_b_buffer, size)


if __name__ == '__main__':

    ic = ImageCompare(
        image_a='../tests/image_a.png',
        image_b='../tests/image_c.png',
    )
    try:
        ic.compare(blur=20)
    except ImageDifferenceError as ide:
        print(ide)


