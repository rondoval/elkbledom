from __future__ import annotations

import logging
import voluptuous as vol
from typing import Any, Optional, Tuple

from .elkbledom import BLEDOMInstance
from .const import DOMAIN, EFFECTS, EFFECTS_list

from homeassistant.const import CONF_MAC
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.light import (
    PLATFORM_SCHEMA,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ATTR_WHITE,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.util.color import (match_max_scale)
from homeassistant.helpers import device_registry

PARALLEL_UPDATES = 0  # fix entity_platform parallel_updates Semaphore

LOGGER = logging.getLogger(__name__)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MAC): cv.string
})

async def async_setup_entry(hass, config_entry, async_add_devices):
    instance = hass.data[DOMAIN][config_entry.entry_id]
    await instance.update()
    async_add_devices([BLEDOMLight(instance, config_entry.data["name"], config_entry.entry_id)])

class BLEDOMLight(LightEntity):
    def __init__(self, bledomInstance: BLEDOMInstance, name: str, entry_id: str) -> None:
        self._instance = bledomInstance
        self._entry_id = entry_id
        self._attr_supported_color_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP, ColorMode.WHITE}
        self._attr_supported_features = LightEntityFeature.EFFECT
        self._attr_color_mode = ColorMode.WHITE
        self._attr_name = name
        self._attr_effect = None
        self._attr_unique_id = self._instance.address

    @property
    def available(self):
        return self._instance.is_on != None

    @property
    def brightness(self):
        return self._instance.brightness

    @property
    def is_on(self) -> Optional[bool]:
        return self._instance.is_on

    @property
    def color_temp_kelvin(self):
        return self._instance.color_temp_kelvin
    
    @property
    def max_color_temp_kelvin(self):
        return self._instance.max_color_temp_kelvin

    @property
    def min_color_temp_kelvin(self):
        return self._instance.min_color_temp_kelvin

    @property
    def effect_list(self):
        return EFFECTS_list

    @property
    def rgb_color(self):
        if self._instance.rgb_color:
            return self._instance.rgb_color
        return None

    @property
    def device_info(self):
        """Return device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._instance.address)
            },
            name=self.name,
            connections={(device_registry.CONNECTION_NETWORK_MAC, self._instance.address)},
        )

    @property
    def should_poll(self):
        """No polling needed for a demo light."""
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        LOGGER.debug(f"Params turn on: {kwargs} color mode: {self._attr_color_mode}")
        if not self.is_on:
            await self._instance.turn_on()
            if self._instance.reset:
                LOGGER.debug("Change color to white to reset led strip when other infrared control interact")
                self._attr_color_mode = ColorMode.WHITE
                self._attr_effect = None
                await self._instance.set_color((255, 255, 255))
                await self._instance.set_brightness(255)

        if ATTR_BRIGHTNESS in kwargs and kwargs[ATTR_BRIGHTNESS] != self.brightness:
            await self._instance.set_brightness(kwargs[ATTR_BRIGHTNESS])

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._attr_effect = None
            await self._instance.set_color_temp_kelvin(kwargs[ATTR_COLOR_TEMP_KELVIN], None)

        if ATTR_WHITE in kwargs:
            self._attr_color_mode = ColorMode.WHITE
            await self._instance.set_color((255, 255, 255))
            self._attr_effect = None
            await self._instance.set_brightness(kwargs[ATTR_WHITE])

        if ATTR_RGB_COLOR in kwargs:
            self._attr_color_mode = ColorMode.RGB
            self._attr_effect = None
            await self._instance.set_color(kwargs[ATTR_RGB_COLOR])

        if ATTR_EFFECT in kwargs:
            self._attr_effect = kwargs[ATTR_EFFECT]
            await self._instance.set_effect(EFFECTS[kwargs[ATTR_EFFECT]].value)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        LOGGER.debug(f"Params turn off: {kwargs} color mode: {self._attr_color_mode}")
        await self._instance.turn_off()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        await self._instance.update()
        self.async_write_ha_state()
