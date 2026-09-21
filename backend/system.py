import psutil

from .models import SystemStats


class SystemFunction:
    """Collect operating-system and Raspberry Pi hardware statistics."""

    def get_stats(self) -> SystemStats:
        """Return normalized CPU, memory, disk, battery, and temperature values."""
        disk = psutil.disk_usage("/")
        battery = psutil.sensors_battery()
        temperature_celsius = self._get_temperature()
        return SystemStats(
            cpu_percent=psutil.cpu_percent(interval=None) / 100,
            memory_percent=psutil.virtual_memory().percent / 100,
            disk_percent=disk.percent / 100,
            battery_percent=battery.percent / 100 if battery else 1.0,
            temperature_celsius=temperature_celsius,
        )

    def _get_temperature(self) -> float:
        """Return the first available sensor temperature, or zero when absent."""
        temperatures = psutil.sensors_temperatures()
        for entries in temperatures.values():
            if entries:
                return float(entries[0].current)
        return 0.0
