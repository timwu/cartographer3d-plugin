from __future__ import annotations

import csv
import logging
import time
from typing import TYPE_CHECKING, final

from typing_extensions import override

from cartographer.interfaces.printer import Macro, MacroParams, Mcu
from cartographer.probe.touch_mode import TouchMode

if TYPE_CHECKING:
    from cartographer.interfaces.printer import Toolhead


logger = logging.getLogger(__name__)


@final
class TouchDebugMacro(Macro):
    description = "Run a touch probe and record frequency data for debugging"

    def __init__(
        self,
        touch_mode: TouchMode,
        mcu: Mcu,
        toolhead: Toolhead,
    ) -> None:
        self._touch_mode = touch_mode
        self._mcu = mcu
        self._toolhead = toolhead

    @override
    def run(self, params: MacroParams) -> None:
        output_path = "/tmp/cartographer_touch_debug.csv"
        
        # Ensure Z is homed
        if not self._toolhead.is_homed("z"):
             raise RuntimeError("Z axis must be homed before running touch debug")

        logger.info("Starting touch debug sequence...")
        
        # Start streaming session
        session = self._mcu.start_session()
        self._mcu.start_streaming()
        
        try:
            # Perform the probe
            # We use the existing touch mode configuration
            logger.info("Probing...")
            result = self._touch_mode.perform_probe()
            logger.info("Probe result: %.6f", result)
            
            # Wait a bit to capture post-trigger data
            time.sleep(0.5)
            
        finally:
            self._mcu.stop_streaming()
            
        # Collect data
        samples = session.get_items()
        session.stream.end_session(session)
        
        if not samples:
            logger.warning("No samples collected during touch debug!")
            return

        logger.info("Collected %d samples. Writing to %s...", len(samples), output_path)
        
        try:
            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "Frequency", "Temperature", "X", "Y", "Z"])
                
                for sample in samples:
                    writer.writerow([
                        sample.time,
                        sample.frequency,
                        sample.temperature,
                        sample.position.x if sample.position else "",
                        sample.position.y if sample.position else "",
                        sample.position.z if sample.position else "",
                    ])
            
            logger.info("Successfully wrote debug data to %s", output_path)
            logger.info("You can plot this data to analyze the frequency change during touch.")
            
        except Exception as e:
            logger.error("Failed to write debug file: %s", e)
