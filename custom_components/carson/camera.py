"""This component provides support to the Ring Door Bell camera."""
from datetime import timedelta
import logging
import io
from PIL import Image

from homeassistant.components.camera import SUPPORT_STREAM, Camera
from homeassistant.const import ATTR_ATTRIBUTION

from .const import (
    ATTRIBUTION,
    CONF_LIST_FROM_EAGLE_EYE,
    DEFAULT_CONF_LIST_FROM_EAGLE_EYE,
    DOMAIN,
)
from .entity import CarsonEntityMixin

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Create the Cameras for the Carson devices."""
    _LOGGER.debug("Setting up Carson Camera entries")
    carson = hass.data[DOMAIN][config_entry.entry_id]["api"]
    if get_list_een_option(config_entry):
        cameras = [
            camera for b in carson.buildings for camera in b.eagleeye_api.cameras
        ]
    else:
        cameras = [camera for b in carson.buildings for camera in b.cameras]

    async_add_entities(EagleEyeCamera(config_entry.entry_id, cam, hass) for cam in cameras)


def get_list_een_option(config_entry):
    """Return config option load cameras from EEN vs Carson."""
    return config_entry.options.get(
        CONF_LIST_FROM_EAGLE_EYE, DEFAULT_CONF_LIST_FROM_EAGLE_EYE
    )


class EagleEyeCamera(CarsonEntityMixin, Camera):
    """An implementation of a Eagle Eye camera."""

    def __init__(self, config_entry_id, ee_camera, hass):
        """Initialize the lock."""
        super().__init__(config_entry_id, ee_camera)
        self._ee_camera = ee_camera
        self._hass = hass
        self._use_rtsp = False
        self._rtsp_url = None

    @property
    def name(self):
        """Return the name of this camera."""
        return self._ee_camera.name

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "account_id": self._ee_camera.account_id,
            "guid": self._ee_camera.guid,
            "tags": self._ee_camera.tags,
            "utc_offset": self._ee_camera.utc_offset,
            "timezone": self._ee_camera.timezone,
        }

    def enable_rtsp(self):
        """Enable RTSP streaming."""
        self._use_rtsp = True

    def disable_rtsp(self):
        """Disable RTSP and revert to the original streaming method."""
        self._use_rtsp = False

    def camera_image(self, width=None, height=None):
        """Return bytes of camera image."""
        if not self._use_rtsp:
            _LOGGER.debug("Getting live camera image for %s", self.name)
            buffer = io.BytesIO()
            self._ee_camera.get_image(buffer)
            image = Image.open(buffer)
            if width is not None:
                # Calculate the new height to maintain the aspect ratio
                height = int(image.height * width / image.width)
                image = image.resize((width, height))
            new_buffer = io.BytesIO()
            image.save(new_buffer, format='JPEG')
            return new_buffer.getvalue()
        # Add logic for RTSP here if needed

    async def stream_source(self):
        """Return the stream source."""
        if self._use_rtsp:
            return self._rtsp_url
        return await self._hass.async_add_executor_job(self._ee_camera.get_video_url, timedelta(minutes=30))

    def update_rtsp_url(self, url):
        """Update the RTSP URL."""
        self._rtsp_url = url

    @property
    def supported_features(self):
        """Return supported features."""
        return SUPPORT_STREAM

    async def stream_source(self):
        """Return the stream source."""
        _LOGGER.debug("Getting live camera video stream for %s", self.name)
        return await self._hass.async_add_executor_job(self._ee_camera.get_video_url, timedelta(minutes=30))

    def turn_off(self):
        """Turn off camera."""
        raise NotImplementedError("Eagle Eye cannot be turned off")

    def turn_on(self):
        """Turn off camera."""
        raise NotImplementedError("Eagle Eye is always on")

    def enable_motion_detection(self):
        """Enable motion detection in the camera."""
        raise NotImplementedError("Eagle Eye does not support motion detection")

    def disable_motion_detection(self):
        """Disable motion detection in camera."""
        raise NotImplementedError("Eagle Eye does not support motion detection")
