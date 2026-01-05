"""Config flow for UART Time Sender integration."""

from __future__ import annotations

import asyncio
import logging
import serial
import serial.tools.list_ports
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, DEFAULT_BAUDRATE, DEFAULT_NAME, VID_04D9, PID_FD01, DEVICE_NAME

_LOGGER = logging.getLogger(__name__)


def get_available_ports() -> list[str]:
    """Get list of available serial ports."""
    ports = serial.tools.list_ports.comports()
    port_list = []
    
    for port in ports:
        # Filter by VID and PID if specified
        if hasattr(port, 'vid') and hasattr(port, 'pid'):
            if port.vid and port.pid:
                vid_hex = f"{port.vid:04x}"
                pid_hex = f"{port.pid:04x}"
                # Check if it matches our specific device
                if vid_hex == VID_04D9 and pid_hex == PID_FD01:
                    port_list.append(f"{port.device} (CH340 {vid_hex}:{pid_hex})")
                else:
                    port_list.append(f"{port.device} ({vid_hex}:{pid_hex})")
            else:
                port_list.append(port.device)
        else:
            port_list.append(port.device)
    
    return port_list


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    # Clean up port string (remove description if present)
    port = data["port"].split(" ")[0]
    
    # Try to open the serial port
    try:
        ser = serial.Serial(
            port=port,  # Use cleaned port
            baudrate=9600,
            timeout=1
        )
        ser.close()
    except serial.SerialException as err:
        _LOGGER.error("Failed to open serial port %s: %s", port, err)
        raise CannotConnect(f"Cannot connect to {port}: {err}")
    except Exception as err:
        _LOGGER.error("Unexpected error: %s", err)
        raise CannotConnect(f"Unexpected error: {err}")
    
    return {"title": f"{DEVICE_NAME} - {port}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UART Time Sender."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                return self.async_create_entry(
                    title=info["title"], 
                    data=user_input
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Get available ports
        ports = await self.hass.async_add_executor_job(get_available_ports)
        
        if not ports:
            ports = ["No serial ports found"]

        schema = vol.Schema({
            vol.Required("port"): vol.In(ports),
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=schema, 
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for UART Time Sender."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            # Validate the port
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        # Get available ports
        ports = await self.hass.async_add_executor_job(get_available_ports)
        
        if not ports:
            ports = ["No serial ports found"]

        schema = vol.Schema({
            vol.Required(
                "port",
                default=self.config_entry.options.get("port", self.config_entry.data.get("port"))
            ): vol.In(ports),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""