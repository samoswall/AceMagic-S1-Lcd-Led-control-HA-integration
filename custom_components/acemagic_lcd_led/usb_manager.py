"""USB manager for display device using pyusb."""

import asyncio
import logging
import usb1
from typing import Optional
import time

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

# Vendor ID and Product ID
VID = 0x04d9
PID = 0xfd01

class USBManager:
    """Manage USB communication with display."""
    
    def __init__(self):
        """Initialize USB manager."""
        self._context = None
        self._device = None
        self._connected = False
#        self._lock = asyncio.Lock()
        
    async def connect(self) -> bool:
        """Connect to USB device."""
        try:
            self._context = usb1.USBContext()
            self._device = self._context.openByVendorIDAndProductID(VID, PID)
            
            if not self._device:
                return False
            
            self._device.claimInterface(1)
            self._connected = True
            _LOGGER.info("USB device connected")
            return True
            
        except Exception as err:
            _LOGGER.error("Failed to connect to USB device: %s", err)
            self._connected = False
            return False
    
    async def send_packet(self, data: bytes) -> bool:
        """Send packet to USB device."""
        if not self._connected or not self._device:
            return False
        
        try:
            self._device.interruptWrite(0x02, data)
            _LOGGER.debug("Packed send: %s ...", data[0:10].hex())
            return True
        except Exception as err:
            _LOGGER.error("Failed to send USB packet: %s", err)
            self._connected = False
            return False
    
    async def send_orientation_packet(self, orientation: int) -> bool:
        """Send orientation packet: [0x55, 0xa1, 0xf1, ориентация, 0x00, 0x00, 0x00, 0x00]"""
        header = bytes([ 0x55, 0xa1, 0xf1, orientation, 0x00, 0x00, 0x00, 0x00 ])
        packet = bytearray(8 + 4096)
        packet[0:8] = header
        success = await self.send_packet(packet)
        return success
    
    async def send_keepalive_packet(self) -> bool:
        """Send keepalive packet: [0x55, 0xa1, 0xf2, 0x00, 0x00, 0x00, 0x00, 0x00]"""
        header = bytes([ 0x55, 0xa1, 0xf2, 0x00, 0x00, 0x00, 0x00, 0x00 ])
        packet = bytearray(8 + 4096)
        packet[0:8] = header
        success = await self.send_packet(packet)
        if success:
            _LOGGER.debug("Keepalive packet sent")
        return success
    
    async def send_image_packet(self, image_data: bytes) -> bool:
        """Send image packet in chunks."""
        if not self._connected or not self._device:
            return False
        
        try:
            data_len = len(image_data)
            chunk_size = 4096
            num_chunk = (-(-data_len // chunk_size )) - 1
            
            for i in range(0, data_len, chunk_size):
                chunk = image_data[i:i+chunk_size]
                # Prepare packet header
                header = [0x55, 0xa3, 0xF0, 0x01, 0x00, 0x00, 0x00, 0x10]
                
                if i == 0: 
                    header[2] = 0xF0  # First chunk
                elif i == num_chunk * chunk_size:
                    header[2] = 0xF2  # Last chunk
                else:
                    header[2] = 0xF1  # Middle chunk
                
                # Update header
                header[3] = (i // chunk_size) + 1  # Chunk number
                header[5] = ((i // chunk_size) % 16) * 0x10  # Some counter
#                if header[5] > 0xF0: 
#                    header[5] = 0x00
                
                # Prepare full packet (header + chunk)
                packet = bytearray(8 + chunk_size)
                packet[0:8] = header
                packet[8:8+len(chunk)] = chunk
                
                # Send packet
                success = await self.send_packet(bytes(packet))
                if not success:
                    return False
                
#                await asyncio.sleep(0.01)  # Small delay between chunks
            
            _LOGGER.debug("Image packet sent: %d bytes in %d chunks", 
                        data_len, (data_len + chunk_size - 1) // chunk_size)
            return True
            
        except Exception as err:
            _LOGGER.error("Failed to send image packet: %s", err)
            return False
    
    async def disconnect(self):
        """Disconnect from USB device."""
        if self._device:
            try:
                self._device.releaseInterface(1)
                self._device.close()
            except Exception:
                pass
        
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
        
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if USB device is connected."""
        return self._connected